import os
import re
import ffmpeg
from .models import VideoLocations, VideoFileUpload
from . import conversion_progress
from .ffmpeg_capabilities import gpu_encoder
import pathlib
import subprocess


duration_re = re.compile(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)")
time_re = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")

def parse_time(what2search,line):
    m = what2search.search(line)
    if not m:
        return None

    h = int(m.group(1))
    mnt = int(m.group(2))
    sec = float(m.group(3))

    return h * 3600 + mnt * 60 + sec

def converter(ulazni_path, ulazni_fajl, video_id, use_gpu=False):
    conversion_progress.start(video_id)

    try:
        # -vf scale=-1:720
        # video_path_1 = ulazni_path / 'index.m3u8'
        video_path_1 = ulazni_path
        poster_path_1 = ulazni_path / 'output.jpg'

        duration = _get_duration(ulazni_fajl)
        encoder = 'libx264'
        encoder_label = 'CPU'

        if use_gpu:
            available_gpu = gpu_encoder()
            if available_gpu:
                encoder = available_gpu['encoder']
                encoder_label = available_gpu['label']

        conversion_progress.update(video_id, percent=1, message='Encoding video with ' + encoder_label + '...')

        # stream = (
        #     ffmpeg
        #     .input(ulazni_fajl)
        #     .filter('scale', 1920, -1)
        #     .output(vcodec=encoder, acodec='aac', format='hls', start_number=0, hls_time=10, hls_list_size=0, filename=video_path_1)
        #     .overwrite_output()
        #     .global_args('-loglevel', 'error', '-progress', 'pipe:1', '-nostats')
        # )
        # process = subprocess.Popen(
        #     ffmpeg.compile(stream),
        #     stdout=subprocess.PIPE,
        #     stderr=subprocess.PIPE,
        #     universal_newlines=True,
        # )
        encoder_options = []
        if encoder == 'libx264':
            encoder_options = ["-preset", "medium", "-pix_fmt", "yuv420p"]
        elif encoder == 'h264_nvenc':
            encoder_options = ["-preset", "p4", "-pix_fmt", "yuv420p"]
        elif encoder == 'h264_qsv':
            encoder_options = ["-pix_fmt", "nv12"]
        elif encoder == 'h264_amf':
            encoder_options = ["-quality", "balanced", "-pix_fmt", "yuv420p"]

        cmd = [
            "ffmpeg",
            "-y",
            "-i", ulazni_fajl,
            "-filter_complex",
            "[0:v]split=3[v1080][v720][v480];"
            "[v1080]scale=-2:1080:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[v0];"
            "[v720]scale=-2:720:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[v1];"
            "[v480]scale=-2:480:force_original_aspect_ratio=decrease,pad=ceil(iw/2)*2:ceil(ih/2)*2[v2]",

            "-map", "[v0]", "-map", "0:a",
            "-map", "[v1]", "-map", "0:a",
            "-map", "[v2]", "-map", "0:a",

            "-c:v", encoder,
            *encoder_options,

            "-g", "60",
            "-keyint_min", "60",
            "-sc_threshold", "0",

            "-c:a", "aac",
            "-ar", "48000",

            "-b:v:0", "5000k",
            "-maxrate:v:0", "5350k",
            "-bufsize:v:0", "7500k",

            "-b:v:1", "2500k",
            "-maxrate:v:1", "2675k",
            "-bufsize:v:1", "3750k",

            "-b:v:2", "900k",
            "-maxrate:v:2", "963k",
            "-bufsize:v:2", "1350k",

            "-b:a:0", "192k",
            "-b:a:1", "128k",
            "-b:a:2", "96k",

            "-f", "hls",

            "-hls_time", "6",
            "-hls_list_size", "0",
            "-hls_playlist_type", "vod",

            "-hls_flags", "independent_segments",
            # "-progress", "pipe:1",
            "-stats",
            # "-loglevel", "info",
            "-master_pl_name", "master.m3u8",

            "-var_stream_map", "v:0,a:0 v:1,a:1 v:2,a:2",

            "-hls_segment_filename",
            "v%v/segment_%05d.ts",
            "v%v/index.m3u8"
        ]
        # print("FFmpeg command:")
        # print(" ".join(map(str, cmd)))
        process = subprocess.Popen(
            cmd,
            cwd=video_path_1,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            # universal_newlines=True,
        )
        # for line in process.stderr:
        #     line = line.strip()
        #     print(line)

        duration=None

        for line in process.stderr:
            line=line.strip()
            print(line)
            if duration is None:
                d = parse_time(duration_re, line)
                if d:
                    duration=d
                    # print("Total duration: ", duration)

            t = parse_time(time_re, line)
            # if t and duration:
                # progress = (t/duration) *100
                # print(f"PROGRESS: {progress:.2f}%")
            # key, _, value = line.strip().partition('=')
            encoded_seconds = t
            if encoded_seconds is not None and duration:
                percent = (encoded_seconds / duration) * 100
                conversion_progress.update(video_id, percent=percent, message='Encoding video with ' + encoder_label + ' and creating poster...')
            # elif encoded_seconds is not None and encoded_seconds >= duration-1:
            #     conversion_progress.update(video_id, percent=95, message='Creating poster...')

        stderr = process.stderr.read()
        if process.wait() != 0:
            raise RuntimeError(stderr or 'ffmpeg conversion failed.')

        (
            ffmpeg
            .input(ulazni_fajl, ss=15)
            .output(filename=poster_path_1, vframes=1)
            .overwrite_output()
            .run(capture_stdout=True, capture_stderr=True)
        )
        embedded_subtitle_path = _extract_embedded_subtitle(ulazni_fajl, ulazni_path)
        vid_asset = VideoFileUpload.objects.get(pk=video_id)
        vid_asset.converted = True
        vid_asset.save()
        # tweaking locations
        file_path = pathlib.PureWindowsPath(ulazni_path / "master.m3u8")
        poster_path = pathlib.PureWindowsPath(ulazni_path / "output.jpg")
        home_dir = pathlib.Path.cwd()
        relative_path_video = file_path.relative_to(home_dir).as_posix()
        relative_path_poster = poster_path.relative_to(home_dir).as_posix()
        relative_path_subtitle = ''
        if embedded_subtitle_path:
            relative_path_subtitle = pathlib.PureWindowsPath(embedded_subtitle_path).relative_to(home_dir).as_posix()
        # end tweaking locations
        kveri = VideoLocations(
            file_path='/'+relative_path_video,
            video_category='Movies',
            poster_path='/'+relative_path_poster,
            video_name=vid_asset.video_name,
            owner=vid_asset.owner,
            is_public=vid_asset.is_public,
            subtitle_path='/' + relative_path_subtitle if relative_path_subtitle else '',
        )
        kveri.save()
        conversion_progress.complete(video_id)
        # print("Putanja m3u8:", ulazni_path / 'index.m3u8', " Poster:", ulazni_path / 'output.jpg')
    except Exception as exc:
        conversion_progress.fail(video_id, str(exc))
        raise


def _get_duration(file_path):
    probe = ffmpeg.probe(file_path)
    return float(probe['format']['duration'])


def _progress_seconds(key, value):
    if not value or value == 'N/A':
        return None

    try:
        if key == 'out_time_ms':
            return int(value) / 1000000

        if key == 'out_time_us':
            return int(value) / 1000000

        if key == 'out_time':
            hours, minutes, seconds = value.split(':')
            return (int(hours) * 3600) + (int(minutes) * 60) + float(seconds)
    except (TypeError, ValueError):
        return None

    return None


def _extract_embedded_subtitle(input_file, output_dir):
    subtitle_stream_count = _subtitle_stream_count(input_file)
    if subtitle_stream_count == 0:
        return None

    output_path = pathlib.Path(output_dir) / 'subtitles.vtt'
    for subtitle_index in range(subtitle_stream_count):
        result = subprocess.run(
            [
                'ffmpeg',
                '-y',
                '-i',
                str(input_file),
                '-map',
                '0:s:' + str(subtitle_index),
                '-c:s',
                'webvtt',
                str(output_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        if result.returncode == 0 and output_path.exists() and output_path.stat().st_size > 0:
            return output_path

    if output_path.exists():
        output_path.unlink()
    return None


def _subtitle_stream_count(input_file):
    try:
        probe = ffmpeg.probe(input_file)
    except ffmpeg.Error:
        return 0

    return len([
        stream for stream in probe.get('streams', [])
        if stream.get('codec_type') == 'subtitle'
    ])
