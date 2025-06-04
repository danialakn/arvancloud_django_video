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
    """
    View to handle the initial phase of uploading a video file to ArvanCloud using the TUS protocol.

    This view receives an upload request from the client, including TUS-specific headers such as
    'upload-length' and 'upload-metadata'. It then constructs a new POST request to the ArvanCloud
    API endpoint associated with a given channel.

    Key Steps:
        1. Extracts the Arvan channel ID from query parameters.
        2. Reads required upload headers from the client request.
        3. Sends a POST request to ArvanCloud's /files endpoint with appropriate headers, including
           authorization and TUS protocol version.
        4. Parses the 'location' header from ArvanCloud's response which contains the temporary upload URL.
        5. Stores the upload URL in the server cache with a UUID-based key for later reference.
        6. Returns the upload URL to the client along with a cookie storing the location key.

    Expected Client Headers:
        - upload-length: Total size of the file to be uploaded (in bytes).
        - upload-metadata: Base64-encoded metadata about the file (e.g. filename, type).

    Response:
        - JSON object containing the upload URL.
        - A cookie ('location_key') storing the unique cache key for identifying the upload session.

    Requirements:
        - ARVAN_API_KEY must be defined in Django settings.
        - The server must have caching (e.g., Redis or in-memory cache) properly configured.
    """

    def post(self, request, *args, **kwargs):
        client_headers = request.headers

        channel_id = request.GET.get("arvan_channel_id")
        if not channel_id:
            return JsonResponse({"error": "Missing arvan_channel_id"}, status=400)

        # Construct ArvanCloud endpoint URL
        destination_url = f'https://napi.arvancloud.ir/vod/2.0/channels/{channel_id}/files'

        # Extract TUS headers from client request
        forwarded_headers = {
            'upload-length': client_headers.get('upload-length'),
            'upload-metadata': client_headers.get('upload-metadata'),
        }

        # Compose final request headers with API key
        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
            **forwarded_headers,
        }

        # Send POST request to ArvanCloud
        arvan_response = requests.request("POST", destination_url, headers=headers)
        location = arvan_response.headers.get('location')

        if not location:
            return JsonResponse({"error": "Upload location not provided by Arvan"}, status=500)

        # Generate unique token and store location in cache
        random_token = str(uuid.uuid4())
        location_key = f'upload_location_{random_token}'
        cache.set(location_key, location, timeout=600)  # 10 minutes

        # Send upload URL back to client with cookie
        response = JsonResponse({'upload_url': location}, status=arvan_response.status_code)
        response.set_cookie('location_key', location_key, max_age=600)

        return response
#-------------------------------------------------------------------------------------------------------#
class UploadChuckView(View):
    """
    View to handle TUS-based video chunk uploads to ArvanCloud.

    Supported HTTP methods:
    - HEAD: Check the current upload offset for a resumable upload.
    - PATCH: Upload a file chunk to the previously created ArvanCloud upload URL.

    Workflow:
        - The client must provide a cookie named 'location_key', which maps to a cached Arvan upload URL.
        - Both HEAD and PATCH requests are forwarded to ArvanCloud's endpoint with appropriate headers.
        - Hop-by-hop headers are stripped from Arvan's response before returning it to the client.

    Requirements:
        - CSRF must be disabled (tus-js-client does not support CSRF tokens).
        - A proper caching backend must be configured to store upload URLs.

    Cookies:
        - location_key: A unique cache key identifying the upload session.
    """

    @method_decorator(csrf_exempt)
    def dispatch(self, request, *args, **kwargs):
        # Retrieve the location key from client cookies
        self.location_key = request.COOKIES.get('location_key')
        return super().dispatch(request, *args, **kwargs)

    def head(self, request, *args, **kwargs):
        # Get the upload URL from the cache using the location key
        destination_url = cache.get(self.location_key)
        if not destination_url:
            return HttpResponse(status=404)

        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
        }

        try:
            # Send a HEAD request to Arvan to check upload status
            response = requests.request("HEAD", destination_url, headers=headers)
        except requests.RequestException as e:
            return HttpResponse(f"Error contacting Arvan: {str(e)}", status=502)

        # Remove hop-by-hop headers (not allowed to be forwarded)
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
            'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        safe_headers = {
            k: v for k, v in response.headers.items() if k.lower() not in hop_by_hop_headers
        }

        # Return Arvan’s response headers and status to the client
        return HttpResponse(status=response.status_code, headers=safe_headers)

    def patch(self, request, *args, **kwargs):
        # Get the upload URL from the cache using the location key
        destination_url = cache.get(self.location_key)
        if not destination_url:
            return HttpResponse(status=404)

        client_headers = request.headers

        headers = {
            'Authorization': settings.ARVAN_API_KEY,
            'tus-resumable': '1.0.0',
            'Content-Type': 'application/offset+octet-stream',
            'Upload-Offset': client_headers.get('Upload-Offset'),  # Required for TUS protocol
        }

        try:
            # Forward the file chunk to Arvan using a PATCH request
            response = requests.request("PATCH", destination_url, headers=headers, data=request.body)
        except requests.RequestException as e:
            return HttpResponse(f"Error uploading chunk to Arvan: {str(e)}", status=502)

        # Remove hop-by-hop headers before returning the response
        hop_by_hop_headers = [
            'connection', 'keep-alive', 'proxy-authenticate', 'proxy-authorization',
            'te', 'trailers', 'transfer-encoding', 'upgrade'
        ]
        safe_headers = {
            k: v for k, v in response.headers.items() if k.lower() not in hop_by_hop_headers
        }

        # Return Arvan’s response back to the client
        return HttpResponse(status=response.status_code, headers=safe_headers, content=response.content)
#-----------------------------------------------------------------------------------------------#
class SaveVideoToArvan(View):
    """
    View to finalize a video upload to ArvanCloud by registering the uploaded file as a permanent video asset.

    This view should be called **after the file upload is completed via the TUS protocol**.

    Workflow:
        1. Retrieves the upload URL from the cookie ('location_key') and extracts the `file_id` from it.
        2. Fetches video metadata from the database using `video_pk` provided in query parameters.
        3. Constructs a POST request to ArvanCloud's `/videos` endpoint for the given `channel_id`.
        4. Sends metadata such as title, description, watermark settings, and the `file_id`.
        5. Returns ArvanCloud’s JSON response, which typically includes the new video ID.

    Query Parameters:
        - arvan_channel_id: The ID of the ArvanCloud channel to which the video should be saved.
        - video_pk: Primary key of the video record in your local database.

    Cookies:
        - location_key: The cache key containing the temporary upload URL from which the file ID is extracted.

    Headers Sent to Arvan:
        - Authorization: Bearer token for Arvan API (read from Django settings).

    JSON Body Sent to Arvan:
        - title: Title of the video (copied from local video model).
        - description: Description (same as title, for simplicity).
        - file_id: Extracted from the temporary upload URL.
        - convert_mode: Fixed to "auto".
        - thumbnail_time: Fixed to 10 seconds.
        - watermark_id and watermark_area: Read from the local `Video` model.

    Response:
        - Returns the JSON response from ArvanCloud (e.g., video ID, status).
        - On error, returns a 400 or 404 with an appropriate message.

    Requirements:
        - `ARVAN_API_KEY` must be set in Django settings.
        - `Video` model must have fields: `title`, `watermark`, and `watermark_area`.
        - Upload URL must be cached and accessible using the key stored in `location_key` cookie.
    """

    def dispatch(self, request, *args, **kwargs):
        # Retrieve the cached upload URL key from cookie for later use
        self.location_key = request.COOKIES.get('location_key')
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # Get Arvan channel ID and local video primary key from query params
        channel_id = request.GET.get("arvan_channel_id")
        video_pk = request.GET.get("video_pk")

        # Retrieve the temporary upload URL from the cache using location_key cookie
        upload_url = cache.get(self.location_key)

        # Validate required parameters
        if not channel_id:
            return JsonResponse({"error": "channel_id is required"}, status=400)
        if not video_pk:
            return JsonResponse({"error": "video_pk is required"}, status=400)

        # Extract the file ID from the cached upload URL (expected pattern: .../files/{file_id})
        match = re.search(r'/files/([^/]+)$', upload_url or "")
        file_id = match.group(1) if match else None
        if not file_id:
            return JsonResponse({"error": "file_id not found in location_key"}, status=400)

        # Fetch the video object from the database
        try:
            video = Video.objects.get(pk=video_pk)
        except Video.DoesNotExist:
            return JsonResponse({"error": "video not found"}, status=404)

        # Prepare ArvanCloud API endpoint for saving the video permanently
        destination_url = f'https://napi.arvancloud.ir/vod/2.0/channels/{channel_id}/videos'

        # Set authorization header with the Arvan API key
        headers = {
            'Authorization': settings.ARVAN_API_KEY,
        }

        # Prepare the JSON payload to send metadata and file info to Arvan
        data = {
            "title": video.title,
            "description": video.title,  # Can be expanded for richer descriptions
            "file_id": file_id,
            "convert_mode": "auto",
            "thumbnail_time": 10,
            "watermark_id": video.watermark,
            "watermark_area": video.watermark_area,
        }

        # Send the POST request to ArvanCloud
        arvan_response = requests.post(destination_url, headers=headers, json=data)

        # Return Arvan's response as JSON to the client with matching status code
        return JsonResponse(arvan_response.json(), status=arvan_response.status_code)




