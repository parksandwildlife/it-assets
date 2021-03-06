# Generated by Django 2.2.14 on 2020-07-21 03:29

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('status', '0010_auto_20200721_1119'),
        ('nginx', '0002_auto_20200626_1415'),
    ]

    operations = [
        migrations.AddField(
            model_name='webserver',
            name='host',
            field=models.ForeignKey(blank=True, help_text='The equivalent Host object in the status application.', null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='webservers', to='status.Host'),
        ),
        migrations.AlterField(
            model_name='webserver',
            name='category',
            field=models.PositiveSmallIntegerField(choices=[(1, 'AWS Server'), (2, 'Rancher Cluster'), (4, 'Docker Server'), (3, 'Web Server'), (5, 'External Server')], null=True),
        ),
    ]
