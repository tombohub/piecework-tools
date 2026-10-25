from django.contrib import admin
from django.http.request import HttpRequest

from .models import (
    Activity,
    ActivityLog,
    DrywallMaterial,
    DrywallRate,
    Note,
    Project,
    RatePeriod,
    Unit,
    UnitSheetCount,
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    extra = 4


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline]
    list_display = ["number"]
    readonly_fields = [
        "total_square_footage",
        "total_price",
        "total_boarding_duration",
        "dollars_per_hour_of_boarding",
        "sheet_count",
        "sheet_count_per_hour_of_boarding",
    ]

    def get_queryset(self, request: HttpRequest):
        qs = super().get_queryset(request)
        return qs.prefetch_related("unitsheetcount_set")


admin.site.register(Unit, UnitAdmin)


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


@admin.register(DrywallMaterial)
class UnitDrywallMaterialAdmin(admin.ModelAdmin):
    pass


admin.site.register(RatePeriod)
admin.site.register(DrywallRate)
