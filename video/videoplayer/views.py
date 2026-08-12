from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Q
from .forms import UserForm, UserProfileInfoForm, AssetUploadForm, VideoLocationEditForm, UserManagementForm, UserManagementCreateForm
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden, JsonResponse
from .models import VideoLocations, VideoFileUpload
from .converter import converter
from . import conversion_progress
from .ffmpeg_capabilities import gpu_encoder
import pathlib
import shutil
from video.settings import MEDIA_ROOT
import threading
# Create your views here.


def video_playlist(request):
    video_items = _visible_videos(request.user)
    return render(request, 'videoplayer/play_list.html', {
        "video_items": video_items,
        "is_public_page": not request.user.is_authenticated,
    })


def videoplayer(request, video_id):
    item = get_object_or_404(VideoLocations, pk=video_id)
    if not _can_view_video(request.user, item):
        if not request.user.is_authenticated:
            return redirect('user_login')
        return HttpResponseForbidden('You do not have permission to view this video.')
    return render(request, 'videoplayer/player.html', {'item': item})


def _superuser_required(user):
    return user.is_authenticated and user.is_superuser


def _staff_required(user):
    return user.is_authenticated and user.is_staff


@login_required
@user_passes_test(_staff_required)
def user_management(request):
    users = User.objects.order_by('username')
    return render(request, 'videoplayer/user_management.html', {'managed_users': users})


@login_required
@user_passes_test(_staff_required)
def user_management_edit(request, user_id):
    managed_user = get_object_or_404(User, pk=user_id)

    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=managed_user, actor=request.user)
        if form.is_valid():
            form.save()
            return redirect('videoplayer:user_management')
    else:
        form = UserManagementForm(instance=managed_user, actor=request.user)

    return render(request, 'videoplayer/user_management_edit.html', {
        'form': form,
        'managed_user': managed_user,
    })


@login_required
@user_passes_test(_staff_required)
def user_management_add(request):
    if request.method == 'POST':
        form = UserManagementCreateForm(request.POST, actor=request.user)
        if form.is_valid():
            form.save()
            return redirect('videoplayer:user_management')
    else:
        form = UserManagementCreateForm(actor=request.user, initial={'is_active': True})

    return render(request, 'videoplayer/user_management_edit.html', {
        'form': form,
        'managed_user': None,
    })


@login_required
def video_edit(request, video_id):
    item = get_object_or_404(_manageable_videos(request.user), pk=video_id)

    if request.method == 'POST':
        form = VideoLocationEditForm(request.POST, request.FILES, instance=item)
        if form.is_valid():
            item = form.save()
            poster_image = form.cleaned_data.get('poster_image')
            if poster_image:
                _replace_poster(item, poster_image)
            _matching_uploads(item).update(video_name=item.video_name, is_public=item.is_public)
            _matching_locations(item).exclude(pk=item.pk).update(video_name=item.video_name, is_public=item.is_public)
            return redirect('videoplayer:video_playlist')
    else:
        form = VideoLocationEditForm(instance=item)

    return render(request, 'videoplayer/video_edit.html', {
        'form': form,
        'item': item,
    })


@login_required
def video_remove_converted_asset(request, video_id):
    item = get_object_or_404(_manageable_videos(request.user), pk=video_id)
    if request.method == 'POST':
        _remove_converted_files(item)
        _matching_uploads(item).update(converted=False)
        _matching_locations(item).delete()
        return redirect('videoplayer:conversion_task')
    return redirect('videoplayer:video_edit', video_id=video_id)


@login_required
def video_delete(request, video_id):
    item = get_object_or_404(_manageable_videos(request.user), pk=video_id)
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
            video_file = form.save(commit=False)
            video_file.owner = request.user
            video_file.save()
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
    data = _manageable_uploads(request.user).filter(converted=False)
    if request.method == 'GET' and video_id != 'None':
        to_be_converted = get_object_or_404(data, pk=video_id)
        current_progress = conversion_progress.get(video_id)
        if current_progress['status'] == 'running':
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({'started': True, 'video_id': video_id})
            return render(request, 'videoplayer/conversion_task.html', _conversion_task_context(data))

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
    get_object_or_404(_manageable_uploads(request.user), pk=video_id)
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


def _visible_videos(user):
    if user.is_authenticated and user.is_superuser:
        return VideoLocations.objects.all()
    if user.is_authenticated:
        return VideoLocations.objects.filter(owner=user)
    return VideoLocations.objects.filter(is_public=True)


def _manageable_videos(user):
    if user.is_superuser:
        return VideoLocations.objects.all()
    return VideoLocations.objects.filter(owner=user)


def _manageable_uploads(user):
    if user.is_superuser:
        return VideoFileUpload.objects.all()
    return VideoFileUpload.objects.filter(owner=user)


def _can_view_video(user, item):
    if item.is_public:
        return True
    if not user.is_authenticated:
        return False
    return user.is_superuser or item.owner_id == user.id


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
