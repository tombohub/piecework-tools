from django.urls import path

from . import views

app_name = "piecework"
urlpatterns = [
    path("", views.index, name="home"),
    path("start-action", views.start_activity, name="start-activity"),
    path("stop-action", views.stop_current_activity, name="stop-action"),
    path("notes", views.notes_index, name="notes"),
    path("notes/delete/<int:pk>", views.notes_delete, name="notes-delete"),
    path("units", views.units_index, name="units_index"),
    path("units/<int:pk>", views.units_details, name="units_detail"),
    path("units/create", views.units_create, name="units_create"),
    path("units/<int:pk>/edit", views.units_edit, name="units_edit"),
    path("units/<int:pk>/complete", views.unit_complete, name="units_complete"),
    path("units/<int:pk>/delete", views.unit_delete, name="units_delete"),
    path(
        "boarding-sprints/start",
        views.start_boarding_sprint,
        name="start_boarding_sprint",
    ),
    path(
        "boarding-sprints/stop",
        views.stop_boarding_sprint,
        name="stop_boarding_sprint",
    ),
    path(
        "boarding-sprints/<int:pk>/sheet-counts",
        views.boarding_sprint_sheet_counts,
        name="boarding_sprint_sheet_counts",
    ),
    path(
        "boarding-sprints/<int:pk>/discard",
        views.discard_boarding_sprint,
        name="discard_boarding_sprint",
    ),
]
