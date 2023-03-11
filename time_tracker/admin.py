from django.contrib import admin
from django import forms
from .models import (
    Activity,
    ActivityTime,
    SprintMethod,
    SprintTime,
    UnitArea,
    Unit,
    UnitSheetCount,
    SheetType,
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount


class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline]


admin.site.register(Unit, UnitAdmin)


@admin.register(ActivityTime)
class ActionTimeAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "action",
        "date",
        "start",
        "end",
        "unit",
    )


admin.site.register([Activity, SprintMethod, SprintTime, UnitArea, UnitSheetCount])
