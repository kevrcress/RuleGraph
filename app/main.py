"""
RuleGraph FastAPI application entry point.
"""
import logging

from fastapi import FastAPI

import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.routers import ingest, rules, admin
from app.config import settings
from app.graph.cognee_client import init_cognee

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title="RuleGraph", version="0.1.0")


@app.on_event("startup")
async def startup():
    await init_cognee()


app.include_router(ingest.router)
app.include_router(rules.router)
app.include_router(admin.router)
