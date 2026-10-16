# CityPulse 10,000-user API load test

This test harness simulates 10,000 concurrent virtual residents using CityPulse, continuously reading the feed, submitting clustered reports, following cases and occasionally commenting. A synthetic administrator verifies incoming cases while resolving only a portion, so resolved, in-progress and unresolved work coexists throughout the run.

It contains:
- \`provision_users.py\`: safely creates one isolated test society and up to 10,000 synthetic residents through the API.
- \`citypulse_10k.js\`: k6 workload, configurable ramp-up, ongoing resident traffic, report creation, case-following, comments, admin triage, metrics and pass/fail thresholds.
- \`users.json\`: generated private credentials/configuration. It is ignored by git; never upload or commit it.

## Important: isolate the environment first

1. Deploy this branch to a **Preview/staging backend**.
2. Configure that Preview backend with a **dedicated disposable MongoDB database**. Set \`MONGO_URL\` to the test cluster URI and \`DB_NAME=citypulse_loadtest\` (or another database used only for this run). Confirm that the preview environment does not inherit the production database URI.
3. Configure the remaining backend startup variables needed by the application, including \`CORS_ORIGINS\`, \`CITYPULSE_DEMO_PASSWORD\` and \`CITYPULSE_OWNER_EMAIL\`.
4. Confirm \`GET /api/health\` returns HTTP 200 against the staging URL.
5. Never paste database URIs, passwords or Vercel bypass secrets into chat, source files or logs. Keep them in local environment variables or Vercel settings.

**Do not run this against production.** Provisioning creates test users and the load test creates reports, comments, signals, notifications, audit events and sessions. The safest cleanup after testing is to delete and recreate the dedicated test database.

If Vercel deployment protection is enabled on the Preview URL, set \`VERCEL_AUTOMATION_BYPASS_SECRET\` in the local shell to the Vercel-generated automation bypass secret. The harness sends it as a request header and never prints it. Do not put a bypass secret into the URL.

## 1. Install the tools

Install Python 3.10+ and [Grafana k6](https://grafana.com/docs/k6/latest/set-up/install-k6/). Verify:

\`\`\`bash
python --version
k6 version
\`\`\`

## 2. Provision the test users

From this directory, set \`BASE_URL\` to the unique staging backend deployment URL, without the \`/api\` suffix.

macOS/Linux:

\`\`\`bash
export BASE_URL="https://YOUR-STAGING-BACKEND-URL"
export LOADTEST_USER_COUNT=10000
export LOADTEST_PROVISION_WORKERS=8
export CITYPULSE_LOADTEST_CONFIRM="YES_I_AM_USING_A_DEDICATED_TEST_DATABASE"
python provision_users.py
\`\`\`

Windows PowerShell:

\`\`\`powershell
$env:BASE_URL = "https://YOUR-STAGING-BACKEND-URL"
$env:LOADTEST_USER_COUNT = "10000"
$env:LOADTEST_PROVISION_WORKERS = "8"
$env:CITYPULSE_LOADTEST_CONFIRM = "YES_I_AM_USING_A_DEDICATED_TEST_DATABASE"
python .\provision_users.py
\`\`\`

The script first calls the staging health endpoint. It then creates a test society and registers uniquely named residents at controlled concurrency, saving only one shared test password and the society/admin credentials in \`users.json\`. It will refuse provisioning without the explicit safety confirmation and refuses the known stable production aliases.

If provisioning fails partway through, investigate the error and reset the dedicated test database before retrying. Do not run the provisioner repeatedly against a shared database.

## 3. Smoke test before increasing load

Begin with 25 VUs and only then increase the test size. Every k6 run requires an explicit staging confirmation. More than 100 VUs requires an additional high-load confirmation.

\`\`\`bash
# First smoke test: 25 virtual users, 1 minute of steady traffic.
export BASE_URL="https://YOUR-STAGING-BACKEND-URL"
k6 run citypulse_10k.js \
  -e CONFIRM_STAGING_TARGET=true \
  -e TARGET_VUS=25 \
  -e RAMP_DURATION=30s \
  -e HOLD_DURATION=1m

# Gradually grow the load. Inspect the prior results and database health before each step.
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e TARGET_VUS=100 -e RAMP_DURATION=1m -e HOLD_DURATION=3m
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e ALLOW_HIGH_LOAD=true -e TARGET_VUS=500 -e RAMP_DURATION=3m -e HOLD_DURATION=5m
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e ALLOW_HIGH_LOAD=true -e TARGET_VUS=1000 -e RAMP_DURATION=5m -e HOLD_DURATION=10m
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e ALLOW_HIGH_LOAD=true -e TARGET_VUS=2500 -e RAMP_DURATION=5m -e HOLD_DURATION=10m
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e ALLOW_HIGH_LOAD=true -e TARGET_VUS=5000 -e RAMP_DURATION=10m -e HOLD_DURATION=15m
k6 run citypulse_10k.js -e CONFIRM_STAGING_TARGET=true -e ALLOW_HIGH_LOAD=true -e TARGET_VUS=10000 -e RAMP_DURATION=10m -e HOLD_DURATION=20m
\`\`\`

The final 10k run lasts approximately 31 minutes: 10 minutes to ramp up, 20 minutes at 10,000 VUs, then one minute to ramp down. The default report probability is 1% per resident iteration; with 10,000 VUs and the default think time, reports arrive continuously rather than all at once. The administrator verifies new cases and:
- resolves about one-third of cases,
- moves about one-third to In Progress,
- leaves about one-third verified but unresolved.

Workload controls:
- \`REPORT_PROBABILITY=0.01\`: report probability per resident iteration.
- \`MIN_THINK_SECONDS=10\` / \`MAX_THINK_SECONDS=20\`: think time between resident iterations.
- \`TARGET_VUS\`: peak active virtual residents, up to 10,000.
- \`RAMP_DURATION\` and \`HOLD_DURATION\`: ramp and sustained-load time.

## 4. Pass/fail gates and output

The script measures request latency/error rates and custom metrics for report submission, report clustering, comments, administrator verification, resolution and unresolved cases. It writes \`results-summary.json\` locally.

Initial gates:
- HTTP errors below 2%. The test aborts if this rate stays too high after the initial two-minute observation window.
- p95 request latency below 2.5 seconds.
- p99 request latency below 5 seconds.
- At least 98% report submissions succeed.
- At least 90% of administrator actions succeed.

These are target SLOs, not claims about current performance. If the test fails, keep the failed result, locate the bottleneck, optimize and rerun. Do not simply loosen the thresholds.

## 5. What to watch while the test runs

Monitor Vercel function duration, invocations/concurrency, CPU/memory where available, 429/500/504 responses, and runtime logs. On MongoDB, watch CPU, memory, connections, operation counts, query latency, slow queries, index use and storage. Watch the load generator too: if it saturates, its limitations can distort the result.

A passing test applies only to the exact frontend/backend commit, Vercel plan/region, MongoDB tier, index state and workload profile tested. For a credible 10k run, use distributed load generators or k6 Cloud if one machine cannot maintain 10,000 VUs without saturation.

## What this test does not cover

This is an API/backend test, not 10,000 browser instances. It does not benchmark browser animation/rendering. Evidence upload should be tested separately at low concurrency after a working object-storage key is configured. Civic weather/AQI feeds and the intelligence layer remain simulated in this MVP.
