from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class UserProfileSchema(BaseModel):
    name: str = ""
    title: str = ""
    summary: str = ""
    skills: list = []
    portfolio_urls: list = []
    experience_years: int = 0
    location: str = "Remote"
    preferred_roles: list = []


class JobSchema(BaseModel):
    id: int
    title: str
    platform: str
    url: str
    description: str
    required_skills: list = []
    budget: str = ""
    client_name: str = ""
    match_score: int = 0
    match_reason: str = ""
    status: str = "new"
    created_at: Optional[datetime] = None


class ProspectSchema(BaseModel):
    id: int
    company_name: str
    industry: str = ""
    contact_name: str = ""
    email: str = ""
    linkedin_url: str = ""
    source: str
    relevance_score: int = 0
    status: str = "new"
    created_at: Optional[datetime] = None


class OutreachDraftSchema(BaseModel):
    id: int
    prospect_id: Optional[int] = None
    job_id: Optional[int] = None
    email_subject: str = ""
    email_body: str = ""
    linkedin_message: str = ""
    channel: str = "both"
    status: str = "draft"
    created_at: Optional[datetime] = None


class StatsSchema(BaseModel):
    total_jobs: int
    total_prospects: int
    total_drafts: int
    matched_jobs: int
    high_score_jobs: int


class ResearchLeadSchema(BaseModel):
    id: int
    name: str = ""
    title: str = ""
    institution: str = ""
    department: str = ""
    country: str = ""
    region: str = ""
    research_fields: list = []
    recent_papers: list = []
    bio: str = ""
    contact_email: str = ""
    linkedin_url: str = ""
    profile_url: str = ""
    source: str = ""
    relevance_score: int = 0
    relevance_reason: str = ""
    why_good_fit: str = ""
    status: str = "new"
    outreach_draft: str = ""
    created_at: Optional[datetime] = None
