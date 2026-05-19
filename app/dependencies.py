"""
FastAPI dependency helpers.
Re-exports get_db for convenience so routers can import from a single place.
"""
from app.database import get_db

__all__ = ["get_db"]
