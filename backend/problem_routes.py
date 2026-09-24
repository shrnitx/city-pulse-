from datetime import datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Query
from pydantic import BaseModel,Field,ConfigDict
from core import ScopedRepo,db,uid,now,event,get_case,notify,TERMINAL
from auth_routes import require
from intelligence import find_cluster,analyze

router=APIRouter()

async def decorate(repo,cases,user_id,detail=False):
    ids=[c['id'] for c in cases]
    reports=await repo.many('reports',{'case_id':{'$in':ids}},limit=15000)
    signals=await repo.many('signals',{'case_id':{'$in':ids}},limit=15000)
    comments=await repo.many('comments',{'case_id':{'$in':ids}})
    files=await repo.many('files',{'case_id':{'$in':ids},'is_deleted':False},projection={'_id':0,'id':1,'case_id':1,'original_filename':1,'content_type':1,'demo':1})
    result=[]
    for case in cases:
        cr=[r for r in reports if r['case_id']==case['id']]
        cs=[s for s in signals if s['case_id']==case['id']]
        cc=[c for c in comments if c['case_id']==case['id']]
        mine=next((s for s in cs if s['user_id']==user_id),{})
        output={**case,'reports_count':len(cr),'confirmations':sum(bool(s.get('affected')) for s in cs),'upvotes':sum(s.get('vote')==1 for s in cs),'downvotes':sum(s.get('vote')==-1 for s in cs),'comments_count':len(cc),'evidence':[f for f in files if f['case_id']==case['id']],'my_vote':mine.get('vote',0),'am_affected':mine.get('affected',False),'following':mine.get('following',False),'is_mine':any(r['reporter_id']==user_id for r in cr)}
        if detail:
            output['comments']=[{k:v for k,v in c.items() if k not in ['helpful_by','society_id']}|{'helpful_count':len(c.get('helpful_by',[])),'my_helpful':user_id in c.get('helpful_by',[])} for c in cc]
            output['reports']=[{k:r.get(k) for k in ['id','title','description','reporter_name','location','observed_at','created_at','duration']} for r in cr]
        else: output.pop('timeline',None)
        result.append(output)
    return result

@router.get('/problems')
async def problems(user=Depends(require('read')),search: str=Query(default='',max_length=200),status: str='',category: str='',scope: str='',sort: str='priority'):
    repo=ScopedRepo(user)
    q={'status':{'$ne':'Merged'}}
    if status=='active':q['status']={'$nin':TERMINAL}
    elif status=='verified':q['verified']=True
    elif status:q['status']=status
    if category:q['category']=category
    if scope=='requests' and not status:q['status']={'$in':['Reported','AI Analyzed','Under Review','Escalated']}
    if search:
        import re
        q['$or']=[{f:{'$regex':re.escape(search),'$options':'i'}} for f in ['title','description','location']]
    cases=await decorate(repo,await repo.many('cases',q,sort=[('created_at',-1)]),user['id'])
    if scope=='mine':cases=[c for c in cases if c['is_mine']]
    if scope=='following':cases=[c for c in cases if c['following']]
    if sort=='priority': cases.sort(key=lambda c:(c['status'] not in TERMINAL,c.get('verified',False),{'High':3,'Medium':2,'Standard':1}.get(c.get('severity'),0),c['confirmations'],bool(c['evidence']),c['created_at']),reverse=True)
    return {'items':cases,'total':len(cases)}

@router.get('/problems/{case_id}')
async def problem(case_id: str,user=Depends(require('read'))):
    repo=ScopedRepo(user)
    case=await get_case(repo,case_id)
    return (await decorate(repo,[case],user['id'],True))[0]

class Report(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    title: str=Field(min_length=5,max_length=150)
    description: str=Field(min_length=15,max_length=5000)
    category: str=Field(min_length=1,max_length=50)
    location: str=Field(min_length=3,max_length=150)
    observed_at: datetime
    duration: str=Field(default='',max_length=120)
    affected_area: str=Field(default='',max_length=150)
    evidence_ids: list[str]=Field(default_factory=list,max_length=5)

@router.post('/problems',status_code=201)
async def report(data: Report,user=Depends(require('report'))):
    repo=ScopedRepo(user)
    society=await repo.one('societies')
    if data.category not in society['settings']['categories']: raise HTTPException(400,'Please select a valid category')
    observed=data.observed_at.replace(tzinfo=timezone.utc) if not data.observed_at.tzinfo else data.observed_at
    if observed>datetime.now(timezone.utc)+timedelta(minutes=5):raise HTTPException(400,'Observation time cannot be in the future')
    for file_id in set(data.evidence_ids):
        f=await repo.one('files',{'id':file_id,'owner_id':user['id'],'is_deleted':False,'case_id':None})
        if not f:raise HTTPException(400,'Evidence is unavailable or already attached to another report')
    cluster=await find_cluster(repo,data)
    new_case=not cluster
    case_id=cluster['id'] if cluster else uid()
    if new_case:
        counter=await db.counters.find_one_and_update({'id':'case_number'},{'$inc':{'value':1}},upsert=True,return_document=True,projection={'_id':0})
        case={'id':case_id,'case_number':counter['value'],'title':data.title,'description':data.description,'category':data.category,'location':data.location,'observed_at':observed.isoformat(),'duration':data.duration,'affected_area':data.affected_area,'reporter_id':user['id'],'reporter_name':user['name'],'created_at':now(),'status':'AI Analyzed','severity':'Standard','verified':False,'assigned_to':None,'assigned_name':None,'timeline':[event('Report submitted','community',user['name']),event('Report organized into an admin pull request','ai','CityPulse · simulated analysis')],'official_updates':[],'demo':False}
        await repo.insert('cases',case)
    report_id=uid()
    await repo.insert('reports',{'id':report_id,'case_id':case_id,'reporter_id':user['id'],'reporter_name':user['name'],**data.model_dump(exclude={'observed_at'}),'observed_at':observed.isoformat(),'created_at':now()})
    for file_id in set(data.evidence_ids):await repo.update('files',{'id':file_id},{'$set':{'case_id':case_id}})
    if not new_case:await repo.update('cases',{'id':case_id},{'$push':{'timeline':event('A related resident report was consolidated into this case','ai','CityPulse · simulated analysis')}})
    await analyze(repo,case_id)
    await notify(repo,[user['id']],'Your problem has been submitted.' if new_case else 'Your report was received and grouped with a related case.',case_id)
    if new_case:
        admins=await repo.many('users',{'active':True,'role':{'$in':['admin','initial_admin']}})
        await notify(repo,[a['id'] for a in admins],f'New admin pull request: {data.title}',case_id)
    return {'message':'Your problem has been submitted.','report_id':report_id,'case_id':case_id,'clustered':not new_case,'request_type':'USER PUSH REQUEST'}

class Signal(BaseModel):
    model_config=ConfigDict(extra='forbid')
    vote: Literal[-1,0,1]|None=None
    affected: bool|None=None
    following: bool|None=None

@router.post('/problems/{case_id}/signals')
async def signal(case_id: str,data: Signal,user=Depends(require('participate'))):
    repo=ScopedRepo(user)
    case=await get_case(repo,case_id)
    if case['status']=='Merged':raise HTTPException(409,'This case has been merged. Open the destination case to participate.')
    changes=data.model_dump(exclude_none=True)
    if not changes:raise HTTPException(400,'Choose a community signal')
    if changes.get('vote') and case['reporter_id']==user['id']:raise HTTPException(400,'You cannot vote on your own report')
    await repo.update('signals',{'case_id':case_id,'user_id':user['id']},{'$set':changes},upsert=True)
    if 'affected' in changes:await analyze(repo,case_id)
    return {'ok':True}

class Comment(BaseModel):
    text: str=Field(min_length=2,max_length=2000)
    model_config=ConfigDict(str_strip_whitespace=True)

@router.post('/problems/{case_id}/comments',status_code=201)
async def comment(case_id: str,data: Comment,user=Depends(require('participate'))):
    repo=ScopedRepo(user)
    case=await get_case(repo,case_id)
    if case['status'] in ['Merged','Closed','Rejected']:raise HTTPException(400,'This case is closed to new comments')
    record={'id':uid(),'case_id':case_id,'text':data.text,'author_id':user['id'],'author_name':user['name'],'created_at':now(),'helpful_by':[]}
    await repo.insert('comments',record)
    await analyze(repo,case_id)
    return {'id':record['id'],'ok':True}

@router.post('/comments/{comment_id}/helpful')
async def helpful(comment_id: str,user=Depends(require('participate'))):
    repo=ScopedRepo(user)
    c=await repo.one('comments',{'id':comment_id})
    if not c:raise HTTPException(404,'Comment not found')
    if c['author_id']==user['id']:raise HTTPException(400,'You cannot endorse your own comment')
    operator='$pull' if user['id'] in c.get('helpful_by',[]) else '$addToSet'
    await repo.update('comments',{'id':comment_id},{operator:{'helpful_by':user['id']}})
    return {'ok':True}

@router.get('/overview')
async def overview(user=Depends(require('read'))):
    repo=ScopedRepo(user)
    cases=await repo.many('cases',{'status':{'$ne':'Merged'}})
    counts={s:sum(c['status']==s for c in cases) for s in ['Reported','AI Analyzed','Under Review','Verified','Assigned','In Progress','Resolved','Closed','Escalated','Rejected']}
    return {'total':len(cases),'active':sum(c['status'] not in TERMINAL for c in cases),'verified':sum(c['verified'] for c in cases),'in_progress':counts['In Progress'],'resolved':counts['Resolved']+counts['Closed'],'new_requests':counts['AI Analyzed']+counts['Reported'],'under_review':counts['Under Review'],'escalated':counts['Escalated'],'reports':await repo.count('reports'),'confirmations':await repo.count('signals',{'affected':True}),'evidence':await repo.count('files',{'is_deleted':False,'case_id':{'$ne':None}}),'counts':counts,'workload':sum(c.get('assigned_to')==user['id'] and c['status'] not in TERMINAL for c in cases)}