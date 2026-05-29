import os
import subprocess
import time
import requests
import socket
import sys

APPIUM_CMD = r"C:\Users\SVC-Systems-TestPC\AppData\Roaming\npm\appium.cmd"
APPIUM_HOME = r"C:\Users\SVC-Systems-TestPC\.appium"
APPIUM_HOST = "127.0.0.1"
APPIUM_PORT = 4723
APPIUM_STATUS_URL = f"http://{APPIUM_HOST}:{APPIUM_PORT}/status"


class AppiumManager:

    @staticmethod
    def _is_port_in_use(host, port):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex((host, port)) == 0

    @staticmethod
    def _wait_for_appium(timeout=60):
        print("Waiting for Appium to be ready...")

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = requests.get(APPIUM_STATUS_URL, timeout=5)
                if response.status_code == 200:
                    print("Appium is running")
                    return True
            except Exception:
                pass

            time.sleep(3)

        return False

    @staticmethod
    def _check_adb_devices():
        print("Checking ADB devices...")
        result = subprocess.run(
            ["adb", "devices"],
            capture_output=True,
            text=True
        )

        print(result.stdout)

        if "device" not in result.stdout:
            print("No Android device detected!")
            sys.exit(1)

    @staticmethod
    def start():

        print("===================================================")
        print("Appium Manager Starting...")
        print("===================================================")

        # Set APPIUM_HOME safely
        os.environ["APPIUM_HOME"] = APPIUM_HOME

        # Check if port already in use
        if AppiumManager._is_port_in_use(APPIUM_HOST, APPIUM_PORT):
            print("Appium already running on port 4723")
        else:
            print("Appium not running. Starting new server...")

            try:
                subprocess.Popen(
                    [APPIUM_CMD, "--address", APPIUM_HOST, "--port", str(APPIUM_PORT)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except Exception as e:
                print(f"Failed to start Appium: {e}")
                sys.exit(1)

            if not AppiumManager._wait_for_appium():
                print("Appium failed to start within timeout!")
                sys.exit(1)

        # Always verify device
        AppiumManager._check_adb_devices()

        print("===================================================")
        print("Appium Environment Ready")
        print("===================================================")