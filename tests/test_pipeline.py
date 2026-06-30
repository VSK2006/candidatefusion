import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.pipeline import process_upload
from app.services.extractor import extract_emails, extract_phones, extract_skills, extract_from_text
from app.services.normalizer import normalize_phone, parse_location, calculate_years_experience
from app.services.projector import project_profile
from app.schemas import OutputConfig, OutputConfigField

import pytest


class DummyUpload:
    def __init__(self, filename: str, content: bytes):
        self.filename = filename
        self._content = content

    async def read(self):
        return self._content


# ---------------------------------------------------------------------------
# Pipeline integration tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_csv_pipeline_saves_candidate():
    csv = b'name,email,phone,skills,headline\nRahul Sharma,rahul@example.com,+1 415-555-0101,Python,Engineer'
    upload = DummyUpload('candidates.csv', csv)
    msg = await process_upload('csv', upload, None)
    assert 'Saved' in msg


@pytest.mark.asyncio
async def test_csv_pipeline_multiple_rows():
    csv = (
        b'name,email,phone,skills\n'
        b'Alice,alice@example.com,+1 415-000-0001,Python\n'
        b'Bob,bob@example.com,+1 415-000-0002,Java\n'
    )
    upload = DummyUpload('multi.csv', csv)
    msg = await process_upload('csv', upload, None)
    assert '2' in msg


@pytest.mark.asyncio
async def test_ats_json_pipeline():
    import json
    payload = json.dumps({
        "name": "Jin Park",
        "email": "jin@example.com",
        "skills": ["Go", "Docker"],
        "headline": "Backend Engineer",
    }).encode()
    upload = DummyUpload('profile.json', payload)
    msg = await process_upload('ats', upload, None)
    assert 'Saved' in msg


@pytest.mark.asyncio
async def test_notes_pipeline():
    notes = b'Name: Sara Osei\nEmail: sara@example.com\nSkills: Python, Machine Learning'
    upload = DummyUpload('notes.txt', notes)
    msg = await process_upload('notes', upload, None)
    assert 'Saved' in msg


@pytest.mark.asyncio
async def test_github_invalid_url():
    with pytest.raises(Exception):
        await process_upload('github', None, 'https://not-github.com/user')


# ---------------------------------------------------------------------------
# Extractor unit tests
# ---------------------------------------------------------------------------

def test_extract_emails():
    text = 'Contact me at john.doe@example.com or john@work.org'
    assert 'john.doe@example.com' in extract_emails(text)
    assert 'john@work.org' in extract_emails(text)


def test_extract_phones():
    text = 'Call +1 415-555-0199 or (212) 555-0143'
    phones = extract_phones(text)
    assert len(phones) == 2


def test_extract_skills():
    text = 'I work with Python, React, and Docker daily.'
    skills = extract_skills(text)
    assert 'Python' in skills
    assert 'React' in skills
    assert 'Docker' in skills


def test_extract_from_text_name():
    text = 'John Smith\njohn@example.com\nSkills: Python, SQL'
    result = extract_from_text(text)
    assert result['name'] == 'John Smith'
    assert 'Python' in result['skills']


# ---------------------------------------------------------------------------
# Normalizer unit tests
# ---------------------------------------------------------------------------

def test_normalize_phone_e164():
    result = normalize_phone('+1 415-555-0199')
    assert result == '+14155550199'


def test_parse_location_us():
    loc = parse_location('San Francisco, CA')
    assert loc['city'] == 'San Francisco'
    assert loc['region'] == 'CA'
    assert loc['country'] == 'US'


def test_parse_location_india():
    loc = parse_location('Mumbai, India')
    assert loc['country'] == 'IN'


def test_calculate_years_experience():
    exp = [{"start": "2020-01", "end": "2022-01"}]
    years = calculate_years_experience(exp)
    assert years == 2.0


# ---------------------------------------------------------------------------
# Projector unit tests (Required Twist)
# ---------------------------------------------------------------------------

CANONICAL = {
    "candidate_id": "abc-123",
    "full_name": "Jane Doe",
    "emails": ["jane@example.com", "jd@work.com"],
    "phones": ["+14155550100"],
    "skills": [
        {"name": "Python", "confidence": 0.9, "sources": ["csv", "github"]},
        {"name": "SQL", "confidence": 0.8, "sources": ["csv"]},
    ],
    "location": {"city": "Austin", "region": "TX", "country": "US"},
    "headline": "Data Engineer",
    "years_experience": 5.0,
    "overall_confidence": 0.85,
    "fusion_score": 0.78,
    "provenance": [{"field": "full_name", "source": "csv", "method": "direct_mapping"}],
}


def test_project_default():
    config = OutputConfig()
    result = project_profile(CANONICAL, config)
    assert result['full_name'] == 'Jane Doe'
    assert result['overall_confidence'] == 0.85


def test_project_field_selection():
    config = OutputConfig(
        fields=[
            OutputConfigField(path='full_name', type='string'),
            OutputConfigField(**{'path': 'primary_email', 'from': 'emails[0]', 'type': 'string'}),
        ],
        include_provenance=False,
    )
    result = project_profile(CANONICAL, config)
    assert 'full_name' in result
    assert result['primary_email'] == 'jane@example.com'
    assert 'emails' not in result
    assert 'provenance' not in result


def test_project_skills_names():
    config = OutputConfig(
        fields=[
            OutputConfigField(**{'path': 'skill_names', 'from': 'skills[].name', 'type': 'string[]', 'normalize': 'canonical'}),
        ],
        include_confidence=False,
        include_provenance=False,
    )
    result = project_profile(CANONICAL, config)
    assert result['skill_names'] == ['Python', 'SQL']  # canonical = proper skill casing, not naive title-case


def test_project_on_missing_omit():
    config = OutputConfig(
        fields=[
            OutputConfigField(path='full_name', type='string'),
            OutputConfigField(path='linkedin', **{'from': 'links.linkedin'}, type='string'),
        ],
        on_missing='omit',
        include_confidence=False,
        include_provenance=False,
    )
    result = project_profile(CANONICAL, config)
    assert 'full_name' in result
    assert 'linkedin' not in result  # omitted because missing


def test_project_on_missing_error_optional_field():
    config = OutputConfig(
        fields=[
            OutputConfigField(path='missing_field', required=False),
        ],
        on_missing='error',
        include_confidence=False,
        include_provenance=False,
    )
    # Should NOT raise for non-required field
    result = project_profile(CANONICAL, config)
    assert result['missing_field'] is None


def test_project_on_missing_error_required_field():
    config = OutputConfig(
        fields=[
            OutputConfigField(path='nonexistent', required=True),
        ],
        on_missing='error',
        include_confidence=False,
        include_provenance=False,
    )
    with pytest.raises(ValueError):
        project_profile(CANONICAL, config)
