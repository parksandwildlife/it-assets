# Generated by Django 2.0.9 on 2019-01-07 07:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('registers', '0015_auto_20190107_1503'),
    ]

    operations = [
        migrations.AddField(
            model_name='itsystem',
            name='system_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Department commercial services'), (2, 'Department fire services'), (3, 'Department visitor services')], null=True),
        ),
        migrations.AlterField(
            model_name='itsystem',
            name='application_type',
            field=models.PositiveSmallIntegerField(blank=True, choices=[(1, 'Web application'), (2, 'Client application'), (3, 'Mobile application'), (5, 'Externally hosted application'), (4, 'Service'), (6, 'Platform'), (7, 'Infrastructure')], null=True),
        ),
    ]
