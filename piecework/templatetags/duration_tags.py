import datetime as dt

from django import template

register = template.Library()


@register.filter
def compact_duration(value: dt.timedelta | None) -> str:
    if value is None:
        return "0m"

    total_minutes = int(value.total_seconds() // 60)
    hours, minutes = divmod(total_minutes, 60)

    if hours and minutes:
        return f"{hours}h {minutes}m"
    if hours:
        return f"{hours}h"

    return f"{minutes}m"


@register.filter
def compact_duration_with_seconds(value: dt.timedelta | None) -> str:
    if value is None:
        return "0m 0s"

    total_seconds = int(value.total_seconds())
    hours, remaining_seconds = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remaining_seconds, 60)

    if hours:
        return f"{hours}h {minutes}m {seconds}s"

    return f"{minutes}m {seconds}s"
