from django.contrib import admin
from .models import (
    Activity,
    ActivityTime,
    SprintMethod,
    Unit,
    UnitSheetCount,
    Note
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    readonly_fields = ['square_footage']

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


admin.site.register([Activity, SprintMethod, Note])
