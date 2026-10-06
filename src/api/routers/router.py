from fastapi import APIRouter

from api.routers import health, runs, transactions

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(runs.router)
api_router.include_router(transactions.router)
