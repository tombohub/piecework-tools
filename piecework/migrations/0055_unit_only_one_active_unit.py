from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("piecework", "0054_unit_status"),
    ]

    operations = [
        migrations.AddConstraint(
            model_name="unit",
            constraint=models.UniqueConstraint(
                condition=models.Q(("status", "active")),
                fields=("status",),
                name="only_one_active_unit",
            ),
        ),
    ]
