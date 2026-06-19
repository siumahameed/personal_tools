from app.core.schemas import UserProfileSchema, JobSchema, ProspectSchema, OutreachDraftSchema, StatsSchema


def test_user_profile_schema_defaults():
    s = UserProfileSchema()
    assert s.name == ""
    assert s.title == ""
    assert s.location == "Remote"


def test_stats_schema():
    s = StatsSchema(total_jobs=10, total_prospects=5, total_drafts=2, matched_jobs=3, high_score_jobs=1)
    assert s.total_jobs == 10
    assert s.total_prospects == 5
    assert s.high_score_jobs == 1


def test_job_schema_optional():
    s = JobSchema(id=1, title="Test", platform="upwork", url="https://x.com", description="desc")
    assert s.match_score == 0
    assert s.status == "new"
    assert s.budget == ""


def test_prospect_schema():
    s = ProspectSchema(id=1, company_name="Acme", source="web_search")
    assert s.relevance_score == 0
    assert s.status == "new"


def test_draft_schema():
    s = OutreachDraftSchema(id=1)
    assert s.status == "draft"
    assert s.channel == "both"
