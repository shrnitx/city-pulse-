import os
import asyncio
import requests
from pathlib import Path
from fastapi import APIRouter,Depends,HTTPException,UploadFile,File,Response
from core import ScopedRepo,uid,now
from auth_routes import require
from intelligence import analyze

router=APIRouter()
STORAGE_BASE=(os.environ.get('INTEGRATION_PROXY_URL') or '').strip() or 'https://integrations.emergentagent.com'
STORAGE_URL=STORAGE_BASE.rstrip('/')+'/objstore/api/v1/storage'
storage_key=None
def init_storage(force=False):
    global storage_key
    if storage_key and not force:return storage_key
    r=requests.post(STORAGE_URL+'/init',json={'emergent_key':os.environ['EMERGENT_LLM_KEY']},timeout=30)
    r.raise_for_status();storage_key=r.json()['storage_key'];return storage_key
def put_object(path,data,mime):
    r=requests.put(f'{STORAGE_URL}/objects/{path}',headers={'X-Storage-Key':init_storage(),'Content-Type':mime},data=data,timeout=120)
    if r.status_code==404:r=requests.put(f'{STORAGE_URL}/objects/{path}',headers={'X-Storage-Key':init_storage(True),'Content-Type':mime},data=data,timeout=120)
    r.raise_for_status();return r.json()
def get_object(path):
    r=requests.get(f'{STORAGE_URL}/objects/{path}',headers={'X-Storage-Key':init_storage()},timeout=60)
    if r.status_code==404:r=requests.get(f'{STORAGE_URL}/objects/{path}',headers={'X-Storage-Key':init_storage(True)},timeout=60)
    r.raise_for_status();return r.content

def detect_type(data):
    if data.startswith(b'\x89PNG\r\n\x1a\n'):return 'image/png','png'
    if data.startswith(b'\xff\xd8\xff'):return 'image/jpeg','jpg'
    if data[:4]==b'RIFF' and data[8:12]==b'WEBP':return 'image/webp','webp'
    if len(data)>12 and data[4:8]==b'ftyp':return 'video/mp4','mp4'
    if data.startswith(b'\x1a\x45\xdf\xa3'):return 'video/webm','webm'
    raise HTTPException(400,'Upload a valid JPG, PNG, WebP, MP4, or WebM file')

@router.post('/files',status_code=201)
async def upload(file: UploadFile=File(...),user=Depends(require('report'))):
    data=await file.read(10*1024*1024+1)
    if len(data)>10*1024*1024:raise HTTPException(413,'Evidence files must be 10 MB or smaller')
    mime,ext=detect_type(data)
    file_id=uid()
    path=f"{os.environ['CITYPULSE_STORAGE_PREFIX']}/uploads/{user['society_id']}/{user['id']}/{file_id}.{ext}"
    try:result=await asyncio.to_thread(put_object,path,data,mime)
    except requests.RequestException:raise HTTPException(503,'Evidence storage is temporarily unavailable. Please try again.')
    await ScopedRepo(user).insert('files',{'id':file_id,'owner_id':user['id'],'case_id':None,'storage_path':result['path'],'original_filename':Path(file.filename or f'evidence.{ext}').name[:150],'content_type':mime,'size':len(data),'is_deleted':False,'created_at':now()})
    return {'id':file_id,'original_filename':file.filename,'content_type':mime}

@router.get('/files/{file_id}')
async def download(file_id: str,user=Depends(require('read'))):
    record=await ScopedRepo(user).one('files',{'id':file_id,'is_deleted':False})
    if not record or (record['case_id'] is None and record['owner_id']!=user['id']):raise HTTPException(404,'Evidence not found')
    if record.get('demo_asset'):
        path=Path(__file__).parent/'sample_assets'/record['demo_asset']
        if not path.exists():raise HTTPException(404,'Sample evidence unavailable')
        data=path.read_bytes()
    else:
        try:data=await asyncio.to_thread(get_object,record['storage_path'])
        except requests.RequestException:raise HTTPException(503,'Evidence could not be retrieved. Please try again.')
    return Response(content=data,media_type=record['content_type'],headers={'Cache-Control':'private, max-age=300','X-Content-Type-Options':'nosniff'})

@router.delete('/files/{file_id}')
async def discard(file_id: str,user=Depends(require('report'))):
    repo=ScopedRepo(user)
    record=await repo.one('files',{'id':file_id,'owner_id':user['id'],'case_id':None})
    if not record:raise HTTPException(404,'Unattached evidence not found')
    await repo.update('files',{'id':file_id},{'$set':{'is_deleted':True}})
    return {'ok':True}