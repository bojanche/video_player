from django import forms
from django.contrib.auth.models import User
from .models import UserProfileInfo, VideoFileUpload, VideoLocations


class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'class': 'form-control',
        'autocomplete': 'new-password',
    }))

    class Meta():
        model = User
        fields = ('username', 'email', 'password')
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'autocomplete': 'username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'autocomplete': 'email'}),
        }


class UserProfileInfoForm(forms.ModelForm):

    class Meta:
        model = UserProfileInfo
        fields = ('profile_pic',)
        widgets = {
            'profile_pic': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class AssetUploadForm(forms.ModelForm):
    class Meta:
        model = VideoFileUpload
        fields = ('video_name', 'file_item')
        widgets = {
            'video_name': forms.TextInput(attrs={'class': 'form-control'}),
            'file_item': forms.ClearableFileInput(attrs={'class': 'form-control'}),
        }


class VideoLocationEditForm(forms.ModelForm):
    poster_image = forms.ImageField(
        required=False,
        label='Video poster',
        widget=forms.ClearableFileInput(attrs={'class': 'form-control'}),
    )

    class Meta:
        model = VideoLocations
        fields = ('video_name',)
        widgets = {
            'video_name': forms.TextInput(attrs={'class': 'form-control'}),
        }
