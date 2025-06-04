# arvancloud_django_video
# Copyright (C) 2025  Daniyal Akhavan <daniyal.akhavan@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

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
