from fastapi import APIRouter

from app.api.v1.endpoints import (
    admin,
    aide,
    auth,
    besoins,
    budget,
    dashboard,
    files,
    health,
    legal,
    performance,
    personnel,
    referentiels,
    rh,
    stock,
    users,
    workflow_admin,
    message,
)

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(users.router, prefix="/users", tags=["users"])
api_router.include_router(auth.router, tags=["auth"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(dashboard.router, tags=["dashboard"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(rh.router, prefix="/rh", tags=["rh"])
api_router.include_router(personnel.router, prefix="/personnel", tags=["personnel"])
api_router.include_router(referentiels.router, prefix="/referentiels", tags=["referentiels"])
api_router.include_router(besoins.router, prefix="/besoins", tags=["besoins"])
api_router.include_router(budget.router, prefix="/budget", tags=["budget"])
api_router.include_router(stock.router, prefix="/stock", tags=["stock"])
api_router.include_router(performance.router, prefix="/performance", tags=["performance"])
api_router.include_router(workflow_admin.router, prefix="/admin", tags=["workflow-admin"])
api_router.include_router(aide.router, prefix="/aide", tags=["aide"])
api_router.include_router(legal.router, tags=["legal"])
api_router.include_router(message.router, prefix="/messages", tags=["messages"])
# access_denied est maintenant dans admin.router
