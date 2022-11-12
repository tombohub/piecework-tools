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
    total_sheets = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return str(self.number)


class ActionTime(models.Model):
    action = models.ForeignKey(Action, on_delete=models.DO_NOTHING)
    start = models.DateTimeField()
    end = models.DateTimeField(null=True, blank=True)
    unit = models.ForeignKey(Unit, on_delete=models.DO_NOTHING)
    is_current = models.BooleanField(default=True)

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
    method = models.ForeignKey(SprintMethod, on_delete=models.DO_NOTHING)

    def __str__(self) -> str:
        return str(self.start)
