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


admin.site.register(
    [Action, ActionTime, SprintMethod, SprintTime, UnitArea, UnitSheetCount]
)
