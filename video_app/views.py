from django.shortcuts import render
from django.shortcuts import get_object_or_404
from django.views import View
from . models import Video


# Create your views here.
class VideoUploadUI(View):
    def get(self, request, pk):
        video = get_object_or_404(Video, pk=pk)
        return render(request, 'admin/custom_upload.html', {'video': video})

