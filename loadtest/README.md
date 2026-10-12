# CityPulse staged load testing

This folder contains a k6 API load-test harness. It is deliberately gated so it does not run against production accidentally.

## What it exercises

- Authenticated problem feed and overview reads
- Notifications and current-user reads
- Optional synthetic complaint creation, comments, and community signals
- Latency and HTTP error thresholds

## Before you run it

1. Deploy the performance branch to a **dedicated staging environment** with its own database and object storage.
2. Seed that environment with a dedicated society, an active case for comment/signal tests, and one or more load-test users.
3. Obtain bearer tokens for those staging users. Set `LOAD_TEST_TOKENS` to comma-separated tokens. The test rotates among them by virtual-user number.
4. Confirm that staging is isolated from production data, credentials, email, push notifications, and billing.
5. Use a sufficiently provisioned load generator. A single laptop is unlikely to generate 10,000 virtual users reliably.

## Smoke test (10 virtual users, read-only)

Install k6, then run from the repository root:

```bash
STAGING_BASE_URL=https://YOUR-STAGING-URL \
CONFIRM_STAGING_TARGET=true \
LOAD_TEST_TOKENS=TOKEN1,TOKEN2 \
PROFILE=smoke \
k6 run loadtest/citypulse.js
```

## Capacity test (up to 10,000 virtual users)

Only run this against isolated staging after an initial smoke test and a gradual 100/1,000/5,000-VU run has been reviewed:

```bash
STAGING_BASE_URL=https://YOUR-STAGING-URL \
CONFIRM_STAGING_TARGET=true \
LOAD_TEST_TOKENS=TOKEN1,TOKEN2,TOKEN3 \
PROFILE=capacity \
TARGET_VUS=10000 \
ALLOW_HIGH_LOAD=true \
k6 run loadtest/citypulse.js
```

This ramps to the target over several minutes, holds briefly, then ramps down. The 5-second think time makes it an interactive-user approximation, not a 10,000-requests-per-second benchmark. Use distributed load generators for the 10k profile and monitor the API, database, and generator throughout.

## Mutating complaint test

The mutating test creates synthetic complaint records and comments/signals against the configured active test case. It changes database contents and can consume resources; do not enable it until the environment is disposable and backed up.

Add:

```bash
ENABLE_WRITES=true \
CONFIRM_MUTATING_TESTS=true \
LOAD_TEST_CASE_ID=ACTIVE_STAGING_CASE_ID
```

A complaint is created by roughly 10% of iterations and comments/signals by another 20%. Use a separate staging database and clean it up after the run.

## Thresholds and interpretation

The initial pass/fail gates are less than 1% HTTP failures and p95 latency below 1.5 seconds. These are starting SLOs, not guarantees. Track p50/p95/p99 latency, throughput, database query latency, CPU, memory, connection pool saturation, and write queue depth.

Do not claim a 10k-user capacity until a run completes without threshold violations and the system stays healthy while the load generator is not saturated.
