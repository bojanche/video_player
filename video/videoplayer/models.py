from django.db import models
from django.contrib.auth.models import User
from datetime import datetime


# Create your models here.
class VideoLocations(models.Model):
    file_path = models.CharField(max_length=255)
    video_name = models.CharField(max_length=200)
    video_category = models.CharField(max_length=50)
    poster_path = models.CharField(max_length=255, default='0')

    def __str__(self):
        return self.video_name


class UserProfileInfo(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_pic = models.ImageField(upload_to='profile_pics', blank=True)

    def __str__(self):
        return self.user.username


def user_directory_path(instance, filename):
    return datetime.utcnow().strftime('')


class VideoFileUpload(models.Model):
    video_name = models.CharField(max_length=200)
    file_item = models.FileField(upload_to='%Y%m%d%H%M%S%f')
    uploaded_at = models.DateTimeField(auto_now_add=True)
    converted = models.BooleanField(default=False)
