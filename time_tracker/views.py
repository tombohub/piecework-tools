from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.views import View
from .models import ActionTime, Unit, Action
from . import contexts
import datetime as dt
from ninja import NinjaAPI, Schema
from typing import List
import json
from dataclasses import dataclass

api = NinjaAPI()


@api.get("/index")
def api_index(request):
    data = contexts.index_context()
    return data


def index(request):
    context = contexts.index_context()
    return render(request, "time_tracker/index.html", context)


def start_action(request):
    end_current_action()

    now = dt.datetime.now()
    action_name = request.GET["action"]
    action = Action.objects.get(name=action_name)
    unit_number = request.GET["unit"]
    unit = get_object_or_404(Unit, number=unit_number)

    action_time = ActionTime(action=action, start=now, unit=unit)
    action_time.save()
    return redirect(index)


def stop_current_action(request):
    end_current_action()
    return redirect(index)


def change_unit(request):
    pass


# helpers
def end_current_action():
    # check if there is any current action and end it
    now = dt.datetime.now()
    exists_current_action = ActionTime.objects.filter(is_current=True).exists()
    if exists_current_action:
        current_action = ActionTime.objects.get(is_current=True)
        current_action.end = now
        current_action.is_current = False
        current_action.save()
