from __future__ import annotations

import datetime as dt
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar

from django.db import models
from django.db.models import F, Q, Sum

## PROJECTS context


class Project(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    drywall_company = models.CharField(max_length=255, null=True, blank=True)
    general_contractor = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


## RATES context
class HeightCategory(models.TextChoices):
    """
    Height of the ceiling
    """

    OVER_EIGHT_TO_NINE_INCLUSIVE = (
        "over_8_to_9_inclusive",
        "Over 8 ft up to and including 9 ft",
    )
    OVER_NINE_TO_TEN_INCLUSIVE = (
        "over_9_to_10_inclusive",
        "Over 9 ft up to and including 10 ft",
    )
    OVER_TEN_TO_ELEVEN_INCLUSIVE = (
        "over_10_to_11_inclusive",
        "Over 10 ft up to and including 11 ft",
    )
    OVER_ELEVEN_TO_TWELVE_INCLUSIVE = (
        "over_11_to_12_inclusive",
        "Over 11 ft up to and including 12 ft",
    )


class DrywallRateCategory(models.TextChoices):
    """
    Drywall Rate can be regular or premium which is extra on top of premium
    """

    STANDARD = "standard", "Standard"
    PREMIUM = "premium", "Premium"


class RatePeriod(models.Model):
    name = models.CharField(max_length=30)
    starts_on = models.DateField()
    ends_on = models.DateField()

    class Meta:
        constraints: ClassVar = [
            models.CheckConstraint(
                condition=Q(ends_on__gt=F("starts_on")),
                name="rate_period_end_after_start",
            ),
            models.UniqueConstraint(
                fields=["starts_on", "ends_on"], name="unique_rate_period_dates"
            ),
        ]

    def __str__(self) -> str:
        return self.name


class DrywallRate(models.Model):
    height = models.CharField(max_length=30, choices=HeightCategory.choices)
    rate_category = models.CharField(
        max_length=20, choices=DrywallRateCategory.choices, null=True, blank=True
    )
    rate = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    rate_period = models.ForeignKey(
        RatePeriod, on_delete=models.PROTECT, null=True, blank=True
    )


## UNIT context


class DrywallMaterial(models.Model):
    class DrywallType(models.TextChoices):
        REGULAR = "regular", "Regular"
        DENS_GLASS = "dens_glass", "Dens glass"
        BLUE = "blue", "Blue"
        TYPE_X = "type_x", "Type X"
        TYPE_C = "type_c", "Type C"

    class Length(models.IntegerChoices):
        EIGHT = 8, "8 ft"
        NINE = 9, "9 ft"
        TEN = 10, "10 ft"
        TWELVE = 12, "12 ft"

    drywall_type = models.CharField(max_length=30, choices=DrywallType.choices)
    length_feet = models.PositiveSmallIntegerField(choices=Length.choices)
    rate_category = models.CharField(
        max_length=20, choices=DrywallRateCategory.choices, null=True, blank=True
    )

    @property
    def square_footage(self) -> int:
        """
        Returns calculated square footage of one sheet
        """
        return self.length_feet * 4

    def __str__(self) -> str:
        return f"{self.drywall_type} - {self.length_feet}"

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["drywall_type", "length_feet"],
                name="unique_drywall_material_type_and_length",
            )
        ]


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
    if TYPE_CHECKING:
        unitsheetcount_set: models.Manager[UnitSheetCount]
        activitylog_set: models.Manager[ActivityLog]

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        ON_HOLD = "on_hold", "On hold"
        COMPLETED = "completed", "Completed"

    number = models.CharField(max_length=10)
    potlights_count = models.PositiveSmallIntegerField(null=True, blank=True)
    sprinklers_count = models.PositiveSmallIntegerField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.ACTIVE)
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=True, blank=True
    )
    height_feet = models.CharField(
        null=True,
        blank=True,
        choices=HeightCategory.choices,
        help_text="Height of the unit ceiling in feet",
    )

    started_on = models.DateField(null=True, blank=True)
    completed_on = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True, null=True)

    objects: UnitManager = UnitManager()

    class Meta:
        constraints: ClassVar = [
            models.UniqueConstraint(
                fields=["status"],
                condition=Q(status="active"),
                name="only_one_active_unit",
            )
        ]

    def mark_completed(self, completed_on: dt.date | None = None) -> None:
        """
        Mark the unit as completed and record its completion date.
        """
        update_fields = []

        if self.status != self.Status.COMPLETED:
            self.status = self.Status.COMPLETED
            update_fields.append("status")

        if self.completed_on is None:
            self.completed_on = completed_on or dt.date.today()
            update_fields.append("completed_on")

        if update_fields:
            self.save(update_fields=update_fields)

    @property
    def total_square_footage(self) -> int:
        """
        Total square footage of all sheets in the unit
        """
        return sum(
            unit_sheet_count.square_footage
            for unit_sheet_count in self.unitsheetcount_set.select_related(
                "drywall_material"
            )
        )

    @property
    def _pricing_date(self) -> dt.date:
        pricing_date = self.completed_on or self.started_on

        if pricing_date is None:
            raise ValueError(
                "The unit must have a start or completion date to determine pricing"
            )
        return pricing_date

    @property
    def drywall_price(self) -> Decimal:
        """
        Calculate the unit's drywall price using its height, applicable
        rate period, and square footage in each drywall rate category.
        """
        # Determine the applicable rate period.
        # Validate that the unit has a height and rate period.
        # Calculate square footage grouped by material rate category.
        # Retrieve the rate for each category, unit height, and rate period.
        # Validate that every used category has exactly one rate.
        # Return the sum of square footage × rate for every category.

    @property
    def total_price(self):
        """
        Total price to get paid for the unit
        """
        return round(self.total_square_footage * 0.352, 2)

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

    @property
    def rate_per_sqft(self): ...

    def __str__(self) -> str:
        return str(self.number)


class UnitSheetCount(models.Model):
    """
    Number of sheets of a particular drywall material used in a unit.
    """

    drywall_material = models.ForeignKey(DrywallMaterial, on_delete=models.PROTECT)

    count = models.PositiveIntegerField()
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    @property
    def square_footage(self) -> int:
        """
        Returns calculated square footage
        """
        return self.drywall_material.square_footage * self.count

    def __str__(self):
        return f"{self.drywall_material} {self.count}"


## ACTIVITY context


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


class Note(models.Model):
    """
    Notes for the application features
    """

    note = models.TextField()

    def __str__(self):
        return str(self.note)
