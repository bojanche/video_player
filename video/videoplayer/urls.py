from django.urls import path
from . import views

app_name = 'videoplayer'

urlpatterns = [
    path('', views.video_playlist, name='video_playlist'),
    path('videoplayer/<int:video_id>/', views.videoplayer, name='videoplayer'),
    path('videoplayer/asset_upload/', views.asset_upload, name='asset_upload'),
    path('videoplayer/conversion_task/', views.conversion_task, name='conversion_task'),
    path('videoplayer/conversion_task/<int:video_id>', views.conversion_task, name='conversion_task'),
]
