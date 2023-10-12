from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("start-action", views.start_activity, name="start-activity"),
    path("stop-action", views.stop_current_activity, name="stop-action"),
    path("daily-durations", views.daily_durations, name="daily-durations"),
    path('notes', views.notes_index, name='notes'),
    path('notes/delete/<int:pk>', views.notes_delete, name='notes-delete')
]
