# -*- coding: utf-8 -*-
# Generated by Django 1.11.16 on 2018-10-10 21:52
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('jwt_devices', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='permanent_token',
            field=models.CharField(max_length=255, unique=True),
        ),
    ]
