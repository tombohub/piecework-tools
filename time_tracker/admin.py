from django.contrib import admin
from .models import (
    Action,
    ActionTime,
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


@admin.register(ActionTime)
class ActionTimeAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "action",
        "date",
        "start",
        "end",
        "unit",
    )


admin.site.register([Action, SprintMethod, SprintTime, UnitArea, UnitSheetCount])
