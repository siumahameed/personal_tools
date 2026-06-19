"""Tests for match_score.py."""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from features.match_score import MatchScoreCalculator


PROFILE = {
    "name": "Test User",
    "gpa": "3.20",
    "cgpa_scale": "4.00",
    "target_countries": ["Germany", "USA", "Canada"],
    "target_fields": ["Machine Learning", "Data Science", "Artificial Intelligence"],
    "top_scholarships": ["DAAD"],
}


class TestMatchScoreCalculator:

    def setup_method(self):
        self.calc = MatchScoreCalculator(PROFILE)

    def test_calculate_with_data_returns_scores(self):
        """Even without input, hardcoded scholarships should be scored."""
        scores = self.calc.calculate([])
        assert len(scores) > 0
        assert all("name" in s for s in scores)
        assert all("overall" in s for s in scores)

    def test_each_score_has_required_fields(self):
        scores = self.calc.calculate([])
        for s in scores:
            assert "name" in s
            assert "overall" in s
            assert "recommendation" in s
            assert "academic_match" in s
            assert "profile_fit" in s
            assert "competition" in s
            assert "german_relevance" in s

    def test_scores_are_sorted_descending(self):
        scores = self.calc.calculate([])
        for i in range(len(scores) - 1):
            assert scores[i]["overall"] >= scores[i + 1]["overall"], \
                f"Scores not sorted: {scores[i]['name']} ({scores[i]['overall']}) < {scores[i+1]['name']} ({scores[i+1]['overall']})"

    def test_germany_scholarship_scores_higher(self):
        """German scholarships should generally score higher for a Germany-targeting profile."""
        scores = self.calc.calculate([])
        daad = next(s for s in scores if "DAAD" in s["name"])
        knight = next(s for s in scores if "Knight" in s["name"])
        assert daad["overall"] >= knight["overall"]

    def test_recommendation_strong_for_high_scores(self):
        scores = self.calc.calculate([])
        top = scores[0]
        assert top["overall"] >= 5
        assert len(top["recommendation"]) > 0

    def test_dynamic_scholarship_added(self):
        """Passing a scholarship not in the hardcoded list should add it."""
        scores = self.calc.calculate([{
            "name": "Custom Test Scholarship",
            "country": "Germany",
            "fields": "Machine Learning",
            "match_score": 80,
            "competition": "Medium",
        }])
        names = [s["name"] for s in scores]
        assert "Custom Test Scholarship" in names

    def test_duplicate_name_skipped(self):
        """If a passed scholarship matches a hardcoded name, the hardcoded one should be kept."""
        scores = self.calc.calculate([{
            "name": "DAAD Scholarship",
            "country": "USA",
            "fields": "Physics",
        }])
        daad = next(s for s in scores if s["name"] == "DAAD Scholarship")
        assert daad["german_relevance"] >= 5  # Should still favor German relevance
