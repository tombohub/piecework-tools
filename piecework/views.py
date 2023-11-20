"""Piecework views"""

import datetime as dt

from django.shortcuts import get_object_or_404, redirect, render

import piecework.db

from . import db
from .forms import NoteModelForm
from .models import Activity, ActivityLog, Note, Unit


def index(request):
    actions = db.list_activities()
    current_action = db.current_activity()
    active_units = db.active_units()
    previous_action = db.previous_activity()
    # NOTE: magic string
    boarding_duration_today = db.calculate_boarding_duration_today()
    break_duration_today = db.calculate_break_duration_today()
    boarding_duration_current_unit = db.calculate_current_unit_total_boarding_duration()
    total_duration_today = db.total_duration_today()
    total_duration_today_without_travel = db.total_duration_today_without_travel_time()

    context = {
        "actions": actions,
        "current_action": current_action,
        "active_units": active_units,
        "previous_action": previous_action,
        "boarding_duration_today": boarding_duration_today,
        "break_duration_today": break_duration_today,
        "boarding_duration_current_unit": boarding_duration_current_unit,
        "total_duration_today": total_duration_today,
        "total_duration_today_without_travel": total_duration_today_without_travel,
        "boarding_pct": db.boarding_duration_today_pct(),
    }
    return render(request, "piecework/index.html", context)


def start_activity(request):
    """
    Starts the new activity.
    """
    end_current_activity()

    now = dt.datetime.now()
    activity_name = request.GET["action"]
    activity = Activity.objects.get(name=activity_name)
    unit_number = request.GET["unit"]
    unit = get_object_or_404(Unit, number=unit_number)

    action_time = ActivityLog(activity=activity, start=now, unit=unit)
    action_time.save()
    return redirect("piecework:home")


def stop_current_activity(request):
    end_current_activity()
    return redirect("piecework:home")


def notes_index(request):
    if request.method == "POST":
        form = NoteModelForm(request.POST)
        if form.is_valid():
            form.save()
            # return to this same view , but now with GET request.
            # So the form is not resubmitted upon refreshing the page
            return redirect("piecework:notes")

    notes = Note.objects.all()
    form = NoteModelForm()
    context = {"notes": notes, "form": form}
    return render(request, "piecework/notes.html", context)


def notes_delete(request, pk):
    note = Note.objects.get(pk=pk)
    note.delete()
    return redirect("piecework:notes")


# helpers
def end_current_activity():
    """
    Ends current activity
    """
    # check if there is any current action and end it
    now = dt.datetime.now()
    exists_current_action = ActivityLog.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action = ActivityLog.objects.get(is_current=True)
        current_action.end = now
        current_action.is_current = False
        current_action.save()
