from threading import Lock


_progress_lock = Lock()
_progress = {}


def start(video_id):
    with _progress_lock:
        _progress[str(video_id)] = {
            'percent': 0,
            'status': 'running',
            'message': 'Starting conversion...',
        }


def update(video_id, percent=None, status='running', message=None):
    with _progress_lock:
        current = _progress.setdefault(str(video_id), {
            'percent': 0,
            'status': status,
            'message': '',
        })

        if percent is not None:
            current['percent'] = max(0, min(100, int(percent)))

        current['status'] = status

        if message is not None:
            current['message'] = message


def complete(video_id):
    update(video_id, percent=100, status='complete', message='Conversion complete.')


def fail(video_id, message='Conversion failed.'):
    update(video_id, status='error', message=message)


def get(video_id):
    with _progress_lock:
        current = _progress.get(str(video_id))
        if current is None:
            return {
                'percent': 0,
                'status': 'idle',
                'message': 'Waiting to start.',
            }
        return current.copy()
