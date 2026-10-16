import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// Read-only smoke/low-load probe. Do not add write requests to this test.
const baseUrl = (__ENV.BASE_URL || '').replace(/\/+$/, '');
const bypassSecret = (__ENV.VERCEL_AUTOMATION_BYPASS_SECRET || '').trim();
if (!baseUrl) throw new Error('BASE_URL is required');
if (!bypassSecret) throw new Error('Set the GitHub Actions secret VERCEL_AUTOMATION_BYPASS_SECRET before testing this protected preview. No HTTP requests were sent.');

const requestErrors = new Rate('drcivic_health_errors');
export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    http_req_failed: ['rate<0.01'],
    http_req_duration: ['p(95)<1500'],
    drcivic_health_errors: ['rate<0.01'],
  },
};

export default function () {
  const response = http.get(`${baseUrl}/api/health`, {
    headers: { 'x-vercel-protection-bypass': bypassSecret },
    timeout: '15s',
    tags: { endpoint: 'health_readonly' },
  });
  const good = check(response, {
    'health responds HTTP 200': r => r.status === 200,
    'application health response is JSON': r => (r.headers['Content-Type'] || '').toLowerCase().includes('application/json'),
    'database ping reports healthy': r => {
      try { return r.json('status') === 'ok'; } catch (_) { return false; }
    },
  });
  requestErrors.add(!good);
  sleep(1);
}
