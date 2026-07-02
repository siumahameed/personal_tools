"""Tests for target.py regex extraction functions."""
import sys
import os
_test_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _test_root)
sys.path.insert(0, os.path.join(_test_root, 'src'))

from agents.target import (
    AMOUNT_RE, DEADLINE_RE, TUITION_RE, TOEFL_RE, GRE_RE,
    TargetEnricherAgent,
)


class TestRegexPatterns:

    def test_amount_eur(self):
        text = "The scholarship provides €1,200 per month"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) > 0
        assert matches[0] == "1,200"

    def test_amount_usd(self):
        text = "Award: $50,000 per year"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) > 0
        assert matches[0] == "50,000"

    def test_amount_eur_word(self):
        text = "Total: EUR 15000"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) > 0
        assert matches[0] == "15000"

    def test_amount_with_decimal(self):
        text = "Fee: $1,200.50"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) > 0
        assert matches[0] == "1,200.50"

    def test_amount_no_match(self):
        text = "No financial information here"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) == 0

    def test_amount_trailing_text(self):
        text = "€ 1,200/month"
        matches = AMOUNT_RE.findall(text)
        assert len(matches) > 0

    def _deadline_match_text(self, match):
        """Extract the deadline text from whichever regex group matched."""
        if match:
            return match.group(1) or match.group(2) or match.group(0)
        return ""

    def test_deadline_standard(self):
        text = "Application deadline: December 15, 2024"
        match = DEADLINE_RE.search(text)
        assert match is not None, f"Failed to match: {text}"
        match_text = self._deadline_match_text(match)
        assert "December" in match_text, f"Expected December in {match_text}"

    def test_deadline_various_formats(self):
        texts = [
            ("Deadline: March 1st, 2025", "March"),
            ("Closing date: September 30, 2024", "September"),
            ("Apply by January 15, 2025", "January"),
            ("Application Deadline: 31st December 2025", "December"),
        ]
        for text, expected_month in texts:
            match = DEADLINE_RE.search(text)
            assert match is not None, f"Failed to match: {text}"
            match_text = self._deadline_match_text(match)
            assert expected_month in match_text, f"Expected {expected_month} in {match_text}"

    def test_deadline_no_match(self):
        text = "No deadline information available"
        match = DEADLINE_RE.search(text)
        assert match is None

    def test_tuition_eur(self):
        text = "Tuition fees: €1,500 per semester"
        match = TUITION_RE.search(text)
        assert match is not None
        assert match.group(1) == "1,500"

    def test_tuition_usd(self):
        text = "Cost: $25,000 per year"
        match = TUITION_RE.search(text)
        assert match is not None

    def test_toefl(self):
        text = "TOEFL requirement: 90"
        match = TOEFL_RE.search(text)
        assert match is not None

    def test_ielts(self):
        text = "IELTS score: 6.5"
        match = TOEFL_RE.search(text)
        assert match is not None

    def test_gre_detection(self):
        text = "GRE General Test required"
        assert GRE_RE.search(text) is not None

    def test_gre_not_present(self):
        text = "No standardized test required"
        assert GRE_RE.search(text) is None


class TestTargetEnricher:
    """Test TargetEnricherAgent utility methods."""

    def setup_method(self):
        self.agent = TargetEnricherAgent(
            profile={"name": "Test User", "target_fields": ["ML", "AI"]},
            interactive=False,
        )

    def test_is_placeholder_empty(self):
        assert self.agent.is_placeholder("") is True
        assert self.agent.is_placeholder(None) is True

    def test_is_placeholder_known(self):
        assert self.agent.is_placeholder("Check website") is True
        assert self.agent.is_placeholder("Unknown") is True
        assert self.agent.is_placeholder("N/A") is True

    def test_is_placeholder_real_value(self):
        assert self.agent.is_placeholder("DAAD Scholarship") is False
        assert self.agent.is_placeholder("Machine Learning") is False
        assert self.agent.is_placeholder("€1,200") is False

    def test_col_index_found(self):
        headers = ["Name", "Country", "Amount", "Deadline"]
        idx = self.agent.col_index(headers, "amount")
        assert idx == 2

    def test_col_index_not_found(self):
        headers = ["Name", "Country"]
        idx = self.agent.col_index(headers, "amount")
        assert idx == -1

    def test_col_index_keyword_match(self):
        headers = ["Scholarship Name", "Country"]
        idx = self.agent.col_index(headers, "name")
        assert idx == 0

    def test_row_by_name_found(self):
        headers = ["Name", "Country"]
        rows = [["Test Scholar", "Germany"], ["Other", "USA"]]
        row = self.agent.row_by_name(headers, rows, "Test Scholar")
        assert row is not None
        assert row[1] == "Germany"

    def test_row_by_name_not_found(self):
        headers = ["Name", "Country"]
        rows = [["Test Scholar", "Germany"]]
        row = self.agent.row_by_name(headers, rows, "Nonexistent")
        assert row is None


class TestExtractFields:

    def setup_method(self):
        self.agent = TargetEnricherAgent(
            profile={"name": "Test User", "target_fields": ["ML"]},
            interactive=False,
        )

    def test_extract_amount_scholarship(self):
        result = self.agent._extract_fields("scholarships", "Award: €1,200 per month for 2 years")
        assert "Amount (per year)" in result
        assert "Coverage Details" in result

    def test_extract_deadline_scholarship(self):
        result = self.agent._extract_fields("scholarships", "Deadline: December 15, 2025")
        assert "Deadline Start" in result or "Coverage Details" in result

    def test_extract_professor_email(self):
        result = self.agent._extract_fields("professors", "Contact: prof@university.edu")
        assert result.get("Email") == "prof@university.edu"

    def test_extract_tuition_university(self):
        result = self.agent._extract_fields("universities", "Tuition fees: €1,500 per semester")
        assert "Tuition Fees" in result

    def test_extract_gre_university(self):
        result = self.agent._extract_fields("universities", "GRE General Test required for admission")
        assert "GRE/GMAT Required" in result
        assert result["GRE/GMAT Required"] == "Yes"

    def test_extract_gre_not_required(self):
        result = self.agent._extract_fields("universities", "No standardized test required")
        assert "GRE/GMAT Required" in result
        assert result["GRE/GMAT Required"] != "Yes"

    def test_amount_parse_error_handled(self):
        """Should not crash on malformed amount strings."""
        result = self.agent._extract_amount("Amount: € bad-data-here")
        assert result == {}  # Should gracefully return empty

    def test_empty_text_extraction(self):
        """Should handle empty text gracefully."""
        result = self.agent._extract_fields("scholarships", "")
        assert isinstance(result, dict)
