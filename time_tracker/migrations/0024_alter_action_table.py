# Generated by Django 4.1.3 on 2022-11-24 15:40

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0023_actiontime_duration"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="action",
            table="actions",
        ),
    ]
