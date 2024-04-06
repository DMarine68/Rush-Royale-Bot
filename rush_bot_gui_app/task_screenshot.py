import subprocess
import base64
from io import BytesIO
from threading import Thread, Lock
import time

# Global variable and lock to store the latest screenshot
latest_screenshot = None
lock = Lock()

def capture_screenshots():
    global latest_screenshot
    serial = 'R5CT31X9GJN'
    while True:
        process = subprocess.Popen(['/Users/jamesonfehlhaber/git/Rush-Royale-Bot2/.scrcpy/adb', '-s', serial, 'shell', 'screencap', '-p'], stdout=subprocess.PIPE)
        screenshot_bytes = process.stdout.read()
        screenshot_io = BytesIO(screenshot_bytes)

        # Convert to Base64 for HTML embedding
        screenshot_base64 = base64.b64encode(screenshot_io.getvalue()).decode('utf-8')

        with lock:
            latest_screenshot = f'data:image/png;base64,{screenshot_base64}'

        time.sleep(1)  # Adjust the sleep time as needed

def get_latest_screenshot():
    global latest_screenshot
    with lock:
        return latest_screenshot if latest_screenshot else ''


def start_background_task():
    # Start the background thread
    thread = Thread(target=capture_screenshots)
    thread.daemon = True  # Daemonize thread
    thread.start()
