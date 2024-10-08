# Generated by Django 4.1.3 on 2022-11-11 02:44

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0007_alter_actiontime_unit"),
    ]

    operations = [
        migrations.CreateModel(
            name="Unit",
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
                ("number", models.PositiveSmallIntegerField()),
                ("washrooms_count", models.PositiveSmallIntegerField()),
                ("closets_count", models.PositiveSmallIntegerField()),
                ("rooms_count", models.PositiveSmallIntegerField()),
            ],
        ),
    ]
