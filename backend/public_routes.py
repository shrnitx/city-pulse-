"""Public, read-only endpoints for the marketing landing page.
Exposes a sanitized snapshot of the seeded demo society feed. No auth, no tenant principal."""
from fastapi import APIRouter
from core import db

router = APIRouter()
DEMO_SID = 'green-valley-demo'


@router.get('/public/demo-feed')
async def demo_feed():
    projection = {'_id': 0, 'case_number': 1, 'title': 1, 'category': 1, 'location': 1, 'status': 1, 'severity': 1, 'verified': 1, 'created_at': 1}
    cases = await db.cases.find({'society_id': DEMO_SID, 'demo': True}, projection).sort('created_at', -1).to_list(6)
    out = []
    for c in cases:
        cid = f"case-{c['case_number']}"
        reports = await db.reports.count_documents({'society_id': DEMO_SID, 'case_id': cid})
        confirmations = await db.signals.count_documents({'society_id': DEMO_SID, 'case_id': cid, 'affected': True})
        out.append({**c, 'reports': reports, 'confirmations': confirmations})
    society = await db.societies.find_one({'id': DEMO_SID}, {'_id': 0, 'name': 1, 'location': 1})
    return {'society': society or {'name': 'Green Valley Residency', 'location': 'Sector 14, Gurugram'}, 'cases': out}
