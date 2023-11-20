# Generated by Django 4.1.3 on 2023-11-20 14:59

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('finances', '0004_recurringexpense_amount'),
    ]

    operations = [
        migrations.RenameField(
            model_name='recurringexpense',
            old_name='amount',
            new_name='aproximate_amount',
        ),
        migrations.AddField(
            model_name='recurringexpense',
            name='item',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.PROTECT, to='finances.item'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='vendor',
            name='items',
            field=models.ManyToManyField(to='finances.item'),
        ),
    ]
