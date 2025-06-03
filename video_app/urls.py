from django.urls import path
from . import views
from .admin_view import UploadVideoToArvan, UploadChuckView , SaveVideoToArvan

app_name = 'video_app'
urlpatterns = [
    path('video/<int:pk>/upload/', views.VideoUploadUI.as_view(), name='video_upload_ui'),
    path('video/upload_proxy/' , UploadVideoToArvan.as_view(), name='upload-video-to-arvan'),
    path('video/upload_chunk/',UploadChuckView.as_view(), name='upload-chunk'),
    path('video/save_as_video/',SaveVideoToArvan.as_view(), name='save-video-to-arvan'),
]
