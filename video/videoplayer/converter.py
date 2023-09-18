import os

import ffmpeg
from .models import VideoLocations, VideoFileUpload
import pathlib


def converter(ulazni_path, ulazni_fajl, video_id):
    # -vf scale=-1:720
    video_path_1 = ulazni_path / 'index.m3u8'
    poster_path_1 = ulazni_path / 'output.jpg'
    # # tmp
    # ulazni_fajl = 'D:\\tmp\\foreign.mp4'
    # video_path_1 = 'D:\\tmp\\index.m3u8'
    # # end tmp
    # print('Bojan: ', ulazni_fajl)
    # print('Bojan1: ', video_path_1)
    (
        ffmpeg
        .input(ulazni_fajl)
        .filter('scale', 1920, -1)
        .output(vcodec='libx264', acodec='aac', format='hls', start_number=0, hls_time=10, hls_list_size=0, filename=video_path_1)
        .overwrite_output()
        .run()
    )

    # stream = ffmpeg.input(ulazni_fajl)
    # output_stream = ffmpeg.output(stream, vcodec='libx264', acodec='aac', format='hls', start_number=0, hls_time=10, hls_list_size=0, filename=video_path_1)
    # output_stream.run()

    (
        ffmpeg
        .input(ulazni_fajl, ss=10)
        .output(filename=poster_path_1, vframes=1)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )
    vid_asset = VideoFileUpload.objects.get(pk=video_id)
    vid_asset.converted = True
    vid_asset.save()
    # tweaking locations
    file_path = pathlib.PureWindowsPath(ulazni_path / "index.m3u8")
    poster_path = pathlib.PureWindowsPath(ulazni_path / "output.jpg")
    home_dir = pathlib.Path.cwd()
    relative_path_video = file_path.relative_to(home_dir).as_posix()
    relative_path_poster = poster_path.relative_to(home_dir).as_posix()
    # end tweaking locations
    kveri = VideoLocations(file_path='/'+relative_path_video, video_category='Movies', poster_path='/'+relative_path_poster, video_name=vid_asset.video_name)
    kveri.save()
    print("Putanja m3u8:", ulazni_path / 'index.m3u8', " Poster:", ulazni_path / 'output.jpg')
