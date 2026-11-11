"""Piecework views"""

import datetime as dt

from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import NoteModelForm, UnitForm, UnitStatsFilterForm
from .models import Activity, ActivityLog, BoardingSprint, Note, Project, Unit


def index(request):

    activity_names = Activity.objects.names()
    current_activity_log = ActivityLog.objects.current()
    current_boarding_sprint = BoardingSprint.objects.current()
    can_start_boarding_sprint = BoardingSprint.objects.can_start(current_activity_log)
    last_completed_activity_log = ActivityLog.objects.last_completed()
    active_unit = Unit.objects.active_unit()
    # NOTE: magic string
    boarding_duration_today = ActivityLog.objects.boarding_duration_today()
    break_duration_today = ActivityLog.objects.break_duration_today()
    boarding_duration_current_unit = (
        active_unit.total_boarding_duration if active_unit else dt.timedelta()
    )
    total_duration_today = ActivityLog.objects.total_duration_today()

    unit_stats_filter_form = UnitStatsFilterForm(request.GET)
    selected_project = None
    selected_height_feet = None

    if unit_stats_filter_form.is_valid():
        selected_project = unit_stats_filter_form.cleaned_data["project"]
        selected_height_feet = unit_stats_filter_form.cleaned_data["height_feet"]

    weighted_sheets_per_hour = Unit.objects.weighted_sheets_per_hour(
        project=selected_project, height_feet=selected_height_feet
    )

    context = {
        "activity_names": activity_names,
        "current_activity_log": current_activity_log,
        "current_boarding_sprint": current_boarding_sprint,
        "can_start_boarding_sprint": can_start_boarding_sprint,
        "last_completed_activity_log": last_completed_activity_log,
        "active_unit": active_unit,
        "boarding_duration_today": boarding_duration_today,
        "break_duration_today": break_duration_today,
        "boarding_duration_current_unit": boarding_duration_current_unit,
        "total_duration_today": total_duration_today,
        "project_filter_form": unit_stats_filter_form,
        "selected_project": selected_project,
        "selected_height_feet": selected_height_feet,
        "weighted_sheets_per_hour": weighted_sheets_per_hour,
    }
    return render(request, "piecework/index.html", context)


@require_POST
def start_activity(request):
    """
    Starts the new activity.
    """
    unit = get_object_or_404(Unit, status=Unit.Status.ACTIVE)
    end_current_activity()

    activity = get_object_or_404(Activity, name=request.POST["action"])

    ActivityLog.objects.create(activity=activity, start=timezone.now(), unit=unit)

    return redirect("piecework:home")


def stop_current_activity(request):
    end_current_activity()
    return redirect("piecework:home")


@require_POST
def start_boarding_sprint(request):
    BoardingSprint.objects.start_sprint()

    return redirect("piecework:home")


## NOTES


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


## UNIT


def units_index(request):
    units = Unit.objects.order_by("-created_at")

    return render(request, "piecework/units/index.html", {"units": units})


def units_create(request):
    if request.method == "POST":
        form = UnitForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("piecework:units_index")
    else:
        form = UnitForm(initial={"project": Project.objects.active_project()})

    return render(request, "piecework/units/create.html", {"form": form})


def units_edit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)

    if request.method == "POST":
        form = UnitForm(request.POST, instance=unit)

        if form.is_valid():
            form.save()
            return redirect("piecework:units_detail", pk=unit.pk)
    else:
        form = UnitForm(instance=unit)

    context = {"form": form, "unit": unit}
    return render(request, "piecework/units/edit.html", context)


@require_POST
def unit_complete(request, pk):
    unit = get_object_or_404(Unit, pk=pk, status=Unit.Status.ACTIVE)
    unit.mark_completed()

    return redirect("piecework:home")


@require_POST
def unit_delete(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    unit.delete()

    return redirect("piecework:units_index")


def units_details(request, pk):
    unit = get_object_or_404(Unit, pk=pk)

    drywall_sheet_counts = unit.unitsheetcount_set.select_related(
        "drywall_material"
    ).order_by("drywall_material__length_feet", "drywall_material__drywall_type")

    jmould_counts = unit.unitjmouldcount_set.order_by("length_feet")

    insulation_counts = unit.unitinsulationcount_set.select_related(
        "insulation_material"
    ).order_by(
        "insulation_material__insulation_type",
        "insulation_material__width_inches",
        "insulation_material__length_inches",
    )

    context = {
        "unit": unit,
        "drywall_sheet_counts": drywall_sheet_counts,
        "jmould_counts": jmould_counts,
        "insulation_counts": insulation_counts,
    }

    return render(request, "piecework/units/details.html", context)


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
