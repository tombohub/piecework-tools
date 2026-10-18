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
