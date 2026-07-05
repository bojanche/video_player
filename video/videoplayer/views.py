from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from .forms import UserForm, UserProfileInfoForm, AssetUploadForm, VideoLocationEditForm
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from .models import VideoLocations, VideoFileUpload
from .converter import converter
from . import conversion_progress
from .ffmpeg_capabilities import gpu_encoder
import pathlib
import shutil
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


def _superuser_required(user):
    return user.is_authenticated and user.is_superuser


@login_required
@user_passes_test(_superuser_required)
def video_edit(request, video_id):
    item = get_object_or_404(VideoLocations, pk=video_id)

    if request.method == 'POST':
        form = VideoLocationEditForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            poster_image = form.cleaned_data.get('poster_image')
            if poster_image:
                _replace_poster(item, poster_image)
            _matching_uploads(item).update(video_name=item.video_name)
            _matching_locations(item).exclude(pk=item.pk).update(video_name=item.video_name)
            return redirect('videoplayer:video_playlist')
    else:
        form = VideoLocationEditForm(instance=item)

    return render(request, 'videoplayer/video_edit.html', {
        'form': form,
        'item': item,
    })


@login_required
@user_passes_test(_superuser_required)
def video_remove_converted_asset(request, video_id):
    item = get_object_or_404(VideoLocations, pk=video_id)
    if request.method == 'POST':
        _remove_converted_files(item)
        _matching_uploads(item).update(converted=False)
        _matching_locations(item).delete()
        return redirect('videoplayer:conversion_task')
    return redirect('videoplayer:video_edit', video_id=video_id)


@login_required
@user_passes_test(_superuser_required)
def video_delete(request, video_id):
    item = get_object_or_404(VideoLocations, pk=video_id)
    if request.method == 'POST':
        asset_dir = _asset_dir(item)
        _matching_uploads(item).delete()
        _matching_locations(item).delete()
        if asset_dir.exists():
            shutil.rmtree(asset_dir)
    return redirect('videoplayer:video_playlist')


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
            return redirect('videoplayer:conversion_task')
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
        current_progress = conversion_progress.get(video_id)
        if current_progress['status'] == 'running':
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'started': True, 'video_id': video_id})
            return render(request, 'videoplayer/conversion_task.html', _conversion_task_context(data))

        to_be_converted = VideoFileUpload.objects.get(pk=video_id)
        to_be_converted_file = pathlib.Path(str(to_be_converted.file_item))
        to_be_converted_path = to_be_converted_file.parent
        use_gpu = request.GET.get('gpu') == '1'
        x_thread = threading.Thread(target=converter, args=(MEDIA_ROOT / to_be_converted_path, MEDIA_ROOT / to_be_converted_file, video_id, use_gpu,))
        x_thread.daemon = True
        x_thread.start()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'started': True, 'video_id': video_id})

    return render(request, 'videoplayer/conversion_task.html', _conversion_task_context(data))


@login_required
def conversion_task_progress(request, video_id):
    return JsonResponse(conversion_progress.get(video_id))


def _conversion_task_context(data):
    tasks = []
    for video in data:
        tasks.append({
            'video': video,
            'progress': conversion_progress.get(video.id),
        })
    return {
        'tasks': tasks,
        'gpu_encoder': gpu_encoder(),
    }


def _asset_dir(item):
    media_root = MEDIA_ROOT.resolve()
    item_path = pathlib.Path(item.file_path.lstrip('/'))
    asset_dir = (pathlib.Path.cwd() / item_path).resolve().parent
    if media_root != asset_dir and media_root not in asset_dir.parents:
        raise ValueError('Refusing to operate outside MEDIA_ROOT.')
    return asset_dir


def _poster_path(item):
    media_root = MEDIA_ROOT.resolve()
    poster_path = (pathlib.Path.cwd() / pathlib.Path(item.poster_path.lstrip('/'))).resolve()
    if media_root != poster_path.parent and media_root not in poster_path.parents:
        raise ValueError('Refusing to operate outside MEDIA_ROOT.')
    return poster_path


def _matching_uploads(item):
    folder_name = _asset_dir(item).name
    return VideoFileUpload.objects.filter(file_item__startswith=folder_name + '/')


def _matching_locations(item):
    folder_name = _asset_dir(item).name
    return VideoLocations.objects.filter(file_path__startswith='/media/' + folder_name + '/')


def _replace_poster(item, poster_image):
    poster_path = _poster_path(item)
    with poster_path.open('wb+') as destination:
        for chunk in poster_image.chunks():
            destination.write(chunk)


def _remove_converted_files(item):
    asset_dir = _asset_dir(item)
    for path in asset_dir.iterdir():
        if path.is_file() and (path.name == 'output.jpg' or path.name == 'master.m3u8' or path.suffix == '.ts'):
            path.unlink()
        if path.is_dir() and (path.name == 'v0' or path.name == 'v1' or path.name == 'v2'):
            shutil.rmtree(path, ignore_errors=True)


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
