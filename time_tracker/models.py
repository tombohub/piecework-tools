from django.db import models

# Create your models here.


class Action(models.Model):
    name = models.CharField(max_length=20, unique=True)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class UnitArea(models.Model):
    name = models.CharField(max_length=20)

    def __str__(self) -> str:
        return str(self.name)


class Unit(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)
    washrooms_count = models.PositiveSmallIntegerField(null=True, blank=True)
    closets_count = models.PositiveSmallIntegerField(null=True, blank=True)
    rooms_count = models.PositiveSmallIntegerField(null=True, blank=True)
    windows_count = models.PositiveSmallIntegerField(null=True, blank=True)
    bulkheads_count = models.PositiveSmallIntegerField(null=True, blank=True)
    is_finished = models.BooleanField(default=False)

    def __str__(self) -> str:
        return str(self.number)


class SheetType(models.Model):
    name = models.CharField(max_length=10)

    def __str__(self):
        return str(self.name)


class UnitSheetCount(models.Model):
    type = models.ForeignKey(SheetType, on_delete=models.PROTECT)
    length = models.PositiveIntegerField(choices=[(8, 8), (9, 9), (10, 10), (12, 12)])
    count = models.PositiveIntegerField()
    unit = models.ForeignKey(Unit, on_delete=models.CASCADE)

    def __str__(self):
        return f"{self.length}ft {self.type}"


class ActionTime(models.Model):
    action = models.ForeignKey(Action, on_delete=models.PROTECT)
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


class SprintMethod(models.Model):
    name = models.CharField(max_length=50)
    description = models.TextField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.name)


class SprintTime(models.Model):
    start = models.DateTimeField()
    end = models.DateTimeField()
    sheets_count = models.PositiveIntegerField()
    pieces_count = models.PositiveIntegerField()
    method = models.ForeignKey(SprintMethod, on_delete=models.PROTECT)
    area = models.ForeignKey(UnitArea, on_delete=models.PROTECT)

    def __str__(self) -> str:
        return str(self.start)
