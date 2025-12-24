"""Tests for time utilities."""

from datetime import date, datetime, time

import pytest
import pytz

from easyscale.config.models import DayOfWeek
from easyscale.utils.time_utils import (
    format_datetime,
    format_time,
    get_current_datetime,
    is_date_match,
    is_day_match,
    is_time_in_range,
)


class TestGetCurrentDatetime:
    """Tests for get_current_datetime."""

    def test_utc_timezone(self):
        """Test getting current datetime in UTC."""
        dt = get_current_datetime("UTC")
        assert dt.tzinfo is not None
        assert dt.tzinfo == pytz.UTC

    def test_custom_timezone(self):
        """Test getting current datetime in custom timezone."""
        dt = get_current_datetime("America/New_York")
        assert dt.tzinfo is not None
        # Check that timezone name contains expected string
        tz_name = str(dt.tzinfo)
        assert "America/New_York" in tz_name or "EST" in tz_name or "EDT" in tz_name

    def test_invalid_timezone(self):
        """Test with invalid timezone."""
        with pytest.raises(ValueError) as exc_info:
            get_current_datetime("Invalid/Timezone")
        assert "Invalid timezone" in str(exc_info.value)


class TestIsDateMatch:
    """Tests for is_date_match."""

    def test_date_matches(self):
        """Test date matches in list."""
        current = date(2025, 12, 25)
        targets = [date(2025, 12, 24), date(2025, 12, 25), date(2025, 12, 26)]
        assert is_date_match(current, targets) is True

    def test_date_not_matches(self):
        """Test date not in list."""
        current = date(2025, 12, 27)
        targets = [date(2025, 12, 24), date(2025, 12, 25), date(2025, 12, 26)]
        assert is_date_match(current, targets) is False

    def test_empty_target_list(self):
        """Test with empty target list."""
        current = date(2025, 12, 25)
        targets = []
        assert is_date_match(current, targets) is False

    def test_single_date(self):
        """Test with single target date."""
        current = date(2025, 12, 25)
        targets = [date(2025, 12, 25)]
        assert is_date_match(current, targets) is True


class TestIsDayMatch:
    """Tests for is_day_match."""

    def test_monday_matches(self):
        """Test Monday matches."""
        # 2025-01-06 is a Monday
        dt = datetime(2025, 1, 6, 12, 0, 0)
        target_days = [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY]
        assert is_day_match(dt, target_days) is True

    def test_tuesday_not_matches(self):
        """Test Tuesday not in target days."""
        # 2025-01-07 is a Tuesday
        dt = datetime(2025, 1, 7, 12, 0, 0)
        target_days = [DayOfWeek.MONDAY, DayOfWeek.WEDNESDAY, DayOfWeek.FRIDAY]
        assert is_day_match(dt, target_days) is False

    def test_weekend_days(self):
        """Test weekend days."""
        # 2025-01-11 is a Saturday
        dt = datetime(2025, 1, 11, 12, 0, 0)
        target_days = [DayOfWeek.SATURDAY, DayOfWeek.SUNDAY]
        assert is_day_match(dt, target_days) is True

    def test_empty_target_days(self):
        """Test with empty target days."""
        dt = datetime(2025, 1, 6, 12, 0, 0)
        target_days = []
        assert is_day_match(dt, target_days) is False

    def test_all_weekdays(self):
        """Test all weekdays."""
        target_days = [
            DayOfWeek.MONDAY,
            DayOfWeek.TUESDAY,
            DayOfWeek.WEDNESDAY,
            DayOfWeek.THURSDAY,
            DayOfWeek.FRIDAY,
        ]
        # Test each weekday
        for day_num in range(5):  # Monday=0 to Friday=4
            dt = datetime(2025, 1, 6 + day_num, 12, 0, 0)
            assert is_day_match(dt, target_days) is True


class TestIsTimeInRange:
    """Tests for is_time_in_range."""

    def test_time_in_range(self):
        """Test time within range."""
        current = time(14, 30)  # 2:30 PM
        start = time(9, 0)  # 9:00 AM
        end = time(17, 0)  # 5:00 PM
        assert is_time_in_range(current, start, end) is True

    def test_time_before_range(self):
        """Test time before range."""
        current = time(8, 0)  # 8:00 AM
        start = time(9, 0)  # 9:00 AM
        end = time(17, 0)  # 5:00 PM
        assert is_time_in_range(current, start, end) is False

    def test_time_after_range(self):
        """Test time after range."""
        current = time(18, 0)  # 6:00 PM
        start = time(9, 0)  # 9:00 AM
        end = time(17, 0)  # 5:00 PM
        assert is_time_in_range(current, start, end) is False

    def test_time_at_start(self):
        """Test time at start (inclusive)."""
        current = time(9, 0)  # 9:00 AM
        start = time(9, 0)  # 9:00 AM
        end = time(17, 0)  # 5:00 PM
        assert is_time_in_range(current, start, end) is True

    def test_time_at_end(self):
        """Test time at end (exclusive)."""
        current = time(17, 0)  # 5:00 PM
        start = time(9, 0)  # 9:00 AM
        end = time(17, 0)  # 5:00 PM
        assert is_time_in_range(current, start, end) is False

    def test_no_range_specified(self):
        """Test with no range specified."""
        current = time(14, 30)
        assert is_time_in_range(current, None, None) is True

    def test_only_start_time(self):
        """Test with only start time."""
        current = time(10, 0)
        start = time(9, 0)
        assert is_time_in_range(current, start, None) is True

        current = time(8, 0)
        assert is_time_in_range(current, start, None) is False

    def test_only_end_time(self):
        """Test with only end time."""
        current = time(16, 0)
        end = time(17, 0)
        assert is_time_in_range(current, None, end) is True

        current = time(18, 0)
        assert is_time_in_range(current, None, end) is False


class TestFormatFunctions:
    """Tests for format functions."""

    def test_format_datetime(self):
        """Test datetime formatting."""
        dt = datetime(2025, 12, 25, 14, 30, 0, tzinfo=pytz.UTC)
        formatted = format_datetime(dt)
        assert "2025-12-25" in formatted
        assert "14:30:00" in formatted
        assert "UTC" in formatted

    def test_format_time(self):
        """Test time formatting."""
        t = time(14, 30, 45)
        formatted = format_time(t)
        assert formatted == "14:30"

    def test_format_time_midnight(self):
        """Test time formatting at midnight."""
        t = time(0, 0, 0)
        formatted = format_time(t)
        assert formatted == "00:00"

    def test_format_time_noon(self):
        """Test time formatting at noon."""
        t = time(12, 0, 0)
        formatted = format_time(t)
        assert formatted == "12:00"
