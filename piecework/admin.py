from math import ceil

from django.contrib import admin
from django.http.request import HttpRequest

from .models import (
    Activity,
    ActivityLog,
    DrywallRate,
    InsulationRate,
    JmouldRate,
    Note,
    PotlightRate,
    Project,
    RatePeriod,
    SprinklerRate,
    Unit,
    UnitDrywallMaterial,
    UnitInsulationCount,
    UnitInsulationMaterial,
    UnitJmouldCount,
    UnitSheetCount,
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    extra = 4


class UnitJmouldCountInline(admin.TabularInline):
    model = UnitJmouldCount
    extra = 2


class UnitInsulationCountInline(admin.TabularInline):
    model = UnitInsulationCount
    extra = 2
    readonly_fields = ["calculated_square_footage"]

    @admin.display(description="Square footage")
    def calculated_square_footage(self, obj):
        if obj is None or not obj.insulation_material_id or not obj.count:
            return "-"
        return ceil(obj.square_footage)


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    pass


class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline, UnitJmouldCountInline, UnitInsulationCountInline]

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

        change_url_name = f"{self.opts.app_label}_{self.opts.model_name}_change"
        url_name = getattr(request.resolver_match, "url_name", None)

        if url_name != change_url_name:
            return qs

        return qs.prefetch_related(
            "unitsheetcount_set",
            "unitjmouldcount_set",
            "unitinsulationcount_set",
        )


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


@admin.register(UnitDrywallMaterial)
class UnitDrywallMaterialAdmin(admin.ModelAdmin):
    pass


admin.site.register(RatePeriod)
admin.site.register(DrywallRate)
admin.site.register(JmouldRate)
admin.site.register(SprinklerRate)
admin.site.register(PotlightRate)
admin.site.register(InsulationRate)
admin.site.register(UnitInsulationMaterial)
