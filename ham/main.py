import ast
import configparser
import os
import random
import subprocess
import time

import pandas as pd
import scrcpy
import adbutils

import cv2
import numpy as np


class Bot:

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

    def tap(self, x, y):
        command = [self.adb, 'shell', 'input', 'tap', str(x), str(y)]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

    def screenshot(self):
        command = [self.adb, 'exec-out', 'screencap', '-p']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        img_data, err = p.communicate()
        if err:
            print(f'Error: {err.decode()}')
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

    def device_is_locked(self):
        command = [self.adb, 'shell', 'dumpsys', 'window', 'displays']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        data = p.stdout.read().decode('utf-8')
        for line in data.splitlines():
            if 'mDreamingLockscreen=true' in line:
                return True
        return False

    def device_is_activity_focused(self, activity_name):
        command = [self.adb, 'shell', 'dumpsys', 'window', 'displays']
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()
        data = p.stdout.read().decode('utf-8')
        for line in data.splitlines():
            if 'mCurrentFocus' in line and activity_name in line:
                return True
        return False

    def device_launch_app(self, package):
        print(f'Launching {package}')
        command = [self.adb, 'shell', 'monkey', '-p', package, "1"]
        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        p.wait()

    def load_icons_to_memory(self, path='icons'):
        if self.loaded_icons is not None:
            return self.loaded_icons

        self.loaded_icons = {}
        for target in os.listdir(path):
            print(f'{path}/{target}')
            self.loaded_icons[target] = cv2.imread(f'{path}/{target}', 0)

    # Check if any icons are on screen
    def get_current_icons(self, screenshot, available=False, path='icons'):
        current_icons = []
        # Update screen and load screenshot as grayscale
        img_rgb = screenshot
        img_gray = cv2.cvtColor(img_rgb, cv2.COLOR_BGR2GRAY)
        self.load_icons_to_memory(path)

        # Check every target in dir
        for icon_name, icon_img in self.loaded_icons.items():
            x = y = 0  # reset position
            # Compare images
            res = cv2.matchTemplate(img_gray, icon_img, cv2.TM_CCOEFF_NORMED)
            threshold = 0.8
            loc = np.where(res >= threshold)
            icon_found = len(loc[0]) > 0
            if icon_found:
                y = loc[0][0]
                x = loc[1][0]
            current_icons.append([icon_name, icon_found, (x, y)])
        icon_df = pd.DataFrame(current_icons, columns=['icon', 'available', 'pos [X,Y]'])
        # filter out only available buttons
        if available:
            icon_df = icon_df[icon_df['available'] == True].reset_index(drop=True)
        return icon_df

    def bot_loop(self):

        self.scrcpy_client = scrcpy.Client(self.get_devices()[0])
        print('here')
        print(self.get_devices()[0])

        while True:
            t = time.time()
            screenshot = self.screenshot()
            if screenshot is None:
                break
            print(f'Time for screenshot: {time.time() - t}')

            if self.device_screenshot is None:
                self.device_screenshot = screenshot

            t = time.time()
            img1 = cv2.cvtColor(self.device_screenshot, cv2.COLOR_BGR2GRAY)
            img2 = cv2.cvtColor(screenshot, cv2.COLOR_BGR2GRAY)
            diff = cv2.absdiff(img1, img2)
            _, thresh = cv2.threshold(diff, 30, 255, cv2.THRESH_BINARY)
            changed_pixels = np.sum(thresh > 0)
            percentage_changed = changed_pixels / thresh.size * 100
            print(f'changed: {percentage_changed}')

            if percentage_changed > 50 or self.icons is None:
                self.icons = self.get_current_icons(screenshot, True, '../icons/homescreen')
            print(f'Time for icons: {time.time() - t}')

            self.device_screenshot = screenshot

            print(self.icons)
            print((self.icons['icon'] == 'co-op.png').any())

            filter_coop = self.icons[self.icons['icon'] == 'co-op.png']

            print(filter_coop)

            if len(filter_coop) > 0:
                pos = filter_coop['pos [X,Y]'].tolist()[0]

                self.tap(pos[0], pos[1])
                time.sleep(3)

                print('On Homescreen....')
            print('\n')
        print('Exiting bot loop')


bot = Bot()
if bot.connect_device():
    print('Connected to ADB!')
else:
    print('Unable to connect')

devices = bot.get_devices()
print(devices)

if bot.device_is_locked():
    print('The device is locked...doing nothing')
else:
    activity = 'com.my.defense'
    is_focused = bot.device_is_activity_focused(activity)

    if not is_focused:
        bot.device_launch_app(activity)
        time.sleep(10)
    # bot.bot_loop()
bot.disconnect()

print(cv2.getBuildInformation())
print('done')
