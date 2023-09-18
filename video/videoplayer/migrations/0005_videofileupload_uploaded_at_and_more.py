# Generated by Django 4.0.1 on 2022-02-13 05:58

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('videoplayer', '0004_videofileupload'),
    ]

    operations = [
        migrations.AddField(
            model_name='videofileupload',
            name='uploaded_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='videofileupload',
            name='video_name',
            field=models.CharField(default=django.utils.timezone.now, max_length=200),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='videolocations',
            name='video_name',
            field=models.CharField(max_length=200),
        ),
    ]