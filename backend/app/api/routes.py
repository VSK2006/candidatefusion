from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Body
from fastapi.responses import JSONResponse
from app.schemas import UploadResponse, OutputConfig, ExportRequest
from app.services.pipeline import process_upload
from app.services.candidate_service import (
    list_candidates,
    get_candidate,
    get_source_count,
    get_stats,
)
from app.services.projector import project_profile

router = APIRouter(prefix="/api", tags=["CandidateFusion"])


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/upload", response_model=UploadResponse)
async def upload_source(
    source_type: str = Form(...),
    file: UploadFile | None = File(None),
    reference_url: str | None = Form(None),
):
    result = await process_upload(source_type, file, reference_url)
    return UploadResponse(message=result)


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------

@router.get("/stats")
def stats():
    s = get_stats()
    s["source_count"] = get_source_count()
    return s


# ---------------------------------------------------------------------------
# Candidates list
# ---------------------------------------------------------------------------

@router.get("/candidates")
def candidates_list():
    return {"candidates": list_candidates()}


# ---------------------------------------------------------------------------
# Single candidate detail
# ---------------------------------------------------------------------------

@router.get("/candidate/{candidate_id}")
def candidate_detail(candidate_id: str):
    c = get_candidate(candidate_id)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    return c


# ---------------------------------------------------------------------------
# Export — canonical JSON with optional configurable projection
# ---------------------------------------------------------------------------

@router.post("/candidate/{candidate_id}/export")
def export_candidate(candidate_id: str, body: ExportRequest = Body(default=ExportRequest())):
    c = get_candidate(candidate_id)
    if not c:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    try:
        config = body.config or OutputConfig()
        projected = project_profile(c, config)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return JSONResponse(content=projected)


# ---------------------------------------------------------------------------
# Batch export — all candidates with optional config
# ---------------------------------------------------------------------------

@router.post("/export/batch")
def export_batch(body: ExportRequest = Body(default=ExportRequest())):
    candidates = list_candidates()
    config = body.config or OutputConfig()
    results = []
    for c in candidates:
        try:
            results.append(project_profile(c, config))
        except ValueError:
            results.append({"candidate_id": c.get("candidate_id"), "error": "projection_failed"})
    return {"count": len(results), "candidates": results}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
def health():
    return {"status": "ok", "service": "CandidateFusion"}
