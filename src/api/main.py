import taskiq_fastapi
from fastapi import FastAPI

from api.routers.router import api_router
from core import setup_logging
from jobs.broker import broker

setup_logging()

app = FastAPI(title="RCN Extraction")
taskiq_fastapi.init(broker, "api.main:app")

app.include_router(api_router)
