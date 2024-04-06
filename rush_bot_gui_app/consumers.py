from channels.generic.websocket import AsyncWebsocketConsumer
from task_screenshot import get_latest_screenshot
import json

class ScreenshotConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # When a message is received, you can send the latest screenshot
        # For this, you might need to adjust the logic to fetch the latest screenshot appropriately
        await self.send(text_data=json.dumps({
            'screenshot': get_latest_screenshot(),
        }))
