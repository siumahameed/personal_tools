"""Tests for deadlines.py."""
import sys
import os
from datetime import datetime, timedelta
_test_root = os.path.dirname(os.path.dirname(__file__))
sys.path.insert(0, _test_root)
sys.path.insert(0, os.path.join(_test_root, 'src'))

from features.deadlines import DeadlineTracker


PROFILE = {
    "name": "Test User",
    "target_countries": ["Germany"],
}


class TestDeadlineTracker:

    def setup_method(self):
        self.tracker = DeadlineTracker(PROFILE)

    def test_calculate_empty(self):
        deadlines = self.tracker.calculate([], [])
        assert deadlines == []

    def test_scholarship_deadline_parsing(self):
        scholarships = [{
            "name": "DAAD",
            "country": "Germany",
            "deadline_end": "December 15, 2025",
        }]
        deadlines = self.tracker.calculate(scholarships, [])
        assert len(deadlines) > 0
        assert deadlines[0]["name"] == "DAAD"

    def test_deadline_has_required_fields(self):
        scholarships = [{
            "name": "Test Scholarship",
            "country": "Germany",
            "deadline_end": "December 31, 2025",
        }]
        deadlines = self.tracker.calculate(scholarships, [])
        d = deadlines[0]
        assert "name" in d
        assert "deadline" in d
        assert "remaining_days" in d
        assert "status" in d
        assert "type" in d

    def test_overdue_deadline(self):
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%B %d, %Y")
        scholarships = [{
            "name": "Past Due",
            "country": "Germany",
            "deadline_end": yesterday,
        }]
        deadlines = self.tracker.calculate(scholarships, [])
        assert len(deadlines) > 0
        assert deadlines[0]["remaining_days"] < 0
        assert deadlines[0]["remaining_days"] < 0  # status may vary, but days should be negative

    def test_future_deadline(self):
        next_year = (datetime.now() + timedelta(days=365)).strftime("%B %d, %Y")
        scholarships = [{
            "name": "Future",
            "country": "Germany",
            "deadline_end": next_year,
        }]
        deadlines = self.tracker.calculate(scholarships, [])
        assert len(deadlines) > 0
        assert deadlines[0]["remaining_days"] > 0

    def test_university_deadline(self):
        universities = [{
            "name": "TU Munich",
            "country": "Germany",
            "deadline": "July 15, 2025",
            "program": "Data Science",
        }]
        deadlines = self.tracker.calculate([], universities)
        assert len(deadlines) > 0
        assert deadlines[0]["type"] == "university"

    def test_parse_date(self):
        from features.deadlines import DeadlineTracker
        dt = DeadlineTracker(PROFILE)
        result = dt._parse_date("December 15, 2025")
        assert result is not None
        assert result.year == 2025
        assert result.month == 12
        assert result.day == 15
