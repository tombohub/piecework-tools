from django.shortcuts import render, redirect, get_object_or_404

import time_tracker.db
from .models import ActivityTime, Unit, Activity, Note, DailyDurations
import datetime as dt
from . import db
from .forms import NoteModelForm


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
        "pp": DailyDurations.objects.get(id=158),
    }
    return render(request, "time_tracker/index.html", context)


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

    action_time = ActivityTime(activity=activity, start=now, unit=unit)
    action_time.save()
    return redirect(index)


def stop_current_activity(request):
    end_current_activity()
    return redirect(index)


def notes_index(request):
    if request.method == "POST":
        form = NoteModelForm(request.POST)
        if form.is_valid():
            form.save()
            # return to this same view , but now with GET request.
            # So the form is not resubmitted upon refreshing the page
            return redirect(notes_index)

    notes = Note.objects.all()
    form = NoteModelForm()
    context = {"notes": notes, "form": form}
    return render(request, "time_tracker/notes.html", context)


def notes_delete(request, pk):
    note = Note.objects.get(pk=pk)
    note.delete()
    return redirect(notes_index)


# helpers
def end_current_activity():
    """
    Ends current activity
    """
    # check if there is any current action and end it
    now = dt.datetime.now()
    exists_current_action = ActivityTime.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action = ActivityTime.objects.get(is_current=True)
        current_action.end = now
        current_action.is_current = False
        current_action.save()
