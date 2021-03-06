# Generated by Django 2.2.16 on 2020-09-11 07:32

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rancher', '0012_auto_20200910_1259'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ingress',
            name='project',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='ingresses', to='rancher.Project'),
        ),
        migrations.AlterField(
            model_name='persistentvolumeclaim',
            name='project',
            field=models.ForeignKey(editable=False, null=True, on_delete=django.db.models.deletion.PROTECT, related_name='volumeclaims', to='rancher.Project'),
        ),
    ]
