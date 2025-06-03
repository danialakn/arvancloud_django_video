from django.db import models

WATERMARK_CHOICES = [
    ('center','CENTER'),
    ('fix_top_left','FIX_TOP_LEFT'),
    ('fix_top_right','FIX_TOP_RIGHT'),
    ('fix_top_center','FIX_TOP_CENTER'),
    ('fix_bottom_left','FIX_BOTTOM_LEFT'),
    ('fix_bottom_right','FIX_BOTTOM_RIGHT'),
    ('fix_bottom_center','FIX_BOTTOM_CENTER'),
    ('animate_left_to_right','ANIMATE_LEFT_TO_RIGHT'),
    ('animate_top_to_bottom','ANIMATE_TOP_TO_BOTTOM')
]

class Video(models.Model):
    title = models.CharField(max_length=100)
    video_slug = models.SlugField(max_length=100, unique=True)
    video_id = models.CharField(max_length=100, unique=True , blank=True, null=True)
    arvan_channel_title = models.CharField(max_length=100)
    arvan_channel_id = models.CharField(max_length=100)
    watermark = models.CharField(max_length=100 , null=True, blank=True)
    watermark_area = models.CharField(
        null=True, blank=True,
        max_length=30,
        choices=WATERMARK_CHOICES,
    )

