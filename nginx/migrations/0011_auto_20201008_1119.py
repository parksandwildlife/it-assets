# Generated by Django 2.2.16 on 2020-10-08 03:19

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('nginx', '0010_auto_20201008_1117'),
    ]

    operations = [
        migrations.AlterIndexTogether(
            name='webappaccesslog',
            index_together={('webserver', 'http_status'), ('webapp', 'webapplocation'), ('webapp', 'http_status'), ('log_starttime', 'webapp', 'webapplocation')},
        ),
    ]
