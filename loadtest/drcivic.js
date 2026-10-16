import http from 'k6';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Safety gate: this harness only accepts an explicitly confirmed staging target.
const baseUrl = (__ENV.STAGING_BASE_URL || '').replace(/\/+$/, '');
const bypassSecret = (__ENV.VERCEL_AUTOMATION_BYPASS_SECRET || '').trim();
const confirmed = __ENV.CONFIRM_STAGING_TARGET === 'true';
const highLoadAllowed = __ENV.ALLOW_HIGH_LOAD === 'true';
const enableWrites = __ENV.ENABLE_WRITES === 'true';
const confirmWrites = __ENV.CONFIRM_MUTATING_TESTS === 'true';
const targetVus = Number(__ENV.TARGET_VUS || 10);
const profile = __ENV.PROFILE || 'smoke';
const tokens = (__ENV.LOAD_TEST_TOKENS || '').split(',').map(x => x.trim()).filter(Boolean);
const caseId = (__ENV.LOAD_TEST_CASE_ID || '').trim();
const errors = new Rate('drcivic_request_errors');

if (!baseUrl) throw new Error('Set STAGING_BASE_URL to a dedicated staging deployment URL.');
if (!bypassSecret) throw new Error('Set VERCEL_AUTOMATION_BYPASS_SECRET in the runner environment before calling a protected preview.');
if (!confirmed) throw new Error('Set CONFIRM_STAGING_TARGET=true only after verifying this is staging, not production.');
if (tokens.length === 0) throw new Error('Set LOAD_TEST_TOKENS to one or more dedicated staging-user bearer tokens.');
if (!Number.isInteger(targetVus) || targetVus < 1 || targetVus > 10000) throw new Error('TARGET_VUS must be an integer from 1 to 10000.');
if (targetVus > 100 && !highLoadAllowed) throw new Error('TARGET_VUS > 100 requires ALLOW_HIGH_LOAD=true.');
if (profile === 'capacity' && !highLoadAllowed) throw new Error('PROFILE=capacity requires ALLOW_HIGH_LOAD=true.');
if (enableWrites && !confirmWrites) throw new Error('ENABLE_WRITES=true requires CONFIRM_MUTATING_TESTS=true.');
if (enableWrites && !caseId) throw new Error('Set LOAD_TEST_CASE_ID to an active, dedicated staging test case before enabling writes.');

const ramp = profile === 'capacity'
  ? [
      { duration: '1m', target: Math.min(100, targetVus) },
      { duration: '2m', target: Math.min(1000, targetVus) },
      { duration: '3m', target: Math.min(5000, targetVus) },
      { duration: '2m', target: targetVus },
      { duration: '1m', target: targetVus },
      { duration: '1m', target: 0 },
    ]
  : [
      { duration: '10s', target: Math.min(10, targetVus) },
      { duration: '30s', target: Math.min(10, targetVus) },
      { duration: '10s', target: 0 },
    ];

export const options = {
  scenarios: {
    drcivic_api: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: ramp,
      gracefulRampDown: '30s',
    },
  },
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
    drcivic_request_errors: ['rate<0.01'],
  },
};

const jsonHeaders = {
  'Content-Type': 'application/json',
  Accept: 'application/json',
};

function request(path, token, label, params = {}) {
  const response = http.get(`${baseUrl}/api${path}`, {
    headers: { ...jsonHeaders, Authorization: `Bearer ${token}`, 'x-vercel-protection-bypass': bypassSecret },
    tags: { endpoint: label },
    timeout: '30s',
    ...params,
  });
  const ok = check(response, {
    [`${label} returns success`]: r => r.status >= 200 && r.status < 400,
  });
  errors.add(!ok);
  return response;
}

function write(path, token, label, payload) {
  const response = http.post(`${baseUrl}/api${path}`, JSON.stringify(payload), {
    headers: { ...jsonHeaders, Authorization: `Bearer ${token}` },
    tags: { endpoint: label },
    timeout: '30s',
  });
  const ok = check(response, {
    [`${label} returns success`]: r => r.status >= 200 && r.status < 400,
  });
  errors.add(!ok);
  return response;
}

export default function () {
  // Rotate among supplied tokens to avoid making every request the same account.
  const token = tokens[(__VU - 1) % tokens.length];
  const bucket = (__VU + __ITER) % 10;

  if (enableWrites && bucket === 0) {
    const id = `load-${__VU}-${__ITER}-${Date.now()}`;
    write('/problems', token, 'create_complaint', {
      title: `Load-test civic report ${id}`,
      description: `Dedicated staging load-test complaint ${id}. This is synthetic test data for capacity validation.`,
      category: 'Road',
      location: `Load-test location ${id}`,
      observed_at: new Date().toISOString(),
      duration: 'Synthetic load test',
      affected_area: 'Load-test staging zone',
      evidence_ids: [],
    });
  } else if (enableWrites && bucket === 1) {
    write(`/problems/${caseId}/comments`, token, 'create_comment', {
      text: `Synthetic load-test comment from VU ${__VU}, iteration ${__ITER}.`,
    });
  } else if (enableWrites && bucket === 2) {
    write(`/problems/${caseId}/signals`, token, 'update_signal', {
      following: true,
    });
  } else if (bucket <= 4) {
    request('/problems?status=active&sort=recent', token, 'problem_feed');
  } else if (bucket <= 6) {
    request('/overview', token, 'overview');
  } else if (bucket <= 8) {
    request('/notifications', token, 'notifications');
  } else {
    request('/auth/me', token, 'auth_me');
  }

  // Think time prevents this from modelling an unreasonably frantic click bot.
  sleep(5);
}
