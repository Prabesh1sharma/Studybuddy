# Generated by Django 4.2.1 on 2023-06-16 03:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('base', '0007_userprofile_following'),
    ]

    operations = [
        migrations.AlterField(
            model_name='user',
            name='bio',
            field=models.TextField(blank=True, null=True),
        ),
    ]
