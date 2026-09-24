"""CityPulse API regression tests: auth, tenancy, permissions, and core workflows."""

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import requests
from dotenv import dotenv_values


def _base_url() -> str:
    frontend_env = dotenv_values("/app/frontend/.env")
    url = os.environ.get("REACT_APP_BACKEND_URL") or frontend_env.get("REACT_APP_BACKEND_URL")
    assert url, "REACT_APP_BACKEND_URL is required for public endpoint testing"
    return url.rstrip("/")


BASE_URL = _base_url()
API = f"{BASE_URL}/api"


@pytest.fixture(scope="session")
def api_client():
    session = requests.Session()
    session.headers.update({"Accept": "application/json"})
    return session


def _iso_past(minutes: int = 10) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _create_society(api_client, suffix: str):
    payload = {
        "name": f"TEST CityPulse {suffix}",
        "location": f"TEST Sector {suffix}",
        "address": f"TEST Address {suffix}, City", "population": 1200,
        "latitude": 28.4595,
        "longitude": 77.0266,
        "admin_name": f"Owner {suffix}",
        "admin_email": f"owner.{suffix.lower()}@example.com",
        "admin_capacity": 4,
        "admin_ratio": 300,
    }
    res = api_client.post(f"{API}/societies", json=payload, timeout=30)
    assert res.status_code == 201, res.text
    data = res.json()
    assert data["user"]["role"] == "initial_admin"
    assert data["user"]["email"] == payload["admin_email"]
    assert data["credentials"]["society_code"]
    assert data["credentials"]["username"]
    assert data["credentials"]["password"]
    return data


def _login(api_client, society_code: str, username: str, password: str):
    res = api_client.post(
        f"{API}/auth/login",
        json={"society_code": society_code, "username": username, "password": password},
        timeout=30,
    )
    assert res.status_code == 200, res.text
    data = res.json()
    assert isinstance(data.get("token"), str) and len(data["token"]) > 12
    assert data["user"]["username"] == username.lower()
    return data


def _auth_headers(token: str):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def societies(api_client):
    stamp = str(int(time.time()))
    a = _create_society(api_client, f"A{stamp}")
    b = _create_society(api_client, f"B{stamp}")

    resident_a_payload = {
        "society_code": a["credentials"]["society_code"],
        "username": f"resident.a{stamp}",
        "password": "StrongPass!2026",
        "name": "Resident A",
        "area": "Block A",
    }
    reg_a = api_client.post(f"{API}/auth/register", json=resident_a_payload, timeout=30)
    assert reg_a.status_code == 201, reg_a.text

    resident_b_payload = {
        "society_code": b["credentials"]["society_code"],
        "username": f"resident.b{stamp}",
        "password": "StrongPass!2026",
        "name": "Resident B",
        "area": "Block B",
    }
    reg_b = api_client.post(f"{API}/auth/register", json=resident_b_payload, timeout=30)
    assert reg_b.status_code == 201, reg_b.text

    owner_a_login = _login(
        api_client,
        a["credentials"]["society_code"],
        a["credentials"]["username"],
        a["credentials"]["password"],
    )
    owner_b_login = _login(
        api_client,
        b["credentials"]["society_code"],
        b["credentials"]["username"],
        b["credentials"]["password"],
    )
    resident_a_login = _login(api_client, resident_a_payload["society_code"], resident_a_payload["username"], resident_a_payload["password"])
    resident_b_login = _login(api_client, resident_b_payload["society_code"], resident_b_payload["username"], resident_b_payload["password"])

    return {
        "a": a,
        "b": b,
        "owner_a": owner_a_login,
        "owner_b": owner_b_login,
        "resident_a": resident_a_login,
        "resident_b": resident_b_login,
        "resident_a_payload": resident_a_payload,
    }


# Health and basic auth module
def test_health_public(api_client):
    res = api_client.get(f"{API}/health", timeout=20)
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["civic_data"] == "simulated"


def test_anonymous_denied_on_protected_endpoint(api_client):
    res = api_client.get(f"{API}/overview", timeout=20)
    assert res.status_code == 401
    assert "sign in" in res.json()["detail"].lower()


def test_demo_login_and_me_does_not_leak_sensitive_fields(api_client):
    demo = api_client.get(f"{API}/auth/demo", timeout=20)
    assert demo.status_code == 200
    demo_data = demo.json()
    login = api_client.post(
        f"{API}/auth/login",
        json={"society_code": demo_data["society_code"], "username": "elena", "password": demo_data["password"]},
        timeout=30,
    )
    assert login.status_code == 200
    token = login.json()["token"]
    me = api_client.get(f"{API}/auth/me", headers=_auth_headers(token), timeout=20)
    assert me.status_code == 200
    body = me.json()
    assert "password_hash" not in str(body)
    assert "token_hash" not in str(body)
    assert body["user"]["username"] == "elena"


# Society creation and registration module
def test_register_duplicate_and_password_policy(api_client, societies):
    duplicate = api_client.post(f"{API}/auth/register", json=societies["resident_a_payload"], timeout=20)
    assert duplicate.status_code == 409
    assert "already taken" in duplicate.json()["detail"].lower()

    weak_payload = {
        "society_code": societies["a"]["credentials"]["society_code"],
        "username": "shortpw.user",
        "password": "12345",
        "name": "Weak User",
        "area": "Block C",
    }
    weak = api_client.post(f"{API}/auth/register", json=weak_payload, timeout=20)
    assert weak.status_code == 422
    assert "at least 8 characters" in weak.text.lower()


def test_registration_off_blocks_new_resident(api_client, societies):
    owner_token = societies["owner_a"]["token"]
    me = api_client.get(f"{API}/auth/me", headers=_auth_headers(owner_token), timeout=20)
    settings = me.json()["society"]["settings"]
    society = me.json()["society"]

    payload = {
        "name": society["name"],
        "location": society["location"],
        "address": society["address"],
        "population": society["population"],
        "latitude": society["latitude"],
        "longitude": society["longitude"],
        "admin_capacity": settings["admin_capacity"],
        "admin_ratio": settings["admin_ratio"],
        "registration_open": False,
        "votes_per_point": settings["votes_per_point"],
        "verified_report_points": settings["verified_report_points"],
        "confirmation_points": settings["confirmation_points"],
        "evidence_points": settings["evidence_points"],
        "categories": settings["categories"],
        "statuses": settings["statuses"],
    }
    updated = api_client.patch(f"{API}/society/settings", json=payload, headers=_auth_headers(owner_token), timeout=30)
    assert updated.status_code == 200, updated.text

    blocked_payload = {
        "society_code": societies["a"]["credentials"]["society_code"],
        "username": f"blocked-{int(time.time())}",
        "password": "StrongPass!2026",
        "name": "Blocked Resident",
        "area": "Block A",
    }
    blocked = api_client.post(f"{API}/auth/register", json=blocked_payload, timeout=20)
    assert blocked.status_code == 403
    assert "registration" in blocked.json()["detail"].lower()


# Authorization and tenancy module
def test_resident_cannot_run_admin_action(api_client, societies):
    resident_token = societies["resident_a"]["token"]

    report = {
        "title": "TEST Road crack near gate",
        "description": "TEST Residents observed a widening road crack near the main gate causing traffic disruption.",
        "category": "Road",
        "location": "TEST Gate A",
        "observed_at": _iso_past(20),
        "duration": "2 hours",
        "affected_area": "Gate A",
        "evidence_ids": [],
    }
    created = api_client.post(f"{API}/problems", json=report, headers=_auth_headers(resident_token), timeout=30)
    assert created.status_code == 201, created.text
    case_id = created.json()["case_id"]

    admin_action = api_client.post(
        f"{API}/admin/cases/{case_id}/action",
        json={"action": "review", "note": ""},
        headers=_auth_headers(resident_token),
        timeout=20,
    )
    assert admin_action.status_code == 403


def test_admin_role_can_manage_cases_but_not_initial_admin_settings(api_client, societies):
    owner_token = societies["owner_a"]["token"]

    add_admin_payload = {
        "name": "TEST Admin One",
        "username": f"admin.one.{int(time.time())}",
        "email": "admin.one@example.com",
        "area": "TEST Zone",
        "categories": ["Road"],
    }
    add_admin = api_client.post(f"{API}/society/admins", json=add_admin_payload, headers=_auth_headers(owner_token), timeout=30)
    assert add_admin.status_code == 201, add_admin.text
    admin_creds = add_admin.json()

    admin_login = _login(
        api_client,
        admin_creds["society_code"],
        admin_creds["username"],
        admin_creds["password"],
    )
    admin_token = admin_login["token"]

    deny_settings = api_client.get(f"{API}/auth/me", headers=_auth_headers(admin_token), timeout=20)
    assert deny_settings.status_code == 200
    s = deny_settings.json()["society"]
    st = s["settings"]
    update_payload = {
        "name": s["name"], "location": s["location"], "address": s["address"], "population": s["population"],
        "latitude": s["latitude"], "longitude": s["longitude"], "admin_capacity": st["admin_capacity"], "admin_ratio": st["admin_ratio"],
        "registration_open": st["registration_open"], "votes_per_point": st["votes_per_point"], "verified_report_points": st["verified_report_points"],
        "confirmation_points": st["confirmation_points"], "evidence_points": st["evidence_points"], "categories": st["categories"], "statuses": st["statuses"],
    }
    forbidden = api_client.patch(f"{API}/society/settings", json=update_payload, headers=_auth_headers(admin_token), timeout=30)
    assert forbidden.status_code == 403


def test_demoted_admin_token_loses_rights_immediately(api_client, societies):
    owner_token = societies["owner_a"]["token"]
    add_admin_payload = {
        "name": "TEST Temp Admin",
        "username": f"temp.admin.{int(time.time())}",
        "email": "temp.admin@example.com",
        "area": "TEST Lane",
        "categories": ["Road"],
    }
    add_admin = api_client.post(f"{API}/society/admins", json=add_admin_payload, headers=_auth_headers(owner_token), timeout=30)
    assert add_admin.status_code == 201
    creds = add_admin.json()
    admin_login = _login(api_client, creds["society_code"], creds["username"], creds["password"])
    demoted_token = admin_login["token"]
    admin_id = admin_login["user"]["id"]

    remove = api_client.delete(f"{API}/society/admins/{admin_id}", headers=_auth_headers(owner_token), timeout=20)
    assert remove.status_code == 200

    using_old_token = api_client.post(
        f"{API}/society/admins",
        json={"name": "X", "username": "x.demoted", "email": "x@example.com", "area": "X", "categories": []},
        headers=_auth_headers(demoted_token),
        timeout=20,
    )
    assert using_old_token.status_code == 403


def test_cross_tenant_case_comment_file_admin_access_returns_404(api_client, societies):
    token_a = societies["resident_a"]["token"]
    token_b = societies["resident_b"]["token"]
    owner_a = societies["owner_a"]["token"]

    create_case = api_client.post(
        f"{API}/problems",
        json={
            "title": "TEST Water pipeline leak",
            "description": "TEST Water leakage observed near service lane and residents report pressure drop.",
            "category": "Water",
            "location": "TEST Service Lane",
            "observed_at": _iso_past(25),
            "duration": "30 minutes",
            "affected_area": "Service lane",
            "evidence_ids": [],
        },
        headers=_auth_headers(token_a),
        timeout=30,
    )
    assert create_case.status_code == 201, create_case.text
    case_id = create_case.json()["case_id"]

    add_comment = api_client.post(
        f"{API}/problems/{case_id}/comments",
        json={"text": "TEST Additional observation from resident."},
        headers=_auth_headers(token_a),
        timeout=20,
    )
    assert add_comment.status_code == 201
    comment_id = add_comment.json()["id"]

    evidence_path = Path("/app/backend/sample_assets/evidence-1.jpg")
    with evidence_path.open("rb") as fh:
        upload = api_client.post(
            f"{API}/files",
            headers=_auth_headers(token_a),
            files={"file": ("evidence-1.jpg", fh, "image/jpeg")},
            timeout=60,
        )
    assert upload.status_code == 201, upload.text
    file_id = upload.json()["id"]

    other_tenant_case = api_client.get(f"{API}/problems/{case_id}", headers=_auth_headers(token_b), timeout=20)
    assert other_tenant_case.status_code == 404

    other_tenant_comment = api_client.post(f"{API}/comments/{comment_id}/helpful", headers=_auth_headers(token_b), timeout=20)
    assert other_tenant_comment.status_code == 404

    other_tenant_file = api_client.get(f"{API}/files/{file_id}", headers=_auth_headers(token_b), timeout=20)
    assert other_tenant_file.status_code == 404

    community = api_client.get(f"{API}/community", headers=_auth_headers(owner_a), timeout=20)
    assert community.status_code == 200
    admin_id = community.json()["admins"][0]["id"]
    other_tenant_admin_reputation = api_client.post(
        f"{API}/community/admins/{admin_id}/feedback",
        headers=_auth_headers(token_b),
        json={"value": 1},
        timeout=20,
    )
    assert other_tenant_admin_reputation.status_code == 404


def test_extra_field_injection_rejected(api_client, societies):
    injection = api_client.post(
        f"{API}/auth/register",
        json={
            "society_code": societies["b"]["credentials"]["society_code"],
            "username": f"inject-{int(time.time())}",
            "password": "StrongPass!2026",
            "name": "Inject",
            "area": "B",
            "role": "initial_admin",
        },
        timeout=20,
    )
    assert injection.status_code == 422
    assert "extra" in injection.text.lower() or "forbid" in injection.text.lower()


def test_merge_self_disallowed(api_client, societies):
    owner_token = societies["owner_b"]["token"]
    resident_token = societies["resident_b"]["token"]
    created = api_client.post(
        f"{API}/problems",
        json={
            "title": "TEST Traffic bottleneck",
            "description": "TEST Vehicles are queued near south exit causing delays and unsafe turns.",
            "category": "Traffic",
            "location": "TEST South Exit",
            "observed_at": _iso_past(15),
            "duration": "1 hour",
            "affected_area": "South Exit",
            "evidence_ids": [],
        },
        headers=_auth_headers(resident_token),
        timeout=30,
    )
    assert created.status_code == 201
    case_id = created.json()["case_id"]

    merge_self = api_client.post(
        f"{API}/admin/cases/{case_id}/action",
        json={"action": "merge", "target_id": case_id},
        headers=_auth_headers(owner_token),
        timeout=20,
    )
    assert merge_self.status_code == 400
    assert "different case" in merge_self.json()["detail"].lower()
