from django import forms

from .models import RecurringTask, Task


class TaskModelForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = "__all__"


class RecurringTaskModelForm(forms.ModelForm):
    class Meta:
        model = RecurringTask
        fields = "__all__"
