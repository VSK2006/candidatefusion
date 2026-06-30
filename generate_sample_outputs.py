"""
Generates sample_outputs/ by running all sample inputs through the pipeline.
Run from the project root:  python generate_sample_outputs.py
"""
import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

from app.services.pipeline import process_upload
from app.services.candidate_service import list_candidates
from app.services.projector import project_profile
from app.schemas import OutputConfig, OutputConfigField


OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "sample_outputs")
os.makedirs(OUTPUT_DIR, exist_ok=True)


class FakeUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self) -> bytes:
        return self._content


def _load(path: str) -> bytes:
    with open(path, "rb") as f:
        return f.read()


async def main():
    # Start with a clean DB so output only reflects sample inputs
    from app.db import engine
    from app.models import Base
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("DB reset — starting fresh.")

    base = os.path.dirname(__file__)
    inputs = os.path.join(base, "sample_inputs")

    print("=" * 60)
    print("CandidateFusion — Sample Output Generator")
    print("=" * 60)

    # ── 1. CSV ────────────────────────────────────────────────────
    csv_path = os.path.join(inputs, "sample.csv")
    print(f"\n[1/3] Ingesting CSV: {csv_path}")
    upload = FakeUpload("sample.csv", _load(csv_path))
    msg = await process_upload("csv", upload, None)
    print(f"      -> {msg}")

    # ── 2. ATS JSON ───────────────────────────────────────────────
    ats_path = os.path.join(inputs, "sample_ats.json")
    print(f"\n[2/3] Ingesting ATS JSON: {ats_path}")
    upload = FakeUpload("sample_ats.json", _load(ats_path))
    msg = await process_upload("ats", upload, None)
    print(f"      -> {msg}")

    # ── 3. Recruiter notes ────────────────────────────────────────
    notes_path = os.path.join(inputs, "notes.txt")
    print(f"\n[3/3] Ingesting recruiter notes: {notes_path}")
    upload = FakeUpload("notes.txt", _load(notes_path))
    msg = await process_upload("notes", upload, None)
    print(f"      -> {msg}")

    # ── Default output (all candidates) ──────────────────────────
    print("\n--- Generating default output ---")
    candidates = list_candidates()
    default_output = {"count": len(candidates), "candidates": candidates}

    default_path = os.path.join(OUTPUT_DIR, "default_output.json")
    with open(default_path, "w", encoding="utf-8") as f:
        json.dump(default_output, f, indent=2, default=str)
    print(f"Saved -> {default_path}  ({len(candidates)} candidates)")

    # ── Custom config output ──────────────────────────────────────
    print("\n--- Generating custom config output ---")
    custom_config = OutputConfig(
        fields=[
            OutputConfigField(path="full_name", type="string", required=True),
            OutputConfigField(**{"path": "primary_email", "from": "emails[0]", "type": "string", "required": True}),
            OutputConfigField(**{"path": "phone", "from": "phones[0]", "type": "string", "normalize": "E164"}),
            OutputConfigField(**{"path": "location_city", "from": "location.city", "type": "string"}),
            OutputConfigField(**{"path": "location_country", "from": "location.country", "type": "string"}),
            OutputConfigField(**{"path": "skills", "from": "skills[].name", "type": "string[]", "normalize": "canonical"}),
            OutputConfigField(path="headline", type="string"),
            OutputConfigField(path="years_experience", type="number"),
        ],
        include_confidence=True,
        include_provenance=False,
        on_missing="null",
    )

    projected = []
    for c in candidates:
        projected.append(project_profile(c, custom_config))

    custom_path = os.path.join(OUTPUT_DIR, "custom_config_output.json")
    with open(custom_path, "w", encoding="utf-8") as f:
        json.dump({"config": custom_config.model_dump(), "count": len(projected), "candidates": projected}, f, indent=2, default=str)
    print(f"Saved -> {custom_path}")

    # ── Skills-only config ────────────────────────────────────────
    print("\n--- Generating skills-only config output ---")
    skills_config = OutputConfig(
        fields=[
            OutputConfigField(path="full_name", type="string"),
            OutputConfigField(**{"path": "skills", "from": "skills[].name", "type": "string[]"}),
            OutputConfigField(path="headline", type="string"),
        ],
        include_confidence=False,
        include_provenance=False,
        on_missing="omit",
    )
    skills_projected = [project_profile(c, skills_config) for c in candidates]
    skills_path = os.path.join(OUTPUT_DIR, "skills_only_output.json")
    with open(skills_path, "w", encoding="utf-8") as f:
        json.dump({"count": len(skills_projected), "candidates": skills_projected}, f, indent=2)
    print(f"Saved -> {skills_path}")

    print("\n" + "=" * 60)
    print(f"Done. {len(candidates)} candidates · 3 output files in sample_outputs/")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
