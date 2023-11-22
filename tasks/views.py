"""Tasks views"""

from django.shortcuts import redirect, render

from .forms import RecurringTaskModelForm, TaskModelForm
from .models import RecurringTask, Task


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


def recurring_tasks_list(request):
    if request.method == "POST":
        form = RecurringTaskModelForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("tasks:recurring")
    form = RecurringTaskModelForm()
    recurring_tasks_all = RecurringTask.objects.all()
    context = {"tasks": recurring_tasks_all, "form": form}
    return render(request, "tasks/recurring-tasks.html", context)


def delete_recurring_task(request, pk):
    task = RecurringTask.objects.get(pk=pk)
    task.delete()
    return redirect("tasks:recurring")
