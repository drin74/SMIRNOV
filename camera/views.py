import cv2
import numpy as np
from django.http import StreamingHttpResponse, JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
import os
import json
import time

from .forms import VideoUploadForm
from .models import UploadedVideo



@login_required
def analyze_uploaded_video(request, pk):
    video = get_object_or_404(UploadedVideo, pk=pk, uploaded_by=request.user)
    return render(request, 'camera/analyze_video.html', {'video': video})


@login_required
def analyze_video_stream(request, pk):
    video_obj = get_object_or_404(UploadedVideo, pk=pk, uploaded_by=request.user)
    video_path = video_obj.video_file.path

    min_area = request.session.get('detector_settings', {}).get('min_area', 3000)
    threshold = request.session.get('detector_settings', {}).get('threshold', 35)
    stability_frames = request.session.get('detector_settings', {}).get('stability_frames', 3)

    def generate_frames():
        cap = cv2.VideoCapture(video_path)

        if not cap.isOpened():
            frame = np.zeros((480, 640, 3), np.uint8)
            cv2.putText(frame, "ERROR: Cannot open video", (100, 240),
                        cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            ret, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            return

        prev_frame = None
        motion_count = 0
        frame_count = 0
        motion_detected_count = 0

        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_count += 1

            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (21, 21), 0)

            if prev_frame is None:
                prev_frame = gray
                cv2.putText(frame, "ANALYZING...", (200, 30),
                            cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 255), 2)
                ret, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
                continue

            frame_delta = cv2.absdiff(prev_frame, gray)
            thresh = cv2.threshold(frame_delta, threshold, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)

            contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            motion_detected = False
            for contour in contours:
                if cv2.contourArea(contour) > min_area:
                    motion_detected = True
                    cv2.drawContours(frame, [contour], -1, (0, 255, 0), 2)
                    break

            if motion_detected:
                motion_count += 1
                motion_detected_count += 1
            else:
                motion_count = max(0, motion_count - 1)

            is_motion = motion_count >= stability_frames

            if is_motion:
                cv2.rectangle(frame, (10, 10), (180, 60), (0, 0, 255), -1)
                cv2.putText(frame, "Movement!", (25, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
            else:
                cv2.rectangle(frame, (10, 10), (220, 60), (0, 255, 0), -1)
                cv2.putText(frame, "No movement!", (25, 45),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)

            cv2.putText(frame, f"Frame: {frame_count}", (10, frame.shape[0] - 40),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

            prev_frame = gray

            ret, jpeg = cv2.imencode('.jpg', frame)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

            time.sleep(0.03)

        cap.release()

        final_frame = np.zeros((480, 640, 3), np.uint8)
        cv2.putText(final_frame, "ANALYSIS COMPLETE", (150, 200),
                    cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        cv2.putText(final_frame, f"Total frames: {frame_count}", (180, 250),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(final_frame, f"Motion frames: {motion_detected_count}", (180, 290),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        if frame_count > 0:
            percent = (motion_detected_count / frame_count) * 100
            cv2.putText(final_frame, f"Motion: {percent:.1f}%", (220, 330),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

        ret, jpeg = cv2.imencode('.jpg', final_frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')

    return StreamingHttpResponse(
        generate_frames(),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


@login_required
def save_analysis_result(request, pk):

    video = get_object_or_404(UploadedVideo, pk=pk, uploaded_by=request.user)
    messages.success(request, f" Video analysis '{video.title}' completed!")
    return redirect('video_list')



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
            cv2.putText(frame, "INITIALIZATION...", (180, 240),
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
            cv2.rectangle(frame, (10, 10), (180, 60), (0, 0, 255), -1)
            cv2.putText(frame, "Movement", (25, 45),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        else:
            cv2.rectangle(frame, (10, 10), (220, 60), (0, 255, 0), -1)
            cv2.putText(frame, "No movement", (25, 45),
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
    if request.user.is_authenticated:
        settings = request.session.get('detector_settings', {
            'min_area': 3000,
            'threshold': 35,
            'stability_frames': 3,
        })
    else:
        settings = request.session.get('detector_settings', guest_settings)

    return StreamingHttpResponse(
        generate_frames(settings),
        content_type='multipart/x-mixed-replace; boundary=frame'
    )


def index(request):
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

            request.session['detector_settings'] = settings

            return JsonResponse({'status': 'ok', 'settings': settings})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

    return JsonResponse({'status': 'error', 'message': 'POST only'}, status=405)



@login_required
def video_list(request):
    videos = UploadedVideo.objects.filter(uploaded_by=request.user).order_by('-uploaded_at')
    return render(request, 'camera/video_list.html', {'videos': videos})


@login_required
def upload_video(request):
    if request.method == 'POST':
        form = VideoUploadForm(request.POST, request.FILES)
        if form.is_valid():
            video_file = request.FILES.get('video_file')
            if video_file:
                ext = os.path.splitext(video_file.name)[1].lower().strip('.')
                allowed_exts = settings.ALLOWED_VIDEO_EXTENSIONS

                if ext not in allowed_exts:
                    messages.error(request, f'Недопустимый формат. Разрешены: {", ".join(allowed_exts)}')
                elif video_file.size > 500 * 1024 * 1024:
                    messages.error(request, 'Файл слишком большой. Максимум 500MB')
                else:
                    video = form.save(commit=False)
                    video.uploaded_by = request.user
                    video.save()
                    messages.success(request, f'Видео "{video.title}" успешно загружено!')
                    return redirect('video_list')
        else:
            messages.error(request, 'Ошибка при загрузке. Проверьте данные.')
    else:
        form = VideoUploadForm()

    return render(request, 'camera/upload_video.html', {'form': form})


@login_required
def video_detail(request, pk):

    video = get_object_or_404(UploadedVideo, pk=pk, uploaded_by=request.user)
    return render(request, 'camera/video_detail.html', {'video': video})


@login_required
def delete_video(request, pk):

    video = get_object_or_404(UploadedVideo, pk=pk, uploaded_by=request.user)
    if request.method == 'POST':
        if os.path.exists(video.video_file.path):
            os.remove(video.video_file.path)
        video.delete()
        messages.success(request, '️Видео удалено')
        return redirect('video_list')
    return render(request, 'camera/video_confirm_delete.html', {'video': video})