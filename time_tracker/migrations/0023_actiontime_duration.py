# Generated by Django 4.1.3 on 2022-11-20 20:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0022_actiontime_date"),
    ]

    operations = [
        migrations.AddField(
            model_name="actiontime",
            name="duration",
            field=models.DurationField(blank=True, null=True),
        ),
    ]