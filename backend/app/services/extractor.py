"""
Smart extraction of structured fields from unstructured text sources
(resume PDFs, recruiter notes, plain-text files).
"""
import re
from typing import Any

# ---------------------------------------------------------------------------
# Skill taxonomy — keyword → canonical name
# ---------------------------------------------------------------------------
_SKILL_MAP: dict[str, str] = {
    "python": "Python", "javascript": "JavaScript", "typescript": "TypeScript",
    "java": "Java", "c++": "C++", "c#": "C#", "go": "Go", "golang": "Go",
    "rust": "Rust", "ruby": "Ruby", "php": "PHP", "swift": "Swift",
    "kotlin": "Kotlin", "scala": "Scala", "r": "R", "matlab": "MATLAB",
    "react": "React", "vue": "Vue.js", "angular": "Angular",
    "next.js": "Next.js", "node.js": "Node.js", "express": "Express.js",
    "fastapi": "FastAPI", "django": "Django", "flask": "Flask",
    "spring": "Spring Boot", "rails": "Ruby on Rails",
    "postgresql": "PostgreSQL", "mysql": "MySQL", "mongodb": "MongoDB",
    "redis": "Redis", "sqlite": "SQLite", "cassandra": "Cassandra",
    "elasticsearch": "Elasticsearch",
    "docker": "Docker", "kubernetes": "Kubernetes",
    "aws": "AWS", "gcp": "GCP", "azure": "Azure",
    "terraform": "Terraform", "ansible": "Ansible",
    "machine learning": "Machine Learning", "ml": "Machine Learning",
    "deep learning": "Deep Learning", "tensorflow": "TensorFlow",
    "pytorch": "PyTorch", "scikit-learn": "scikit-learn",
    "nlp": "NLP", "computer vision": "Computer Vision",
    "data science": "Data Science", "data analysis": "Data Analysis",
    "sql": "SQL", "graphql": "GraphQL", "rest": "REST", "grpc": "gRPC",
    "git": "Git", "linux": "Linux", "ci/cd": "CI/CD",
    "agile": "Agile", "scrum": "Scrum", "figma": "Figma",
    "html": "HTML", "css": "CSS", "tailwind": "Tailwind CSS",
}


# ---------------------------------------------------------------------------
# Email / phone / URL helpers
# ---------------------------------------------------------------------------

def extract_emails(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', text
    )))


def extract_phones(text: str) -> list[str]:
    return list(dict.fromkeys(re.findall(
        r'(?:\+\d{1,3}[\s.\-]?)?\(?\d{3}\)?[\s.\-]?\d{3}[\s.\-]?\d{4}', text
    )))


def extract_links(text: str) -> dict[str, Any]:
    gh = re.search(r'github\.com/([a-zA-Z0-9_\-]+)', text)
    li = re.search(r'linkedin\.com/in/([a-zA-Z0-9_\-]+)', text)
    # portfolio: any https URL that isn't github / linkedin
    portfolio_m = re.search(
        r'https?://(?!(?:www\.)?github\.com|(?:www\.)?linkedin\.com)[^\s"\'<>]+', text
    )
    return {
        "github": f"https://github.com/{gh.group(1)}" if gh else None,
        "linkedin": f"https://linkedin.com/in/{li.group(1)}" if li else None,
        "portfolio": portfolio_m.group(0) if portfolio_m else None,
        "other": [],
    }


# ---------------------------------------------------------------------------
# Name extraction
# ---------------------------------------------------------------------------

_NAME_TOKEN = r"[A-Z][a-zA-Z'\-]+(?:[ \t]+[A-Z][a-zA-Z'\-]+){1,3}"


def extract_name(text: str) -> str | None:
    # Explicit label: "Name: John Smith"
    m = re.search(
        r'(?:Name|Full Name|Candidate Name|Applicant)\s*[:\-]\s*'
        rf'({_NAME_TOKEN})',
        text,
    )
    if m:
        return m.group(1).strip()

    for line in text.strip().splitlines()[:5]:
        line = line.strip()
        if not line:
            continue
        # Whole line is just a name
        if re.match(rf'^{_NAME_TOKEN}$', line):
            return line
        # "<prefix> - Name" / "<prefix> -- Name" / "<prefix> : Name" — the name
        # sits after the last separator (handles "Recruiter Notes — Jane Doe")
        sep_m = re.search(r'[:\-‐-―]\s*([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+){1,3})\s*$', line)
        if sep_m:
            return sep_m.group(1).strip()
    return None


# ---------------------------------------------------------------------------
# Skills extraction
# ---------------------------------------------------------------------------

def extract_skills(text: str) -> list[str]:
    text_lower = text.lower()
    found: dict[str, str] = {}  # canonical_name → canonical_name

    # Match from taxonomy
    for keyword, canonical in _SKILL_MAP.items():
        if re.search(r'\b' + re.escape(keyword) + r'\b', text_lower):
            found[canonical.lower()] = canonical

    # Also parse explicit "Skills:" section
    skills_block = re.search(r'Skills?\s*[:\-]\s*([^\n]{3,200})', text, re.IGNORECASE)
    if skills_block:
        for token in re.split(r'[,;|•·/]', skills_block.group(1)):
            token = token.strip()
            if 2 < len(token) < 50:
                tok_lower = token.lower()
                canonical = _SKILL_MAP.get(tok_lower, token)
                found[canonical.lower()] = canonical

    return sorted(found.values())


# ---------------------------------------------------------------------------
# Experience extraction
# ---------------------------------------------------------------------------

_EXP_TITLE_WORDS = (
    r'Engineer|Developer|Designer|Manager|Analyst|Architect|Lead|Director|'
    r'VP|Intern|Consultant|Specialist|Scientist|Researcher|Officer|Head'
)

_EXP_LINE_RE = re.compile(
    r'^(?P<title>[A-Z][a-zA-Z]+(?:[ \t]+[A-Z]?[a-zA-Z]+)*?[ \t]+(?:' + _EXP_TITLE_WORDS + r')(?:[ \t]+[A-Z][a-zA-Z]+)*)'
    r'[ \t]+(?:at|@)[ \t]+'
    r'(?P<company>[A-Z][a-zA-Z0-9 \t&,\.\-]+?)'
    r'(?:,?[ \t]*(?P<start>[A-Za-z]{3,9}\.?[ \t]+\d{4})[ \t]*[-–—][ \t]*(?P<end>[A-Za-z]{3,9}\.?[ \t]+\d{4}|Present|Current))?'
    r'[ \t]*$'
)


def extract_experience(text: str) -> list[dict]:
    """Line-based, same rationale as extract_education: resume/notes entries
    are normally one line each, and processing per-line guarantees a match
    can't span across an unrelated heading or the previous bullet point
    (e.g. a stray "CD" fragment from "CI/CD" bleeding into the next line)."""
    experiences: list[dict] = []
    seen: set[str] = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _EXP_LINE_RE.search(line)
        if not m:
            continue
        title = m.group("title").strip()
        company = m.group("company").strip().rstrip(",")
        key = f"{title.lower()}|{company.lower()}"
        if key in seen or len(company) >= 80:
            continue
        seen.add(key)
        experiences.append({
            "company": company,
            "title": title,
            "start": m.group("start"),
            "end": m.group("end"),
            "summary": None,
        })
    return experiences[:6]


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------

_DEGREE_RE = re.compile(
    r'(?<![A-Za-z])'  # degree token must not be a substring inside a longer word (e.g. "MS" in "BMS")
    r'(?P<degree>B\.?Tech\.?|M\.?Tech\.?|B\.?E\.?|M\.?E\.?|B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|MBA|Ph\.?D\.?|'
    r'Bachelor|Master|Doctorate)(?![A-Za-z])'
)
_YEAR_RE = re.compile(r'(?:19|20)\d{2}')
_FIELD_SEP_RE = re.compile(r'\b(?:from|at)\b', re.IGNORECASE)


def extract_education(text: str) -> list[dict]:
    """Line-based: each resume education entry is normally one line, so we
    process line-by-line rather than a single do-everything regex — that
    avoids lazy-quantifier truncation (e.g. "Wharton School" -> "Whar")
    since there's no ambiguity about where the line (and institution) ends.
    """
    education: list[dict] = []
    seen: set[str] = set()

    for line in text.splitlines():
        m = _DEGREE_RE.search(line)
        if not m:
            continue
        degree = m.group("degree")
        rest = line[m.end():].strip()
        had_field_connector = bool(re.match(r'^(?:of|in)\b', rest, flags=re.IGNORECASE))
        rest = re.sub(r'^(?:of|in)\b', '', rest, flags=re.IGNORECASE).lstrip(', ').strip()

        year_match = _YEAR_RE.search(rest)
        end_year = int(year_match.group()) if year_match else None
        if year_match:
            rest = rest[:year_match.start()] + rest[year_match.end():]
        rest = rest.strip(' ,.-–')

        field = None
        institution = rest
        sep_match = _FIELD_SEP_RE.search(rest)
        if sep_match:
            # "<field> from/at <institution>"
            field = rest[:sep_match.start()].strip(' ,') or None
            institution = rest[sep_match.end():].strip(' ,')
        elif had_field_connector and ',' in rest:
            # "<degree> of/in <field>, <institution>"
            head, _, tail = rest.partition(',')
            head, tail = head.strip(), tail.strip()
            if head and tail:
                field, institution = head, tail
        elif ',' in rest:
            # No field connector -> what follows the degree is the institution
            # itself (e.g. "B.Tech, BMS College of Engineering, Bangalore");
            # only take the first comma segment, dropping trailing city/etc.
            head, _, _tail = rest.partition(',')
            head = head.strip()
            if head:
                institution = head

        institution = institution.strip(' ,.')
        if not institution or len(institution) > 80:
            continue
        key = institution.lower()
        if key in seen:
            continue
        seen.add(key)
        education.append({
            "institution": institution,
            "degree": degree,
            "field": field,
            "end_year": end_year,
        })

    return education[:4]


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def extract_from_text(text: str) -> dict[str, Any]:
    return {
        "name": extract_name(text),
        "emails": extract_emails(text),
        "phones": extract_phones(text),
        "links": extract_links(text),
        "skills": extract_skills(text),
        "experience": extract_experience(text),
        "education": extract_education(text),
    }
