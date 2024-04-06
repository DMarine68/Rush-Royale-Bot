from django.urls import path
from . import consumers

websocket_urlpatterns = [
    path('ws/screenshot/', consumers.ScreenshotConsumer.as_asgi()),
]
