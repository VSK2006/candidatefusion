import uuid
from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Candidate(Base):
    __tablename__ = "candidate"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    full_name = Column(String(255))
    headline = Column(String(500))
    years_experience = Column(Float)
    overall_confidence = Column(Float, default=0.0)
    emails = Column(Text)
    phones = Column(Text)
    location_city = Column(String(255))
    location_region = Column(String(255))
    location_country = Column(String(10))
    github_url = Column(String(500))
    linkedin_url = Column(String(500))
    portfolio_url = Column(String(500))

    sources = relationship("Source", back_populates="candidate", cascade="all, delete-orphan")
    skills = relationship("Skill", back_populates="candidate", cascade="all, delete-orphan")
    experience = relationship("Experience", back_populates="candidate", cascade="all, delete-orphan")
    education = relationship("Education", back_populates="candidate", cascade="all, delete-orphan")
    provenance = relationship("Provenance", back_populates="candidate", cascade="all, delete-orphan")


class Source(Base):
    __tablename__ = "source"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), nullable=False)
    source_type = Column(String(100), nullable=False)
    file_name = Column(String(255))
    candidate = relationship("Candidate", back_populates="sources")


class Skill(Base):
    __tablename__ = "skill"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), nullable=False)
    name = Column(String(255), nullable=False)
    confidence = Column(Float, default=0.0)
    sources = Column(Text)  # comma-separated source types that provided this skill
    candidate = relationship("Candidate", back_populates="skills")


class Experience(Base):
    __tablename__ = "experience"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), nullable=False)
    company = Column(String(255))
    title = Column(String(255))
    start = Column(String(10))   # YYYY-MM
    end = Column(String(10))     # YYYY-MM or null (= present)
    summary = Column(Text)
    candidate = relationship("Candidate", back_populates="experience")


class Education(Base):
    __tablename__ = "education"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), nullable=False)
    institution = Column(String(255))
    degree = Column(String(255))
    field = Column(String(255))
    end_year = Column(Integer)
    candidate = relationship("Candidate", back_populates="education")


class Provenance(Base):
    __tablename__ = "provenance"
    id = Column(Integer, primary_key=True)
    candidate_id = Column(Integer, ForeignKey("candidate.id"), nullable=False)
    field = Column(String(255), nullable=False)
    source = Column(String(100), nullable=False)
    method = Column(String(255))
    candidate = relationship("Candidate", back_populates="provenance")
