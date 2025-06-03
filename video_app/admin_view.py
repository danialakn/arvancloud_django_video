
from django.http import HttpResponse, JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
import requests
from .models import Video
from django.core.cache import cache
import uuid
from django .views import View
import re
from django.conf import settings

class UploadVideoToArvan(View):

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        client_headers = request.headers
        try:
            channel_id = request.GET.get("arvan_channel_id")


        except Video.DoesNotExist:
            return JsonResponse({"error": "Channel not found"}, status=404)

        destination_url = f'https://napi.arvancloud.ir/vod/2.0/channels/{channel_id}/files'
        print(destination_url)

        forwarded_headers = {
            'upload-length': client_headers.get('upload-length'),
            'upload-metadata': client_headers.get('upload-metadata'),
        }
        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
            **forwarded_headers,
        }

        arvan_response = requests.request("POST", destination_url, headers=headers)
        location = arvan_response.headers.get('location')
        # ساختن توکن و ذخیره در کش
        random_token = str(uuid.uuid4())
        location_key = f'upload_location_{random_token}'
        cache.set(location_key, location, timeout=60 * 10)

        response = JsonResponse({'upload_url': location}, status=arvan_response.status_code)
        response.set_cookie('location_key', location_key, max_age=3000)

        return response



class UploadChuckView(View):

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        self.location_key = request.COOKIES.get('location_key')
        return super().dispatch(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        if self.location_key:
            destination_url = cache.get(self.location_key)
        else:
            return HttpResponse(status=404)

        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
        }
        response = requests.request("HEAD", destination_url, headers=headers)

        # حذف هدرهای غیرمجاز
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
            'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        safe_headers = {
            k: v for k, v in response.headers.items() if k.lower() not in hop_by_hop_headers
        }

        return HttpResponse(status=response.status_code, headers=safe_headers)

    def patch(self, request, *args, **kwargs):

        if self.location_key:
            destination_url = cache.get(self.location_key)
        else:
            return HttpResponse(status=404)

        client_headers = request.headers
        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
            'Content-Type': 'application/offset+octet-stream',
            'Upload-Offset': client_headers.get('Upload-Offset'),

        }

        response = requests.request("PATCH", destination_url, headers=headers, data=request.body)
        # حذف هدرهای غیرمجاز
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
            'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        safe_headers = {
            k: v for k, v in response.headers.items() if k.lower() not in hop_by_hop_headers
        }


        return HttpResponse(status=response.status_code, headers=safe_headers, content=response.content)



class SaveVideoToArvan(View):


    def dispatch(self, request, *args, **kwargs):
        self.location_key = request.COOKIES.get('location_key')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        channel_id = request.GET.get("arvan_channel_id")
        video_pk = request.GET.get("video_pk")
        upload_url= cache.get(self.location_key)
        if not channel_id:
            return JsonResponse({"error": "channel_id is required"}, status=400)
        if not video_pk:
            return JsonResponse({"error": "video_pk is required"}, status=400)

        match = re.search(r'/files/([^/]+)$', upload_url or "")
        file_id = match.group(1) if match else None
        if not file_id:
            return JsonResponse({"error": "file_id not found in location_key"}, status=400)

        try:
            video = Video.objects.get(pk=video_pk)
        except Video.DoesNotExist:
            return JsonResponse({"error": "video not found"}, status=404)

        destination_url = f'https://napi.arvancloud.ir/vod/2.0/channels/{channel_id}/videos'

        headers = {
            'Authorization': settings.ARVAN_API_KEY,
        }

        data = {
            "title": f'{video.title}',
            "description": f'{video.title}',
            "file_id": file_id,
            "convert_mode": "auto",
            "thumbnail_time": 10,
            "watermark_id": video.watermark,
            "watermark_area": video.watermark_area,
        }

        arvan_response = requests.post(destination_url, headers=headers, json=data)

        return JsonResponse(arvan_response.json(), status=arvan_response.status_code)






