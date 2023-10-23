from django.contrib import admin
from .models import (
    Activity,
    ActivityTime,
    Unit,
    UnitSheetCount,
    Note,
    DailyDurations
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    readonly_fields = ["square_footage"]
    extra = 4


class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline]
    list_display = ['number', 'is_finished', 'windows_count']
    readonly_fields = [
        "total_square_footage",
        "total_price",
        "total_boarding_duration",
        "dollars_per_hour_of_boarding",
        "sheet_count",
        "sheet_count_per_hour_of_boarding",
    ]

class DailyDurationsAdmin(admin.ModelAdmin):
    list_display = ['date', 'activity_name', 'duration']

admin.site.register(Unit, UnitAdmin)
admin.site.register(DailyDurations, DailyDurationsAdmin)

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


admin.site.register([Activity, Note])
