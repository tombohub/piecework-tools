# Generated by Django 4.1.3 on 2022-11-12 10:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0011_unit_bulkheads_count_unit_windows_count_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="total_sheets",
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]
