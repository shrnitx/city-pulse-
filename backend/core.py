import os
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
from fastapi import HTTPException

load_dotenv(Path(__file__).parent / '.env')
client = AsyncIOMotorClient(os.environ['MONGO_URL'])
db = client[os.environ['DB_NAME']]
def now(): return datetime.now(timezone.utc).isoformat()
def uid(): return str(uuid.uuid4())

CATEGORIES = ['Road','Traffic','Water','Electricity','Garbage','Public Safety','Maintenance','Weather-related','Transit','Other']
STATUSES = ['Reported','AI Analyzed','Under Review','Verified','Assigned','In Progress','Resolved','Closed']
TERMINAL = ['Resolved','Closed','Rejected','Merged']
DEFAULT_SETTINGS = {'admin_capacity': 12, 'admin_ratio': 1000, 'registration_open': True, 'votes_per_point': 10, 'verified_report_points': 10, 'confirmation_points': 1, 'evidence_points': 2, 'categories': CATEGORIES, 'statuses': STATUSES}

class ScopedRepo:
    """All tenant data access is constrained here, including ID-based operations."""
    def __init__(self, principal): self.society_id = principal['society_id']
    def query(self, q=None): return {'$and': [{'society_id': self.society_id}, q or {}]}
    async def one(self, collection, q=None, projection=None):
        return await db[collection].find_one(self.query(q), projection or {'_id': 0})
    async def many(self, collection, q=None, limit=2000, sort=None, projection=None):
        cursor = db[collection].find(self.query(q), projection or {'_id': 0})
        if sort: cursor = cursor.sort(sort)
        return await cursor.to_list(limit)
    async def count(self, collection, q=None): return await db[collection].count_documents(self.query(q))
    async def insert(self, collection, doc):
        clean = {**doc, 'society_id': self.society_id}
        await db[collection].insert_one(clean.copy())
        return clean
    async def update(self, collection, q, changes, upsert=False):
        if any('society_id' in v for v in changes.values() if isinstance(v, dict)):
            raise ValueError('Tenant cannot be reassigned')
        if upsert:
            changes = {**changes, '$setOnInsert': {**changes.get('$setOnInsert', {}), 'society_id': self.society_id}}
        return await db[collection].update_one(self.query(q), changes, upsert=upsert)
    async def update_many(self, collection, q, changes):
        return await db[collection].update_many(self.query(q), changes)
    async def delete(self, collection, q): return await db[collection].delete_one(self.query(q))
    async def aggregate(self, collection, pipeline):
        if any(op in str(pipeline) for op in ['$lookup','$unionWith','$graphLookup']): raise ValueError('Unscoped join')
        return await db[collection].aggregate([{'$match': {'society_id': self.society_id}}, *pipeline]).to_list(2000)

PERMISSIONS = {
 'resident': {'read','report','participate','feedback','profile'},
 'admin': {'read','report','participate','profile','case_manage','analytics'},
 'initial_admin': {'read','report','participate','profile','case_manage','analytics','society_manage','admins_manage'},
}
def authorize(principal, action, resource=None):
    allowed = action in PERMISSIONS.get(principal.get('role'), set())
    logging.getLogger('citypulse.audit').info('principal=%s society=%s action=%s allowed=%s', principal['id'], principal['society_id'], action, allowed)
    if resource and resource.get('society_id') != principal['society_id']: raise HTTPException(404, 'Not found')
    if not allowed: raise HTTPException(403, 'You do not have permission for this action')

async def get_case(repo, case_id):
    case = await repo.one('cases', {'id': case_id})
    if not case: raise HTTPException(404, 'Problem not found')
    return case

def event(text, kind='status', actor='CityPulse', **extra):
    return {'id': uid(), 'text': text, 'kind': kind, 'actor': actor, 'created_at': now(), **extra}

async def notify(repo, recipients, title, case_id=None):
    for user_id in set(recipients):
        await repo.insert('notifications', {'id': uid(), 'user_id': user_id, 'title': title, 'case_id': case_id, 'read': False, 'created_at': now()})

async def notify_case(repo, case_id, title):
    reports = await repo.many('reports', {'case_id': case_id})
    follows = await repo.many('signals', {'case_id': case_id, 'following': True})
    await notify(repo, [r['reporter_id'] for r in reports] + [s['user_id'] for s in follows], title, case_id)

async def point_total(user):
    repo = ScopedRepo(user)
    society = await repo.one('societies')
    cfg = society['settings']
    reports = await repo.many('reports', {'reporter_id': user['id']})
    case_ids = list({r['case_id'] for r in reports})
    verified = await repo.many('cases', {'id': {'$in': case_ids}, 'verified': True})
    confirmed = await repo.many('signals', {'user_id': user['id'], 'affected': True})
    valid_confirmations = await repo.count('cases', {'id': {'$in': [s['case_id'] for s in confirmed]}, 'verified': True})
    votes = await repo.count('signals', {'case_id': {'$in': case_ids}, 'vote': 1, 'user_id': {'$ne': user['id']}})
    comments = await repo.many('comments', {'author_id': user['id']})
    helpful = sum(len(c.get('helpful_by', [])) for c in comments)
    evidence = sum(len(r.get('evidence_ids', [])) for r in reports if r['case_id'] in {c['id'] for c in verified})
    points = user.get('base_points', 0) + len(verified)*cfg['verified_report_points'] + valid_confirmations*cfg['confirmation_points'] + evidence*cfg['evidence_points'] + (votes+helpful)//cfg['votes_per_point']
    rank = 'Diamond' if points >= 1000 else 'Platinum' if points >= 500 else 'Gold' if points >= 250 else 'Silver' if points >= 100 else 'Bronze'
    return {'points': points, 'rank': rank, 'report_count': len(reports), 'verified_contributions': len(verified), 'confirmation_count': len(confirmed)}