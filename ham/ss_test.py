import configparser
import os
import subprocess

import cv2
import numpy as np
from adbnativeblitz import AdbFastScreenshots


class AdbTest:
    def __init__(self):
        self.scrcpy_client = None
        self.config = configparser.ConfigParser()
        self.config.read('config.ini')
        self.adb = os.path.join('../', '.scrcpy', 'adb')
        self.adb_debug = False
        self.device_screenshot = None
        self.icons = None

        self.loaded_icons = None

    def disconnect(self):
        command = [self.adb, 'disconnect']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = p.wait()
        return res == 0

    def connect_device(self):
        ip = self.config.get('device', 'ip')
        port = self.config.getint('device', 'port')
        command = [self.adb, 'connect', f'{ip}:{port}']
        print(command)
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        res = p.wait()

        if self.adb_debug: print(p.stdout.read().decode('utf-8'))
        return res == 0

    def get_devices(self):
        command = [self.adb, 'devices']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

        device_list = str(p.stdout.read().decode('utf-8')).split('\n')
        return [item.split('\t', 1)[0] for item in device_list[1:-2]]

    def get_serial_number(self):
        command = [self.adb, 'shell', 'getprop', 'ro.serialno']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        return p.stdout.read().decode('utf-8')

    def device_is_locked(self):
        command = [self.adb, 'shell', 'dumpsys', 'window', 'displays']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        data = p.stdout.read().decode('utf-8')
        for line in data.splitlines():
            if 'mDreamingLockscreen=true' in line:
                return True
        return False

    def screenshot(self, serial=None):
        command = [self.adb]
        if serial is not None:
            command += ['-s', serial]
        command += ['exec-out', 'screencap', '-p']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        img_data, err = p.communicate()
        if err:
            print(f'Error: {err.decode()}')
            return None

        if p.returncode != 0:
            return None

        img_array = np.frombuffer(img_data, dtype=np.uint8)
        new_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

        debug_img = False
        if debug_img:
            cv2.imwrite(f'bot_feed.png', new_img)

        if new_img is not None:
            return new_img
        else:
            print('Failed to get screen')

    def screenshot2(self, serial=None):
        s = self.screenshot(serial)
        if s is None:
            return None

        return s
        img1 = cv2.cvtColor(self.device_screenshot, cv2.COLOR_BGR2GRAY)
        img2 = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
        diff = cv2.absdiff(img1, img2)
        _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
        changed_pixels = np.sum(thresh > 0)
        percentage_changed = changed_pixels / thresh.size * 100

        # if percentage_changed > 50 or self.icons is None:
        #    self.icons = self.get_current_icons(screenshot, True, '../icons/homescreen')
        return screenshot


bot = AdbTest()
if bot.connect_device():
    print('Connected to ADB!')
else:
    print('Unable to connect')

devices = bot.get_devices()
print(devices)

if bot.device_is_locked():
    print('The device is locked...doing nothing')
else:
    print('we do something here')
    while True:
        screenshot = bot.screenshot2(devices[0])

        if screenshot is None:
            continue
        cv2.imshow('CV2 Window', screenshot)
        cv2.waitKey(1)
        cv2.destroyAllWindows()
bot.disconnect()
print('bye')
