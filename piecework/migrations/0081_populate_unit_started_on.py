from django.db import migrations
from django.db.models import Min


def populate_unit_started_on(apps, schema_editor):
    Unit = apps.get_model("piecework", "Unit")
    ActivityLog = apps.get_model("piecework", "ActivityLog")
    database = schema_editor.connection.alias

    earliest_starts = dict(
        ActivityLog.objects.using(database)
        .values("unit_id")
        .annotate(first_start=Min("start"))
        .values_list("unit_id", "first_start")
    )

    units_to_update = []

    for unit in Unit.objects.using(database).filter(started_on__isnull=True).iterator():
        first_start = earliest_starts.get(unit.pk)

        if first_start is not None:
            unit.started_on = first_start.date()
            units_to_update.append(unit)

    if units_to_update:
        Unit.objects.using(database).bulk_update(
            units_to_update,
            ["started_on"],
            batch_size=500,
        )


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0080_rename_ended_on_unit_completed_on"),
    ]

    operations = [
        migrations.RunPython(
            populate_unit_started_on,
            migrations.RunPython.noop,
        ),
    ]
