"""Deterministic simulation adapter. No real AI or live civic provider is used."""
import re
from datetime import datetime, timezone, timedelta
from core import TERMINAL, now

def words(text): return set(re.findall(r'[a-z]{3,}', text.lower())) - {'the','and','near','has','are','this','there','for','with','from'}
async def find_cluster(repo, report):
    recent = (datetime.now(timezone.utc)-timedelta(hours=48)).isoformat()
    candidates = await repo.many('cases', {'category': report.category, 'status': {'$nin': TERMINAL}, 'created_at': {'$gte': recent}})
    best, score = None, 0
    for c in candidates:
        loc_a, loc_b = words(report.location), words(c['location'])
        location_match = report.location.lower().strip() == c['location'].lower().strip() or (bool(loc_a & loc_b) and len(loc_a & loc_b)/max(len(loc_a | loc_b),1) >= .5)
        a, b = words(report.title+' '+report.description), words(c['title']+' '+c['description'])
        sim = len(a & b)/max(len(a | b),1)
        if location_match and sim >= .15 and sim > score: best, score = c, sim
    return best

async def analyze(repo, case_id):
    case = await repo.one('cases', {'id': case_id})
    reports = await repo.many('reports', {'case_id': case_id})
    comments = await repo.many('comments', {'case_id': case_id})
    confirmations = await repo.count('signals', {'case_id': case_id, 'affected': True})
    evidence = await repo.count('files', {'case_id': case_id, 'is_deleted': False})
    admins = await repo.many('users', {'role': {'$in': ['admin','initial_admin']}, 'active': True}, projection={'_id':0,'id':1,'name':1,'area':1,'categories':1})
    suggested = next((a for a in admins if case['category'] in a.get('categories',[]) or a.get('area','__') in case['location']), admins[0] if admins else None)
    text = ' '.join(r['description'] for r in reports) + ' ' + ' '.join(c['text'] for c in comments)
    contradictions = []
    if re.search(r'\b(blocked|closed|outage|no water)\b', text, re.I) and re.search(r'\b(clear|reopened|restored|normal)\b', text, re.I): contradictions.append('Reports or comments describe both disruption and normal conditions. An administrator should confirm the latest situation.')
    duration = next((r.get('duration') for r in reversed(reports) if r.get('duration')), 'Not yet established')
    relation = 'Nearby traffic congestion may be related to this road disruption. This is a possible correlation, not a confirmed cause.' if case['category'] in ['Road','Traffic','Transit'] else 'No additional relationship established from available signals.'
    insight = {'mode':'simulated','summary': f"{len(reports)} community report{'s' if len(reports)!=1 else ''} describe {case['title'].lower()} at {case['location']}. {confirmations} residents confirm they are affected. Administrator review is required.", 'report_count':len(reports),'confirmations':confirmations,'evidence_count':evidence, 'comment_count':len(comments), 'location':case['location'], 'affected_area':case.get('affected_area') or case['location'], 'observed_at':case.get('observed_at'), 'duration':duration, 'contradictions':contradictions, 'related_signal':relation, 'suggested_admin': suggested['name'] if suggested else 'Society administration', 'suggested_admin_id':suggested['id'] if suggested else None, 'suggested_category':case['category'],'updated_at':now()}
    await repo.update('cases', {'id':case_id}, {'$set':{'ai': insight}})
    return insight

class SimulatedCivicProvider:
    def get(self, society):
        seed = sum(ord(c) for c in society['location'])
        temp = 24+seed%6
        return {'mode':'simulated','location':society['location'],'updated_at':now(), 'weather':{'temperature':temp,'condition':'Partly cloudy','humidity':58,'wind':9,'forecast':'Partly cloudy through the afternoon. A light breeze expected this evening.','days':[{'day':'Today','high':temp+2,'low':temp-6,'condition':'sun'},{'day':'Tomorrow','high':temp+1,'low':temp-5,'condition':'cloud'},{'day':'Next day','high':temp,'low':temp-7,'condition':'rain'}]}, 'aqi':{'value':68,'category':'Moderate','pm25':20.4,'pm10':42,'standard':'US AQI','advisory':'Unusually sensitive people may consider reducing prolonged outdoor exertion.'},'traffic':{'condition':'Slower than usual','delay':12,'area': 'Block B · North Gate' if society.get('demo') else society['location']},'utilities':{'water':'Operational','electricity':'Operational'}, 'map':{'latitude':society['latitude'],'longitude':society['longitude'],'mode':'schematic'}}