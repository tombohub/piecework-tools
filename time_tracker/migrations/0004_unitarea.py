# Generated by Django 4.1.3 on 2022-11-08 11:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("time_tracker", "0003_sprintmethod_sprinttime_method"),
    ]

    operations = [
        migrations.CreateModel(
            name="UnitArea",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=20)),
            ],
        ),
    ]
