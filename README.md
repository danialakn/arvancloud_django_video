# Django ArvanCloud TUS Uploader

A Django application designed for uploading and managing video content, storing videos on the ArvanCloud VOD platform using the TUS resumable upload protocol. This project acts as a secure proxy between your client-side uploader and ArvanCloud, handling authentication, chunked uploading, and optimizing resource usage.

## Overview

This project provides a backend solution to facilitate large file uploads directly from the client's browser to ArvanCloud's video platform. By leveraging the TUS protocol, uploads are resumable and broken into manageable chunks. The Django application serves as a set of proxy endpoints to:
1.  Securely initiate the upload with ArvanCloud by injecting API keys.
2.  Proxy the actual file chunks (PATCH requests) from the client to ArvanCloud, again handling authentication.
3.  Finalize the upload or save relevant metadata once the TUS upload completes.

This architecture avoids exposure of sensitive credentials to the client-side and bypasses the need for intermediate server storage of the entire uploaded file.

## The Challenge

When enabling clients to upload files directly to a cloud storage provider like ArvanCloud, two distinct primary challenges emerge:

1.  **Security Risks**: Providing the client-side with direct access credentials (like your ArvanCloud API key) is a major security vulnerability. These keys could be easily compromised, leading to unauthorized access to your ArvanCloud resources.
2.  **Server-Side Bottlenecks & Inefficiency**: A common alternative is to have the client upload the entire file to your application server first, which then re-uploads it to the cloud provider. This "double handling":
    * Consumes significant server resources (bandwidth, disk space, memory, CPU).
    * Can be very slow for large files, leading to poor user experience.
    * Doesn't inherently support resumable uploads without complex custom logic on your server.

## Our Solution

This project implements a multi-stage proxy pattern using Django views to address these challenges:

-   The **frontend** utilizes a TUS client (e.g., `tus-js-client`).
-   **Step 1: Initiation**: The client makes an initial `POST` request to a Django endpoint (e.g., `/initiate-upload/`). This endpoint communicates with ArvanCloud to create an upload resource and gets back a unique TUS upload URL from ArvanCloud. This ArvanCloud URL (or an identifier for it) is returned to the client, possibly along with a session token.
-   **Step 2: Chunk Uploading (Proxying PATCH requests)**: The `tus-js-client` then sends the file in chunks (`PATCH` requests) to a *different* Django endpoint (e.g., `/upload-chunk/`). This Django view acts as a proxy: it receives each chunk, adds the necessary `Authorization` headers, and forwards the chunk to the specific ArvanCloud TUS URL obtained in Step 1.
-   **Step 3: Finalization**: After the `tus-js-client` successfully uploads all chunks, it triggers a callback. Within this callback, the client can make a final `POST` request to another Django endpoint (e.g., `/finalize-upload/`) to notify the server that the upload is complete. This endpoint can then perform any necessary actions, like updating database records or triggering post-processing on ArvanCloud.

This approach ensures your ArvanCloud API key remains secure on the server, while clients benefit from direct-to-cloud (via proxy) resumable uploads, and your server only handles smaller, manageable chunks of data at a time.

## Key Features

-   **Secure API Key Management**: Your ArvanCloud API key is never exposed to the client.
-   **Resumable Uploads**: Utilizes the TUS protocol for robust, resumable uploads.
-   **Resource Optimization**: Avoids storing large files temporarily on your server.
-   **Efficient Chunked Uploads**: Optimally handles large files and unstable connections by proxying chunks.
-   **Clear Separation of Concerns**: Dedicated endpoints for initiating, chunking, and finalizing uploads.

## Prerequisites

-   Python (3.12+)
-   Django (5.0+)
-   Redis (recommended if `django-redis` is used for caching upload locations or other TUS-related states)
-   An active ArvanCloud VOD platform account and an API Key.

## Installation

### Backend (Django)

1.  Clone this repository or integrate the application code into your existing Django project.
2.  Install the required Python packages:
    ```bash
    pip install django-redis requests python-dotenv
    ```
3.  Ensure Redis server is running and accessible if `django-redis` is used.

### Frontend

1.  Include the `tus-js-client` library. You can use a CDN:
    ```html
    <script src="[https://cdn.jsdelivr.net/npm/tus-js-client@latest/dist/tus.min.js](https://cdn.jsdelivr.net/npm/tus-js-client@latest/dist/tus.min.js)"></script> 
    ```

## Configuration

### 1. Environment Variables (API Key)

**IMPORTANT**: Never hardcode your `ARVAN_API_KEY` directly into your source code or commit it to version control.

1.  Create a `.env` file in the root directory of your Django project (alongside `manage.py`):
    ```env
    # .env
    ARVAN_API_KEY=your_actual_arvancloud_api_key_here
    # Example: DEBUG=True
    # Example: SECRET_KEY=your_django_secret_key
    ```
2.  Add the `.env` file to your `.gitignore` file:
    ```gitignore
    # .gitignore
    .env
    __pycache__/
    db.sqlite3
    *.sqlite3
    # ... other entries
    ```
3.  Load the environment variables in your Django `settings.py` file:
    ```python
    # settings.py
    from pathlib import Path
    import os
    from dotenv import load_dotenv

    BASE_DIR = Path(__file__).resolve().parent.parent
    DOTENV_PATH = BASE_DIR / '.env'

    if os.path.exists(DOTENV_PATH):
        load_dotenv(dotenv_path=DOTENV_PATH)
    else:
        print(f"Warning: .env file not found at {DOTENV_PATH}. ARVAN_API_KEY should be set via environment variables.")

    ARVAN_API_KEY = os.environ.get('ARVAN_API_KEY')

    if not ARVAN_API_KEY:
        # Consider raising ImproperlyConfigured in a real project if this key is essential
        print("CRITICAL WARNING: ARVAN_API_KEY is not set!")
    ```

### 2. Django Settings
   - Add the application (e.g., `'video_app'`) to your `INSTALLED_APPS` in `settings.py`.
   - Configure `django-redis` in `settings.py` if used for caching ArvanCloud upload URLs:
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

## How It Works & Basic Usage Example

The process involves three main interactions with your Django backend:

### 1. Frontend: Initiating the Upload

The client first sends a `POST` request to your Django server to signal the start of an upload and send metadata.
Your Django template would provide necessary initial data like `video.arvan_channel_id` and `video.pk`.

```html
<input type="file" id="uploadInput" />
<button id="startUploadBtn">Start Upload</button>
<progress id="uploadProgress" value="0" max="100"></progress>
<p id="uploadStatus"></p>

<script src="[https://cdn.jsdelivr.net/npm/tus-js-client@latest/dist/tus.min.js](https://cdn.jsdelivr.net/npm/tus-js-client@latest/dist/tus.min.js)"></script>
<script>
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      const cookies = document.cookie.split(";");
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  const input = document.getElementById("uploadInput");
  const progress = document.getElementById("uploadProgress");
  const statusText = document.getElementById("uploadStatus");
  const startButton = document.getElementById("startUploadBtn");

  let selectedFile = null;
  // These would typically be rendered by your Django template
  const arvanChannelId = "{{ video.arvan_channel_id|escapejs }}"; // Example: Get from Django template
  const videoPk = "{{ video.pk|escapejs }}"; // Example: Get from Django template

  // Django URLs - ensure these are correctly resolved in your template
  const initiateUploadUrl = "{% url 'video_app:upload-video-to-arvan' %}?arvan_channel_id=" + arvanChannelId;
  const chunkUploadUrl = "{% url 'video_app:upload-chunk' %}"; // This will be the TUS endpoint
  const finalizeUploadUrl = `{% url 'video_app:save-video-to-arvan' %}?arvan_channel_id=${arvanChannelId}&video_pk=${videoPk}`;


  input.addEventListener("change", function () {
    selectedFile = input.files[0];
    if (selectedFile) {
        statusText.textContent = "File selected: " + selectedFile.name;
    } else {
        statusText.textContent = "No file selected.";
    }
  });

  startButton.addEventListener("click", function () {
    if (!selectedFile) {
      alert("Please select a file first.");
      return;
    }
    if (!arvanChannelId) {
        alert("Arvan Channel ID is missing.");
        return;
    }

    statusText.textContent = "Initiating upload...";
    progress.value = 0;

    // Step 1: Initial POST to your Django server to get ArvanCloud upload details
    fetch(initiateUploadUrl, {
      method: "POST",
      headers: {
        "Upload-Length": selectedFile.size.toString(),
        "Upload-Metadata": "filename " + btoa(unescape(encodeURIComponent(selectedFile.name))) + ",filetype " + btoa(selectedFile.type),
        "X-CSRFToken": getCookie("csrftoken"),
      },
      // credentials: "include", // if your Django endpoint requires authentication via cookies
    })
    .then(response => {
      if (!response.ok) {
        // Handle errors from your Django initiation endpoint
        return response.json().then(errData => { throw new Error(errData.error || `Initiation failed: ${response.statusText}`) });
      }
      return response.json();
    })
    .then(data => {
      // data should contain information needed by your chunk proxy,
      // e.g., data.arvan_upload_url (the direct ArvanCloud TUS URL)
      // and data.location_key_token (a token your server uses to find the cached arvan_upload_url).
      // The 'uploadUrl' for tus.Upload will be your Django chunk proxy endpoint.
      // Your chunk proxy endpoint will use the token (e.g., from a cookie or URL param)
      // to retrieve the actual ArvanCloud upload URL from cache.

      statusText.textContent = "Starting TUS upload...";
      const upload = new tus.Upload(selectedFile, {
          endpoint: chunkUploadUrl, // TUS client sends chunks to your Django proxy
          // uploadUrl: chunkUploadUrl, // Some versions of tus-js-client use 'uploadUrl'
          retryDelays: [0, 3000, 5000, 10000, 20000],
          chunkSize: 2 * 1024 * 1024,  // Example: 2MB chunks
          metadata: { // This metadata is sent with the TUS PATCH requests by some clients
            filename: selectedFile.name,
            filetype: selectedFile.type
          },
          headers: { // Custom headers for requests made by tus-js-client to your chunk proxy
            "X-CSRFToken": getCookie("csrftoken"), // If your chunk proxy endpoint needs CSRF
            // If your server uses a token to identify the upload session for proxying:
            // "X-Upload-Token": data.location_key_token, // Send the token received from initiation
          },
          // withCredentials: true, // If your Django proxy needs cookies (like sessionid or the token cookie)
          onError: error => {
            console.error("TUS Error:", error);
            statusText.textContent = "Upload Error: " + error;
          },
          onProgress: (bytesUploaded, bytesTotal) => {
            const percentage = (bytesUploaded / bytesTotal * 100).toFixed(2);
            progress.value = percentage;
            statusText.textContent = `Uploading: ${percentage}%`;
          },
          onSuccess: () => {
            statusText.textContent = "TUS Upload Complete! Finalizing...";
            progress.value = 100;

            // Step 3: Notify your Django server that TUS upload is complete
            fetch(finalizeUploadUrl, {
              method: "POST",
              headers: {
                  "X-CSRFToken": getCookie("csrftoken"),
                  // Include any other necessary headers or body
              },
              // credentials: "include",
            })
            .then(res => {
                if (!res.ok) {
                    return res.json().then(errData => { throw new Error(errData.error || `Finalization failed: ${res.statusText}`) });
                }
                return res.json();
            })
            .then(data => {
              console.log("Video successfully finalized on ArvanCloud:", data);
              statusText.textContent = "Upload complete and finalized!";
            })
            .catch(err => {
              console.error("Error finalizing video:", err);
              statusText.textContent = "Upload complete, but finalization failed: " + err.message;
            });
          }
        });

      upload.start();
    })
    .catch(error => {
        console.error("Error in upload process:", error);
        statusText.textContent = "Error: " + error.message;
    });
  });
</script>

## License

This project is licensed under the GNU General Public License v3.0 - see the [LICENSE](LICENSE) file for details.