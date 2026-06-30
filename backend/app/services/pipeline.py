from fastapi import UploadFile
from .parser import parse_source, canonicalize_source
from .normalizer import normalize_profile
from ..validator.validator import validate_candidate
from .candidate_service import persist_candidate


async def process_upload(
    source_type: str,
    file: UploadFile | None,
    reference_url: str | None,
) -> str:
    raw_payload = await parse_source(source_type, file, reference_url)
    canonical = canonicalize_source(raw_payload, source_type)

    file_name = file.filename if file else None

    if isinstance(canonical, list):
        saved = []
        for record in canonical:
            normalized = normalize_profile(record, source_type)
            candidate_data = validate_candidate(normalized)
            saved.append(persist_candidate(candidate_data, source_type, file_name))
        return f"Saved {len(saved)} candidate(s) from {source_type} source."

    normalized = normalize_profile(canonical, source_type)
    candidate_data = validate_candidate(normalized)
    saved = persist_candidate(candidate_data, source_type, file_name)
    return f"Saved candidate '{saved.full_name}' from {source_type} source."
