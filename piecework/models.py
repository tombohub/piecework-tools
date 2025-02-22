import datetime as dt

from django.db import models

from .domain import PRICE_PER_SQUARE_FOOT

# Create your models here.


class Activity(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class Project(models.Model):
    name = models.CharField(max_length=255, null=True, blank=True)
    drywall_company = models.CharField(max_length=255, null=True, blank=True)
    general_contractor = models.CharField(max_length=255, null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class Unit(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.PROTECT, null=True, blank=True
    )
    number = models.PositiveSmallIntegerField()
    washrooms_count = models.PositiveSmallIntegerField(null=True, blank=True)
    closets_count = models.PositiveSmallIntegerField(null=True, blank=True)
    rooms_count = models.PositiveSmallIntegerField(null=True, blank=True)
    windows_count = models.PositiveSmallIntegerField(null=True, blank=True)
    bulkheads_count = models.PositiveSmallIntegerField(null=True, blank=True)
    potlights_count = models.PositiveSmallIntegerField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)

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


class ActivityLog(models.Model):
    activity = models.ForeignKey(Activity, on_delete=models.PROTECT)
    date = models.DateField(auto_now_add=True)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.PROTECT)
    is_current = models.BooleanField(default=True)
    is_boarding = models.BooleanField(default=False)
    duration = models.DurationField(null=True, blank=True)

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
