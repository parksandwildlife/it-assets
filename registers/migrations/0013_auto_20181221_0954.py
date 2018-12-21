# Generated by Django 2.0.9 on 2018-12-21 01:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('registers', '0012_auto_20181219_1210'),
    ]

    operations = [
        migrations.AddField(
            model_name='itsystem',
            name='database_server',
            field=models.TextField(blank=True, help_text="Database server(s) that host this system's data"),
        ),
        migrations.AlterField(
            model_name='changerequest',
            name='approver',
            field=models.ForeignKey(blank=True, help_text='The person who will endorse this change prior to CAB', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='approver', to='organisation.DepartmentUser'),
        ),
        migrations.AlterField(
            model_name='changerequest',
            name='requester',
            field=models.ForeignKey(blank=True, help_text='The person who is requesting this change', null=True, on_delete=django.db.models.deletion.PROTECT, related_name='requester', to='organisation.DepartmentUser'),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='availability',
            field=models.PositiveIntegerField(blank=True, choices=[(1, '24/7/365'), (2, 'Business hours')], help_text='Expected availability for this system', null=True),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='biller_code',
            field=models.CharField(blank=True, help_text='BPAY biller code for this system (must be unique).', max_length=64, null=True),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='oim_internal_only',
            field=models.BooleanField(default=False, help_text='For OIM use only', verbose_name='OIM internal only'),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='user_groups',
            field=models.ManyToManyField(blank=True, help_text='User group(s) that use this system', to='registers.UserGroup'),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='user_notification',
            field=models.EmailField(blank=True, help_text='Users (group email address) to be advised of any changes (outage or upgrade) to the system', max_length=254, null=True),
        ),
    ]
