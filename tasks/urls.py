from django.urls import path

from . import views

app_name = "tasks"
urlpatterns = [
    path("", views.index, name="home"),
    path("tasks/delete/<int:pk>", views.task_delete, name="delete"),
    path("recurring/", views.recurring_tasks_list, name="recurring"),
    path(
        "tasks/recurring/delete/<int:pk>",
        views.delete_recurring_task,
        name="recurring-delete",
    ),
]
