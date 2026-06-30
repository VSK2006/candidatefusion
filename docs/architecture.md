# CandidateFusion Architecture

## Pipeline

Each upload flows through `backend/app/services/`:

1. **Parse** (`parser.py`) — Dispatches by source type (CSV, ATS JSON, resume PDF/DOCX, recruiter notes, GitHub URL) into a raw intermediate dict. Unstructured sources (resume, notes) are routed through the extractor.
2. **Extract** (`extractor.py`) — Regex-based field extraction from free text: emails, phones, links, name, skills (60+ keyword taxonomy), experience, education.
3. **Normalize** (`normalizer.py`) — Standardizes phones to E.164, dates to YYYY-MM, locations to city/region/ISO-3166 country, skill names to canonical casing. Computes per-source confidence and the Fusion Score.
4. **Dedupe & Merge** (`candidate_service.py`) — Matches existing candidates by email (exact), phone (exact, E.164), or fuzzy name (rapidfuzz token_sort_ratio >= 85). On match, merges skills (confidence boosted per additional confirming source), deduplicates experience by company+title, deduplicates education by institution.
5. **Validate** (`validator/validator.py`) — Coerces and validates against the Pydantic `CandidateCreate` schema before persistence.
6. **Store** (`models.py` / `db.py`) — Persists to SQLite via SQLAlchemy. Candidate, Skill, Experience, Education tables, plus provenance records tracking which source contributed which field.
7. **Project** (`projector.py`) — Runtime-configurable output layer. Given an `OutputConfig`, resolves a JSONPath-like `from` expression per field, applies optional normalization, and handles missing values per the `on_missing` policy. This is what lets a consumer reshape the canonical schema without backend changes.

## API Endpoints

- `POST /api/upload` — Upload a file or GitHub URL (`source_type` + `file` or `reference_url` form fields)
- `GET /api/candidates` — List all candidates, full canonical schema
- `GET /api/candidate/{id}` — Single candidate by UUID
- `POST /api/candidate/{id}/export` — Export one candidate with an optional `OutputConfig` body
- `POST /api/export/batch` — Export all candidates with a shared `OutputConfig`
- `GET /api/stats` — Aggregate counts for the dashboard
- `GET /api/health` — Health check

## Frontend

- `UploadPanel` — Source type selector + drag-and-drop file upload / GitHub URL input
- `Dashboard` — Aggregate stats strip (candidate count, avg Fusion Score, top skill, upload count)
- `CandidateList` — Cards sorted by Fusion Score, with search, skill badges (multi-source indicator), expandable work history/education/provenance
- `ExportModal` — Full canonical export or custom `OutputConfig` projection, with copy-to-clipboard
- `PipelineVisualizer` — Static diagram of the 7 pipeline stages

See [README.md](../README.md) for run instructions and the full API/config reference.
