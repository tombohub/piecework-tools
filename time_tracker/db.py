"""
Database fetching and saving operations.
To avoid using models in views
"""
from django.db.models import Sum
from .models import ActionTime, Action, Unit
from . import domain
import datetime as dt
from django_pandas.io import read_frame
from django_pivot.pivot import pivot


def list_activities() -> list[str]:
    """
    get list of all available actions

    Returns
    -------
    list[str]
        available actions
    """
    actions = Action.objects.all()
    return [action.name for action in actions]


def current_action() -> domain.CurrentActivity | None:
    """
    Get current action name if exists. Otherwise None

    Returns
    -------
    str | None
        current action name
    """
    exists_current_action = ActionTime.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action_object = ActionTime.objects.get(is_current=True)
        current_action = domain.CurrentActivity(
            name=current_action_object.action.name, start=current_action_object.start
        )
    else:
        current_action = None

    return current_action


def previous_action():
    prev_action_time_obj = ActionTime.objects.filter(is_current=False).last()
    duration = prev_action_time_obj.duration
    name = prev_action_time_obj.action.name
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


def daily_durations() -> list[dict]:
    """
    Get pivot data, daily total duration for each activity

    Returns
    -------
    list[dict]
        [{'date': dt.datetime, ...'activity_name': Duration}]
    """
    pivot_table = pivot(ActionTime, "date", "action__name", "duration")
    for record in pivot_table:
        for key, value in record.items():
            if key == "date":
                continue
            record[key] = domain.Duration(value)

    return list(pivot_table)


def get_activity_times(date: dt.date, activity: str) -> list[domain.ActivityTime]:
    activity_times_db = ActionTime.objects.filter(date=date, action__name=activity)
    activity_times = [
        domain.ActivityTime(
            activity=domain.Activity(
                name=act_time.action.name, description=act_time.action.description
            ),
            date=act_time.date,
            start=act_time.start,
            end=act_time.end,
            duration=act_time.duration,
        )
        for act_time in activity_times_db
    ]
    return activity_times


def calculate_boarding_duration_today() -> dt.timedelta:
    """
    Calculate today's total duration for board activity

    Returns
    -------
    dt.timedelta
        total duration
    """
    result = ActionTime.objects.filter(
        action__name="board", date=dt.date.today()
    ).aggregate(duration=Sum("duration"))
    return result["duration"]


def calculate_board_activity_daily_durations():
    result = (
        ActionTime.objects.filter(action__name="board")
        .values("date")
        .annotate(total_duration=Sum("duration"))
    )
    return list(result)
