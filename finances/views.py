from django.shortcuts import render

from .models import RecurringExpense, Vendor


def index(request):
    return render(request, "finances/index.html")


def recurring_expenses_list(request):
    recurring_expenses_all = RecurringExpense.objects.all()
    context = {"recurring_expenses": recurring_expenses_all}
    return render(request, "finances/recurring-expenses.html", context)


def vendors_list(request):
    vendors_all = Vendor.objects.all()
    context = {"vendors": vendors_all}
    return render(request, "finances/vendors.html", context)
