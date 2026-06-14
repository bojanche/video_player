import subprocess
from functools import lru_cache


GPU_ENCODERS = (
    ('h264_nvenc', 'NVIDIA NVENC'),
    ('h264_qsv', 'Intel Quick Sync'),
    ('h264_amf', 'AMD AMF'),
)


@lru_cache(maxsize=1)
def gpu_encoder():
    for encoder, label in GPU_ENCODERS:
        if _encoder_is_usable(encoder):
            return {
                'encoder': encoder,
                'label': label,
            }
    return None


def _encoder_is_usable(encoder):
    command = [
        'ffmpeg',
        '-hide_banner',
        '-loglevel',
        'error',
        '-f',
        'lavfi',
        '-i',
        'color=c=black:s=64x64:d=0.1',
        '-frames:v',
        '1',
        '-c:v',
        encoder,
        '-f',
        'null',
        '-',
    ]

    try:
        result = subprocess.run(
            command,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
        )
    except (OSError, subprocess.TimeoutExpired):
        return False

    return result.returncode == 0
