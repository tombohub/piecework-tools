from django.db import models
from .domain import PRICE_PER_SQUARE_FOOT

# Create your models here.


class Activity(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)

    class Meta:
        db_table = "activities"

class Unit(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
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

    def __str__(self) -> str:
        return str(self.number)

    class Meta:
        db_table = "units"


class SheetType(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return str(self.name)

    class Meta:
        db_table = "sheet_types"


class UnitSheetCount(models.Model):
    """
    Number and type of sheets per unit
    """

    type = models.ForeignKey(SheetType, on_delete=models.PROTECT)
    length = models.PositiveIntegerField(choices=[(8, 8), (9, 9), (10, 10), (12, 12)])
    count = models.PositiveIntegerField()
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)
    square_footage = models.PositiveIntegerField()

    def save(self, *args, **kwargs):
        self.square_footage = self.length * self.count * 4
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.length}ft {self.type}"

    class Meta:
        db_table = "unit_sheet_counts"

class ActivityTime(models.Model):
    action = models.ForeignKey(Activity, on_delete=models.PROTECT)
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
        return str(self.action)

    class Meta:
        db_table = "activity_times"

class TotalDurationActivityPerUnit(models.Model):
    number = models.SmallIntegerField(blank=True, null=True)
    activity = models.CharField(max_length=20, blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = "total_duration_activity_per_unit"


class DailyDurations(models.Model):
    date = models.DateField(blank=True, null=True)
    duration = models.DurationField(blank=True, null=True)
    activity_name = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = "daily_durations"


class CompletedUnitsSquareFootage(models.Model):
    unit_number = models.SmallIntegerField(blank=True, null=True)
    footage = models.BigIntegerField(blank=True, null=True)

    class Meta:
        managed = False  # Created from a view. Don't remove.
        db_table = "completed_units_square_footage"

class Note(models.Model):
    note = models.TextField(help_text='notes for various ideas and reminders', )

    def __str__(self):
        return self.note
