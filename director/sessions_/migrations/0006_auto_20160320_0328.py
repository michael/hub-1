# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-03-20 03:28
from __future__ import unicode_literals

from django.db import migrations, models

def convert_session_memory(apps, schema_editor):
    # Migration baulks when trying to convert
    # memory values like "1g". Alos went from CPU shares out
    # of 1024 to out of 100. Since most sessions to date
    # have not had any resources limits applied, just do this:
    Session = apps.get_model("sessions_", "Session")
    for session in Session.objects.all():
        session.memory = 1
        session.cpu = 1
        session.network = -1
        session.save()


class Migration(migrations.Migration):

    dependencies = [
        ('sessions_', '0005_auto_20160316_2124'),
    ]

    operations = [
        migrations.RunPython(convert_session_memory),

        migrations.RemoveField(
            model_name='sessiontype',
            name='ram',
        ),
        migrations.AddField(
            model_name='sessiontype',
            name='memory',
            field=models.FloatField(default=1, help_text='Gigabytes (GB) of memory allocated'),
        ),
        migrations.AlterField(
            model_name='session',
            name='cpu',
            field=models.FloatField(blank=True, help_text='CPU shares (out of 100 per CPU) allocated If left null will default to that of session type.', null=True),
        ),
        migrations.AlterField(
            model_name='session',
            name='memory',
            field=models.FloatField(blank=True, help_text='Gigabytes (GB) of memory allocated. If left null will default to that of session type.', null=True),
        ),
        migrations.AlterField(
            model_name='session',
            name='network',
            field=models.FloatField(blank=True, help_text='Gigabytes (GB) of network transfer allocated. -1 = unlimited. If left null will default to that of session type.', null=True),
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='cpu',
            field=models.FloatField(default=1, help_text='CPU shares (out of 100 per CPU) allocated'),
        ),
        migrations.AlterField(
            model_name='sessiontype',
            name='network',
            field=models.FloatField(default=-1, help_text='Gigabytes (GB) of network transfer allocated. -1 = unlimited'),
        ),
    ]
