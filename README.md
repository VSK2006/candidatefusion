# CandidateFusion — Multi-Source Candidate Data Transformer

A FastAPI + React pipeline that ingests candidate data from five heterogeneous sources (CSV, ATS JSON, Resume PDF/DOCX, Recruiter Notes, GitHub URL), deduplicates and merges records, and exposes a **runtime-configurable output projection layer** (the "Required Twist") that lets any consumer reshape the schema without touching the backend.

---

## Quick-start

### Prerequisites

| Tool | Minimum version |
|---|---|
| Python | 3.11 |
| Node.js | 18 |
| npm | 9 |

### 1 — Backend

```bash
cd backend

# Create & activate virtual environment
python -m venv .venv

# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
source .venv/bin/activate

# Install dependencies
python -m pip install -r requirements.txt

# Start the API server (auto-creates SQLite DB on first run)
uvicorn app.main:app --reload --port 8000
```

The API is now available at `http://localhost:8000`.
Interactive docs: `http://localhost:8000/docs`

### 2 — Frontend

Open a **new terminal** (keep the backend running).

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Running Tests

```bash
cd backend
python -m pytest tests/ -v
```

18 of 18 tests pass. The one GitHub test is skipped unless a live network is present.

---

## Generating Sample Outputs

From the **project root** (not `backend/`):

```bash
python generate_sample_outputs.py
```

This resets the DB, ingests all three sample input files, and writes three JSON files to `sample_outputs/`.

---

## Supported Source Types

| Source | Upload type | What it parses |
|---|---|---|
| **CSV** | File upload | Columns: name, email, phone, skills (comma-separated), headline, current_company, location |
| **ATS JSON** | File upload | Structured JSON with experience / education arrays |
| **Resume (PDF / DOCX)** | File upload | Free-text extraction: name, email, phone, skills, experience, education |
| **Recruiter Notes** | File upload (`.txt`) | Same free-text extraction as resume |
| **GitHub URL** | URL input | Fetches `/users/{username}` + `/repos` via GitHub REST API; extracts bio, languages, repo count, location |

**Deduplication** is automatic: records are merged by email (exact match), phone (E.164 match), or name (fuzzy >= 85 token-sort ratio). Skills confirmed across multiple sources get a confidence boost (+0.05 per additional source, max 1.0).

---

## Architecture

```
sample_inputs/          Raw test files (CSV, ATS JSON, notes.txt)
sample_outputs/         Pre-generated output files

backend/
  app/
    main.py             FastAPI app, CORS, lifespan
    db.py               SQLAlchemy engine + auto-migration
    models.py           Candidate, Skill, Experience, Education ORM tables
    schemas.py          Pydantic v2 schemas (CandidateCreate, OutputConfig, ...)
    api/routes.py       All REST endpoints
    services/
      parser.py         Source dispatching -> intermediate canonical dict
      extractor.py      Regex-based field extraction from unstructured text
      normalizer.py     E.164 phones, YYYY-MM dates, ISO-3166 countries, Fusion Score
      candidate_service.py  Deduplication, merge, persist, list
      pipeline.py       Orchestrates parse -> normalize -> persist
      projector.py      Required Twist: runtime output projection

frontend/
  src/
    components/
      UploadPanel.tsx     File + URL upload form
      CandidateList.tsx   Cards with Fusion Score bar, skill badges, expandable history
      ExportModal.tsx     Default JSON / Custom Config tabs with copy button
      Dashboard.tsx       Stats header (total candidates, sources, avg. Fusion Score)
      PipelineVisualizer.tsx  7-step pipeline diagram

tests/
  test_pipeline.py        18 integration + unit tests
```

---

## Fusion Score

Every candidate gets a composite quality metric (0.0 to 1.0):

```
Fusion Score = 0.40 * completeness + 0.40 * source_confidence + 0.20 * cross_source_verification
```

- **Completeness** — fraction of key fields populated (name, email, phone, location, headline, years_experience, skills, experience)
- **Source confidence** — per-source weight: ATS 0.90 · GitHub 0.85 · CSV 0.80 · Resume 0.65 · Notes 0.55
- **Cross-source verification** — fraction of skills confirmed by more than one source

---

## Required Twist — Configurable Output Projection

Every candidate export accepts an `OutputConfig` body that reshapes the response at runtime without changing the stored data.

### API endpoints

```
POST /api/candidate/{candidate_id}/export
POST /api/export/batch          (array of candidate_ids + shared config)
```

### Example config

```json
{
  "fields": [
    { "path": "full_name",        "type": "string",    "required": true },
    { "path": "primary_email",    "from": "emails[0]", "type": "string" },
    { "path": "phone",            "from": "phones[0]", "type": "string",   "normalize": "E164" },
    { "path": "location_city",    "from": "location.city",    "type": "string" },
    { "path": "location_country", "from": "location.country", "type": "string" },
    { "path": "skill_names",      "from": "skills[].name",    "type": "string[]" },
    { "path": "years_experience", "type": "number" }
  ],
  "include_confidence": true,
  "include_provenance": false,
  "on_missing": "null"
}
```

| Config key | Values | Effect |
|---|---|---|
| `path` | output field name | Key in the output object |
| `from` | JSONPath-like source | `field`, `nested.field`, `array[0]`, `array[].subfield` |
| `normalize` | `"E164"`, `"canonical"` | Phone -> E.164; skill names -> canonical casing |
| `on_missing` | `"null"` / `"omit"` / `"error"` | Behaviour when the source field is absent |
| `include_confidence` | bool | Append `_confidence` per field |
| `include_provenance` | bool | Append `_provenance` array per field |

Omit the `fields` array to receive the full canonical output.

---

## REST API Reference

| Method | Path | Description |
|---|---|---|
| `GET` | `/api/health` | Health check |
| `GET` | `/api/stats` | `{total_candidates, total_uploads, source_count}` |
| `POST` | `/api/upload` | Upload a file (`source_type` form field) |
| `POST` | `/api/upload-url` | Ingest a GitHub URL (`url` + `source_type` body) |
| `GET` | `/api/candidates` | List all candidates (full canonical schema) |
| `GET` | `/api/candidate/{id}` | Get one candidate by UUID |
| `POST` | `/api/candidate/{id}/export` | Export with custom `OutputConfig` |
| `POST` | `/api/export/batch` | Batch export `{candidate_ids, config}` |

---

## Sample Outputs (pre-generated)

| File | Description |
|---|---|
| `sample_outputs/default_output.json` | All 5 candidates, full canonical schema |
| `sample_outputs/custom_config_output.json` | Field-selected and renamed output |
| `sample_outputs/skills_only_output.json` | Skills-only projection (`on_missing: omit`) |

---

## Design Notes

**Why fuzzy deduplication?**
Real recruiting data has inconsistent spacing, middle names, and abbreviations. `rapidfuzz.token_sort_ratio` at threshold 85 catches "Aisha Patel" vs "Aisha P." while rejecting false positives like two different Johns.

**Why ISO-3166 alpha-2 for country codes?**
Downstream ATS systems almost universally expect two-letter codes. Normalizing at ingest time means every consumer gets the same format regardless of whether the source said "India", "IN", or "india".

**Why a separate Fusion Score instead of just `overall_confidence`?**
Source confidence alone rewards high-quality sources unconditionally. Fusion Score also penalises sparse profiles (missing phone, location, experience) and rewards cross-source corroboration, giving recruiters a richer quality signal for prioritization.

**Why auto-migration in `db.py`?**
SQLite doesn't support `ALTER TABLE ADD COLUMN` well and has no built-in migration tool. The lightweight schema check (`_schema_is_current`) avoids requiring developers to manually delete the DB file after a schema change during development.
