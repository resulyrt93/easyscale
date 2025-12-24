"""Time utilities for EasyScale."""

import logging
from datetime import date, datetime, time
from typing import Optional

import pytz

from easyscale.config.models import DayOfWeek

logger = logging.getLogger(__name__)


def get_current_datetime(timezone: str = "UTC") -> datetime:
    """
    Get current datetime in specified timezone.

    Args:
        timezone: IANA timezone name (e.g., 'UTC', 'America/New_York')

    Returns:
        Current datetime in specified timezone

    Raises:
        ValueError: If timezone is invalid
    """
    try:
        tz = pytz.timezone(timezone)
        return datetime.now(tz)
    except pytz.exceptions.UnknownTimeZoneError as e:
        raise ValueError(f"Invalid timezone: {timezone}") from e


def is_date_match(current_date: date, target_dates: list[date]) -> bool:
    """
    Check if current date matches any target dates.

    Args:
        current_date: Date to check
        target_dates: List of target dates

    Returns:
        True if current_date matches any target date
    """
    if not target_dates:
        return False

    return current_date in target_dates


def is_day_match(current_datetime: datetime, target_days: list[DayOfWeek]) -> bool:
    """
    Check if current day of week matches any target days.

    Args:
        current_datetime: Datetime to check
        target_days: List of target days (DayOfWeek enum)

    Returns:
        True if current day matches any target day
    """
    if not target_days:
        return False

    # Get day name from datetime (e.g., 'Monday', 'Tuesday')
    current_day_name = current_datetime.strftime("%A")

    # Check if current day matches any target days
    for target_day in target_days:
        if target_day.value == current_day_name:
            return True

    return False


def is_time_in_range(
    current_time: time,
    start_time: Optional[time],
    end_time: Optional[time]
) -> bool:
    """
    Check if current time is within the specified range.

    Args:
        current_time: Time to check
        start_time: Start time of range (inclusive)
        end_time: End time of range (exclusive)

    Returns:
        True if current_time is within range, or if no range specified

    Note:
        - If both start_time and end_time are None, returns True
        - If only start_time is set, checks if current_time >= start_time
        - If only end_time is set, checks if current_time < end_time
        - Time ranges do NOT span midnight (create two rules instead)
    """
    # No time range specified
    if start_time is None and end_time is None:
        return True

    # Only start time specified
    if start_time is not None and end_time is None:
        return current_time >= start_time

    # Only end time specified
    if start_time is None and end_time is not None:
        return current_time < end_time

    # Both times specified
    # Note: We don't support ranges spanning midnight
    # The validation in models.py ensures start_time < end_time
    return start_time <= current_time < end_time


def format_datetime(dt: datetime) -> str:
    """
    Format datetime for logging.

    Args:
        dt: Datetime to format

    Returns:
        Formatted datetime string
    """
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def format_time(t: time) -> str:
    """
    Format time for logging.

    Args:
        t: Time to format

    Returns:
        Formatted time string (HH:MM)
    """
    return t.strftime("%H:%M")
