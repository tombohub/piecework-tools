# Generated by Django 4.1.3 on 2022-11-15 12:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0013_sprinttime_area"),
    ]

    operations = [
        migrations.AlterField(
            model_name="sprinttime",
            name="method",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                to="time_tracker.sprintmethod",
            ),
        ),
    ]
