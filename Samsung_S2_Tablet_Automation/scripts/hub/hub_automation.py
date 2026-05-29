import os
import time
import subprocess
from appium import webdriver
from appium.options.android import UiAutomator2Options
# from selenium.webdriver.common.by import By
from appium.webdriver.common.appiumby import AppiumBy as By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions.interaction import Interaction
from selenium.webdriver.common.action_chains import ActionBuilder
import sys

sys.stdout.reconfigure(encoding="utf-8")

# add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

# --------------------------------------------------
# CORE IMPORTS
# --------------------------------------------------
from core.device_registry import is_device_allowed, get_device_name
from core.adb_utils import (
    get_connected_device_serial,
    is_device_locked,
    unlock_device_with_password
)
from core.config_loader import load_device_password
from datetime import datetime


def log(section, message):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{section:<14}] {message}")

# --------------------------------------------------
# DISPLAY SERIAL MAPPING
# --------------------------------------------------

DISPLAY_SERIAL_MAP = {

    "22a9e8a977239f73": "R52M10M43NV"

}

# --------------------------------------------------
# DEVICE RESOLUTION & UNLOCK
# --------------------------------------------------
device_serial = os.environ.get("DEVICE_SERIAL") or get_connected_device_serial()
display_serial = DISPLAY_SERIAL_MAP.get(
    device_serial,
    device_serial
)

if not is_device_allowed(device_serial):
    raise RuntimeError(f"Unauthorized A4P device connected: {device_serial}")

device_name = get_device_name(device_serial)
log(
    "DEVICE",
    f"Authorized device detected: {device_name} ({display_serial})"
)

if is_device_locked():
    unlock_device_with_password(load_device_password())
else:
    # print("Device already unlocked.")
    log("DEVICE", "Device already unlocked")

# --------------------------------------------------
# START APPIUM
# --------------------------------------------------
from appiumManager.appium_manager import AppiumManager

AppiumManager.start()


# ====== HubCode1 Functions ======

def dump_container_children(container):
    print("Dumping container children:")
    children = container.find_elements(By.XPATH, ".//*")
    for i, child in enumerate(children, 1):
        try:
            class_name = child.get_attribute("className")
            res_id = child.get_attribute("resourceId")
            text = child.text
            clickable = child.get_attribute("clickable")
            print(f"  Child #{i}: class={class_name}, resource-id={res_id}, text='{text}', clickable={clickable}")
        except Exception as e:
            print(f"  Child #{i}: Exception reading attributes: {e}")


def get_connected_device_serial():
    try:
        result = subprocess.run("adb devices", capture_output=True, text=True, shell=True)
        lines = result.stdout.strip().split("\n")[1:]
        devices = [line.split()[0] for line in lines if "device" in line]
        if not devices:
            raise RuntimeError("No connected Android device found.")
        return devices[0]
    except Exception as e:
        print(f"Error detecting device: {e}")
        return None


def tap_by_bounds(driver, bounds_str):
    bounds = bounds_str.replace("][", ",").replace("[", "").replace("]", "").split(",")
    x1, y1, x2, y2 = map(int, bounds)
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2

    finger = PointerInput(Interaction.TOUCH, "finger")
    action = ActionBuilder(driver, mouse=finger)
    action.pointer_action.move_to_location(center_x, center_y)
    action.pointer_action.pointer_down()
    action.pointer_action.pause(0.1)
    action.pointer_action.pointer_up()
    action.perform()


def force_stop_and_launch_hub(serial):
    # print(f"Launching Hub on {serial}")
    log("HUB", f"Launching Hub on {serial}")

    subprocess.run(
        f"adb -s {serial} shell am force-stop com.airwatch.androidagent",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    subprocess.run(
        f"adb -s {serial} shell monkey -p com.airwatch.androidagent "
        f"-c android.intent.category.LAUNCHER 1",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(5)


def get_driver_for_hub(serial):
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.app_package = "com.airwatch.androidagent"
    options.app_activity = "com.airwatch.androidagent.AgentHomeActivity"
    options.no_reset = True
    options.new_command_timeout = 300
    # ADD – REQUIRED for Samsung / slow devices
    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000
    # ADD – allow attach since Hub is already launched via adb
    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True

    # return webdriver.Remote("http://localhost:4723", options=options)
    return webdriver.Remote("http://127.0.0.1:4723", options=options)


def wait_for_package(driver, package_name="com.airwatch.androidagent", timeout=20):
    # print(f"⏳ Waiting for package '{package_name}' to be active...")
    log("HUB", f"Waiting for package: {package_name}")
    for _ in range(timeout):
        if driver.current_package == package_name:
            # print(f"Package detected: {package_name}")
            log("HUB", f"Package active: {package_name}")
            return True
        time.sleep(1)
    print(f"Timeout waiting for package {package_name}")
    return False


def wait_for_hub_screen(driver, timeout=20):
    # log("HUB", "Waiting for Hub UI (EditText)...")
    try:
        WebDriverWait(driver, timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "android.widget.EditText"))
        )
        print("Hub UI detected.")
    except TimeoutException:
        log("HUB", "Waiting for Hub UI.")


def click_all_apps(driver):

    log("HUB", "Opening All Apps")

    try:

        # --------------------------------------------------
        # WAIT FOR HUB HOME SCREEN
        # --------------------------------------------------

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(@text,'All Apps')]"
            ))
        )

        log("HUB", "Hub home screen loaded")

    except TimeoutException:

        log("HUB", "Hub home screen load timeout")

    # --------------------------------------------------
    # CLICK ALL APPS
    # --------------------------------------------------

    try:

        all_apps_xpath = (
            "//android.widget.TextView"
            "[@text='All Apps']"
        )

        all_apps = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                all_apps_xpath
            ))
        )

        all_apps.click()

        log("HUB", "'All Apps' clicked")

        time.sleep(3)

    except Exception as e:

        log("HUB", f"Failed to click All Apps: {e}")

def swipe_up(driver):
    size = driver.get_window_size()
    start_x = int(size['width'] * 0.5)
    start_y = int(size['height'] * 0.7)
    end_y = int(size['height'] * 0.3)
    duration_ms = 800

    # print("Swiping up...")
    log("HUB", "Swiping up")
    driver.swipe(start_x, start_y, start_x, end_y, duration_ms)
    time.sleep(2)


def update_or_install_apps(driver):
    # print("Starting app update/install process...")
    log("HUB", "Starting app update/install scan")
    processed_apps = set()
    last_screen_apps = set()
    max_scrolls = 30
    scrolls_done = 0

    while scrolls_done < max_scrolls:
        app_containers = driver.find_elements(
            By.XPATH,
            '//androidx.recyclerview.widget.RecyclerView[@resource-id="com.airwatch.androidagent:id/recyclerView"]/android.view.ViewGroup'
        )

        # print(f"Found {len(app_containers)} apps on scroll #{scrolls_done + 1}")
        log("HUB", f"Scroll #{scrolls_done + 1} — {len(app_containers)} apps found")
        current_screen_apps = set()

        for container in app_containers:
            try:
                app_name_elem = container.find_element(
                    By.ID, "com.airwatch.androidagent:id/txt_app_name"
                )
                app_name = app_name_elem.text.strip()
            except Exception:
                continue

            try:
                action_button = container.find_element(
                    By.ID, "com.airwatch.androidagent:id/button_app_action"
                )
                action_text = action_button.text.strip().upper()
            except NoSuchElementException:
                continue

            current_screen_apps.add(app_name)

            if (app_name, action_text) in processed_apps:
                continue

            if action_text in ["UPDATE", "INSTALL"]:
                try:
                    action_button.click()
                    # print(f"Clicked '{action_text}' for {app_name}")
                    log("HUB", f"{app_name} → {action_text} clicked")
                    processed_apps.add((app_name, action_text))
                    time.sleep(2)
                except Exception as e:
                    # print(f"Could not click {action_text} for {app_name}: {e}")
                    log("HUB", f"{app_name} → {action_text} (skipped)")
            else:
                # print(f"⏭ Skipped {app_name} with status '{action_text}'")
                log("HUB", f"{app_name} → {action_text} (skipped)")

        if current_screen_apps == last_screen_apps:
            # print("No new apps on this screen. Finished scrolling.")
            log("HUB", "No new apps detected — stopping scroll")
            break

        last_screen_apps = current_screen_apps

        try:
            swipe_up(driver)
            scrolls_done += 1
        except Exception as e:
            print(f"Swipe failed: {e}")
            break

    # print("Done processing all app updates/installations.")
    log("HUB", "App processing completed")

# --------------------------------------------------
# CLEANUP
# --------------------------------------------------

def clear_recent_apps_ui(serial):

    options = UiAutomator2Options()

    options.platform_name = "Android"
    options.device_name = serial
    options.no_reset = True

    driver = webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

    try:

        log("CLEANUP", "Opening Recent Apps")

        # Open Recents
        driver.press_keycode(187)

        time.sleep(3)

        log("CLEANUP", "Searching for Close All button")

        close_all_locators = [

            # Samsung
            (By.XPATH, "//*[contains(@text,'CLOSE ALL')]"),
            (By.XPATH, "//*[contains(@text,'Close all')]"),

            # Android
            (By.XPATH, "//*[contains(@text,'CLEAR ALL')]"),
            (By.XPATH, "//*[contains(@text,'Clear all')]"),

            # Accessibility
            (By.XPATH, "//*[contains(@content-desc,'Close all')]"),
            (By.XPATH, "//*[contains(@content-desc,'Clear all')]"),
        ]

        # --------------------------------------------------
        # NORMAL LOCATOR SEARCH
        # --------------------------------------------------

        for by, value in close_all_locators:

            try:

                close_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((by, value))
                )

                close_btn.click()

                log("CLEANUP", "Recent apps closed successfully")

                time.sleep(2)

                return

            except Exception:
                continue

        # --------------------------------------------------
        # COORDINATE FALLBACK
        # --------------------------------------------------

        log("CLEANUP", "Locator failed → trying coordinate tap")

        size = driver.get_window_size()

        width = size["width"]
        height = size["height"]

        x = int(width * 0.50)
        y = int(height * 0.92)

        finger = PointerInput(
            Interaction.TOUCH,
            "finger"
        )

        actions = ActionBuilder(
            driver,
            mouse=finger
        )

        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.2)
        actions.pointer_action.pointer_up()

        actions.perform()

        log("CLEANUP", "Recent apps closed using coordinate tap")

        time.sleep(2)

    except Exception as e:

        log("CLEANUP", f"Cleanup failed: {e}")

    finally:

        driver.quit()


# ====== Main Integration ======

def main():
    # print("Starting Full Integration Script")
    log("INIT", "Starting Hub automation")

    serial = get_connected_device_serial()
    if not serial:
        # print("No device connected.")
        log("DEVICE", "No device connected")
        return

    # print(f"Device Detected: {serial}")
    log(
        "DEVICE",
        f"Device detected: {display_serial}"
    )

    # Step 1: Hub app update/install (HubCode1)
    force_stop_and_launch_hub(serial)
    driver = get_driver_for_hub(serial)
    try:
        if wait_for_package(driver):
            wait_for_hub_screen(driver)
            swipe_up(driver)
            click_all_apps(driver)
            time.sleep(5)
            update_or_install_apps(driver)
    finally:
        driver.quit()
        # print("Hub app session closed.")
        log("HUB", "Hub session closed")

    clear_recent_apps_ui(device_serial)

    # print("All steps complete.")
    log("RESULT", "Hub automation completed successfully")


if __name__ == "__main__":
    main()
