from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="home"),
    path("start-action", views.start_action, name="start-action"),
    path("stop-action", views.stop_current_activity, name="stop-action"),
    path("stats", view=views.stats, name="stats"),
]
