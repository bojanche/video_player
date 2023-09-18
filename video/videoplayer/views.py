from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from .forms import UserForm, UserProfileInfoForm, AssetUploadForm
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse
from .models import VideoLocations, VideoFileUpload
from .converter import converter
import pathlib
from video.settings import MEDIA_ROOT
import threading
# Create your views here.


@login_required
def video_playlist(request):
    video_items = VideoLocations.objects.all()
    return render(request, 'videoplayer/play_list.html', {"video_items": video_items})


@login_required
def videoplayer(request, video_id):
    print(video_id)
    item = VideoLocations.objects.get(id=video_id)
    return render(request, 'videoplayer/player.html', {'item': item})


@login_required
def user_logout(request):
    logout(request)
    return HttpResponseRedirect(reverse('videoplayer:video_playlist'))


@login_required
def asset_upload(request):
    if request.method == 'POST':
        form = AssetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('videoplayer:video_playlist')
    else:
        form = AssetUploadForm()
    return render(request, 'videoplayer/asset_upload.html', {'form':form})


@login_required
def remove_video(request, id):
    if request.method == 'GET':
        form = AssetUploadForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect('videoplayer:video_playlist')
    else:
        form = AssetUploadForm()
    return render(request, 'videoplayer/asset_upload.html', {'form':form})


@login_required
def conversion_task(request, video_id='None'):
    data = VideoFileUpload.objects.filter(converted=False)
    if request.method == 'GET' and video_id != 'None':
        to_be_converted = VideoFileUpload.objects.get(pk=video_id)
        to_be_converted_file = pathlib.Path(str(to_be_converted.file_item))
        to_be_converted_path = to_be_converted_file.parent
        x_thread = threading.Thread(target=converter, args=(MEDIA_ROOT / to_be_converted_path, MEDIA_ROOT / to_be_converted_file, video_id,))
        x_thread.start()

    return render(request, 'videoplayer/conversion_task.html', {'data': data})


def register(request):
    registered = False
    if request.method == 'POST':
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileInfoForm(data=request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            user.set_password(user.password)
            user.save()

            profile = profile_form.save(commit=False)
            profile.user = user

            if 'profile_pic' in request.FILES:
                profile.profile_pic = request.FILES['profile_pic']

            profile.save()
            registered = True
        else:
            print(user_form.errors, profile_form.errors)

    else:
        user_form = UserForm()
        profile_form = UserProfileInfoForm()

    return render(request, 'videoplayer/registration.html', {'user_form': user_form,
                                                             'profile_form': profile_form,
                                                             'registered': registered})


def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(username=username, password=password)

        if user:
            if user.is_active:
                login(request, user)
                return HttpResponseRedirect(reverse('videoplayer:video_playlist'))
            else:
                HttpResponse('Account is not active!!!')
        else:
            print('Login failed!!!')
            return HttpResponse('Invalid login details provided!')
    else:
        return render(request, 'videoplayer/login.html', {})