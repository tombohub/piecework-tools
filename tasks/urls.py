from django.urls import path

from . import views

app_name = "tasks"
urlpatterns = [
    path("", views.index, name="home"),
    path("tasks/delete/<int:pk>", views.delete, name="delete"),
]
