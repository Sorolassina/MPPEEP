from fastapi import APIRouter
from app.api.v1.endpoints import health, users, auth, admin, dashboard, files, rh, personnel

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(dashboard.router,  tags=["dashboard"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(rh.router, prefix="/rh", tags=["rh"])
api_router.include_router(personnel.router, prefix="/personnel", tags=["personnel"])