from django.db import migrations


def set_boarding_category(apps, schema_editor):
    Activity = apps.get_model("piecework", "Activity")
    Activity.objects.filter(name="board").update(category="boarding")


def unset_boarding_category(apps, schema_editor):
    Activity = apps.get_model("piecework", "Activity")
    Activity.objects.filter(
        name="board",
        category="boarding",
    ).update(category="other")


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0113_activity_category"),
    ]

    operations = [
        migrations.RunPython(
            set_boarding_category,
            unset_boarding_category,
        ),
    ]
