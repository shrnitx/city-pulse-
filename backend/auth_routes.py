import hashlib
import hmac
import secrets
import os
from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field, ConfigDict
from pymongo.errors import DuplicateKeyError
from core import db, ScopedRepo, now, uid, authorize, point_total

router = APIRouter()
bearer = HTTPBearer(auto_error=False)
def hash_password(password):
    salt = secrets.token_hex(16)
    return salt + ':' + hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 220000).hex()
def check_password(password, stored):
    try:
        salt, digest = stored.split(':')
        return hmac.compare_digest(digest, hashlib.pbkdf2_hmac('sha256', password.encode(), salt.encode(), 220000).hex())
    except (ValueError, AttributeError): return False

async def current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    if not credentials: raise HTTPException(401, 'Please sign in to continue')
    session = await db.sessions.find_one({'token_hash': hashlib.sha256(credentials.credentials.encode()).hexdigest(), 'expires_at': {'$gt': datetime.now(timezone.utc)}}, {'_id': 0})
    if not session: raise HTTPException(401, 'Your session expired. Please sign in again')
    user = await db.users.find_one({'id': session['user_id'], 'active': True}, {'_id': 0, 'password_hash': 0})
    if not user: raise HTTPException(401, 'Account is no longer active')
    return user

def require(action):
    async def dependency(user=Depends(current_user)):
        authorize(user, action)
        return user
    return dependency

def public_user(user):
    return {k: user.get(k, '') for k in ['id','society_id','username','name','email','role','area','categories','base_points']}

async def session_response(user):
    token = secrets.token_urlsafe(40)
    await db.sessions.insert_one({'token_hash': hashlib.sha256(token.encode()).hexdigest(), 'user_id': user['id'], 'expires_at': datetime.now(timezone.utc)+timedelta(days=7)})
    society = await ScopedRepo(user).one('societies')
    return {'token': token, 'user': {**public_user(user), **await point_total(user)}, 'society': society}

class Login(BaseModel):
    society_code: str = Field(min_length=3, max_length=30)
    username: str = Field(min_length=2, max_length=60)
    password: str = Field(min_length=1, max_length=128)
class Register(Login):
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=2, max_length=80)
    area: str = Field(default='', max_length=120)
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)

@router.post('/auth/login')
async def login(data: Login):
    society = await db.societies.find_one({'code': data.society_code.strip().upper()}, {'_id': 0})
    user = await db.users.find_one({'society_id': society['id'], 'username': data.username.strip().lower(), 'active': True}, {'_id': 0}) if society else None
    if not user or not check_password(data.password, user.get('password_hash')): raise HTTPException(401, 'Society code, username, or password is incorrect')
    return await session_response(user)

@router.post('/auth/register', status_code=201)
async def register(data: Register):
    society = await db.societies.find_one({'code': data.society_code.strip().upper()}, {'_id': 0})
    if not society: raise HTTPException(404, 'Society code not found')
    if not society['settings']['registration_open']: raise HTTPException(403, 'Resident registration is currently closed')
    user = {'id': uid(), 'society_id': society['id'], 'username': data.username.lower(), 'name': data.name, 'area': data.area, 'email': '', 'role': 'resident', 'categories': [], 'active': True, 'base_points': 0, 'created_at': now(), 'password_hash': hash_password(data.password)}
    try: await ScopedRepo(user).insert('users', user)
    except DuplicateKeyError: raise HTTPException(409, 'This username is already taken in your society')
    return await session_response(user)

@router.get('/auth/me')
async def me(user=Depends(require('read'))):
    return {'user': {**public_user(user), **await point_total(user)}, 'society': await ScopedRepo(user).one('societies')}

@router.post('/auth/logout')
async def logout(user=Depends(require('read')), credentials: HTTPAuthorizationCredentials = Depends(bearer)):
    await db.sessions.delete_one({'token_hash': hashlib.sha256(credentials.credentials.encode()).hexdigest()})
    return {'ok': True}

@router.get('/auth/demo')
async def demo():
    return {'society_code': 'GV-48291', 'password': os.environ['CITYPULSE_DEMO_PASSWORD'], 'accounts': [{'username':'elena','name':'Elena Vance','role':'resident'}, {'username':'blockb.admin','name':'Arjun Mehta','role':'admin'}, {'username':'owner','name':'Society Owner','role':'initial_admin'}]}

class ProfileEdit(BaseModel):
    name: str = Field(min_length=2, max_length=80)
    area: str = Field(default='', max_length=120)
class PasswordEdit(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)

@router.patch('/auth/profile')
async def edit_profile(data: ProfileEdit, user=Depends(require('profile'))):
    await ScopedRepo(user).update('users', {'id': user['id']}, {'$set': data.model_dump()})
    return {'ok': True}

@router.post('/auth/password')
async def edit_password(data: PasswordEdit, user=Depends(require('profile'))):
    record = await ScopedRepo(user).one('users', {'id': user['id']})
    if record.get('demo'): raise HTTPException(400, 'Shared demo account passwords cannot be changed. Create a society or register your own account.')
    if not check_password(data.current_password, record['password_hash']): raise HTTPException(400, 'Current password is incorrect')
    await ScopedRepo(user).update('users', {'id': user['id']}, {'$set': {'password_hash': hash_password(data.new_password)}})
    return {'ok': True}