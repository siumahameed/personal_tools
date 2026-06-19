from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, func
from app.core.database import Base


class UserProfile(Base):
    __tablename__ = "user_profile"

    id = Column(Integer, primary_key=True)
    name = Column(Text, default="")
    title = Column(Text, default="Freelancer")
    summary = Column(Text, default="")
    skills = Column(JSON, default=list)
    portfolio_urls = Column(JSON, default=list)
    experience_years = Column(Integer, default=0)
    location = Column(Text, default="Remote")
    preferred_roles = Column(JSON, default=list)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    def __repr__(self):
        return f"<UserProfile(name='{self.name}', title='{self.title}')>"


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True)
    title = Column(Text)
    platform = Column(Text)
    url = Column(Text)
    description = Column(Text)
    required_skills = Column(JSON, default=list)
    budget = Column(Text, default="")
    client_name = Column(Text, default="")
    client_location = Column(Text, default="")
    posted_date = Column(DateTime, nullable=True)
    match_score = Column(Integer, default=0)
    match_reason = Column(Text, default="")
    source_query = Column(Text, default="")
    status = Column(Text, default="new")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Job(id={self.id}, title='{self.title[:50]}', platform='{self.platform}', score={self.match_score})>"


class Prospect(Base):
    __tablename__ = "prospects"

    id = Column(Integer, primary_key=True)
    company_name = Column(Text)
    industry = Column(Text, default="")
    contact_name = Column(Text, default="")
    contact_title = Column(Text, default="")
    email = Column(Text, default="")
    linkedin_url = Column(Text, default="")
    company_url = Column(Text, default="")
    source = Column(Text)
    source_query = Column(Text, default="")
    notes = Column(Text, default="")
    relevance_score = Column(Integer, default=0)
    relevance_reason = Column(Text, default="")
    status = Column(Text, default="new")
    contacts = Column(JSON, default=list)
    social_links = Column(JSON, default=dict)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<Prospect(id={self.id}, company='{self.company_name}', score={self.relevance_score})>"


class OutreachDraft(Base):
    __tablename__ = "outreach_drafts"

    id = Column(Integer, primary_key=True)
    prospect_id = Column(Integer, nullable=True)
    job_id = Column(Integer, nullable=True)
    email_subject = Column(Text, default="")
    email_body = Column(Text, default="")
    linkedin_message = Column(Text, default="")
    channel = Column(Text, default="both")
    status = Column(Text, default="draft")
    sent_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<OutreachDraft(id={self.id}, subject='{self.email_subject[:50]}', status='{self.status}')>"


class ScrapeSession(Base):
    __tablename__ = "scrape_sessions"

    id = Column(Integer, primary_key=True)
    source = Column(Text)
    query = Column(Text, default="")
    urls_found = Column(Integer, default=0)
    jobs_found = Column(Integer, default=0)
    prospects_found = Column(Integer, default=0)
    status = Column(Text, default="running")
    error = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ScrapeSession(id={self.id}, source='{self.source}', status='{self.status}')>"


class ResearchLead(Base):
    __tablename__ = "research_leads"

    id = Column(Integer, primary_key=True)
    name = Column(Text, default="")
    title = Column(Text, default="")
    institution = Column(Text, default="")
    department = Column(Text, default="")
    country = Column(Text, default="")
    region = Column(Text, default="")  # bangladesh, south_asia, global
    research_fields = Column(JSON, default=list)        # combined (for back-compat)
    current_fields = Column(JSON, default=list)         # currently working on
    past_fields = Column(JSON, default=list)            # previously worked on
    recent_papers = Column(JSON, default=list)
    bio = Column(Text, default="")
    contact_email = Column(Text, default="")            # primary email
    all_emails = Column(JSON, default=list)             # every email found on page
    contact_phone = Column(Text, default="")
    office_address = Column(Text, default="")
    personal_website = Column(Text, default="")
    linkedin_url = Column(Text, default="")
    twitter_url = Column(Text, default="")
    github_url = Column(Text, default="")
    google_scholar_url = Column(Text, default="")
    orcid_url = Column(Text, default="")
    researchgate_url = Column(Text, default="")
    profile_url = Column(Text, default="")
    source = Column(Text, default="web_search")
    source_query = Column(Text, default="")
    relevance_score = Column(Integer, default=0)
    relevance_reason = Column(Text, default="")
    why_good_fit = Column(Text, default="")
    status = Column(Text, default="new")
    outreach_draft = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    def __repr__(self):
        return f"<ResearchLead(id={self.id}, name='{self.name[:30]}', institution='{self.institution[:30]}', score={self.relevance_score})>"
