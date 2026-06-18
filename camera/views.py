# camera/views.py
import cv2
import numpy as np
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render
from django.views.decorators.csrf import csrf_exempt
import json

# Глобальные настройки для гостей (временные)
guest_settings = {
    'min_area': 3000,
    'threshold': 35,
    'stability_frames': 3,
}


class VideoCamera:
    def __init__(self):
        self.video = cv2.VideoCapture(0)
        self.prev_frame = None
        self.motion_count = 0

    def __del__(self):
        self.video.release()

    def get_frame(self, settings):
        ret, frame = self.video.read()
        if not ret:
            frame = np.zeros((480, 640, 3), np.uint8)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)

        if self.prev_frame is None:
            self.prev_frame = gray
            cv2.putText(frame, "ИНИЦИАЛИЗАЦИЯ...", (180, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 0), 2)
            ret, jpeg = cv2.imencode('.jpg', frame)
            return jpeg.tobytes()

        frame_delta = cv2.absdiff(self.prev_frame, gray)
        thresh = cv2.threshold(frame_delta, settings['threshold'], 255, cv2.THRESH_BINARY)[1]
        thresh = cv2.dilate(thresh, None, iterations=2)

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        motion_detected = False
        for contour in contours:
            if cv2.contourArea(contour) > settings['min_area']:
                motion_detected = True
                break

        if motion_detected:
            self.motion_count += 1
        else:
            self.motion_count = max(0, self.motion_count - 1)

        is_motion = self.motion_count >= settings['stability_frames']

        if is_motion:
            cv2.rectangle(frame, (10, 10), (200, 60), (0, 0, 255), -1)
            cv2.putText(frame, "ДВИЖЕНИЕ!", (25, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        else:
            cv2.rectangle(frame, (10, 10), (200, 60), (0, 255, 0), -1)
            cv2.putText(frame, "НЕТ ДВИЖЕНИЯ", (25, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

        self.prev_frame = gray

        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()


camera = None


def get_camera():
    global camera
    if camera is None:
        camera = VideoCamera()
    return camera


def generate_frames(settings):
    cam = get_camera()
    while True:
        frame = cam.get_frame(settings)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')


def video_feed(request):
    # Получаем настройки: из сессии (гость) или из профиля (пользователь)
    if request.user.is_authenticated:
        # Для авторизованных - из сессии (позже можно из БД)
        settings = request.session.get('detector_settings', {
            'min_area': 3000,
            'threshold': 35,
            'stability_frames': 3,
        })
    else:
        # Для гостей - из сессии
        settings = request.session.get('detector_settings', guest_settings)

    return StreamingHttpResponse(
        generate_frames(settings),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


def index(request):
    # Получаем текущие настройки
    if request.user.is_authenticated:
        settings = request.session.get('detector_settings', {
            'min_area': 3000,
            'threshold': 35,
            'stability_frames': 3,
        })
    else:
        settings = request.session.get('detector_settings', guest_settings)

    return render(request, 'camera/index.html', {
        'settings': settings,
        'user': request.user
    })


@csrf_exempt
def update_settings(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)

            settings = {
                'min_area': int(data.get('min_area', 3000)),
                'threshold': int(data.get('threshold', 35)),
                'stability_frames': int(data.get('stability_frames', 3)),
            }

            # Сохраняем в сессии (для всех: и гостей, и пользователей)
            request.session['detector_settings'] = settings

            return JsonResponse({'status': 'ok', 'settings': settings})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)