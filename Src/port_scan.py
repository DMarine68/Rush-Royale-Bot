import socket
# import thread module
from _thread import *
import threading
import time
import os
from subprocess import check_output, Popen, DEVNULL


class PortScan:
    def __init__(self, adb, config):
        self.adb = adb
        self.config = config

    # Connects to a target IP and port, if port is open try to connect adb
    def connect_port(self, ip, port, batch, open_ports):
        for target_port in range(port, port + batch):
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex((ip, target_port))
            if result == 0:
                open_ports[target_port] = 'open'
                # Make it Popen and kill shell after couple seconds
                p = Popen([self.adb, 'connect', f'{ip}:{target_port}'])
                time.sleep(5)  # Give real client 5 seconds to connect
                p.terminate()

    # Attempts to connect to ip over every port in range
    # Returns device if found
    def scan_ports(self, target_ip, port_start, port_end, batch=3):
        threads = []
        open_ports = {}
        port_range = range(port_start, port_end, batch)
        socket.setdefaulttimeout(1)
        print(f'Scanning {target_ip} Ports {port_start} - {port_end}')
        # Create one thread per port
        for port in port_range:
            thread = threading.Thread(target=self.connect_port, args=(target_ip, port, batch, open_ports))
            threads.append(thread)
        # Attempt to connect to every port
        for thread in threads:
            thread.start()
        # Join threads
        print(f'Started {len(port_range)} threads')
        for thread in threads:
            thread.join()
        # Get open ports
        port_list = list(open_ports.keys())
        print(f'Ports Open: {port_list}')
        return self.get_adb_device() # return first device found

    # Check if adb device is already connected
    def get_adb_device(self, target_serial=None):
        devices_str = check_output([self.adb, 'devices'])
        devices_arr = str(devices_str).split('\n')
        # Check for online status
        for device in devices_arr[1:]:
            device_data = device.split('\t')
            device_serial = device_data[0]
            device_status = device_data[1]
            if device_status == 'device':
                if target_serial is None or target_serial == device_serial:
                    print(f'Found ADB device! {device_serial}')
                    return device_serial
            else:
                print(f'Device {device_serial} is offline...disconnecting!')
                p = Popen([self.adb, 'disconnect', device_serial], shell=True, stderr=DEVNULL)
                p.wait()
        return None

    def get_config_device_serial(self):
        last_serial_index = self.config.getint('DEFAULT', 'last_serial_index', fallback=0)
        serials = self.config.get('DEFAULT', 'serials', fallback='')
        serials.replace(' ', '')  # remove spaces
        serials_arr = serials.split(',')
        return serials_arr[last_serial_index] if last_serial_index < len(serials_arr) else None

    def is_device_online(self, device_serial):
        if device_serial is None:
            return False
        devices_str = check_output([self.adb, 'devices'])
        devices = str(devices_str).split('\n')
        # Check for online status
        for device in devices[1:]:
            device_data = device.split('\t')
            if device_data[0] != device_serial:
                continue
            if device_data[1] == 'device':
                return True
        return False

    def get_device(self):
        p = Popen([self.adb, 'kill-server'])
        p.wait()
        p = Popen([self.adb, 'devices'], shell=True, stdout=DEVNULL)
        p.wait()
        target_serial = self.get_config_device_serial()

        # Check if adb got connected
        device = self.get_adb_device(target_serial)
        if not device:
            # Find valid ADB device by scanning ports
            section = 'PORT SCAN'
            min_port = self.config.getint(section, 'min', fallback=50000)
            max_port = self.config.getint(section, 'max', fallback=65000)
            host = self.config.get(section, 'host', fallback='127.0.0.1')
            device = self.scan_ports(host, min_port, max_port)
        if device:
            return device
