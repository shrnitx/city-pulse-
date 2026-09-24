import logging
import os
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from core import client
from auth_routes import router as auth_router
from society_routes import router as society_router
from problem_routes import router as problem_router
from admin_routes import router as admin_router
from media_routes import router as media_router
from seed import seed_demo

app = FastAPI(title="CityPulse Civic Intelligence")
app.add_middleware(CORSMiddleware, allow_origins=os.environ['CORS_ORIGINS'].split(','), allow_credentials=False, allow_methods=['*'], allow_headers=['*'])
for router in [auth_router, society_router, problem_router, admin_router, media_router]:
    app.include_router(router, prefix='/api')

@app.on_event('startup')
async def startup():
    await seed_demo()

@app.on_event('shutdown')
async def shutdown():
    client.close()

@app.get('/api/health')
async def health():
    await client.admin.command('ping')
    return {'status': 'ok', 'civic_data': 'simulated', 'ai': 'simulated'}

logging.basicConfig(level=logging.INFO)