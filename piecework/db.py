"""
Database fetching and saving operations.
To avoid using models in views
"""

import datetime as dt

from django.db.models import Sum

from .models import ActivityLog


def calculate_boarding_duration_today() -> dt.timedelta:
    """
    Calculate today's total duration for board activity

    Returns
    -------
    dt.timedelta
        total duration
    """
    result = ActivityLog.objects.filter(
        activity__name="board", date=dt.date.today()
    ).aggregate(duration=Sum("duration"))
    return result["duration"]


def total_duration_today_without_travel_time():
    """
    Calculate today's total duration for all activities except travel
    """
    result = (
        ActivityLog.objects.filter(date=dt.date.today())
        .exclude(activity__name="travel")
        .aggregate(duration=Sum("duration"))
    )

    return result["duration"]


def boarding_duration_today_pct():
    """
    Calculate today's total boarding duration as a percentage of total duration without travel
    """
    boarding_duration = calculate_boarding_duration_today()
    duration_no_travel = total_duration_today_without_travel_time()
    if boarding_duration and duration_no_travel:
        pct1 = boarding_duration / duration_no_travel * 100 if duration_no_travel else 0
        pct2 = round(pct1, 2)
        return pct2
    else:
        return 0
