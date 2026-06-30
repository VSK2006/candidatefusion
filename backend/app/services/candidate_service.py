import uuid
from app.db import SessionLocal
from app.models import Candidate, Skill, Source, Experience, Education, Provenance
from app.schemas import CandidateCreate
from rapidfuzz import fuzz


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _split(text: str | None) -> list[str]:
    return [t.strip() for t in (text or "").split(",") if t.strip()]


def _join(values: list[str]) -> str:
    return ",".join(values)


def _merge_unique(existing: str | None, new_values: list[str]) -> str:
    combined = _split(existing) + [v.strip() for v in new_values if v.strip()]
    seen: list[str] = []
    for item in combined:
        if item not in seen:
            seen.append(item)
    return _join(seen)


def _find_by_email(session, email: str) -> Candidate | None:
    rows = session.query(Candidate).filter(Candidate.emails.like(f"%{email}%")).all()
    for c in rows:
        if email in _split(c.emails):
            return c
    return None


def _find_by_phone(session, phone: str) -> Candidate | None:
    rows = session.query(Candidate).filter(Candidate.phones.like(f"%{phone}%")).all()
    for c in rows:
        if phone in _split(c.phones):
            return c
    return None


def _find_by_name(session, name: str) -> Candidate | None:
    if not name:
        return None
    first_word = name.split()[0]
    query = session.query(Candidate).filter(Candidate.full_name.ilike(f"%{first_word}%"))
    best, best_score = None, 0
    for c in query.all():
        score = fuzz.token_sort_ratio(name, c.full_name or "")
        if score > 85 and score > best_score:
            best_score = score
            best = c
    return best


def _find_existing(session, profile: CandidateCreate) -> Candidate | None:
    for email in profile.emails:
        c = _find_by_email(session, email)
        if c:
            return c
    for phone in profile.phones:
        c = _find_by_phone(session, phone)
        if c:
            return c
    if profile.full_name:
        return _find_by_name(session, profile.full_name)
    return None


# ---------------------------------------------------------------------------
# Candidate → dict
# ---------------------------------------------------------------------------

def _candidate_to_dict(candidate: Candidate) -> dict:
    from app.services.normalizer import calculate_fusion_score

    loc = None
    if candidate.location_city or candidate.location_region or candidate.location_country:
        loc = {
            "city": candidate.location_city,
            "region": candidate.location_region,
            "country": candidate.location_country,
        }

    links = None
    if any([candidate.github_url, candidate.linkedin_url, candidate.portfolio_url]):
        links = {
            "github": candidate.github_url,
            "linkedin": candidate.linkedin_url,
            "portfolio": candidate.portfolio_url,
            "other": [],
        }

    skills = [
        {
            "name": s.name,
            "confidence": s.confidence,
            "sources": _split(s.sources),
        }
        for s in candidate.skills
    ]

    experience = [
        {
            "company": e.company,
            "title": e.title,
            "start": e.start,
            "end": e.end,
            "summary": e.summary,
        }
        for e in candidate.experience
    ]

    education = [
        {
            "institution": ed.institution,
            "degree": ed.degree,
            "field": ed.field,
            "end_year": ed.end_year,
        }
        for ed in candidate.education
    ]

    provenance = [
        {"field": pv.field, "source": pv.source, "method": pv.method}
        for pv in candidate.provenance
    ]

    profile = {
        "candidate_id": candidate.candidate_id,
        "full_name": candidate.full_name,
        "emails": _split(candidate.emails),
        "phones": _split(candidate.phones),
        "location": loc,
        "links": links,
        "headline": candidate.headline,
        "years_experience": candidate.years_experience,
        "skills": skills,
        "experience": experience,
        "education": education,
        "provenance": provenance,
        "overall_confidence": candidate.overall_confidence,
    }
    profile["fusion_score"] = calculate_fusion_score(profile)
    return profile


# ---------------------------------------------------------------------------
# Persist / merge
# ---------------------------------------------------------------------------

def persist_candidate(
    profile: CandidateCreate, source_type: str, file_name: str | None
) -> Candidate:
    with SessionLocal() as session:
        existing = _find_existing(session, profile)

        if existing:
            # ── Merge ─────────────────────────────────────────────────────
            existing.full_name = profile.full_name or existing.full_name
            existing.headline = profile.headline or existing.headline
            existing.years_experience = profile.years_experience or existing.years_experience
            existing.overall_confidence = max(
                existing.overall_confidence or 0.0, profile.overall_confidence
            )
            existing.emails = _merge_unique(existing.emails, profile.emails)
            existing.phones = _merge_unique(existing.phones, profile.phones)

            # Location: fill in gaps
            if profile.location:
                existing.location_city = existing.location_city or profile.location.city
                existing.location_region = existing.location_region or profile.location.region
                existing.location_country = existing.location_country or profile.location.country

            # Links: fill in gaps
            if profile.links:
                existing.github_url = existing.github_url or profile.links.github
                existing.linkedin_url = existing.linkedin_url or profile.links.linkedin
                existing.portfolio_url = existing.portfolio_url or profile.links.portfolio

            # Skills: merge with source tracking + confidence boost
            existing_skills = {s.name.lower(): s for s in existing.skills}
            for sk in profile.skills:
                key = sk.name.lower()
                if key in existing_skills:
                    # Boost confidence only when a genuinely NEW source confirms
                    # this skill -- re-uploading the same source must be a no-op,
                    # otherwise confidence inflates indefinitely on re-upload.
                    db_skill = existing_skills[key]
                    srcs = _split(db_skill.sources)
                    if source_type not in srcs:
                        srcs.append(source_type)
                        db_skill.sources = _join(srcs)
                        db_skill.confidence = min(1.0, db_skill.confidence + 0.05)
                else:
                    new_skill = Skill(
                        name=sk.name,
                        confidence=sk.confidence,
                        sources=_join(sk.sources or [source_type]),
                    )
                    existing.skills.append(new_skill)
                    existing_skills[key] = new_skill

            # Experience: add if not already from same company+title
            exp_keys = {
                (e.company or "").lower() + "|" + (e.title or "").lower()
                for e in existing.experience
            }
            for exp in profile.experience:
                key = (exp.company or "").lower() + "|" + (exp.title or "").lower()
                if key not in exp_keys and (exp.company or exp.title):
                    existing.experience.append(Experience(
                        company=exp.company, title=exp.title,
                        start=exp.start, end=exp.end, summary=exp.summary,
                    ))
                    exp_keys.add(key)

            # Education: add if not already same institution
            edu_keys = {(e.institution or "").lower() for e in existing.education}
            for edu in profile.education:
                key = (edu.institution or "").lower()
                if key and key not in edu_keys:
                    existing.education.append(Education(
                        institution=edu.institution, degree=edu.degree,
                        field=edu.field, end_year=edu.end_year,
                    ))
                    edu_keys.add(key)

            # Provenance
            for pv in profile.provenance:
                existing.provenance.append(Provenance(
                    field=pv.field, source=pv.source, method=pv.method,
                ))
            existing.provenance.append(Provenance(
                field="merged_profile", source=source_type, method="merge_engine",
            ))

            session.commit()
            session.refresh(existing)
            return existing

        # ── Create ──────────────────────────────────────────────────────────
        loc = profile.location
        lnk = profile.links
        candidate = Candidate(
            candidate_id=str(uuid.uuid4()),
            full_name=profile.full_name or "Unknown Candidate",
            headline=profile.headline,
            years_experience=profile.years_experience,
            overall_confidence=profile.overall_confidence,
            emails=_join(profile.emails),
            phones=_join(profile.phones),
            location_city=loc.city if loc else None,
            location_region=loc.region if loc else None,
            location_country=loc.country if loc else None,
            github_url=lnk.github if lnk else None,
            linkedin_url=lnk.linkedin if lnk else None,
            portfolio_url=lnk.portfolio if lnk else None,
        )

        for sk in profile.skills:
            candidate.skills.append(Skill(
                name=sk.name,
                confidence=sk.confidence,
                sources=_join(sk.sources or [source_type]),
            ))
        for exp in profile.experience:
            if exp.company or exp.title:
                candidate.experience.append(Experience(
                    company=exp.company, title=exp.title,
                    start=exp.start, end=exp.end, summary=exp.summary,
                ))
        for edu in profile.education:
            if edu.institution:
                candidate.education.append(Education(
                    institution=edu.institution, degree=edu.degree,
                    field=edu.field, end_year=edu.end_year,
                ))

        candidate.sources.append(Source(source_type=source_type, file_name=file_name))

        for pv in profile.provenance:
            candidate.provenance.append(Provenance(
                field=pv.field, source=pv.source, method=pv.method,
            ))
        candidate.provenance.append(Provenance(
            field="created_profile", source=source_type, method="canonical_mapper",
        ))

        session.add(candidate)
        session.commit()
        session.refresh(candidate)
        return candidate


# ---------------------------------------------------------------------------
# Read operations
# ---------------------------------------------------------------------------

def list_candidates() -> list[dict]:
    with SessionLocal() as session:
        candidates = session.query(Candidate).order_by(Candidate.id.asc()).all()
        return [_candidate_to_dict(c) for c in candidates]


def get_candidate(candidate_id: str) -> dict | None:
    with SessionLocal() as session:
        candidate = (
            session.query(Candidate)
            .filter(Candidate.candidate_id == candidate_id)
            .first()
        )
        if not candidate:
            return None
        return _candidate_to_dict(candidate)


def get_source_count() -> int:
    with SessionLocal() as session:
        return session.query(Source).count()


def get_stats() -> dict:
    with SessionLocal() as session:
        total = session.query(Candidate).count()
        source_count = session.query(Source).count()
        return {"total_candidates": total, "total_uploads": source_count}
