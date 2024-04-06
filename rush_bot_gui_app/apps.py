from django.apps import AppConfig


class RushBotGuiAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'rush_bot_gui_app'

    def ready(self):
        from . import task_screenshot
        task_screenshot.start_background_task()
