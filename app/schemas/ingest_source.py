"""Pydantic schemas for ingest source management."""
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel


class IngestSourceCreate(BaseModel):
    name: str
    source_type: str = "github_repo"
    repo_url: str
    branch: str = "main"
    paths: Optional[list[str]] = None
    exclude: Optional[list[str]] = None
    test_paths: Optional[list[str]] = None
    pat: Optional[str] = None  # plaintext — encrypted before storage


class IngestSourceUpdate(BaseModel):
    name: Optional[str] = None
    repo_url: Optional[str] = None
    branch: Optional[str] = None
    paths: Optional[list[str]] = None
    exclude: Optional[list[str]] = None
    test_paths: Optional[list[str]] = None
    pat: Optional[str] = None  # if provided, re-encrypted
    status: Optional[str] = None


class IngestSourceResponse(BaseModel):
    id: uuid.UUID
    name: str
    source_type: str
    repo_url: str
    branch: str
    paths: Optional[list[str]]
    exclude: Optional[list[str]]
    test_paths: Optional[list[str]]
    has_pat: bool
    created_at: Optional[datetime]
    last_ingested_at: Optional[datetime]
    status: str
    ingest_status: str
    ingest_error: Optional[str]
    ingest_progress: Optional[str] = None
    last_commit_sha: Optional[str] = None
    run_status: Optional[str] = None
    done_file_count: int = 0
    total_file_count: int = 0
    run_is_stale: bool = False
    can_resume: bool = False

    model_config = {"from_attributes": True}


class PaginatedSources(BaseModel):
    items: list[IngestSourceResponse]
    total: int


class IngestTriggerResponse(BaseModel):
    status: str
    source_name: str
    message: str
    run_id: Optional[str] = None
