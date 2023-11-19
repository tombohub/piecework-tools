"""
Database fetching and saving operations.
To avoid using models in views
"""
from django.db.models import Sum

from .models import ActivityLog, Activity, Unit
from . import domain
import datetime as dt
from django_pandas.io import read_frame
from django_pivot.pivot import pivot


def list_activities() -> list[str]:
    """
    get list of all available activities

    Returns
    -------
    list[str]
        available activities
    """
    activities = Activity.objects.all()
    return [action.name for action in activities]


def current_activity() -> "domain.CurrentActivity | None":
    """
    Get current action name if exists. Otherwise None

    Returns
    -------
    str | None
        current action name
    """
    exists_current_action = ActivityLog.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action_object = ActivityLog.objects.get(is_current=True)
        current_action = domain.CurrentActivity(
            name=current_action_object.activity.name, start=current_action_object.start
        )
    else:
        current_action = None

    return current_action


def previous_activity():
    prev_action_time_obj = ActivityLog.objects.filter(is_current=False).last()
    duration = prev_action_time_obj.duration
    name = prev_action_time_obj.activity.name
    return {"name": name, "duration": str(duration).split(".")[0]}


def active_units() -> list[int]:
    """
    Get currently active unit numbers. Most likely one only

    Returns
    -------
    list[int]
        active unit numbers
    """
    active_units_obj = Unit.objects.filter(is_finished=False)
    active_units_numbers = [unit.number for unit in active_units_obj]
    return active_units_numbers


def get_current_unit() -> Unit:
    """
    Get current active unit.
    Can only be one. Throws error if multiple

    Returns
    -------
    Unit
        current unit model object
    """
    unit_obj = Unit.objects.get(is_finished=False)
    return unit_obj


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


def calculate_current_unit_total_boarding_duration() -> dt.timedelta:
    """
    Total boarding duration for the current active unit so far

    Returns
    -------
    dt.timedelta
        total boarding duration
    """
    current_unit = get_current_unit()
    result = ActivityLog.objects.filter(
        activity__name="board", unit=current_unit
    ).aggregate(duration=Sum("duration"))
    return result["duration"]


def calculate_break_duration_today() -> dt.timedelta:
    """
    Calculate today's total duration for break activity

    Returns
    -------
    dt.timedelta
        total duration
    """
    result = ActivityLog.objects.filter(
        activity__name="break", date=dt.date.today()
    ).aggregate(duration=Sum("duration"))
    return result["duration"]


def total_duration_today() -> dt.timedelta:
    """
    Calculate today's total duration for all activities

    Returns
    -------
    dt.timedelta
        total duration
    """
    result = ActivityLog.objects.filter(date=dt.date.today()).aggregate(
        duration=Sum("duration")
    )
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