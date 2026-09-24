import secrets
import math
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from pymongo.errors import DuplicateKeyError
from core import db, ScopedRepo, DEFAULT_SETTINGS, CATEGORIES, STATUSES, uid, now, notify
from auth_routes import require, hash_password, session_response
from intelligence import SimulatedCivicProvider

router=APIRouter()
class SocietyCreate(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str=Field(min_length=3,max_length=100)
    location: str=Field(min_length=3,max_length=150)
    address: str=Field(min_length=5,max_length=300)
    population: int=Field(ge=1,le=10000000)
    latitude: float=Field(ge=-90,le=90)
    longitude: float=Field(ge=-180,le=180)
    admin_name: str=Field(min_length=2,max_length=80)
    admin_email: EmailStr
    admin_capacity: int=Field(default=12,ge=1,le=10000)
    admin_ratio: int=Field(default=1000,ge=1,le=100000)

@router.post('/societies', status_code=201)
async def create_society(data: SocietyCreate):
    society_id=uid()
    prefix=''.join(x[0] for x in data.name.split()[:2]).upper()
    code=prefix+'-'+str(secrets.randbelow(900000)+100000)
    password=secrets.token_urlsafe(12)
    username='admin.'+secrets.token_hex(2)
    society={'id':society_id,'society_id':society_id,'name':data.name,'location':data.location,'address':data.address,'population':data.population,'latitude':data.latitude,'longitude':data.longitude,'code':code,'settings':{**DEFAULT_SETTINGS,'admin_capacity':data.admin_capacity,'admin_ratio':data.admin_ratio},'created_at':now(),'demo':False}
    repo=ScopedRepo(society)
    await repo.insert('societies',society)
    user={'id':uid(),'society_id':society_id,'username':username,'name':data.admin_name,'email':str(data.admin_email),'role':'initial_admin','area':data.location,'categories':[],'active':True,'base_points':0,'password_hash':hash_password(password),'created_at':now()}
    await repo.insert('users',user)
    return {**await session_response(user),'credentials':{'society_code':code,'username':username,'password':password}}

class SettingsEdit(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True, extra='forbid')
    name: str=Field(min_length=3,max_length=100)
    location: str=Field(min_length=3,max_length=150)
    address: str=Field(min_length=5,max_length=300)
    population: int=Field(ge=1,le=10000000)
    latitude: float=Field(ge=-90,le=90)
    longitude: float=Field(ge=-180,le=180)
    admin_capacity: int=Field(ge=1,le=10000)
    admin_ratio: int=Field(ge=1,le=100000)
    registration_open: bool
    votes_per_point: int=Field(ge=1,le=10000)
    verified_report_points: int=Field(ge=0,le=1000)
    confirmation_points: int=Field(ge=0,le=1000)
    evidence_points: int=Field(ge=0,le=1000)
    categories: list[str]=Field(min_length=1,max_length=30)
    statuses: list[str]=Field(min_length=8,max_length=30)

@router.patch('/society/settings')
async def settings(data: SettingsEdit,user=Depends(require('society_manage'))):
    repo=ScopedRepo(user)
    if not set(STATUSES).issubset(data.statuses): raise HTTPException(400,'The eight core workflow states must be retained')
    if any(not x.strip() or len(x)>50 for x in data.categories+data.statuses): raise HTTPException(400,'Category and status names must contain 1–50 characters')
    current_count=await repo.count('users',{'role':{'$in':['admin','initial_admin']},'active':True})
    if data.admin_capacity<current_count: raise HTTPException(400,f'Admin capacity must be at least {current_count}, the current number of administrators')
    value=data.model_dump()
    society_fields={k:value.pop(k) for k in ['name','location','address','population','latitude','longitude']}
    value['categories']=list(dict.fromkeys(value['categories']))
    value['statuses']=list(dict.fromkeys(value['statuses']))
    await repo.update('societies',{}, {'$set':{**society_fields,'settings':value}})
    return await repo.one('societies')

@router.get('/civic')
async def civic(user=Depends(require('read'))):
    return SimulatedCivicProvider().get(await ScopedRepo(user).one('societies'))

@router.get('/community')
async def community(user=Depends(require('read'))):
    repo=ScopedRepo(user)
    admins=await repo.many('users',{'role':{'$in':['admin','initial_admin']},'active':True},projection={'_id':0,'id':1,'name':1,'role':1,'area':1,'categories':1,'username':1})
    for admin in admins:
        admin['positive']=await repo.count('reputation',{'admin_id':admin['id'],'value':1})
        admin['negative']=await repo.count('reputation',{'admin_id':admin['id'],'value':-1})
        mine=await repo.one('reputation',{'admin_id':admin['id'],'voter_id':user['id']})
        admin['my_vote']=mine['value'] if mine else 0
        admin['workload']=await repo.count('cases',{'assigned_to':admin['id'],'status':{'$nin':['Resolved','Closed','Rejected','Merged']}})
    return {'admins':admins,'registered_residents':await repo.count('users',{'role':'resident','active':True}),'population':(await repo.one('societies'))['population']}

class Feedback(BaseModel): value: Literal[-1,0,1]
@router.post('/community/admins/{admin_id}/feedback')
async def feedback(admin_id: str,data: Feedback,user=Depends(require('feedback'))):
    repo=ScopedRepo(user)
    admin=await repo.one('users',{'id':admin_id,'role':{'$in':['admin','initial_admin']},'active':True})
    if not admin: raise HTTPException(404,'Administrator not found')
    await repo.update('reputation',{'admin_id':admin_id,'voter_id':user['id']},{'$set':{'value':data.value}},upsert=True)
    return {'ok':True,'message':'Your anonymous feedback has been recorded'}

class AdminCreate(BaseModel):
    model_config=ConfigDict(str_strip_whitespace=True,extra='forbid')
    name: str=Field(min_length=2,max_length=80)
    username: str=Field(min_length=3,max_length=60)
    email: EmailStr
    area: str=Field(min_length=1,max_length=120)
    categories: list[str]=Field(default_factory=list,max_length=30)

@router.post('/society/admins',status_code=201)
async def add_admin(data: AdminCreate,user=Depends(require('admins_manage'))):
    repo=ScopedRepo(user)
    society=await repo.one('societies')
    if await repo.count('users',{'role':{'$in':['admin','initial_admin']},'active':True})>=society['settings']['admin_capacity']: raise HTTPException(400,'Admin capacity reached. Increase the capacity in society settings first.')
    password=secrets.token_urlsafe(12)
    record={'id':uid(),'name':data.name,'username':data.username.lower(),'email':str(data.email),'area':data.area,'categories':data.categories,'role':'admin','active':True,'created_at':now(),'base_points':0,'password_hash':hash_password(password)}
    try: await repo.insert('users',record)
    except DuplicateKeyError: raise HTTPException(409,'This username already exists in your society')
    await repo.insert('audit',{'id':uid(),'actor_id':user['id'],'action':'admin_created','target_id':record['id'],'created_at':now()})
    return {'id':record['id'],'username':record['username'],'password':password,'society_code':society['code']}

class AdminResponsibility(BaseModel):
    area: str=Field(min_length=1,max_length=120)
    categories: list[str]=Field(default_factory=list,max_length=30)

@router.patch('/society/admins/{admin_id}')
async def responsibility(admin_id: str,data: AdminResponsibility,user=Depends(require('admins_manage'))):
    repo=ScopedRepo(user)
    admin=await repo.one('users',{'id':admin_id,'role':{'$in':['admin','initial_admin']}})
    if not admin: raise HTTPException(404,'Administrator not found')
    await repo.update('users',{'id':admin_id},{'$set':data.model_dump()})
    return {'ok':True}

@router.delete('/society/admins/{admin_id}')
async def remove_admin(admin_id: str,user=Depends(require('admins_manage'))):
    repo=ScopedRepo(user)
    admin=await repo.one('users',{'id':admin_id})
    if not admin: raise HTTPException(404,'Administrator not found')
    if admin['role']=='initial_admin': raise HTTPException(400,'The initial administrator cannot be removed')
    if admin['role']!='admin': raise HTTPException(400,'This user is not an administrator')
    await repo.update('users',{'id':admin_id},{'$set':{'role':'resident'}})
    await repo.update_many('cases',{'assigned_to':admin_id,'status':{'$nin':['Resolved','Closed']}},{'$set':{'assigned_to':None,'assigned_name':None}})
    await repo.insert('audit',{'id':uid(),'actor_id':user['id'],'action':'admin_removed','target_id':admin_id,'created_at':now()})
    return {'ok':True}

@router.get('/notifications')
async def notifications(user=Depends(require('read'))):
    repo=ScopedRepo(user)
    return {'items':await repo.many('notifications',{'user_id':user['id']},limit=60,sort=[('created_at',-1)]),'unread':await repo.count('notifications',{'user_id':user['id'],'read':False})}

@router.post('/notifications/read')
async def read_notifications(user=Depends(require('read'))):
    await ScopedRepo(user).update_many('notifications',{'user_id':user['id']},{'$set':{'read':True}})
    return {'ok':True}