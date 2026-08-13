from django.urls import path
from . import views

app_name = 'videoplayer'

urlpatterns = [
    path('', views.video_playlist, name='video_playlist'),
    path('videoplayer/<int:video_id>/', views.videoplayer, name='videoplayer'),
    path('videoplayer/<int:video_id>/edit/', views.video_edit, name='video_edit'),
    path('videoplayer/<int:video_id>/remove_converted_asset/', views.video_remove_converted_asset, name='video_remove_converted_asset'),
    path('videoplayer/<int:video_id>/delete/', views.video_delete, name='video_delete'),
    path('videoplayer/asset_upload/', views.asset_upload, name='asset_upload'),
    path('videoplayer/account/password/', views.account_password, name='account_password'),
    path('videoplayer/account/photo/', views.account_photo, name='account_photo'),
    path('videoplayer/users/', views.user_management, name='user_management'),
    path('videoplayer/users/add/', views.user_management_add, name='user_management_add'),
    path('videoplayer/users/<int:user_id>/edit/', views.user_management_edit, name='user_management_edit'),
    path('videoplayer/conversion_task/', views.conversion_task, name='conversion_task'),
    path('videoplayer/conversion_task/<int:video_id>/progress/', views.conversion_task_progress, name='conversion_task_progress'),
    path('videoplayer/conversion_task/<int:video_id>', views.conversion_task, name='conversion_task'),
]
