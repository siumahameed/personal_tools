from app.discovery.web_search import (
    WebSearchAgent,
    GENERIC_COMPANY_NAMES,
    JOB_BOARD_DOMAINS,
    LINKEDIN_JOB_RE,
    LINKEDIN_PROFILE_RE,
    LINKEDIN_COMPANY_RE,
)


def _is_valid_social_url(url: str, domain: str) -> bool:
    return WebSearchAgent._is_valid_social_url(url, domain)


def _is_real_company_name(name: str) -> bool:
    return WebSearchAgent._is_real_company_name(name)


def _is_meaningful_title(title: str, description: str, company: str) -> bool:
    return WebSearchAgent._is_meaningful_title(title, description, company)


class TestUrlValidation:
    def test_linkedin_company_url_accepted(self):
        assert _is_valid_social_url("https://www.linkedin.com/company/acme-software", "linkedin.com") is True

    def test_linkedin_job_url_accepted(self):
        assert _is_valid_social_url("https://www.linkedin.com/jobs/view/data-analyst-1234567890", "linkedin.com") is True

    def test_linkedin_profile_url_accepted(self):
        assert _is_valid_social_url("https://www.linkedin.com/in/john-doe", "linkedin.com") is True

    def test_linkedin_search_rejected(self):
        assert _is_valid_social_url("https://www.linkedin.com/search/results/all/?keywords=data", "linkedin.com") is False

    def test_linkedin_feed_rejected(self):
        assert _is_valid_social_url("https://www.linkedin.com/feed/", "linkedin.com") is False

    def test_linkedin_jobs_search_rejected(self):
        assert _is_valid_social_url("https://www.linkedin.com/jobs/search/?keywords=ml", "linkedin.com") is False

    def test_twitter_account_accepted(self):
        assert _is_valid_social_url("https://twitter.com/acme_data", "twitter.com") is True

    def test_twitter_hashtag_rejected(self):
        assert _is_valid_social_url("https://twitter.com/hashtag/data", "twitter.com") is False

    def test_twitter_explore_rejected(self):
        assert _is_valid_social_url("https://twitter.com/explore", "twitter.com") is False

    def test_x_account_accepted(self):
        assert _is_valid_social_url("https://x.com/acme_data", "x.com") is True

    def test_x_home_rejected(self):
        assert _is_valid_social_url("https://x.com/home", "x.com") is False

    def test_facebook_page_accepted(self):
        assert _is_valid_social_url("https://facebook.com/AcmeDataServices", "facebook.com") is True

    def test_facebook_groups_rejected(self):
        assert _is_valid_social_url("https://facebook.com/groups/datascience", "facebook.com") is False

    def test_facebook_events_rejected(self):
        assert _is_valid_social_url("https://facebook.com/events/12345", "facebook.com") is False

    def test_facebook_marketplace_rejected(self):
        assert _is_valid_social_url("https://facebook.com/marketplace/item/12345", "facebook.com") is False

    def test_facebook_login_rejected(self):
        assert _is_valid_social_url("https://facebook.com/login/", "facebook.com") is False

    def test_arbitrary_company_site_accepted(self):
        assert _is_valid_social_url("https://acme.com/about", "acme.com") is True


class TestCompanyNameFiltering:
    def test_generic_linkedin_rejected(self):
        assert _is_real_company_name("Linkedin") is False
        assert _is_real_company_name("LinkedIn") is False
        assert _is_real_company_name("linkedin") is False

    def test_generic_facebook_rejected(self):
        assert _is_real_company_name("Facebook") is False
        assert _is_real_company_name("facebook") is False

    def test_generic_twitter_rejected(self):
        assert _is_real_company_name("Twitter") is False
        assert _is_real_company_name("X") is False

    def test_real_company_accepted(self):
        assert _is_real_company_name("Acme Software") is True
        assert _is_real_company_name("DataCorp") is True
        assert _is_real_company_name("Insight Analytics LLC") is True

    def test_short_names_rejected(self):
        assert _is_real_company_name("A") is False
        assert _is_real_company_name("") is False

    def test_blocked_starts_rejected(self):
        assert _is_real_company_name("Login Page") is False
        assert _is_real_company_name("Sign Up Now") is False
        assert _is_real_company_name("404 Not Found") is False

    def test_pure_numbers_rejected(self):
        assert _is_real_company_name("12345") is False
        assert _is_real_company_name("2024-01-01") is False


class TestTitleMeaningfulness:
    def test_meaningful_title_accepted(self):
        assert _is_meaningful_title("Data Analyst at Acme", "We are looking for a data analyst", "Acme") is True

    def test_empty_combined_rejected(self):
        assert _is_meaningful_title("", "", "") is False

    def test_generic_platform_title_rejected(self):
        assert _is_meaningful_title("LinkedIn", "", "") is False


class TestLinkedInPatterns:
    def test_job_pattern_matches(self):
        match = LINKEDIN_JOB_RE.search("https://www.linkedin.com/jobs/view/data-analyst-at-acme-1234567890")
        assert match is not None
        assert match.group(1) == "1234567890"

    def test_job_pattern_no_match(self):
        assert LINKEDIN_JOB_RE.search("https://www.linkedin.com/company/acme") is None

    def test_profile_pattern_matches(self):
        match = LINKEDIN_PROFILE_RE.search("https://www.linkedin.com/in/john-doe-123")
        assert match is not None
        assert match.group(1) == "john-doe-123"

    def test_company_pattern_matches(self):
        match = LINKEDIN_COMPANY_RE.search("https://www.linkedin.com/company/acme-software")
        assert match is not None
        assert match.group(1) == "acme-software"


class TestGenericNamesConstant:
    def test_social_platforms_in_set(self):
        assert "linkedin" in GENERIC_COMPANY_NAMES
        assert "facebook" in GENERIC_COMPANY_NAMES
        assert "twitter" in GENERIC_COMPANY_NAMES
        assert "x" in GENERIC_COMPANY_NAMES

    def test_job_boards_in_set(self):
        assert "indeed" in GENERIC_COMPANY_NAMES
        assert "glassdoor" in GENERIC_COMPANY_NAMES
        assert "ycombinator" in GENERIC_COMPANY_NAMES
