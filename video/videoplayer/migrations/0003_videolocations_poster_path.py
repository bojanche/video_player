# Generated by Django 4.0.1 on 2022-01-30 18:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('videoplayer', '0002_userprofileinfo'),
    ]

    operations = [
        migrations.AddField(
            model_name='videolocations',
            name='poster_path',
            field=models.CharField(default='0', max_length=255),
        ),
    ]
