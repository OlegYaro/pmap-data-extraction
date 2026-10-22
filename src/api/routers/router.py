from fastapi import APIRouter, Depends

from api.routers import admin_page, analytics, health, runs, transactions
from api.security import require_api_key

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(admin_page.router)
api_router.include_router(runs.router, dependencies=[Depends(require_api_key)])
api_router.include_router(transactions.router, dependencies=[Depends(require_api_key)])
api_router.include_router(analytics.router, dependencies=[Depends(require_api_key)])
