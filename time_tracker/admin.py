from django.contrib import admin
from .models import Activity, ActivityLog, Unit, UnitSheetCount, Note, DailyDurations


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    readonly_fields = ["square_footage"]
    extra = 4


class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline]
    list_display = ["number", "total_square_footage"]
    readonly_fields = [
        "total_square_footage",
        "total_price",
        "total_boarding_duration",
        "dollars_per_hour_of_boarding",
        "sheet_count",
        "sheet_count_per_hour_of_boarding",
    ]


class DailyDurationsAdmin(admin.ModelAdmin):
    list_display = ["date", "activity_name", "duration"]


admin.site.register(Unit, UnitAdmin)
admin.site.register(DailyDurations, DailyDurationsAdmin)


@admin.register(ActivityLog)
class ActivityTimeAdmin(admin.ModelAdmin):
    date_hierarchy = "date"
    list_display = (
        "activity",
        "date",
        "start",
        "end",
        "unit",
    )


admin.site.register([Activity, Note])
