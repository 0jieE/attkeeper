# Generated by Django 5.0.6 on 2024-07-16 14:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0008_shift_period_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='member',
            name='contact_no',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
