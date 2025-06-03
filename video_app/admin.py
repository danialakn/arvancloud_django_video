from django.contrib import admin
from . models import Video
from django.utils.html import format_html
from django.urls import reverse

# Register your models here.
@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ('title', 'upload_link')

    def upload_link(self, obj):
        url = reverse('video_app:video_upload_ui', args=[obj.id])
        return format_html('<a class="button" href="{}">آپلود ویدیو</a>', url)

    upload_link.short_description = 'آپلود'
    upload_link.allow_tags = True