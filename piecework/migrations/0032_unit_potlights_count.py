# Generated by Django 4.1.3 on 2022-12-20 16:22

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0031_alter_action_table_alter_actiontime_table"),
    ]

    operations = [
        migrations.AddField(
            model_name="unit",
            name="potlights_count",
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]