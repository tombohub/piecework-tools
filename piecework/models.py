# from __future__ import annotations

import datetime as dt
from typing import ClassVar

from django.db import models
from django.db.models import Q, Sum
from django.utils import timezone

from .domain import PRICE_PER_SQUARE_FOOT


class ActivityManager(models.Manager):
    def names(self):
        """
        Retrieve list of avaliable activity names.
        """
        return self.get_queryset().values_list("name", flat=True)


class Activity(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    objects: ActivityManager = ActivityManager()

    def __str__(self) -> str:
        return str(self.name)


class Project(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    drywall_company = models.CharField(max_length=255, null=True, blank=True)
    general_contractor = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class UnitManager(models.Manager["Unit"]):
    def active(self):
        """
        Return the active unit, or None if there isn't one
        """
        try:
            return self.get_queryset().get(status=self.model.Status.ACTIVE)
        except self.model.DoesNotExist:
            return None


class Unit(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"

    number = models.CharField(max_length=10)
    potlights_count = models.PositiveSmallIntegerField(null=True, blank=True)
    sprinklers_count = models.PositiveSmallIntegerField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=Status, default=Status.ACTIVE)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=True, blank=True
    )

    objects: UnitManager = UnitManager()

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["status"],
                condition=Q(status="active"),
                name="only_one_active_unit",
            )
        ]

    @property
    def total_square_footage(self):
        """
        Total square footage of all sheets in the unit
        """
        return sum(
            [
                unit_sheet_count.square_footage
                for unit_sheet_count in self.unitsheetcount_set.all()
            ]
        )

    @property
    def total_price(self):
        """
        Total price for the unit
        """
        return round(self.total_square_footage * PRICE_PER_SQUARE_FOOT, 2)

    @property
    def total_boarding_duration(self) -> dt.timedelta:
        """
        Total boarding duration for the unit
        """
        duration = self.activitylog_set.filter(activity__name="board").aggregate(
            duration=models.Sum("duration")
        )["duration"]
        return duration if duration is not None else dt.timedelta(seconds=0)

    @property
    def dollars_per_hour_of_boarding(self):
        """
        Dollars per hour of boarding for the unit
        """
        return (
            round(
                self.total_price / self.total_boarding_duration.total_seconds() * 3600,
                2,
            )
            if self.total_boarding_duration.total_seconds() > 0
            else 0
        )

    @property
    def sheet_count(self):
        """
        Total number of sheets in the unit
        """
        return sum(
            [
                unit_sheet_count.count
                for unit_sheet_count in self.unitsheetcount_set.all()
            ]
        )

    @property
    def sheet_count_per_hour_of_boarding(self):
        """
        Total number of sheets in the unit
        """
        return (
            round(
                self.sheet_count / self.total_boarding_duration.total_seconds() * 3600,
                2,
            )
            if self.total_boarding_duration.total_seconds() > 0
            else 0
        )

    def __str__(self) -> str:
        return str(self.number)


class ActivityLogManager(models.Manager):
    def break_duration_today(self) -> dt.timedelta:
        """
        Retrieves the break activity today's total duration.
        """
        duration = (
            self.get_queryset()
            .filter(activity__name="break", date=dt.date.today())
            .aggregate(total=models.Sum("duration"))
        )["total"]

        return duration or dt.timedelta()

    def current(self):
        """
        Currently active activity log.
        """
        try:
            return self.get_queryset().select_related("activity").get(is_current=True)
        except self.model.DoesNotExist:
            return None

    def total_duration_today(self) -> dt.timedelta:
        """
        Return today's total duration for all
        activities.
        """
        duration = (
            self.get_queryset()
            .filter(start__date=dt.date.today())
            .aggregate(total=models.Sum("duration"))
        )["total"]

        return duration or dt.timedelta()

    def boarding_duration_today(self) -> dt.timedelta:
        """
        Return today's total duration for boarding activity
        """
        duration = (
            self.get_queryset()
            .filter(activity__name="board", date=dt.date.today())
            .aggregate(total=Sum("duration"))
        )["total"]

        return duration or dt.timedelta()


class ActivityLog(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    is_current = models.BooleanField(default=True)
    is_boarding = models.BooleanField(default=False)
    duration = models.DurationField(null=True, blank=True)

    objects: ActivityLogManager = ActivityLogManager()

    def save(self, *args, **kwargs):
        if self.end is not None:
            self.duration = self.end - self.start
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return str(self.activity)


class DrywallType(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return str(self.name)


class UnitSheetCount(models.Model):
    """
    Number and type of sheets per unit
    """

    type = models.ForeignKey(DrywallType, on_delete=models.PROTECT)
    length = models.PositiveIntegerField(choices=[(8, 8), (9, 9), (10, 10), (12, 12)])
    count = models.PositiveIntegerField()
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    square_footage = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        self.square_footage = self.length * self.count * 4
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.length}ft {self.type}"


class Note(models.Model):
    note = models.TextField()

    def __str__(self):
        return str(self.note)
