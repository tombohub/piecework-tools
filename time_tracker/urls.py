from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("start-action", views.start_action, name="start-action"),
    path("stop-action", views.stop_current_activity, name="stop-action"),
    path("daily-durations", views.daily_durations, name="daily-durations"),
]
