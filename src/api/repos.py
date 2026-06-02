import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from src.ingestion import indexing


router = APIRouter(prefix="/repos", tags=["repositories"])
logger = logging.getLogger(__name__)


class IndexRepositoryRequest(BaseModel):
    github_url: str | None = Field(default=None, description="GitHub repository URL")
    local_path: str | None = Field(default=None, description="Local repository path")
    branch: str = "main"


class IndexRepositoryResponse(BaseModel):
    repo_id: str
    status: str
    chunks: int


@router.post("/index", response_model=IndexRepositoryResponse)
def index_repository_endpoint(request: IndexRepositoryRequest):
    source = request.github_url or request.local_path
    if not source:
        raise HTTPException(
            status_code=422,
            detail=[{"msg": "Either github_url or local_path must be provided."}],
        )

    try:
        result = indexing.index_repository(source, branch=request.branch)
    except Exception as exc:
        logger.exception("Failed to index repository source=%s branch=%s", source, request.branch)
        detail = str(exc) or exc.__class__.__name__
        raise HTTPException(status_code=500, detail=detail) from exc

    return IndexRepositoryResponse(
        repo_id=result.repo_id,
        status=result.status,
        chunks=result.chunks,
    )
