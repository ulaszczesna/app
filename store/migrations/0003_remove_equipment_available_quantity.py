# Generated by Django 3.2.5 on 2025-01-20 08:22

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0002_alter_equipment_image'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='equipment',
            name='available_quantity',
        ),
    ]
