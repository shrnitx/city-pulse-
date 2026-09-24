from datetime import datetime,timezone,timedelta
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field,ConfigDict
from core import ScopedRepo,uid,now,event,get_case,notify_case,notify,TERMINAL
from auth_routes import require
from intelligence import analyze

router=APIRouter()
class CaseAction(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    action: Literal['review','verify','reject','assign','request_info','merge','escalate','status','update','analyze']
    note: str=Field(default='',max_length=3000)
    status: str=Field(default='',max_length=50)
    assignee_id: str=''
    target_id: str=''
    severity: Literal['High','Medium','Standard']|None=None

async def merge_cases(repo,source,target,actor):
    if source['id']==target['id']:raise HTTPException(400,'Choose a different case to merge into')
    if target['status'] in TERMINAL:raise HTTPException(400,'The destination case must be active')
    for collection in ['reports','comments','files']:
        await repo.update_many(collection,{'case_id':source['id']},{'$set':{'case_id':target['id']}})
    signals=await repo.many('signals',{'case_id':source['id']})
    for s in signals:
        existing=await repo.one('signals',{'case_id':target['id'],'user_id':s['user_id']}) or {}
        await repo.update('signals',{'case_id':target['id'],'user_id':s['user_id']},{'$set':{'vote':existing.get('vote') or s.get('vote',0),'affected':existing.get('affected',False) or s.get('affected',False),'following':existing.get('following',False) or s.get('following',False)}},upsert=True)
        await repo.delete('signals',{'case_id':source['id'],'user_id':s['user_id']})
    await repo.update('cases',{'id':source['id']},{'$set':{'status':'Merged','merged_into':target['id']},'$push':{'timeline':event(f"Merged into case #{target['case_number']}",'official',actor)}})
    inherited=[{**e,'source_case_number':source['case_number']} for e in source.get('timeline',[])]
    await repo.update('cases',{'id':target['id']},{'$push':{'timeline':{'$each':inherited+[event(f"Case #{source['case_number']} merged into this case. Original records retained.",'official',actor)],'$sort':{'created_at':1}}}})
    await analyze(repo,target['id'])
    await notify_case(repo,target['id'],f"Related reports from case #{source['case_number']} were merged into this case.")

@router.post('/admin/cases/{case_id}/action')
async def action(case_id: str,data: CaseAction,user=Depends(require('case_manage'))):
    repo=ScopedRepo(user);case=await get_case(repo,case_id)
    if case['status']=='Merged':raise HTTPException(409,'This case was merged. Review the destination case instead.')
    actor=user['name'];changes={};timeline=None;title=None
    if data.action=='merge':
        await merge_cases(repo,case,await get_case(repo,data.target_id),actor)
        return {'ok':True,'case_id':data.target_id}
    if data.action=='analyze':
        await analyze(repo,case_id);return {'ok':True,'case_id':case_id}
    if data.action in ['reject','request_info','escalate','update'] and len(data.note)<5:raise HTTPException(400,'Please add an explanation of at least 5 characters')
    if data.action=='verify':
        if case.get('verified'):raise HTTPException(409,'This problem has already been verified')
        if case['status'] in TERMINAL:raise HTTPException(400,'Reopen this case for review before verifying it')
        changes={'verified':True,'verified_by':actor,'verified_at':now(),'status':'Verified'}
        timeline=event('Issue verified by administrator','verified',actor)
        title=f"Admin verified: {case['title']}"
    elif data.action=='review':
        if case['status'] in TERMINAL:raise HTTPException(400,'Choose an active status to reopen this case first')
        changes={'status':'Under Review'};timeline=event('Administrator began reviewing this case','official',actor)
    elif data.action=='reject':
        changes={'status':'Rejected','verified':False};timeline=event('Case rejected: '+data.note,'official',actor);title=f"Case review completed: {case['title']}"
    elif data.action=='assign':
        if case['status'] in TERMINAL:raise HTTPException(400,'Reopen the case before assigning it')
        assignee=await repo.one('users',{'id':data.assignee_id,'active':True,'role':{'$in':['admin','initial_admin']}})
        if not assignee:raise HTTPException(404,'Administrator not found')
        changes={'assigned_to':assignee['id'],'assigned_name':assignee['name'],'status':'Assigned'}
        timeline=event('Assigned to '+assignee['name'],'official',actor)
        await notify(repo,[assignee['id']],f"Case assigned to you: {case['title']}",case_id)
        title='Response assigned: '+case['title']
    elif data.action=='request_info':
        timeline=event('More information requested: '+data.note,'official',actor);title='More information requested: '+case['title']
    elif data.action=='escalate':
        if case['status'] in TERMINAL:raise HTTPException(400,'Reopen the case before escalating it')
        changes={'status':'Escalated','severity':'High'};timeline=event('Case escalated: '+data.note,'official',actor);title='Case escalated: '+case['title']
        owners=await repo.many('users',{'role':'initial_admin','active':True})
        await notify(repo,[a['id'] for a in owners],title,case_id)
    elif data.action=='status':
        society=await repo.one('societies')
        if data.status not in society['settings']['statuses']:raise HTTPException(400,'Unknown workflow status')
        if data.status=='Verified':raise HTTPException(400,'Use the Verify action to record administrator verification')
        if data.status in ['Resolved','Closed'] and not case['verified']:raise HTTPException(400,'Verify the problem before resolving or closing it')
        if data.status==case['status']:raise HTTPException(400,'This case already has the selected status')
        changes={'status':data.status};timeline=event(f"Status changed from {case['status']} to {data.status}"+(f': {data.note}' if data.note else ''),'official',actor);title=f"{data.status}: {case['title']}"
        if data.status=='Resolved':changes['resolved_at']=now()
    elif data.action=='update':
        timeline=event(data.note,'official',actor)
        await repo.update('cases',{'id':case_id},{'$push':{'official_updates':timeline}})
        title='Official update: '+case['title']
    if data.severity:changes['severity']=data.severity
    changes['updated_at']=now()
    mutation={'$set':changes}
    if timeline:mutation['$push']={'timeline':timeline}
    await repo.update('cases',{'id':case_id},mutation)
    await repo.insert('audit',{'id':uid(),'actor_id':user['id'],'action':data.action,'case_id':case_id,'created_at':now()})
    if title:await notify_case(repo,case_id,title)
    return {'ok':True,'case_id':case_id}

@router.get('/analytics')
async def analytics(user=Depends(require('analytics'))):
    repo=ScopedRepo(user)
    cases=await repo.many('cases',{'status':{'$ne':'Merged'}})
    reports=await repo.many('reports',limit=15000)
    categories={}
    for c in cases:categories[c['category']]=categories.get(c['category'],0)+1
    trend=[]
    for offset in range(6,-1,-1):
        day=(datetime.now(timezone.utc)-timedelta(days=offset)).strftime('%Y-%m-%d')
        trend.append({'day':day,'reports':sum(r['created_at'].startswith(day) for r in reports),'resolved':sum(c.get('resolved_at','').startswith(day) for c in cases)})
    resolved=[c for c in cases if c['status'] in ['Resolved','Closed']]
    response_hours=[max(0,(datetime.fromisoformat(c['resolved_at'])-datetime.fromisoformat(c['created_at'])).total_seconds()/3600) for c in resolved if c.get('resolved_at')]
    return {'cases':len(cases),'reports':len(reports),'resolved':len(resolved),'resolution_rate':round(len(resolved)/max(len(cases),1)*100),'consolidation_rate':round(max(0,1-len(cases)/max(len(reports),1))*100),'average_resolution_hours':round(sum(response_hours)/len(response_hours),1) if response_hours else None,'categories':[{'name':k,'value':v} for k,v in categories.items()],'trend':trend,'statuses':[{'name':s,'value':sum(c['status']==s for c in cases)} for s in sorted({c['status'] for c in cases})]}