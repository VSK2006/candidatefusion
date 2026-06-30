"""
Normalizer: converts a raw canonical dict into a fully normalised CandidateCreate-ready dict.
Handles E.164 phones, YYYY-MM dates, location parsing, fusion score, and per-source confidence.
"""
import re
from datetime import date
from typing import Any

import phonenumbers
import dateparser

# ---------------------------------------------------------------------------
# Per-source confidence
# ---------------------------------------------------------------------------

SOURCE_CONFIDENCE: dict[str, float] = {
    "ats": 0.9,
    "github": 0.85,
    "csv": 0.80,
    "resume": 0.65,
    "notes": 0.55,
}

# ---------------------------------------------------------------------------
# Skill normalization
# ---------------------------------------------------------------------------

SKILL_REPLACEMENTS: dict[str, str] = {
    # Aliases
    "cpp": "C++", "c sharp": "C#", "golang": "Go",
    "node": "Node.js", "node.js": "Node.js", "next.js": "Next.js",
    "vue.js": "Vue.js", "express.js": "Express.js",
    "ml": "Machine Learning", "dl": "Deep Learning",
    "nlp": "NLP", "ai": "AI", "cv": "Computer Vision",
    "py": "Python", "js": "JavaScript", "ts": "TypeScript",
    "k8s": "Kubernetes", "ci/cd": "CI/CD",
    # Preserve exact casing for well-known names
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "go": "Go", "rust": "Rust", "ruby": "Ruby",
    "swift": "Swift", "kotlin": "Kotlin", "scala": "Scala",
    "react": "React", "angular": "Angular", "django": "Django",
    "flask": "Flask", "fastapi": "FastAPI",
    "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "redis": "Redis", "sqlite": "SQLite", "elasticsearch": "Elasticsearch",
    "docker": "Docker", "kubernetes": "Kubernetes",
    "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "scikit-learn": "scikit-learn",
    "sql": "SQL", "graphql": "GraphQL", "rest": "REST", "grpc": "gRPC",
    "git": "Git", "linux": "Linux",
    "machine learning": "Machine Learning", "deep learning": "Deep Learning",
    "data science": "Data Science", "data analysis": "Data Analysis",
    "figma": "Figma", "html": "HTML", "css": "CSS",
    "agile": "Agile", "scrum": "Scrum",
    "spring boot": "Spring Boot", "microservices": "Microservices",
    "ux design": "UX Design", "ux": "UX Design",
    "tableau": "Tableau", "spark": "Apache Spark", "apache spark": "Apache Spark",
}

def normalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return SKILL_REPLACEMENTS.get(cleaned, skill.strip().title())


# ---------------------------------------------------------------------------
# Phone normalization → E.164
# ---------------------------------------------------------------------------

def normalize_phone(phone: str) -> str | None:
    raw = phone.strip()
    if not raw:
        return None
    try:
        parsed = phonenumbers.parse(raw, None)
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
        parsed = phonenumbers.parse(raw, "US")
        if phonenumbers.is_valid_number(parsed):
            return phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
    except phonenumbers.NumberParseException:
        pass
    return raw  # keep raw rather than drop


# ---------------------------------------------------------------------------
# Date normalization → YYYY-MM
# ---------------------------------------------------------------------------

def normalize_date(date_str: str | None) -> str | None:
    if not date_str:
        return None
    date_str = date_str.strip()
    if re.match(r'^\d{4}-\d{2}$', date_str):
        return date_str
    if date_str.lower() in ("present", "current", "now", "today"):
        return None  # null means present
    try:
        parsed = dateparser.parse(date_str, settings={"PREFER_DAY_OF_MONTH": "first"})
        if parsed:
            return parsed.strftime('%Y-%m')
    except Exception:
        pass
    return None


# ---------------------------------------------------------------------------
# Location parsing
# ---------------------------------------------------------------------------

_COUNTRY_MAP: dict[str, str] = {
    "india": "IN", "united states": "US", "usa": "US", "u.s.a.": "US",
    "uk": "GB", "united kingdom": "GB", "england": "GB", "britain": "GB",
    "canada": "CA", "australia": "AU", "germany": "DE", "france": "FR",
    "singapore": "SG", "china": "CN", "japan": "JP", "brazil": "BR",
    "netherlands": "NL", "sweden": "SE", "norway": "NO", "denmark": "DK",
    "new zealand": "NZ", "ireland": "IE", "spain": "ES", "italy": "IT",
    "portugal": "PT", "switzerland": "CH", "austria": "AT", "belgium": "BE",
    "poland": "PL", "russia": "RU", "ukraine": "UA",
}

_US_STATES: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA", "HI", "ID",
    "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD", "MA", "MI", "MN", "MS",
    "MO", "MT", "NE", "NV", "NH", "NJ", "NM", "NY", "NC", "ND", "OH", "OK",
    "OR", "PA", "RI", "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV",
    "WI", "WY", "DC",
}

def parse_location(location_str: str | None) -> dict[str, str | None] | None:
    if not location_str:
        return None
    parts = [p.strip() for p in location_str.split(',') if p.strip()]
    if not parts:
        return None

    city = parts[0]
    region: str | None = None
    country: str | None = None

    if len(parts) == 1:
        # Could be just a country
        low = parts[0].lower()
        if low in _COUNTRY_MAP:
            city = None
            country = _COUNTRY_MAP[low]
        elif parts[0].upper() in _US_STATES:
            city = None
            region = parts[0].upper()
            country = "US"

    elif len(parts) == 2:
        second = parts[1].strip()
        if second.upper() in _US_STATES:
            region = second.upper()
            country = "US"
        else:
            low = second.lower()
            country = _COUNTRY_MAP.get(low, second[:2].upper() if len(second) >= 2 else None)

    elif len(parts) >= 3:
        second = parts[1].strip()
        if second.upper() in _US_STATES:
            region = second.upper()
        else:
            region = second
        third = parts[2].strip().lower()
        country = _COUNTRY_MAP.get(third, parts[2].strip()[:2].upper())

    return {"city": city, "region": region, "country": country}


# ---------------------------------------------------------------------------
# Years of experience
# ---------------------------------------------------------------------------

def calculate_years_experience(experience: list[dict]) -> float | None:
    total_months = 0
    today = date.today()
    for exp in experience:
        start_str = exp.get("start")
        end_str = exp.get("end")
        if not start_str:
            continue
        try:
            start = dateparser.parse(start_str)
            if not start:
                continue
            if end_str:
                end = dateparser.parse(end_str) or today
            else:
                end = today
            months = (end.year - start.year) * 12 + (end.month - start.month)
            if months > 0:
                total_months += months
        except Exception:
            continue
    if total_months <= 0:
        return None
    return round(total_months / 12, 1)


# ---------------------------------------------------------------------------
# Fusion Score — composite quality metric
# ---------------------------------------------------------------------------

def calculate_fusion_score(profile: dict) -> float:
    """
    Composite quality metric: 0.0 – 1.0.
      40 % data completeness (how many key fields are populated)
      40 % overall confidence
      20 % cross-source verification (skills confirmed by >1 source)
    """
    key_fields = [
        profile.get("full_name"),
        profile.get("emails"),
        profile.get("phones"),
        profile.get("location"),
        profile.get("headline"),
        profile.get("years_experience"),
        profile.get("skills"),
        profile.get("experience"),
    ]
    filled = sum(1 for f in key_fields if f and f != [] and f != {})
    completeness = filled / len(key_fields)

    skills = profile.get("skills", [])
    if skills:
        multi = sum(1 for s in skills if isinstance(s, dict) and len(s.get("sources", [])) > 1)
        verification = min(0.20, (multi / len(skills)) * 0.20)
    else:
        verification = 0.0

    confidence = profile.get("overall_confidence", 0.75)
    score = completeness * 0.40 + confidence * 0.40 + verification
    return round(min(1.0, max(0.0, score)), 3)


# ---------------------------------------------------------------------------
# Main normalization entry point
# ---------------------------------------------------------------------------

def normalize_profile(raw: dict[str, Any], source_type: str = "csv") -> dict[str, Any]:
    confidence = SOURCE_CONFIDENCE.get(source_type, 0.75)

    emails = list(dict.fromkeys(
        e.strip().lower() for e in raw.get("emails", []) if e and e.strip()
    ))
    phones = list(dict.fromkeys(filter(None, (
        normalize_phone(p) for p in raw.get("phones", []) if p
    ))))

    # Skills: accept both str and dict (with name/confidence/sources)
    skills: list[dict] = []
    for s in raw.get("skills", []):
        if isinstance(s, str) and s.strip():
            skills.append({
                "name": normalize_skill(s),
                "confidence": confidence,
                "sources": [source_type],
            })
        elif isinstance(s, dict) and s.get("name"):
            skills.append({
                "name": normalize_skill(s["name"]),
                "confidence": s.get("confidence", confidence),
                "sources": s.get("sources", [source_type]),
            })

    # Experience: normalize dates
    experience: list[dict] = []
    for exp in raw.get("experience", []):
        if isinstance(exp, dict):
            experience.append({
                "company": exp.get("company"),
                "title": exp.get("title"),
                "start": normalize_date(exp.get("start")),
                "end": normalize_date(exp.get("end")),
                "summary": exp.get("summary"),
            })

    # Education: pass through
    education = [
        {
            "institution": e.get("institution"),
            "degree": e.get("degree"),
            "field": e.get("field"),
            "end_year": e.get("end_year"),
        }
        for e in raw.get("education", []) if isinstance(e, dict)
    ]

    location = parse_location(raw.get("location_str")) or (
        raw.get("location") if isinstance(raw.get("location"), dict) else None
    )

    links_raw = raw.get("links") or {}
    links = {
        "linkedin": links_raw.get("linkedin"),
        "github": links_raw.get("github"),
        "portfolio": links_raw.get("portfolio"),
        "other": links_raw.get("other", []),
    }

    years_exp = raw.get("years_experience") or calculate_years_experience(experience)

    profile = {
        "full_name": (raw.get("full_name") or "").strip() or None,
        "emails": emails,
        "phones": phones,
        "location": location,
        "links": links,
        "headline": raw.get("headline"),
        "years_experience": years_exp,
        "skills": skills,
        "experience": experience,
        "education": education,
        "overall_confidence": confidence,
        "provenance": raw.get("provenance", []),
    }

    profile["fusion_score"] = calculate_fusion_score(profile)
    return profile
