from django.contrib import admin
from .models import (
    Activity,
    ActivityTime,
    Unit,
    UnitSheetCount,
    Note,
)


class UnitSheetCountInline(admin.TabularInline):
    model = UnitSheetCount
    readonly_fields = ['square_footage']
    extra = 4

class UnitAdmin(admin.ModelAdmin):
    inlines = [UnitSheetCountInline]
    readonly_fields = ['total_square_footage', 'total_price']


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


admin.site.register([Activity, Note])
