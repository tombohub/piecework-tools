from django.shortcuts import render, redirect, get_object_or_404
from django.views.generic import ListView
from .models import ActionTime, Unit, Action
import datetime as dt
from . import db
from .domain import Activity


def index(request):
    actions = db.list_activities()
    current_action = db.current_action()
    active_units = db.active_units()
    previous_action = db.previous_action()
    # NOTE: magic string
    boarding_duration_today = db.get_boarding_duration_today()

    context = {
        "actions": actions,
        "current_action": current_action,
        "active_units": active_units,
        "previous_action": previous_action,
        "boarding_duration_today": boarding_duration_today,
    }
    return render(request, "time_tracker/index.html", context)


def start_action(request):
    end_current_activity()

    now = dt.datetime.now()
    action_name = request.GET["action"]
    action = Action.objects.get(name=action_name)
    unit_number = request.GET["unit"]
    unit = get_object_or_404(Unit, number=unit_number)

    action_time = ActionTime(action=action, start=now, unit=unit)
    action_time.save()
    return redirect(index)


def stop_current_action(request):
    end_current_activity()
    return redirect(index)


def stats(request):
    daily_stats = db.daily_stats()
    context = {"daily_stats": daily_stats}
    return render(request, "time_tracker/stats.html", context)


# helpers
def end_current_activity():
    """
    Ends current activity
    """
    # check if there is any current action and end it
    now = dt.datetime.now()
    exists_current_action = ActionTime.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action = ActionTime.objects.get(is_current=True)
        current_action.end = now
        current_action.is_current = False
        current_action.save()
