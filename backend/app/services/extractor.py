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

def extract_name(text: str) -> str | None:
    # Explicit label: "Name: John Smith"
    m = re.search(
        r'(?:Name|Full Name|Candidate Name|Applicant)\s*[:\-]\s*'
        r'([A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+){1,3})',
        text,
    )
    if m:
        return m.group(1).strip()
    # First non-empty line that looks like a proper name (2-4 capitalised words)
    for line in text.strip().splitlines():
        line = line.strip()
        if re.match(r'^[A-Z][a-zA-Z\'\-]+(?:\s+[A-Z][a-zA-Z\'\-]+){1,3}$', line):
            return line
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

def extract_experience(text: str) -> list[dict]:
    experiences: list[dict] = []
    pattern = re.compile(
        r'(?P<title>[A-Z][a-zA-Z\s]+(?:' + _EXP_TITLE_WORDS + r')[a-zA-Z\s]*?)'
        r'\s+(?:at|@|,|–|-)\s+'
        r'(?P<company>[A-Z][a-zA-Z0-9\s&,\.\-]+?)(?=\s*[,\n|·•]|\s{2,}|$)',
        re.MULTILINE,
    )
    seen: set[str] = set()
    for m in pattern.finditer(text):
        title = m.group("title").strip()
        company = m.group("company").strip().rstrip(",")
        key = f"{title.lower()}|{company.lower()}"
        if key not in seen and len(company) < 80:
            seen.add(key)
            experiences.append({
                "company": company,
                "title": title,
                "start": None,
                "end": None,
                "summary": None,
            })
    return experiences[:6]


# ---------------------------------------------------------------------------
# Education extraction
# ---------------------------------------------------------------------------

def extract_education(text: str) -> list[dict]:
    education: list[dict] = []
    pattern = re.compile(
        r'(?P<degree>B\.?S\.?|B\.?A\.?|M\.?S\.?|M\.?A\.?|MBA|Ph\.?D\.?|'
        r'Bachelor|Master|Doctorate)\s*'
        r'(?:of|in|,)?\s*'
        r'(?P<field>[A-Z][a-zA-Z\s&]{2,40}?)?\s*'
        r'(?:from|at|,|-|–)?\s*'
        r'(?P<institution>[A-Z][a-zA-Z\s&,\.]{3,60}?)'
        r'(?:\s*,?\s*(?P<year>(?:19|20)\d{2}))?',
        re.MULTILINE,
    )
    seen: set[str] = set()
    for m in pattern.finditer(text):
        institution = (m.group("institution") or "").strip().rstrip(",").rstrip()
        key = institution.lower()
        if key and key not in seen and len(institution) < 80:
            seen.add(key)
            year_str = m.group("year")
            education.append({
                "institution": institution,
                "degree": m.group("degree"),
                "field": (m.group("field") or "").strip() or None,
                "end_year": int(year_str) if year_str else None,
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
