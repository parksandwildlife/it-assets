# Generated by Django 2.2.16 on 2020-10-21 05:52

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('organisation', '0019_auto_20200929_0844'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='departmentuser',
            name='level',
        ),
        migrations.RemoveField(
            model_name='departmentuser',
            name='lft',
        ),
        migrations.RemoveField(
            model_name='departmentuser',
            name='parent',
        ),
        migrations.RemoveField(
            model_name='departmentuser',
            name='rght',
        ),
        migrations.RemoveField(
            model_name='departmentuser',
            name='tree_id',
        ),
    ]
