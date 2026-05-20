"""
RuleGraph FastAPI application entry point.
"""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models  # noqa: F401 — registers all ORM models with Base before create_all
from app.routers import ingest, rules, admin, auth, webhooks
from app.routers import documents, conflicts, coverage, terminology, diff
from app.routers import chat, subscriptions, notifications
from app.config import settings
from app.graph.cognee_client import init_cognee, ingest_skills

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s — %(message)s",
)

app = FastAPI(title="RuleGraph", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_cognee()
    await ingest_skills()


# Public endpoints (no JWT required)
app.include_router(auth.router)
app.include_router(webhooks.router)

# Protected endpoints (JWT required per route dependency)
app.include_router(ingest.router)
app.include_router(rules.router)
app.include_router(admin.router)
app.include_router(documents.router)
app.include_router(conflicts.router)
app.include_router(coverage.router)
app.include_router(terminology.router)
app.include_router(diff.router)
app.include_router(chat.router)
app.include_router(subscriptions.router)
app.include_router(notifications.router)
