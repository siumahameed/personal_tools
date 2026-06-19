from app.core.models import UserProfile, Job, Prospect, OutreachDraft, ScrapeSession


def test_user_profile_default_create():
    p = UserProfile()
    assert p.name is None
    assert p.skills is None


def test_user_profile_assign():
    p = UserProfile()
    p.name = "Test User"
    p.skills = ["Python", "ML"]
    assert p.name == "Test User"
    assert p.skills == ["Python", "ML"]


def test_job_create():
    j = Job(title="ML Engineer", platform="upwork", url="https://example.com/job1")
    assert j.title == "ML Engineer"
    assert j.platform == "upwork"
    assert j.url == "https://example.com/job1"


def test_job_assign():
    j = Job(title="ML Engineer", platform="upwork", url="https://example.com/job1")
    j.match_score = 85
    j.match_reason = "Great fit"
    assert j.match_score == 85
    assert j.match_reason == "Great fit"


def test_prospect_create():
    p = Prospect(company_name="TestCorp", source="web_search")
    assert p.company_name == "TestCorp"
    assert p.source == "web_search"


def test_prospect_assign():
    p = Prospect(company_name="TestCorp", source="web_search")
    p.relevance_score = 75
    assert p.relevance_score == 75


def test_outreach_draft_create():
    d = OutreachDraft(email_subject="Hello", email_body="Body text")
    assert d.email_subject == "Hello"
    assert d.email_body == "Body text"


def test_scrape_session_create():
    s = ScrapeSession(source="web_search")
    assert s.source == "web_search"


def test_scrape_session_assign():
    s = ScrapeSession(source="web_search", query="ML jobs")
    s.status = "completed"
    s.jobs_found = 5
    assert s.status == "completed"
    assert s.jobs_found == 5


def test_user_profile_repr():
    p = UserProfile(name="Test User", title="Engineer")
    assert "Test User" in repr(p)


def test_job_repr():
    j = Job(title="ML Engineer", platform="upwork", url="https://example.com/job1")
    assert "ML Engineer" in repr(j)


def test_prospect_repr():
    p = Prospect(company_name="TestCorp", source="web_search")
    assert "TestCorp" in repr(p)


def test_draft_repr():
    d = OutreachDraft(email_subject="Hello", email_body="Body text")
    assert "Hello" in repr(d)


def test_scrape_session_repr():
    s = ScrapeSession(source="web_search", query="ML jobs")
    assert "web_search" in repr(s)
