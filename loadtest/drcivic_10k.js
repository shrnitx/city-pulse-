import http from 'k6/http';
import { check, sleep } from 'k6';
import exec from 'k6/execution';
import { Counter, Rate } from 'k6/metrics';

// Run from this directory after provision_users.py has generated users.json.
// users.json contains only one set of test credentials and counts, not a
// 10,000-element credential list, so every VU does not duplicate that array.
const testData = JSON.parse(open('./users.json'));
const BASE_URL = (__ENV.BASE_URL || testData.base_url || '').replace(/\/+$/, '');
const API = BASE_URL + '/api';
const BYPASS_SECRET = (__ENV.VERCEL_AUTOMATION_BYPASS_SECRET || '').trim();
const TARGET_VUS = Number(__ENV.TARGET_VUS || 100);
const RAMP_DURATION = __ENV.RAMP_DURATION || '5m';
const HOLD_DURATION = __ENV.HOLD_DURATION || '10m';
const REPORT_PROBABILITY = Math.max(0, Math.min(1, Number(__ENV.REPORT_PROBABILITY || 0.01)));
const MIN_THINK_SECONDS = Math.max(1, Number(__ENV.MIN_THINK_SECONDS || 10));
const MAX_THINK_SECONDS = Math.max(MIN_THINK_SECONDS, Number(__ENV.MAX_THINK_SECONDS || 20));

const reportsAttempted = new Counter('drcivic_reports_attempted');
const reportsSucceeded = new Rate('drcivic_report_success');
const reportsClustered = new Counter('drcivic_reports_clustered');
const commentsAttempted = new Counter('drcivic_comments_attempted');
const commentsSucceeded = new Rate('drcivic_comment_success');
const casesVerified = new Counter('drcivic_cases_verified');
const casesResolved = new Counter('drcivic_cases_resolved');
const casesLeftOpen = new Counter('drcivic_cases_left_open');
const adminActionsSucceeded = new Rate('drcivic_admin_action_success');
const authFailures = new Counter('drcivic_auth_failures');

const templates = [
  { title: 'Water pressure low in Zone 1', category: 'Water', location: 'Load Zone 1 · Utility Junction', description: 'Residents are reporting low water pressure around the utility junction. The water supply appears intermittent and needs a maintenance inspection.' },
  { title: 'Streetlights out in Zone 2', category: 'Electricity', location: 'Load Zone 2 · Walking Path', description: 'Several streetlights are not working along the walking path. The area is unusually dark after sunset and needs an electrical inspection.' },
  { title: 'Waste collection delayed in Zone 3', category: 'Garbage', location: 'Load Zone 3 · Collection Point', description: 'Waste collection appears delayed at the shared collection point. Bags are accumulating and residents are asking for the normal collection schedule to resume.' },
  { title: 'Road surface damage in Zone 4', category: 'Road', location: 'Load Zone 4 · Main Road', description: 'The road surface is damaged close to the main road junction. Vehicles are slowing down to avoid the damaged area and maintenance is needed.' },
  { title: 'Traffic congestion in Zone 5', category: 'Traffic', location: 'Load Zone 5 · North Gate', description: 'Traffic is moving slowly near the north gate and cars are backing up at the junction. Residents may need an update about an alternate route.' },
  { title: 'Lift maintenance needed in Zone 6', category: 'Maintenance', location: 'Load Zone 6 · Residential Tower', description: 'The residential tower lift has stopped intermittently. Residents are requesting a maintenance check and a clear update on the expected repair.' },
  { title: 'Water leakage in Zone 7', category: 'Water', location: 'Load Zone 7 · Service Lane', description: 'Water is leaking onto the service lane near the utility access point. The damp area is growing and needs inspection by the maintenance team.' },
  { title: 'Blocked drain in Zone 8', category: 'Maintenance', location: 'Load Zone 8 · Drainage Lane', description: 'A drainage channel looks blocked near the lane. Water is not flowing away as usual and residents are asking for the blockage to be checked.' },
  { title: 'Footpath obstruction in Zone 9', category: 'Public Safety', location: 'Load Zone 9 · Footpath', description: 'An obstruction is making part of the footpath difficult to use. Pedestrians are moving into the road and a safe passage should be restored.' },
  { title: 'Transit stop access issue in Zone 10', category: 'Transit', location: 'Load Zone 10 · Transit Stop', description: 'Access near the transit stop is restricted by temporary work materials. Residents need a clear walking route and an update from the responsible team.' },
  { title: 'Damaged paving in Zone 11', category: 'Maintenance', location: 'Load Zone 11 · Community Park', description: 'A paving slab near the community park is loose and creates a trip hazard. Maintenance should inspect and secure the area.' },
  { title: 'Weather-related waterlogging in Zone 12', category: 'Weather-related', location: 'Load Zone 12 · Low Road', description: 'Water has gathered along the low section of the road after rainfall. Passing vehicles are slowing and the drain needs to be inspected.' },
];

export const options = {
  discardResponseBodies: false,
  scenarios: {
    residents: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: RAMP_DURATION, target: TARGET_VUS },
        { duration: HOLD_DURATION, target: TARGET_VUS },
        { duration: '1m', target: 0 },
      ],
      gracefulRampDown: '30s',
      exec: 'residentWorkflow',
      tags: { workload: 'resident' },
    },
    administrator: {
      executor: 'constant-vus',
      startTime: RAMP_DURATION,
      vus: 1,
      duration: HOLD_DURATION,
      gracefulStop: '15s',
      exec: 'adminWorkflow',
      tags: { workload: 'administrator' },
    },
  },
  thresholds: {
    // Stop early when sustained server errors begin. Latency thresholds are
    // evaluated at the end so the report preserves the full measured profile.
    http_req_failed: [
      { threshold: 'rate<0.02', abortOnFail: true, delayAbortEval: '2m' },
    ],
    http_req_duration: ['p(95)<2500', 'p(99)<5000'],
    drcivic_report_success: ['rate>0.98'],
    drcivic_admin_action_success: ['rate>0.90'],
  },
};

function authHeaders(token) {
  return {
    headers: {
      Authorization: 'Bearer ' + token,
      Accept: 'application/json',
      'Content-Type': 'application/json',
      ...(BYPASS_SECRET ? { 'x-vercel-protection-bypass': BYPASS_SECRET } : {}),
    },
    timeout: '30s',
  };
}

function parseJson(response) {
  try { return response.json(); } catch (_) { return {}; }
}

function loginResident() {
  // VU IDs are unique across scenarios, so wrap only within the resident account pool.
  const userId = ((exec.vu.idInTest - 1) % testData.resident_count) + 1;
  const username = 'loadresident' + String(userId).padStart(5, '0');
  const response = http.post(
    API + '/auth/login',
    JSON.stringify({
      society_code: testData.society_code,
      username,
      password: testData.resident_password,
    }),
    { headers: { 'Content-Type': 'application/json', ...(BYPASS_SECRET ? { 'x-vercel-protection-bypass': BYPASS_SECRET } : {}) }, tags: { name: 'POST /auth/login', workload: 'resident' }, timeout: '30s' },
  );
  const body = parseJson(response);
  const okay = check(response, {
    'resident login returns 200': (r) => r.status === 200 && !!body.token,
  });
  if (!okay) {
    authFailures.add(1);
    return '';
  }
  return body.token;
}

function loginAdmin() {
  const response = http.post(
    API + '/auth/login',
    JSON.stringify({
      society_code: testData.society_code,
      username: testData.admin.username,
      password: testData.admin.password,
    }),
    { headers: { 'Content-Type': 'application/json', ...(BYPASS_SECRET ? { 'x-vercel-protection-bypass': BYPASS_SECRET } : {}) }, tags: { name: 'POST /auth/login admin', workload: 'administrator' }, timeout: '30s' },
  );
  const body = parseJson(response);
  if (!check(response, { 'admin login returns 200': (r) => r.status === 200 && !!body.token })) {
    authFailures.add(1);
    return '';
  }
  return body.token;
}

let residentToken = '';
let administratorToken = '';
let iteration = 0;

export function setup() {
  if (!BASE_URL) throw new Error('Set BASE_URL to the staging backend base URL, without /api.');
  if (__ENV.CONFIRM_STAGING_TARGET !== 'true') {
    throw new Error('Set CONFIRM_STAGING_TARGET=true only after confirming this is a dedicated staging backend and database, never production.');
  }
  if (TARGET_VUS > 100 && __ENV.ALLOW_HIGH_LOAD !== 'true') {
    throw new Error('TARGET_VUS > 100 requires ALLOW_HIGH_LOAD=true after smoke testing and checking database monitoring.');
  }
  if (!Number.isInteger(TARGET_VUS) || TARGET_VUS < 1 || TARGET_VUS > 10000) {
    throw new Error('TARGET_VUS must be an integer from 1 to 10000.');
  }
  if (TARGET_VUS > Number(testData.resident_count || 0)) {
    throw new Error('TARGET_VUS exceeds the resident count in users.json. Provision enough accounts first.');
  }
  if (BASE_URL.includes('backend-nitin-fa90.vercel.app') || BASE_URL.includes('backend-git-main-nitin-fa90.vercel.app')) {
    throw new Error('Refusing to run the load test against the known stable production backend alias.');
  }
  const health = http.get(API + '/health', { headers: BYPASS_SECRET ? { 'x-vercel-protection-bypass': BYPASS_SECRET } : {}, timeout: '20s', tags: { name: 'GET /health', workload: 'setup' } });
  if (health.status !== 200 || parseJson(health).status !== 'ok') {
    throw new Error('Backend health check failed with HTTP ' + health.status + '. Confirm the staging database connection first.');
  }
  return { started_at: new Date().toISOString(), target_vus: TARGET_VUS };
}

export function residentWorkflow() {
  if (!residentToken) residentToken = loginResident();
  if (!residentToken) { sleep(5); return; }

  iteration += 1;
  const headers = authHeaders(residentToken);

  // Models session refresh plus a frequently refreshed community feed.
  let me = http.get(API + '/auth/me', { ...headers, tags: { name: 'GET /auth/me', workload: 'resident' } });
  if (me.status === 401) {
    residentToken = loginResident();
    if (!residentToken) { sleep(5); return; }
  }

  http.get(API + '/problems?sort=priority', {
    ...authHeaders(residentToken),
    tags: { name: 'GET /problems feed', workload: 'resident' },
  });

  if (iteration % 2 === 0) {
    http.get(API + '/overview', {
      ...authHeaders(residentToken),
      tags: { name: 'GET /overview', workload: 'resident' },
    });
    http.get(API + '/notifications', {
      ...authHeaders(residentToken),
      tags: { name: 'GET /notifications', workload: 'resident' },
    });
  }

  if (Math.random() < REPORT_PROBABILITY) {
    submitReport(residentToken);
  }

  sleep(MIN_THINK_SECONDS + Math.random() * (MAX_THINK_SECONDS - MIN_THINK_SECONDS));
}

function submitReport(token) {
  const pattern = templates[Math.floor(Math.random() * templates.length)];
  reportsAttempted.add(1);
  const response = http.post(
    API + '/problems',
    JSON.stringify({
      title: pattern.title,
      description: pattern.description + ' Observed by a resident during the load-test scenario.',
      category: pattern.category,
      location: pattern.location,
      observed_at: new Date(Date.now() - 60_000).toISOString(),
      duration: 'Observed during load test',
      affected_area: pattern.location.split(' · ')[0],
      evidence_ids: [],
    }),
    { ...authHeaders(token), tags: { name: 'POST /problems', workload: 'resident' } },
  );
  const body = parseJson(response);
  const success = check(response, {
    'report submission returns 201': (r) => r.status === 201 && !!body.case_id,
  });
  reportsSucceeded.add(success);
  if (!success) return;
  if (body.clustered) reportsClustered.add(1);

  // Follow the resulting case to create realistic participation and test the
  // signal write path. This is independent of whether the admin later resolves it.
  if (Math.random() < 0.7) {
    const signal = http.post(
      API + '/problems/' + encodeURIComponent(body.case_id) + '/signals',
      JSON.stringify({ following: true }),
      { ...authHeaders(token), tags: { name: 'POST /problems/:id/signals', workload: 'resident' } },
    );
    check(signal, { 'follow signal accepted': (r) => r.status === 200 });
  }

  // New, unclustered cases occasionally receive a comment before admin triage.
  if (!body.clustered && Math.random() < 0.1) {
    commentsAttempted.add(1);
    const comment = http.post(
      API + '/problems/' + encodeURIComponent(body.case_id) + '/comments',
      JSON.stringify({ text: 'Load-test resident update: the issue is still visible and needs a status update.' }),
      { ...authHeaders(token), tags: { name: 'POST /problems/:id/comments', workload: 'resident' } },
    );
    const commentOkay = comment.status === 201 || (comment.status === 400 && String(comment.body || '').includes('closed to new comments'));
    commentsSucceeded.add(commentOkay);
    check(comment, { 'comment created or case already closed': () => commentOkay });
  }
}

export function adminWorkflow() {
  if (!administratorToken) administratorToken = loginAdmin();
  if (!administratorToken) { sleep(5); return; }

  // The administrator verifies every newly submitted test case. By design,
  // one-third are resolved, one-third move to In Progress, and one-third remain
  // verified but unresolved, so both resolved and open queues persist.
  const response = http.get(API + '/problems?status=AI%20Analyzed&sort=recent', {
    ...authHeaders(administratorToken),
    tags: { name: 'GET /problems admin queue', workload: 'administrator' },
  });
  const body = parseJson(response);
  if (response.status === 200 && Array.isArray(body.items) && body.items.length) {
    const nextCase = body.items.find((item) => item.status === 'AI Analyzed' && !item.verified);
    if (nextCase) {
      const verify = http.post(
        API + '/admin/cases/' + encodeURIComponent(nextCase.id) + '/action',
        JSON.stringify({ action: 'verify' }),
        { ...authHeaders(administratorToken), tags: { name: 'POST /admin verify', workload: 'administrator' } },
      );
      const verifyOkay = verify.status === 200;
      adminActionsSucceeded.add(verifyOkay);
      check(verify, { 'admin verifies a new case': (r) => r.status === 200 });
      if (verifyOkay) {
        casesVerified.add(1);
        if (Number(nextCase.case_number) % 3 === 0) {
          const resolve = http.post(
            API + '/admin/cases/' + encodeURIComponent(nextCase.id) + '/action',
            JSON.stringify({ action: 'status', status: 'Resolved' }),
            { ...authHeaders(administratorToken), tags: { name: 'POST /admin resolve', workload: 'administrator' } },
          );
          const resolveOkay = resolve.status === 200;
          adminActionsSucceeded.add(resolveOkay);
          check(resolve, { 'admin resolves selected cases': (r) => r.status === 200 });
          if (resolveOkay) casesResolved.add(1);
        } else if (Number(nextCase.case_number) % 3 === 1) {
          const progress = http.post(
            API + '/admin/cases/' + encodeURIComponent(nextCase.id) + '/action',
            JSON.stringify({ action: 'status', status: 'In Progress' }),
            { ...authHeaders(administratorToken), tags: { name: 'POST /admin in-progress', workload: 'administrator' } },
          );
          const progressOkay = progress.status === 200;
          adminActionsSucceeded.add(progressOkay);
          check(progress, { 'admin moves selected cases to in progress': (r) => r.status === 200 });
        } else {
          casesLeftOpen.add(1);
        }
      }
    }
  }
  sleep(5);
}

export function handleSummary(data) {
  return {
    'results-summary.json': JSON.stringify({
      generated_at: new Date().toISOString(),
      target_vus: TARGET_VUS,
      ramp_duration: RAMP_DURATION,
      hold_duration: HOLD_DURATION,
      report_probability: REPORT_PROBABILITY,
      metrics: data.metrics,
    }, null, 2),
  };
}
