from django.db import migrations

DEFAULT_HEIGHT = "over_8_to_9_inclusive"


def backfill_unit_height(apps, schema_editor):
    Unit = apps.get_model("piecework", "Unit")
    database = schema_editor.connection.alias

    Unit.objects.using(database).filter(height_feet__isnull=True).update(
        height_feet=DEFAULT_HEIGHT
    )


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0085_backfill_unit_timestamps"),
    ]

    operations = [
        migrations.RunPython(
            backfill_unit_height,
            reverse_code=migrations.RunPython.noop,
        ),
    ]
