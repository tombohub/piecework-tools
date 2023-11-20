from django.shortcuts import render

from .models import Task

# Create your views here.


def index(request):
    tasks_all = Task.objects.all()
    context = {"tasks": tasks_all}
    return render(request, "tasks/index.html", context)
