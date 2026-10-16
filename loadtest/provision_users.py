#!/usr/bin/env python3
"""Provision an isolated CityPulse load-test society and deterministic residents.

This script creates real test records through the API. Run it ONLY against a
staging backend connected to a disposable/dedicated MongoDB database.
"""
from __future__ import annotations

import concurrent.futures
import json
import os
import secrets
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

API_TIMEOUT = 45
BYPASS_SECRET = os.environ.get('VERCEL_AUTOMATION_BYPASS_SECRET', '').strip()
PROTECTED_HOSTS = {
    "backend-nitin-fa90.vercel.app",
    "backend-git-main-nitin-fa90.vercel.app",
}


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"Missing required environment variable: {name}")
    return value


def request_json(base_url: str, method: str, path: str, payload=None):
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    headers = {"Accept": "application/json"}
    if BYPASS_SECRET:
        headers["x-vercel-protection-bypass"] = BYPASS_SECRET
    if body is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api" + path,
        data=body,
        headers=headers,
        method=method,
    )
    try:
        with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
            text = response.read().decode("utf-8", errors="replace")
            return response.status, json.loads(text) if text else {}
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        try:
            body = json.loads(text)
        except json.JSONDecodeError:
            body = {"detail": text[:500]}
        return exc.code, body
    except Exception as exc:
        return 0, {"detail": f"{type(exc).__name__}: {exc}"}


def main() -> int:
    base_url = require_env("BASE_URL").rstrip("/")
    confirmation = require_env("CITYPULSE_LOADTEST_CONFIRM")
    count = int(require_env("LOADTEST_USER_COUNT"))
    workers = int(os.environ.get("LOADTEST_PROVISION_WORKERS", "8"))

    if confirmation != "YES_I_AM_USING_A_DEDICATED_TEST_DATABASE":
        raise SystemExit(
            "Refusing to create test data. Set CITYPULSE_LOADTEST_CONFIRM="
            "YES_I_AM_USING_A_DEDICATED_TEST_DATABASE only after verifying "
            "that this backend uses a dedicated, disposable test database."
        )
    if not 1 <= count <= 10000:
        raise SystemExit("LOADTEST_USER_COUNT must be between 1 and 10000.")
    if not 1 <= workers <= 30:
        raise SystemExit("LOADTEST_PROVISION_WORKERS must be between 1 and 30.")

    parsed = urllib.parse.urlparse(base_url)
    if parsed.scheme != "https" and parsed.hostname not in {"localhost", "127.0.0.1"}:
        raise SystemExit("BASE_URL must use HTTPS (localhost is allowed for local tests).")
    if (parsed.hostname or "").lower() in PROTECTED_HOSTS:
        raise SystemExit("Refusing to target a known stable production backend alias.")

    project_dir = Path(__file__).resolve().parent
    output_file = project_dir / "users.json"
    if output_file.exists():
        raise SystemExit(
            f"{output_file} already exists. Move it aside or delete it before "
            "provisioning a new test society. It contains credentials."
        )

    health_status, health = request_json(base_url, "GET", "/health")
    if health_status != 200 or health.get("status") != "ok":
        raise SystemExit(
            f"Backend health check failed (HTTP {health_status}): "
            f"{health.get('detail', health)}. Check MONGO_URL and DB_NAME "
            "in the staging environment before provisioning."
        )

    run_id = f"{int(time.time())}-{secrets.token_hex(3)}"
    password = "CP-LoadTest-" + secrets.token_urlsafe(18)
    society_payload = {
        "name": f"CityPulse Load Test {run_id}",
        "location": "Load Test District",
        "address": f"Dedicated test site, run {run_id}",
        "population": max(count, 1),
        "latitude": 28.4595,
        "longitude": 77.0266,
        "admin_name": "Load Test Administrator",
        "admin_email": f"load-admin-{run_id}@example.com",
        "admin_capacity": 12,
        "admin_ratio": 1000,
    }
    status, society = request_json(base_url, "POST", "/societies", society_payload)
    if status != 201:
        raise SystemExit(
            f"Could not create test society (HTTP {status}): "
            f"{society.get('detail', society)}"
        )

    credentials = society.get("credentials") or {}
    code = credentials.get("society_code")
    owner_user = credentials.get("username")
    owner_password = credentials.get("password")
    if not all([code, owner_user, owner_password]):
        raise SystemExit("Society creation did not return administrator credentials.")

    print(f"Staging health check passed. Creating {count:,} synthetic resident accounts.")
    print(f"Provisioning concurrency: {workers}. No credential values will be printed.")

    failures = []
    completed = 0

    def create_resident(index: int):
        username = f"loadresident{index:05d}"
        payload = {
            "society_code": code,
            "username": username,
            "password": password,
            "name": f"Load Resident {index:05d}",
            "email": f"loadresident{index:05d}@example.com",
            "area": f"Load Zone {(index % 12) + 1}",
        }
        status_code, result = request_json(base_url, "POST", "/auth/register", payload)
        if status_code == 201:
            return index, True, ""
        # Recover from a timed-out response that actually created the account.
        if status_code in {0, 409}:
            login_status, login_result = request_json(
                base_url,
                "POST",
                "/auth/login",
                {"society_code": code, "username": username, "password": password},
            )
            if login_status == 200:
                return index, True, ""
            result = login_result
            status_code = login_status
        detail = result.get("detail", "Unknown API error")
        return index, False, f"resident {index:05d}: HTTP {status_code}: {detail}"

    started = time.monotonic()
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(create_resident, n) for n in range(1, count + 1)]
        for future in concurrent.futures.as_completed(futures):
            index, okay, message = future.result()
            if okay:
                completed += 1
            else:
                failures.append(message)
            if completed and completed % 250 == 0:
                print(f"Provisioned {completed:,}/{count:,} residents...")
            if len(failures) >= 25:
                for pending in futures:
                    pending.cancel()
                break

    elapsed = time.monotonic() - started
    if failures or completed != count:
        print(f"Provisioning incomplete: {completed:,}/{count:,} in {elapsed:.1f}s.")
        for message in failures[:25]:
            print(f"  - {message}")
        print("Fix the underlying error, then remove the partial test society/database before retrying.")
        return 2

    metadata = {
        "base_url": base_url,
        "society_code": code,
        "resident_count": count,
        "resident_password": password,
        "admin": {"username": owner_user, "password": owner_password},
        "run_id": run_id,
        "provisioned_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "warning": "Synthetic credentials. Store locally; never commit or share this file.",
    }
    temporary = output_file.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    try:
        os.chmod(temporary, 0o600)
    except OSError:
        pass
    temporary.replace(output_file)
    print(f"Provisioning complete: {completed:,} residents in {elapsed:.1f}s.")
    print(f"Private test metadata saved to {output_file}.")
    print("The next step is the staged k6 load test, starting with 100 VUs.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        raise SystemExit(f"Invalid numeric environment variable: {exc}")
