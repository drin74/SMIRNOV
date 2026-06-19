from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('video_feed/', views.video_feed, name='video_feed'),
    path('update_settings/', views.update_settings, name='update_settings'),

    # Видео
    path('videos/', views.video_list, name='video_list'),
    path('videos/upload/', views.upload_video, name='upload_video'),
    path('videos/<int:pk>/', views.video_detail, name='video_detail'),
    path('videos/<int:pk>/delete/', views.delete_video, name='delete_video'),

    # АНАЛИЗ ВИДЕО
    path('videos/<int:pk>/analyze/', views.analyze_uploaded_video, name='analyze_uploaded_video'),
    path('videos/<int:pk>/analyze/stream/', views.analyze_video_stream, name='analyze_video_stream'),
    path('videos/<int:pk>/analyze/save/', views.save_analysis_result, name='save_analysis_result'),
]