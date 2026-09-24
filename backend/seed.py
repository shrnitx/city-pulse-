import os
from datetime import datetime,timezone,timedelta
from core import db,ScopedRepo,DEFAULT_SETTINGS,uid,now,event
from auth_routes import hash_password
from intelligence import analyze

async def seed_demo():
    await db.societies.create_index('code',unique=True)
    await db.users.create_index([('society_id',1),('username',1)],unique=True)
    await db.users.create_index('id',unique=True)
    await db.sessions.create_index('token_hash',unique=True)
    await db.sessions.create_index('expires_at',expireAfterSeconds=0)
    await db.signals.create_index([('society_id',1),('case_id',1),('user_id',1)],unique=True)
    await db.reputation.create_index([('society_id',1),('admin_id',1),('voter_id',1)],unique=True)
    for col in ['cases','reports','comments','files','notifications','audit']:
        await db[col].create_index([('society_id',1),('id',1)],unique=True)
    await db.counters.update_one({'id':'case_number'},{'$setOnInsert':{'value':1049}},upsert=True)
    if await db.societies.find_one({'code':'GV-48291'}):return
    sid='green-valley-demo';repo=ScopedRepo({'society_id':sid})
    society={'id':sid,'society_id':sid,'name':'Green Valley Residency','code':'GV-48291','location':'Sector 14, Gurugram','address':'Green Valley Residency, Sector 14, Gurugram, Haryana 122001','population':10000,'latitude':28.4695,'longitude':77.0310,'settings':DEFAULT_SETTINGS,'created_at':now(),'demo':True}
    await repo.insert('societies',society)
    pw=hash_password(os.environ['CITYPULSE_DEMO_PASSWORD'])
    for user_id,username,name,role,area,categories,points in [('demo-resident','elena','Elena Vance','resident','Block B · Apartment 402',[],420),('demo-admin','blockb.admin','Arjun Mehta','admin','Block B',['Road','Traffic','Public Safety'],80),('demo-owner','owner','Society Owner','initial_admin','All blocks',[],120),('demo-admin-water','utilities.admin','Priya Sharma','admin','Sector 4',['Water','Electricity','Maintenance'],95)]:
        await repo.insert('users',{'id':user_id,'username':username,'name':name,'role':role,'area':area,'categories':categories,'email':os.environ['CITYPULSE_OWNER_EMAIL'] if role=='initial_admin' else '', 'active':True,'demo':True,'base_points':points,'password_hash':pw,'created_at':now()})
    for i in range(65):
        await repo.insert('users',{'id':f'demo-signal-user-{i}','username':f'resident.{2800+i}','name':f'Resident #{2800+i}','role':'resident','area':['Block A','Block B','Block C'][i%3],'categories':[],'email':'','active':True,'demo':True,'base_points':0,'created_at':now(),'password_hash':'disabled'})
    specifications=[
      (1042,'Road incident near Block B intersection','Residents have reported a minor road accident near the North Gate Avenue intersection. Debris is obstructing one lane and traffic is moving slowly. Please use the South Gate route while the situation is reviewed.','Road','Block B · North Gate Avenue','AI Analyzed','High',50,37,9,False,48),
      (1039,'Low water pressure in Sector 4','Water pressure has been unusually low since this morning. Several homes across Sector 4 are experiencing an intermittent supply. Residents have requested an inspection of the booster pump.','Water','Sector 4 · Utility Junction','Under Review','Medium',22,18,0,False,132),
      (1031,'Streetlights out along the Crossroad Path','Three streetlights along the walking path near Block C are not working. The issue has been inspected and an electrical maintenance team is replacing the circuit breaker.','Electricity','Block C · 3rd Crossroad Path','In Progress','Standard',8,14,0,True,310),
      (1026,'Waste collection completed at the East Gate','The delayed waste collection at the East Gate has been completed. The sanitation team cleared the collection point and restored the regular schedule.','Garbage','East Gate · Collection Point','Resolved','Standard',6,9,0,True,1700),
      (1045,'Damaged paving beside the community park','A loose paving slab near the park entrance creates a trip hazard. Residents have marked the spot and requested maintenance, especially for elderly residents who use the path.','Maintenance','Block A · Community Park','AI Analyzed','Standard',4,6,0,False,92),
    ]
    for num,title,description,category,location,status,severity,count,confirmed,evidence,verified,minutes in specifications:
        case_id=f'case-{num}';created=(datetime.now(timezone.utc)-timedelta(minutes=minutes)).isoformat();timeline=[{**event('Report submitted','community','Resident #2841'),'created_at':created},{**event(f'{count} related reports consolidated into one admin pull request','ai','CityPulse · simulated analysis'),'created_at':(datetime.fromisoformat(created)+timedelta(minutes=3)).isoformat()}]
        if verified:timeline.append({**event('Issue verified by administrator','verified','Priya Sharma'),'created_at':(datetime.fromisoformat(created)+timedelta(minutes=18)).isoformat()})
        official=[]
        if status=='In Progress':official=[{**event('Circuit breaker replacement is in progress. The electrical maintenance team is attending to Junction Box CJ-12.','official','Priya Sharma'),'created_at':(datetime.fromisoformat(created)+timedelta(minutes=30)).isoformat()}];timeline+=official
        if status=='Resolved':official=[{**event('The collection point is clear. Regular waste collection has resumed. Thank you for your patience.','official','Arjun Mehta'),'created_at':(datetime.fromisoformat(created)+timedelta(hours=5)).isoformat()}];timeline+=official+[event('Problem marked resolved','official','Arjun Mehta')]
        case={'id':case_id,'case_number':num,'title':title,'description':description,'category':category,'location':location,'observed_at':created,'duration':'Approximately 3 hours' if num==1042 else 'Since this morning','affected_area':location.split(' · ')[0],'reporter_id':'demo-signal-user-41','reporter_name':'Resident #2841','created_at':created,'status':status,'severity':severity,'verified':verified,'assigned_to':'demo-admin-water' if verified else None,'assigned_name':'Priya Sharma' if verified else None,'timeline':timeline,'official_updates':official,'demo':True}
        if verified:case.update(verified_by='Priya Sharma',verified_at=timeline[2]['created_at'])
        if status=='Resolved':case['resolved_at']=(datetime.fromisoformat(created)+timedelta(hours=5)).isoformat()
        await repo.insert('cases',case)
        for i in range(count):
            await repo.insert('reports',{'id':f'demo-report-{num}-{i}','case_id':case_id,'title':title,'description':description if i==0 else f'{title}. I noticed the same disruption at {location}.','location':location,'category':category,'reporter_id':f'demo-signal-user-{i}','reporter_name':f'Resident #{2800+i}','observed_at':created,'duration':case['duration'],'affected_area':case['affected_area'],'evidence_ids':[],'created_at':created,'demo':True})
        for i in range(max(confirmed,12)):
            await repo.insert('signals',{'case_id':case_id,'user_id':f'demo-signal-user-{i}','affected':i<confirmed,'vote':-1 if i==2 else 1,'following':i<5})
        for i in range(evidence):
            await repo.insert('files',{'id':f'demo-evidence-{i}','owner_id':f'demo-signal-user-{i}','case_id':case_id,'demo_asset':f'evidence-{i%3+1}.jpg','original_filename':f'Sample resident evidence {i+1}.jpg','content_type':'image/jpeg','size':0,'is_deleted':False,'created_at':created,'demo':True})
        if num==1042:
            for i,text in enumerate(['Traffic is backing up towards the North Gate. The South Gate is still accessible.','I passed this intersection a few minutes ago. One lane is blocked by debris.','Residents approaching from Block C can use the park-side road. Please drive carefully.']):
                await repo.insert('comments',{'id':f'demo-comment-{i}','case_id':case_id,'text':text,'author_id':f'demo-signal-user-{i+2}','author_name':['Rohan Kapoor','Aisha Khan','Neha Patel'][i],'created_at':created,'helpful_by':[]})
            await repo.insert('signals',{'case_id':case_id,'user_id':'demo-resident','following':True,'vote':0,'affected':False})
        await analyze(repo,case_id)
    for i in range(8):await repo.insert('reputation',{'admin_id':'demo-admin','voter_id':f'demo-signal-user-{i}','value':-1 if i==7 else 1})
    await repo.insert('notifications',{'id':uid(),'user_id':'demo-resident','title':'Welcome to Green Valley Residency. Your community is connected.','case_id':None,'read':False,'created_at':now()})
    await repo.insert('notifications',{'id':uid(),'user_id':'demo-admin','title':'High-attention pull request #1042 is ready for review.','case_id':'case-1042','read':False,'created_at':now()})