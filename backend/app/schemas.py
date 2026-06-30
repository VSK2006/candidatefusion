from pydantic import BaseModel, Field
from pydantic import ConfigDict
from typing import List, Optional, Literal, Any


# ---------- Sub-schemas ----------

class LocationSchema(BaseModel):
    city: Optional[str] = None
    region: Optional[str] = None
    country: Optional[str] = None  # ISO-3166 alpha-2

class LinksSchema(BaseModel):
    linkedin: Optional[str] = None
    github: Optional[str] = None
    portfolio: Optional[str] = None
    other: List[str] = []

class SkillSchema(BaseModel):
    name: str
    confidence: float = 0.75
    sources: List[str] = []

class ExperienceSchema(BaseModel):
    company: Optional[str] = None
    title: Optional[str] = None
    start: Optional[str] = None   # YYYY-MM
    end: Optional[str] = None     # YYYY-MM or null = present
    summary: Optional[str] = None

class EducationSchema(BaseModel):
    institution: Optional[str] = None
    degree: Optional[str] = None
    field: Optional[str] = None
    end_year: Optional[int] = None

class ProvenanceSchema(BaseModel):
    field: str
    source: str
    method: str


# ---------- Canonical create / read ----------

class CandidateCreate(BaseModel):
    full_name: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    location: Optional[LocationSchema] = None
    links: Optional[LinksSchema] = None
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[SkillSchema] = []
    experience: List[ExperienceSchema] = []
    education: List[EducationSchema] = []
    overall_confidence: float = Field(0.75, ge=0.0, le=1.0)
    provenance: List[ProvenanceSchema] = []

class CandidateRead(BaseModel):
    candidate_id: str
    full_name: Optional[str] = None
    emails: List[str] = []
    phones: List[str] = []
    location: Optional[LocationSchema] = None
    links: Optional[LinksSchema] = None
    headline: Optional[str] = None
    years_experience: Optional[float] = None
    skills: List[SkillSchema] = []
    experience: List[ExperienceSchema] = []
    education: List[EducationSchema] = []
    provenance: List[ProvenanceSchema] = []
    overall_confidence: float = 0.0
    fusion_score: Optional[float] = None  # composite quality metric

    model_config = ConfigDict(from_attributes=True)


# ---------- Configurable output (Required Twist) ----------

class OutputConfigField(BaseModel):
    path: str
    from_: Optional[str] = Field(None, alias="from")
    type: str = "string"
    required: bool = False
    normalize: Optional[str] = None  # "E164" | "canonical" | "lowercase"

    model_config = ConfigDict(populate_by_name=True)

class OutputConfig(BaseModel):
    fields: Optional[List[OutputConfigField]] = None
    include_confidence: bool = True
    include_provenance: bool = True
    on_missing: Literal["null", "omit", "error"] = "null"


# ---------- API wrappers ----------

class UploadResponse(BaseModel):
    message: str

class ExportRequest(BaseModel):
    config: Optional[OutputConfig] = None
