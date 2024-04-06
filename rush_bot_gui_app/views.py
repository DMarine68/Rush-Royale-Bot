import base64
import subprocess
from io import BytesIO

from django.http import JsonResponse
from django.shortcuts import render, redirect
from .models import UserSettings
from .forms import SettingsForm
from .task_screenshot import get_latest_screenshot

def latest_screenshot_view(request):
    return JsonResponse({'image_url': get_latest_screenshot()})


def settings_view(request):
    if request.method == 'POST':
        form = SettingsForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('settings_view')
    else:
        form = SettingsForm()
    settings = UserSettings.objects.all()
    # Take a screenshot via adb and save it

    return render(request, 'settings.html', {'form': form, 'settings': settings, 'image_url': get_latest_screenshot()})

