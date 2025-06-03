from django.db import models
import requests
from django.conf import settings


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
    arvan_channel_title = models.CharField(max_length=100 , blank=True, null=True)
    arvan_channel_id = models.CharField(max_length=100 , blank=True, null=True)
    watermark = models.CharField(max_length=100 , null=True, blank=True)
    watermark_area = models.CharField(
        null=True, blank=True,
        max_length=30,
        choices=WATERMARK_CHOICES,
    )

# --------------------------------------------------------------------------------------------#
    @staticmethod
    def get_channel_list(api_key):
        """
         Retrieves a list of all available channels from ArvanCloud VOD API.

         Args:
             api_key (str): The API key for authenticating with ArvanCloud.

         Returns:
             dict: The JSON response containing channel data.
         """
        response = requests.get(
            'https://napi.arvancloud.ir/vod/2.0/channels',
            headers={
                'Authorization': api_key,
            }
        )
        return response.json()

    # --------------------------------------------------------------------------------------------#

    def get_channel_id(self,arvan_channel_title, api_key):
        """
        Finds the ID of a channel by its title.

        Args:
            arvan_channel_title (str): The title of the channel to search for.
            api_key (str): The API key for authenticating with ArvanCloud.

        Returns:
            str or None: The ID of the channel if found, otherwise None.
        """
        ch_list = self.get_channel_list(api_key=settings.ARVAN_API_KEY)
        for channel in ch_list['data']:
            if channel['title'] ==self.arvan_channel_title:
                self.arvan_channel_id = channel['id']
                return self.arvan_channel_id
        return None

    def save(self, *args, **kwargs):

        if self.arvan_channel_title and not self.arvan_channel_id:
            self.get_channel_id(arvan_channel_title=self.arvan_channel_title, api_key=settings.ARVAN_API_KEY)
        super().save(*args, **kwargs)


    def __str__(self):
        return self.title






