# Django ArvanCloud TUS Uploader

A Django application designed for uploading and managing video content, storing videos on the ArvanCloud VOD platform using the TUS resumable upload protocol. This project acts as a secure proxy between your client-side uploader and ArvanCloud, handling authentication and optimizing resource usage.

## Overview

This project provides a backend solution to facilitate large file uploads directly from the client's browser to ArvanCloud's video platform. By leveraging the TUS protocol, uploads are resumable and broken into manageable chunks. The Django application serves as a proxy endpoint to securely inject API keys and forward requests to ArvanCloud, thus avoiding exposure of sensitive credentials to the client-side and bypassing the need for intermediate server storage of the uploaded file.

## The Challenge

When allowing clients to upload files directly to a cloud storage provider like ArvanCloud, two main challenges arise:
1.  **Security**: Exposing your ArvanCloud API key or other sensitive credentials to the client-side is a significant security risk.
2.  **Efficiency**: Uploading the file first to your server and then from your server to ArvanCloud (double handling) consumes unnecessary server resources (bandwidth, disk space, processing power) and is slower.

## Our Solution

This project implements a proxy pattern:
-   The **frontend** uses a TUS client (e.g., `tus-js-client`) to send file chunks.
-   These chunks are sent to a dedicated **Django endpoint**.
-   The Django server receives these requests, appends necessary authentication headers (specifically, your ArvanCloud API key).
-   The augmented request is then securely forwarded to the ArvanCloud VOD API.

This approach ensures that your ArvanCloud API key remains confidential on the server-side while still allowing clients to benefit from direct, chunked uploads.

## Key Features

-   **Secure API Key Management**: Your ArvanCloud API key is never exposed to the client.
-   **Resumable Uploads**: Utilizes the TUS protocol for robust, resumable uploads.
-   **Resource Optimization**: Avoids storing large files temporarily on your server, saving disk space and bandwidth.
-   **Chunked Uploads**: Efficiently handles large files and unstable connections.
-   **Optimized Server Load**: Configurable resource consumption on the server for processing chunks.

## Prerequisites

-   Python (3.8+)
-   Django (3.2+ recommended)
-   Redis (required by `django-redis` for caching or session management related to TUS, if applicable)
-   An active ArvanCloud VOD platform account and an API Key.

## Installation

### Backend (Django)

1.  Clone this repository or integrate the application code into your existing Django project.
2.  Install the required Python packages:
    ```bash
    pip install django-redis requests python-dotenv
    ```
3.  Ensure Redis server is running and accessible if `django-redis` requires it for your setup.

### Frontend

1.  Include the `tus-js-client` library. You can use a CDN:
    ```html
    <script src="[https://cdn.jsdelivr.net/npm/tus-js-client@2.3.0/dist/tus.js](https://cdn.jsdelivr.net/npm/tus-js-client@2.3.0/dist/tus.js)"></script>
    ```

## Configuration

### 1. Environment Variables (API Key)

**IMPORTANT**: Never hardcode your `ARVAN_API_KEY` directly into your source code or commit it to version control.

1.  Create a `.env` file in the root directory of your Django project (alongside `manage.py`):
    ```env
    # .env
    ARVAN_API_KEY=your_actual_arvancloud_api_key_here
    # Add other environment-specific variables here, like DEBUG, DATABASE_URL, etc.
    ```
2.  Add the `.env` file to your `.gitignore` file to prevent it from being committed:
    ```gitignore
    # .gitignore
    .env
    __pycache__/
    db.sqlite3
    # ... other entries
    ```
3.  Load the environment variables in your Django `settings.py` file, typically at the beginning:
    ```python
    # settings.py
    from pathlib import Path
    import os # Make sure os is imported
    from dotenv import load_dotenv

    BASE_DIR = Path(__file__).resolve().parent.parent
    DOTENV_PATH = BASE_DIR / '.env'

    if os.path.exists(DOTENV_PATH):
        load_dotenv(dotenv_path=DOTENV_PATH)
    else:
        # Handle the case where .env file might be missing in some environments
        # or log a warning.
        print(f"Warning: .env file not found at {DOTENV_PATH}. Ensure ARVAN_API_KEY is set via other means if this is a production environment.")

    ARVAN_API_KEY = os.environ.get('ARVAN_API_KEY')

    if not ARVAN_API_KEY:
        # Optional: Raise an error or log if the API key is crucial for startup
        print("CRITICAL: ARVAN_API_KEY is not set in environment variables!")
    ```

### 2. Django Settings
   - Add the application (e.g., `'video_app'`) to your `INSTALLED_APPS` in `settings.py`.
   - Configure `django-redis` cache settings in `settings.py` if you are using it for caching upload locations or other TUS-related states. Example:
     ```python
     # settings.py
     CACHES = {
         "default": {
             "BACKEND": "django_redis.cache.RedisCache",
             "LOCATION": "redis://127.0.0.1:6379/1", # Your Redis server location
             "OPTIONS": {
                 "CLIENT_CLASS": "django_redis.client.DefaultClient",
             }
         }
     }
     ```

## How It Works & Basic Usage

The TUS protocol typically involves an initial POST request to create an upload resource, followed by one or more PATCH requests to upload file chunks.

### 1. Initial Client Request (Creating Upload Resource)

ArvanCloud requires certain metadata to initiate an upload. The client sends this information to your Django server, which then forwards it to ArvanCloud along with authentication.

Here's an example of how your frontend JavaScript might make the initial `POST` request to your Django server:

```javascript
// Ensure you have a function to get CSRF token if not using a global one
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const selectedFile = /* your file object from an <input type="file"> */;
const arvanChannelId = /* ID of the ArvanCloud channel */;
// Replace 'your_app_name:upload_endpoint_name' with your actual Django URL name
const yourDjangoUploadInitiationUrl = `/your-django-proxy-endpoint/?arvan_channel_id=${arvanChannelId}`; // Or use Django's {% url %} tag if in a Django template

fetch(yourDjangoUploadInitiationUrl, {
  method: "POST",
  headers: {
    "Upload-Length": selectedFile.size,
    // Ensure filename is properly encoded, especially for non-ASCII characters
    "Upload-Metadata": "filename " + btoa(unescape(encodeURIComponent(selectedFile.name))) + ",filetype " + btoa(selectedFile.type),
    "X-CSRFToken": getCookie("csrftoken"), // Required for Django POST requests
  },
  // credentials: "include", // Only if you need to send cookies to your Django backend for auth
})
.then(response => {
  if (!response.ok) {
    // For TUS, a 201 Created status from ArvanCloud (proxied by your server) is expected.
    // Your server might return other statuses for its own errors.
    throw new Error(`Server responded with ${response.status}`);
  }
  // Your server should return the 'Location' header from ArvanCloud,
  // potentially in the JSON body or as a custom header.
  // Let's assume your server returns it in JSON as 'upload_url'.
  return response.json();
})
.then(data => {
  const tusUploadUrl = data.upload_url; // The URL provided by ArvanCloud via your proxy
  const locationKeyToken = data.location_key_token; // Token to identify cached ArvanCloud URL

  // Now, configure tus-js-client to use this tusUploadUrl for chunked uploads
  var upload = new tus.Upload(selectedFile, {
    endpoint: tusUploadUrl, // This might be the ArvanCloud URL directly,
                            // OR another endpoint on your Django server if you proxy PATCH requests too.
                            // Your problem description suggests PATCH requests might also be proxied.
    // If PATCH requests are also proxied via your Django server:
    // endpoint: `/your-django-proxy-patch-endpoint/${locationKeyToken}/`,
    retryDelays: [0, 3000, 5000, 10000, 20000],
    metadata: {
      filename: selectedFile.name,
      filetype: selectedFile.type
    },
    headers: {
        // If PATCH requests are proxied by Django and need CSRF:
        // "X-CSRFToken": getCookie("csrftoken"),
    },
    onError: function(error) {
      console.error("Failed because: " + error);
    },
    onProgress: function(bytesUploaded, bytesTotal) {
      var percentage = (bytesUploaded / bytesTotal * 100).toFixed(2);
      console.log(bytesUploaded, bytesTotal, percentage + "%");
    },
    onSuccess: function() {
      console.log("Download %s from %s", upload.file.name, upload.url);
      // `upload.url` is the final URL of the uploaded file on ArvanCloud
    }
  });

  // Start the upload
  upload.start();
})
.catch(error => {
  console.error('Error initiating TUS upload:', error);
});