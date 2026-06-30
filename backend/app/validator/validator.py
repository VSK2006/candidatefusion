from app.schemas import CandidateCreate


def validate_candidate(data: dict) -> CandidateCreate:
    # Convert nested dicts to the expected sub-schema shapes
    skills = data.get("skills", [])
    data["skills"] = [
        s if isinstance(s, dict) else {"name": s, "confidence": 0.75, "sources": []}
        for s in skills
    ]
    return CandidateCreate.model_validate(data)
