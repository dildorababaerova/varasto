# Generated by Django 5.2 on 2025-05-28 09:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('stock', '0006_order'),
    ]

    operations = [
        migrations.AddField(
            model_name='order',
            name='completed',
            field=models.BooleanField(default=False),
        ),
    ]
