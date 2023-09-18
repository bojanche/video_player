from django import forms
from django.contrib.auth.models import User
from .models import UserProfileInfo, VideoFileUpload


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)

    class Meta():
        model = User
        fields = ('username', 'email', 'password')


class UserProfileInfoForm(forms.ModelForm):

    class Meta:
        model = UserProfileInfo
        fields = ('profile_pic',)


class AssetUploadForm(forms.ModelForm):
    class Meta:
        model = VideoFileUpload
        fields = ('video_name', 'file_item')
