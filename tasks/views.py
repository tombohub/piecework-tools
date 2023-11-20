"""Tasks views"""

from django.shortcuts import redirect, render

from .forms import TaskModelForm
from .models import Task


def index(request):
    if request.method == "POST":
        task_form = TaskModelForm(request.POST)
        if task_form.is_valid():
            task_form.save()
            return redirect("tasks:home")

    tasks_all = Task.objects.all()
    task_form = TaskModelForm()
    context = {"tasks": tasks_all, "task_form": task_form}
    return render(request, "tasks/index.html", context)


def delete(request, pk):
    task = Task.objects.get(pk=pk)
    task.delete()
    return redirect("tasks:home")
