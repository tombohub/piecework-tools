from django.urls import path

from . import views

app_name = "finances"
urlpatterns = [
    path("", views.index, name="home"),
    path(
        "recurring-expenses/", views.recurring_expenses_list, name="recurring-expenses"
    ),
    path("vedors/", views.vendors_list, name="vendors"),
]
