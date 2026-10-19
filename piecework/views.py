"""Piecework views"""

import datetime as dt

from django.shortcuts import get_object_or_404, redirect, render

from .forms import NoteModelForm
from .models import Activity, ActivityLog, Note, Unit


def index(request):
    activity_names = Activity.objects.names()
    current_activity_log = ActivityLog.objects.current()
    active_unit = Unit.objects.active()
    # NOTE: magic string
    boarding_duration_today = ActivityLog.objects.boarding_duration_today()
    break_duration_today = ActivityLog.objects.break_duration_today()
    boarding_duration_current_unit = (
        active_unit.total_boarding_duration if active_unit else dt.timedelta()
    )
    total_duration_today = ActivityLog.objects.total_duration_today()

    context = {
        "activity_names": activity_names,
        "current_activity_log": current_activity_log,
        "active_unit": active_unit,
        "boarding_duration_today": boarding_duration_today,
        "break_duration_today": break_duration_today,
        "boarding_duration_current_unit": boarding_duration_current_unit,
        "total_duration_today": total_duration_today,
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
    unit_pk = request.GET["unit_pk"]
    unit = get_object_or_404(Unit, pk=unit_pk)

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
