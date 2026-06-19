import re

from app.research.agent import ResearchDiscoveryAgent, _is_valid_research_url
from app.core.models import ResearchLead


class TestUrlValidation:
    def _ok(self, url: str) -> bool:
        ok, _ = _is_valid_research_url(url)
        return ok

    def test_researchgate_accepted(self):
        assert self._ok("https://www.researchgate.net/profile/John-Doe") is True

    def test_arxiv_accepted(self):
        assert self._ok("https://arxiv.org/a/author_12345") is True

    def test_arxiv_paper_accepted(self):
        assert self._ok("https://arxiv.org/abs/2305.12345") is True
        assert self._ok("https://arxiv.org/abs/2305.12345v1") is True

    def test_university_profile_accepted(self):
        assert self._ok("https://cs.du.ac.bd/~jdoe") is True
        assert self._ok("https://www.du.ac.bd/people/john-doe") is True
        assert self._ok("https://mit.edu/people/jdoe") is True
        assert self._ok("https://www.bracu.ac.bd/faculty/john-doe") is True
        assert self._ok("https://www.example.edu/profile/john") is True
        assert self._ok("https://www.example.edu/staff/researcher") is True
        assert self._ok("https://www.example.edu/directory/john-smith") is True

    def test_university_list_page_rejected(self):
        assert self._ok("https://www.du.ac.bd/department/statistics") is False
        assert self._ok("https://www.bracu.ac.bd/faculties") is False
        assert self._ok("https://mit.edu/research/labs") is False

    def test_linkedin_accepted(self):
        assert self._ok("https://linkedin.com/in/john-doe") is True

    def test_facebook_rejected(self):
        assert self._ok("https://facebook.com/john.doe") is False

    def test_twitter_rejected(self):
        assert self._ok("https://twitter.com/johndoe") is False

    def test_instagram_rejected(self):
        assert self._ok("https://instagram.com/johndoe") is False

    def test_youtube_rejected(self):
        assert self._ok("https://youtube.com/watch?v=abc") is False

    def test_empty_url_rejected(self):
        assert self._ok("https:///") is False

    def test_reddit_user_accepted(self):
        assert self._ok("https://www.reddit.com/user/johndoe") is True
        assert self._ok("https://reddit.com/u/johndoe") is True
        assert self._ok("https://old.reddit.com/user/johndoe") is True

    def test_reddit_subreddit_rejected(self):
        assert self._ok("https://www.reddit.com/r/MachineLearning") is False
        assert self._ok("https://reddit.com/r/deeplearning") is False

    def test_reddit_post_accepted(self):
        assert self._ok("https://www.reddit.com/r/MachineLearning/comments/abc123/") is True
        assert self._ok("https://www.reddit.com/r/deeplearning/comments/xyz789/some_title/") is True


class TestNameValidation:
    def test_real_name_accepted(self):
        assert ResearchDiscoveryAgent._is_real_name("Sium Ahameed") is True
        assert ResearchDiscoveryAgent._is_real_name("John Michael Smith") is True
        assert ResearchDiscoveryAgent._is_real_name("Md. Rahim Uddin") is True

    def test_too_short_rejected(self):
        assert ResearchDiscoveryAgent._is_real_name("Joe") is False
        assert ResearchDiscoveryAgent._is_real_name("") is False

    def test_too_long_rejected(self):
        assert ResearchDiscoveryAgent._is_real_name("A" * 100) is False

    def test_generic_rejected(self):
        for term in ["home", "login", "search", "profile", "faculty", "research"]:
            assert ResearchDiscoveryAgent._is_real_name(term.title()) is False, f"should reject {term}"

    def test_lowercase_rejected(self):
        assert ResearchDiscoveryAgent._is_real_name("john doe") is False

    def test_single_name_rejected(self):
        assert ResearchDiscoveryAgent._is_real_name("John") is False

    def test_too_many_words_rejected(self):
        assert ResearchDiscoveryAgent._is_real_name("John Michael Peter Smith Jones Williams") is False


class TestCountryGuessing:
    def test_bangladesh_detected(self):
        assert "Bangladesh" in ResearchDiscoveryAgent._guess_country_from_text("University of Dhaka, Bangladesh")

    def test_india_detected(self):
        assert "India" in ResearchDiscoveryAgent._guess_country_from_text("IIT Delhi, India")

    def test_usa_detected(self):
        assert "USA" in ResearchDiscoveryAgent._guess_country_from_text("MIT, United States")

    def test_unknown_returns_empty(self):
        assert ResearchDiscoveryAgent._guess_country_from_text("Some random research text") == ""


class TestRegionClassification:
    def test_bangladesh_country_bangladesh(self):
        assert ResearchDiscoveryAgent._classify_region("Bangladesh", "") == "bangladesh"

    def test_india_is_south_asia(self):
        assert ResearchDiscoveryAgent._classify_region("India", "") == "south_asia"

    def test_usa_is_global(self):
        assert ResearchDiscoveryAgent._classify_region("USA", "") == "global"

    def test_bangladesh_url_in_bd(self):
        assert ResearchDiscoveryAgent._classify_region("", "https://du.ac.bd/people") == "bangladesh"

    def test_dhaka_url_in_bd(self):
        assert ResearchDiscoveryAgent._classify_region("", "https://bracu.ac.bd/dhaka") == "bangladesh"

    def test_empty_country_global(self):
        assert ResearchDiscoveryAgent._classify_region("", "https://mit.edu/people") == "global"


class TestSourceClassification:
    def test_researchgate_source(self):
        assert ResearchDiscoveryAgent._classify_source("https://www.researchgate.net/profile/X") == "researchgate"

    def test_arxiv_source(self):
        assert ResearchDiscoveryAgent._classify_source("https://arxiv.org/a/xyz") == "arxiv"

    def test_google_scholar_source(self):
        assert ResearchDiscoveryAgent._classify_source("https://scholar.google.com/citations?user=xyz") == "google_scholar"

    def test_linkedin_source(self):
        assert ResearchDiscoveryAgent._classify_source("https://www.linkedin.com/in/john") == "linkedin"

    def test_university_fallback(self):
        assert ResearchDiscoveryAgent._classify_source("https://cs.du.ac.bd/~jdoe") == "university_site"

    def test_reddit_source(self):
        assert ResearchDiscoveryAgent._classify_source("https://www.reddit.com/user/johndoe") == "reddit"


class TestResearchLeadModel:
    def test_default_create(self):
        lead = ResearchLead()
        assert lead.name in (None, "")
        assert lead.country in (None, "")
        assert lead.region in (None, "")
        assert lead.relevance_score in (None, 0)
        assert lead.research_fields in (None, [])
        assert lead.recent_papers in (None, [])
        assert lead.status in (None, "new")

    def test_assign(self):
        lead = ResearchLead(
            name="Dr. Test",
            title="Associate Professor",
            institution="Test University",
            country="Bangladesh",
            region="bangladesh",
            research_fields=["ml", "statistics"],
            recent_papers=["Paper 1"],
            relevance_score=85,
        )
        assert lead.name == "Dr. Test"
        assert lead.institution == "Test University"
        assert lead.country == "Bangladesh"
        assert lead.region == "bangladesh"
        assert "ml" in lead.research_fields
        assert lead.relevance_score == 85

    def test_repr(self):
        lead = ResearchLead(name="Test Person", institution="Test Uni", relevance_score=50)
        r = repr(lead)
        assert "Test" in r
        assert "50" in r
