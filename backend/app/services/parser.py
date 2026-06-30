"""
Parser: raw bytes/URL → source payload → canonical dict.

Supports:
  csv      — Recruiter CSV export (structured)
  ats      — ATS JSON blob (structured)
  resume   — PDF / DOCX / TXT (unstructured)
  notes    — Recruiter notes .txt (unstructured)
  github   — GitHub profile URL (REST API)
"""
import csv
import io
import json
import re
import httpx
from urllib.parse import urlparse
from fastapi import UploadFile, HTTPException
from typing import Any

from app.services.extractor import extract_from_text


# ---------------------------------------------------------------------------
# Structured parsers
# ---------------------------------------------------------------------------

async def _parse_csv(file: UploadFile) -> dict[str, Any]:
    content = await file.read()
    text = content.decode("utf-8", errors="replace")
    reader = csv.DictReader(text.splitlines())
    return {"records": [row for row in reader]}


async def _parse_json(file: UploadFile) -> dict[str, Any]:
    content = await file.read()
    try:
        return json.loads(content.decode("utf-8", errors="replace"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail=f"Invalid JSON: {exc}")


# ---------------------------------------------------------------------------
# Unstructured parsers
# ---------------------------------------------------------------------------

async def _extract_text(file: UploadFile) -> str:
    content = await file.read()
    filename = (file.filename or "").lower()

    # PDF
    if filename.endswith(".pdf"):
        try:
            import pdfplumber
            with pdfplumber.open(io.BytesIO(content)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        except Exception:
            pass  # fall through to plain-text decode

    # DOCX
    if filename.endswith(".docx"):
        try:
            import docx as python_docx
            doc = python_docx.Document(io.BytesIO(content))
            return "\n".join(p.text for p in doc.paragraphs)
        except Exception:
            pass

    # Plain text (or fallback)
    return content.decode("utf-8", errors="replace")


async def _parse_text_source(file: UploadFile) -> dict[str, Any]:
    text = await _extract_text(file)
    return {"text": text, "filename": file.filename}


# ---------------------------------------------------------------------------
# GitHub parser
# ---------------------------------------------------------------------------

async def _parse_github(url: str) -> dict[str, Any]:
    parsed = urlparse(url if '://' in url else f'https://{url}')
    hostname = (parsed.hostname or '').lower()
    if hostname not in ('github.com', 'www.github.com'):
        raise HTTPException(status_code=400, detail="URL must be a github.com profile link.")

    match = re.match(r'^/([^/?#\s]+)/?$', parsed.path)
    if not match:
        raise HTTPException(status_code=400, detail="Cannot extract a GitHub username from the URL.")
    username = match.group(1)

    async with httpx.AsyncClient(timeout=12.0) as client:
        profile_resp = await client.get(
            f"https://api.github.com/users/{username}",
            headers={"Accept": "application/vnd.github+json"},
        )
    if profile_resp.status_code == 404:
        raise HTTPException(status_code=404, detail=f"GitHub user '{username}' not found.")
    if profile_resp.status_code != 200:
        raise HTTPException(status_code=502, detail=f"GitHub API returned {profile_resp.status_code}.")
    profile = profile_resp.json()

    # Fetch repos for language data
    async with httpx.AsyncClient(timeout=12.0) as client:
        repos_resp = await client.get(
            f"https://api.github.com/users/{username}/repos",
            params={"per_page": 50, "sort": "pushed"},
            headers={"Accept": "application/vnd.github+json"},
        )
    repos = repos_resp.json() if repos_resp.status_code == 200 else []

    languages: dict[str, int] = {}
    for repo in repos:
        lang = repo.get("language")
        if lang:
            languages[lang] = languages.get(lang, 0) + 1

    return {"source_url": url, "profile": profile, "languages": languages}


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------

async def parse_source(
    source_type: str,
    file: UploadFile | None,
    reference_url: str | None,
) -> dict[str, Any]:
    if source_type == "csv" and file:
        return await _parse_csv(file)
    if source_type == "ats" and file:
        return await _parse_json(file)
    if source_type in {"resume", "notes"} and file:
        return await _parse_text_source(file)
    if source_type == "github" and reference_url:
        return await _parse_github(reference_url)

    if source_type == "github":
        raise HTTPException(status_code=400, detail="GitHub source requires a URL.")
    raise HTTPException(
        status_code=400,
        detail=f"Source type '{source_type}' requires a file upload.",
    )


# ---------------------------------------------------------------------------
# Canonicalization — source payload → intermediate canonical dict
# ---------------------------------------------------------------------------

def _coerce_list(value: Any) -> list:
    if isinstance(value, list):
        return value
    if isinstance(value, str) and value:
        return [value]
    return []


def canonicalize_source(
    payload: dict[str, Any], source_type: str
) -> dict[str, Any] | list[dict[str, Any]]:

    # ── CSV ──────────────────────────────────────────────────────────────────
    if source_type == "csv":
        records: list[dict] = []
        for row in payload.get("records", []):
            skills_raw = row.get("skills") or ""
            records.append({
                "full_name": row.get("name") or row.get("full_name") or row.get("candidate_name"),
                "emails": [row["email"]] if row.get("email") else [],
                "phones": [row["phone"]] if row.get("phone") else [],
                "location_str": row.get("location") or row.get("city"),
                "links": {
                    "github": row.get("github"),
                    "linkedin": row.get("linkedin"),
                    "portfolio": row.get("portfolio"),
                    "other": [],
                },
                "headline": row.get("headline") or row.get("title"),
                "years_experience": None,
                "skills": [s.strip() for s in skills_raw.split(",") if s.strip()],
                "experience": [
                    {
                        "company": row.get("current_company") or row.get("company"),
                        "title": row.get("title") or row.get("headline"),
                        "start": row.get("start_date"),
                        "end": row.get("end_date"),
                        "summary": row.get("experience") or row.get("summary"),
                    }
                ] if (row.get("current_company") or row.get("company")) else [],
                "education": [],
                "provenance": [
                    {"field": "full_name", "source": "csv", "method": "direct_mapping"},
                    {"field": "emails", "source": "csv", "method": "direct_mapping"},
                ],
            })
        return records

    # ── ATS JSON ─────────────────────────────────────────────────────────────
    if source_type == "ats":
        p = payload if isinstance(payload, dict) else {}
        emails = _coerce_list(p.get("emails") or p.get("email"))
        phones = _coerce_list(p.get("phones") or p.get("phone"))
        skills_raw = p.get("skills") or p.get("technical_skills") or []

        # ATS might provide structured experience
        exp_raw = p.get("experience") or p.get("work_experience") or []
        experience = [
            {
                "company": e.get("company") or e.get("employer"),
                "title": e.get("title") or e.get("role") or e.get("position"),
                "start": e.get("start") or e.get("start_date"),
                "end": e.get("end") or e.get("end_date"),
                "summary": e.get("summary") or e.get("description"),
            }
            for e in exp_raw if isinstance(e, dict)
        ]

        edu_raw = p.get("education") or []
        education = [
            {
                "institution": e.get("institution") or e.get("school") or e.get("university"),
                "degree": e.get("degree"),
                "field": e.get("field") or e.get("major"),
                "end_year": e.get("end_year") or e.get("graduation_year"),
            }
            for e in edu_raw if isinstance(e, dict)
        ]

        return {
            "full_name": p.get("name") or p.get("full_name") or p.get("candidate_name"),
            "emails": emails,
            "phones": phones,
            "location_str": p.get("location") or p.get("city"),
            "links": {
                "github": p.get("github"),
                "linkedin": p.get("linkedin"),
                "portfolio": p.get("portfolio"),
                "other": [],
            },
            "headline": p.get("headline") or p.get("title") or p.get("current_title"),
            "years_experience": p.get("years_experience"),
            "skills": _coerce_list(skills_raw),
            "experience": experience,
            "education": education,
            "provenance": [
                {"field": "full_name", "source": "ats", "method": "ats_field_mapping"},
                {"field": "skills", "source": "ats", "method": "ats_field_mapping"},
            ],
        }

    # ── Resume / Notes ───────────────────────────────────────────────────────
    if source_type in {"resume", "notes"}:
        text = payload.get("text", "")
        extracted = extract_from_text(text)
        return {
            "full_name": extracted.get("name"),
            "emails": extracted.get("emails", []),
            "phones": extracted.get("phones", []),
            "location_str": None,
            "links": extracted.get("links", {}),
            "headline": None,
            "years_experience": None,
            "skills": extracted.get("skills", []),
            "experience": extracted.get("experience", []),
            "education": extracted.get("education", []),
            "provenance": [
                {"field": "skills", "source": source_type, "method": "regex_extraction"},
                {"field": "experience", "source": source_type, "method": "regex_extraction"},
            ],
        }

    # ── GitHub ───────────────────────────────────────────────────────────────
    if source_type == "github":
        p = payload.get("profile", {})
        languages = payload.get("languages", {})
        skills = sorted(languages, key=lambda k: -languages[k])
        blog = p.get("blog") or None
        return {
            "full_name": p.get("name") or p.get("login"),
            "emails": [p["email"]] if p.get("email") else [],
            "phones": [],
            "location_str": p.get("location"),
            "links": {
                "github": p.get("html_url") or payload.get("source_url"),
                "linkedin": None,
                "portfolio": blog if blog and blog.startswith("http") else None,
                "other": [],
            },
            "headline": p.get("bio"),
            "years_experience": None,
            "skills": skills,
            "experience": [],
            "education": [],
            "provenance": [
                {"field": "full_name", "source": "github", "method": "github_api"},
                {"field": "skills", "source": "github", "method": "github_repo_languages"},
                {"field": "location", "source": "github", "method": "github_api"},
            ],
        }

    # Fallback
    return {
        "full_name": None, "emails": [], "phones": [], "location_str": None,
        "links": {}, "headline": None, "years_experience": None,
        "skills": [], "experience": [], "education": [], "provenance": [],
    }
