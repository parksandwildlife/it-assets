# Generated by Django 2.2.16 on 2020-10-09 02:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('status', '0012_auto_20201008_1134'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scanplugin',
            name='plugin',
            field=models.CharField(choices=[('monitor_prtg', 'Monitor - PRTG'), ('vulnerability_nessus', 'Vulnerability - Nessus'), ('backup_acronis', 'Backup - Acronis'), ('backup_aws', 'Backup - AWS snapshots'), ('backup_azure', 'Backup - Azure snapshots'), ('backup_storagesync', 'Backup - Azure Storage Sync Services'), ('patching_oms', 'Patching - Azure OMS')], max_length=32),
        ),
    ]
