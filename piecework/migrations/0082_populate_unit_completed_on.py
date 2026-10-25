from django.db import migrations
from django.db.models import Max


def populate_unit_completed_on(apps, schema_editor):
    Unit = apps.get_model("piecework", "Unit")
    ActivityLog = apps.get_model("piecework", "ActivityLog")
    database = schema_editor.connection.alias

    latest_ends = dict(
        ActivityLog.objects.using(database)
        .filter(
            unit__status="completed",
            end__isnull=False,
        )
        .values("unit_id")
        .annotate(last_end=Max("end"))
        .values_list("unit_id", "last_end")
    )

    units_to_update = []

    units = (
        Unit.objects.using(database)
        .filter(
            status="completed",
            completed_on__isnull=True,
        )
        .iterator()
    )

    for unit in units:
        last_end = latest_ends.get(unit.pk)

        if last_end is not None:
            unit.completed_on = last_end.date()
            units_to_update.append(unit)

    if units_to_update:
        Unit.objects.using(database).bulk_update(
            units_to_update,
            ["completed_on"],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0081_populate_unit_started_on"),
    ]

    operations = [
        migrations.RunPython(
            populate_unit_completed_on,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
