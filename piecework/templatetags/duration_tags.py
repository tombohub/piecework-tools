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
        return f"{hours}h{minutes}m"
    if hours:
        return f"{minutes}m"

    return f"{minutes}m"
