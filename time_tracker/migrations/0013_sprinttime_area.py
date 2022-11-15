# Generated by Django 4.1.3 on 2022-11-15 12:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0012_unit_total_sheets"),
    ]

    operations = [
        migrations.AddField(
            model_name="sprinttime",
            name="area",
            field=models.ForeignKey(
                default=None,
                on_delete=django.db.models.deletion.PROTECT,
                to="time_tracker.unitarea",
            ),
            preserve_default=False,
        ),
    ]
