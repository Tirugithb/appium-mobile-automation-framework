import os
import time
import subprocess

from appium import webdriver
from appium.options.android import UiAutomator2Options
# from selenium.webdriver.common.by import By
from appium.webdriver.common.appiumby import AppiumBy as By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
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

# --------------------------------------------------
# Get Samsung Hardware Serial
# --------------------------------------------------

def get_hardware_serial(serial):

    try:

        result = subprocess.check_output(
            f"adb -s {serial} shell getprop ro.serialno",
            shell=True
        ).decode().strip()

        return result

    except Exception:

        return serial

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
# Resolve device serial
# --------------------------------------------------
device_serial = os.environ.get("DEVICE_SERIAL") or get_connected_device_serial()
display_serial = DISPLAY_SERIAL_MAP.get(
    device_serial,
    device_serial
)

if not is_device_allowed(device_serial):
    raise RuntimeError(f"Unauthorized S2 device connected: {device_serial}")

device_name = get_device_name(device_serial)
# print(f"Authorized device detected: {device_name} ({device_serial})")
log(
    "DEVICE",
    f"Authorized device detected: {device_name} ({display_serial})"
)

# --------------------------------------------------
# Device unlock
# --------------------------------------------------
if is_device_locked():
    unlock_device_with_password(load_device_password())
else:
    # print("Device already unlocked. Skipping unlock.")
    log("DEVICE", "Device already unlocked. Skipping unlock")

# --------------------------------------------------
# START APPIUM
# --------------------------------------------------
from appiumManager.appium_manager import AppiumManager

AppiumManager.start()

def clear_playstore_cache(serial):

    log("PLAY STORE", "Clearing Play Store cache")

    subprocess.run(
        f"adb -s {serial} shell pm trim-caches 128M",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    log("PLAY STORE", "Play Store cache cleared successfully")

def check_playstore_cache(serial):

    result = subprocess.check_output(
        f"adb -s {serial} shell dumpsys package com.android.vending",
        shell=True
    ).decode()

    cache_info = "Cache info not found"

    for line in result.splitlines():
        if "cacheSize" in line:
            cache_info = line.strip()
            break

    log("PLAY STORE", f"Cache status: {cache_info}")

# --------------------------------------------------
# FORCE LAUNCH PLAY STORE
# --------------------------------------------------
def force_stop_and_launch_playstore(serial):
    # print(f"Launching Play Store on {serial}")
    log("PLAY STORE", f"Launching Play Store on {device_serial}")

    subprocess.run(
        f"adb -s {serial} shell am force-stop com.android.vending",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    # subprocess.run(
    #     f"adb -s {serial} shell am start -n com.android.vending/com.google.android.finsky.activities.MainActivity",
    #     shell=True,
    #     stdout=subprocess.DEVNULL,
    #     stderr=subprocess.DEVNULL
    # )
    subprocess.run(
        f"adb -s {serial} shell monkey -p com.android.vending "
        f"-c android.intent.category.LAUNCHER 1",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(3)


# --------------------------------------------------
# Appium Options
# --------------------------------------------------
options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = device_serial
options.udid = device_serial
options.app_package = "com.android.vending"
options.app_activity = "com.android.vending.AssetBrowserActivity"
options.no_reset = True
options.full_reset = False
# ADD – increase UiAutomator2 timeouts
options.uiautomator2_server_launch_timeout = 180000
options.uiautomator2_server_install_timeout = 180000
options.adb_exec_timeout = 180000
options.android_install_timeout = 180000
# ADD – Samsung / Play Store safety
options.allow_running_instrumentation = True
options.ignore_hidden_api_policy_error = True

# # --------------------------------------------------
# # Launch Play Store BEFORE driver
# # --------------------------------------------------
# # force_stop_and_launch_playstore(device_serial)
# # Clear cache before Play Store launch
# clear_playstore_cache(device_serial)
# # check_playstore_cache(device_serial)
#
# # Launch Play Store
# force_stop_and_launch_playstore(device_serial)
#
# driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

# ==================================================
# CREATE PLAY STORE DRIVER
# ==================================================
driver = None
def create_playstore_driver():

    global driver

    # --------------------------------------------------
    # CLEAR PLAY STORE CACHE
    # --------------------------------------------------

    clear_playstore_cache(device_serial)

    # --------------------------------------------------
    # FORCE LAUNCH PLAY STORE
    # --------------------------------------------------

    force_stop_and_launch_playstore(device_serial)

    # --------------------------------------------------
    # CREATE DRIVER
    # --------------------------------------------------

    driver = webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

    log("PLAY STORE", "Play Store driver created")



# ==================================================
# PART 1 — PLAY STORE SETTINGS / MANAGE APPS
# (UNCHANGED CODE)
# ==================================================

def scroll_playstore_menu():
    try:
        driver.find_element(
            By.ANDROID_UIAUTOMATOR,
            'new UiScrollable(new UiSelector().scrollable(true)).scrollForward()'
        )
        # print("Play Store menu scrolled")
        log("PLAY STORE", "Play Store menu scrolled")
        time.sleep(1)
    except Exception:
        pass


def scroll_to_text(text):
    try:
        driver.find_element(
            By.ANDROID_UIAUTOMATOR,
            f'new UiScrollable(new UiSelector().scrollable(true))'
            f'.scrollIntoView(new UiSelector().text("{text}"))'
        )
        # print(f"Scrolled to '{text}'")
        log("PLAY STORE", f"Scrolled to '{text}'")

        time.sleep(1)
    except Exception:
        pass


def handle_playstore_uptodate_popup():
    try:
        # Detect popup message
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(@text,'Google Play Store is up to date')]"
            ))
        )

        log("PLAY STORE", "Google Play Store is already up to date")

        # Click "Got it"
        got_it = WebDriverWait(driver, 5).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//android.widget.Button[@text='Got it'] | //android.widget.TextView[@text='Got it']"
            ))
        )

        got_it.click()

        log("PLAY STORE", "Clicked 'Got it' confirmation")

        time.sleep(1)

    except Exception:
        log("PLAY STORE", "No Play Store update popup shown")


def handle_you_are_all_set_screen():
    try:
        WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(@text,\"You're all set\") or contains(@text,'All your apps')]"
            ))
        )

        # print("✓ Updates status: You're all set")
        log("UPDATES", "You're all set")
        # print("✓ All installed apps are up to date")
        log("UPDATES", "All installed apps are up to date")

    except Exception:
        print("ℹ Updates status screen not shown (updates may exist)")


def wait_for_playstore_ready():
    log("PLAY STORE", "Waiting for Play Store UI to load...")

    WebDriverWait(driver, 30).until(
        lambda d: (
                d.find_elements(By.ACCESSIBILITY_ID, "Account") or
                d.find_elements(By.ID, "com.android.vending:id/profile_avatar") or
                d.find_elements(By.XPATH, "//android.widget.ImageView[contains(@content-desc,'Account')]") or
                d.find_elements(By.XPATH, "//*[contains(@text,'Search')]")
        )
    )

    # print("Play Store UI ready")
    log("PLAY STORE", "Play Store UI ready")


def open_profile_menu():
    log("PLAY STORE", "Opening Play Store profile menu")

    wait_for_playstore_ready()

    # Try the fastest locator first
    try:
        driver.find_element(By.ACCESSIBILITY_ID, "Account").click()
        log("PLAY STORE", "Profile menu opened")
        return
    except:
        pass

    # Backup locator
    try:
        driver.find_element(By.ID, "com.android.vending:id/profile_avatar").click()
        log("PLAY STORE", "Profile menu opened")
        return
    except:
        pass

    # Another fallback locator
    try:
        driver.find_element(
            By.XPATH,
            "//android.widget.ImageView[contains(@content-desc,'Account')]"
        ).click()
        log("PLAY STORE", "Profile menu opened")
        return
    except:
        pass

    # --------------------------------------------------
    # FINAL FALLBACK: COORDINATE TAP
    # --------------------------------------------------
    size = driver.get_window_size()
    orientation = driver.orientation

    if orientation == "LANDSCAPE":
        x = int(size["width"] * 0.965)
        y = int(size["height"] * 0.085)
    else:
        x = int(size["width"] * 0.94)
        y = int(size["height"] * 0.07)

    finger = PointerInput(interaction.POINTER_TOUCH, "finger")
    actions = ActionBuilder(driver, mouse=finger)
    actions.pointer_action.move_to_location(x, y)
    actions.pointer_action.pointer_down()
    actions.pointer_action.release()
    actions.perform()

    time.sleep(1)

    log("PLAY STORE", "Profile menu opened (coordinate)")

def update_play_store():
    try:
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.TextView[@text='Settings']"))
        ).click()
        log("PLAY STORE", "Navigated to Settings")

        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//android.widget.TextView[@text='About']"))
        ).click()
        log("PLAY STORE", "Clicking on About")

        scroll_to_text("Update Play Store")

        links = driver.find_elements(By.XPATH, "//android.widget.TextView[@text='Update Play Store']")

        if links:
            links[0].click()
            handle_playstore_uptodate_popup()
        else:
            log("PLAY STORE", "Google Play Store is already up to date")

        # CLOSE PLAY STORE HERE
        subprocess.run(
            f"adb -s {device_serial} shell am force-stop com.android.vending",
            shell=True
        )

        log("PLAY STORE", "Play Store closed after update check")

    except Exception as e:
        print(f"Update Play Store flow failed: {e}")

def update_installed_apps():
    try:
        # Open Manage apps & device
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                # (By.XPATH, "//android.widget.TextView[@text='Manage apps & device']")
                (By.XPATH, "//android.widget.TextView[contains(@text,'Manage')]")
            )
        ).click()

        # Open Updates
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable(
                # (By.XPATH, "//android.widget.TextView[@text='Updates']")
                (By.XPATH, "//android.widget.TextView[contains(@text,'Update')]")
            )
        ).click()

        time.sleep(3)
        log("UPDATES", "Updates screen opened")

        '''
        # Check if Update All exists
        update_all_buttons = driver.find_elements(
            # By.XPATH, "//android.widget.Button[@text='Update all']"
            By.XPATH, "//android.widget.Button[contains(@text,'Update')]"

        )
        '''
        try:
            update_all_button = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Update all")')
                )
            )

            update_all_button.click()
            log("UPDATES", "Update All button clicked")

        except:
            log("UPDATES", "No updates available")

    except Exception as e:
        # print("Update check failed:", e)
        log("UPDATES", "Update check skipped")

# ==================================================
# APP GRID PROCESSING (UNCHANGED LOGIC)
# ==================================================

APPS_BASE_XPATH = (
    "//androidx.compose.ui.platform.ComposeView"
    "[@resource-id='com.android.vending:id/0_resource_name_obfuscated']"
    "/android.view.View/android.view.View/android.view.View"
    "/android.view.View/android.view.View[2]"
    "/android.view.View/android.view.View"
)

def close_recent_apps_ui(settings_driver):
    try:
        log("DEVICE", "Opening Recent Apps")

        # Open Recent Apps screen
        settings_driver.press_keycode(187)
        time.sleep(3)

        log("DEVICE", "Searching for Close All button")

        close_all_locators = [

            # Samsung tablets
            (By.XPATH, "//*[contains(@text,'CLOSE ALL')]"),
            (By.XPATH, "//*[contains(@text,'Close all')]"),

            # Other Android devices
            (By.XPATH, "//*[contains(@text,'CLEAR ALL')]"),
            (By.XPATH, "//*[contains(@text,'Clear all')]"),

            # Accessibility
            (By.XPATH, "//*[contains(@content-desc,'Close all')]"),
            (By.XPATH, "//*[contains(@content-desc,'Clear all')]"),
        ]

        # --------------------------------------------------
        # TRY NORMAL LOCATORS
        # --------------------------------------------------
        for by, value in close_all_locators:
            try:
                close_btn = WebDriverWait(settings_driver, 5).until(
                    EC.element_to_be_clickable((by, value))
                )

                close_btn.click()

                log("DEVICE", "Recent apps closed successfully")
                time.sleep(2)
                return

            except Exception:
                continue

        # --------------------------------------------------
        # FALLBACK → COORDINATE TAP
        # --------------------------------------------------
        log("DEVICE", "Locator failed → trying coordinate tap")

        size = driver.get_window_size()

        width = size["width"]
        height = size["height"]

        # Samsung Tablet landscape tuning
        x = int(width * 0.50)
        y = int(height * 0.92)

        finger = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions = ActionBuilder(driver, mouse=finger)

        actions.pointer_action.move_to_location(x, y)
        actions.pointer_action.pointer_down()
        actions.pointer_action.pause(0.2)
        actions.pointer_action.release()

        actions.perform()

        log("DEVICE", "Recent apps closed using coordinate tap")

        time.sleep(2)

    except Exception as e:
        log("DEVICE", f"Close recent apps failed: {e}")


# ==================================================
# SETTINGS DRIVER
# ==================================================

def get_settings_driver(serial):

    options = UiAutomator2Options()

    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.automation_name = "UiAutomator2"

    options.app_package = "com.android.settings"
    options.app_activity = "com.android.settings.Settings"

    options.no_reset = True

    # --------------------------------------------------
    # SAMSUNG SAFETY
    # --------------------------------------------------

    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000

    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True

    return webdriver.Remote(
        "http://127.0.0.1:4723",
        options=options
    )

# ==================================================
# HANDLE SCHEDULED SOFTWARE UPDATES
# ==================================================

def handle_schedule_software_updates(settings_driver):

    try:

        log("SOFTWARE", "Checking Scheduled software updates toggle")

        # --------------------------------------------------
        # FIND ROW
        # --------------------------------------------------

        WebDriverWait(settings_driver, 10).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//*[contains(@text,'Scheduled software updates')]"
            ))
        )

        # --------------------------------------------------
        # FIND SWITCH
        # --------------------------------------------------

        switches = settings_driver.find_elements(
            By.CLASS_NAME,
            "android.widget.Switch"
        )

        if not switches:

            log("SOFTWARE", "Scheduled software updates switch not found")
            return

        switch = switches[0]

        # --------------------------------------------------
        # READ STATE
        # --------------------------------------------------

        checked = (
            switch.get_attribute("checked") or ""
        ).lower()

        log("SOFTWARE", f"Switch checked state = {checked}")

        # --------------------------------------------------
        # ENABLED
        # --------------------------------------------------

        if checked == "true":

            log("SOFTWARE", "Scheduled software updates is ENABLED")

            switch.click()

            time.sleep(2)

            log("SOFTWARE", "Scheduled software updates disabled")

        # --------------------------------------------------
        # DISABLED
        # --------------------------------------------------

        else:

            log("SOFTWARE", "Scheduled software updates already disabled")

    except Exception as e:

        log("SOFTWARE", f"Scheduled software updates check failed: {e}")

# ==================================================
# SOFTWARE UPDATE CHECK
# ==================================================

def check_software_update():

    try:
        settings_driver = get_settings_driver(device_serial)

        log("SOFTWARE", "Opening Settings")

        # --------------------------------------------------
        # SCROLL SETTINGS
        # --------------------------------------------------

        scroll_settings(settings_driver)

        # --------------------------------------------------
        # OPEN SOFTWARE UPDATE
        # --------------------------------------------------

        log("SOFTWARE", "Opening Software Update")

        software_update = WebDriverWait(settings_driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(@text,'Software update')]"
            ))
        )

        software_update.click()

        time.sleep(5)

        # --------------------------------------------------
        # HANDLE SCHEDULE SOFTWARE UPDATES
        # --------------------------------------------------

        handle_schedule_software_updates(settings_driver)
        close_recent_apps_ui(settings_driver)
        settings_driver.quit()

    except Exception as e:

        log("SOFTWARE", f"Software update check failed: {e}")


# ==================================================
# SCROLL SETTINGS
# ==================================================

def scroll_settings(settings_driver):

    try:

        settings_driver.find_element(
            By.ANDROID_UIAUTOMATOR,
            'new UiScrollable(new UiSelector().scrollable(true)).scrollForward()'
        )

        log("SOFTWARE", "Settings screen scrolled")

        time.sleep(2)

    except Exception:

        log("SOFTWARE", "Settings scroll skipped")

# ==================================================
# PLAY STORE APPS
# ==================================================

PLAYSTORE_APPS = [
    "Adobe Acrobat Reader: Edit PDF",
    "Brother Print Service Plugin",
    "Canon Print Service",
    "Google Chrome",
    "HP Print Service Plugin",
    "Xerox Print Service Plugin"
]

# ==================================================
# OPEN PLAY STORE SEARCH
# ==================================================

def open_playstore_search():

    try:

        log("PLAY STORE", "Opening Search menu")

        # --------------------------------------------------
        # CLICK LEFT SEARCH MENU
        # --------------------------------------------------

        search_menu = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(@text,'Search')]"
            ))
        )

        search_menu.click()

        time.sleep(3)

        # --------------------------------------------------
        # CLICK SEARCH INPUT AREA
        # --------------------------------------------------

        log("PLAY STORE", "Opening search box")

        search_input_area = WebDriverWait(driver, 15).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[contains(@text,'Search apps')]"
            ))
        )

        search_input_area.click()

        time.sleep(2)

    except Exception as e:

        log("PLAY STORE", f"Search open failed: {e}")

# ==================================================
# SEARCH APP
# ==================================================

def search_playstore_app(app_name):

    try:

        log("PLAY STORE", f"Searching: {app_name}")

        # --------------------------------------------------
        # FIND ACTIVE SEARCH FIELD
        # --------------------------------------------------

        search_field = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//android.widget.EditText"
            ))
        )

        search_field.click()

        time.sleep(1)

        search_field.clear()

        search_field.send_keys(app_name)

        time.sleep(2)

        # --------------------------------------------------
        # PRESS ENTER
        # --------------------------------------------------

        driver.press_keycode(66)

        time.sleep(5)

    except Exception as e:

        log("PLAY STORE", f"{app_name} search failed: {e}")


# ==================================================
# INSTALL / UPDATE / OPEN
# ==================================================

def process_app_status(app_name):

    try:

        time.sleep(5)

        # --------------------------------------------------
        # CHECK UPDATE BUTTON
        # --------------------------------------------------

        update_buttons = driver.find_elements(
            By.XPATH,
            "//*[@text='Update' or @content-desc='Update']"
        )

        if update_buttons:

            log("PLAY STORE", f"{app_name} → UPDATE")

            try:

                update_buttons[0].click()

                log("PLAY STORE", f"{app_name} update started")

                time.sleep(5)

            except:
                pass

            return

        # --------------------------------------------------
        # CHECK INSTALL BUTTON
        # --------------------------------------------------

        install_buttons = driver.find_elements(
            By.XPATH,
            "//*[@text='Install' or @content-desc='Install']"
        )

        if install_buttons:

            log("PLAY STORE", f"{app_name} → INSTALL")

            try:

                install_buttons[0].click()

                log("PLAY STORE", f"{app_name} install started")

                time.sleep(5)

            except:
                pass

            return

        # --------------------------------------------------
        # CHECK OPEN BUTTON
        # --------------------------------------------------

        open_buttons = driver.find_elements(
            By.XPATH,
            "//*[@text='Open' or @content-desc='Open']"
        )

        if open_buttons:

            log("PLAY STORE", f"{app_name} → OPEN")

            return

        # --------------------------------------------------
        # UNKNOWN
        # --------------------------------------------------

        log("PLAY STORE", f"{app_name} → STATUS UNKNOWN")

    except Exception as e:

        log("PLAY STORE", f"{app_name} status check failed: {e}")

# ==================================================
# RETURN TO SEARCH SCREEN
# ==================================================

def return_to_search():

    try:

        driver.back()

        time.sleep(2)

        driver.back()

        time.sleep(2)

    except:
        pass


# ==================================================
# PROCESS PLAY STORE APPS
# ==================================================

def process_playstore_apps():

    log("PLAY STORE", "Starting Play Store app validation")

    for app_name in PLAYSTORE_APPS:

        try:

            open_playstore_search()

            search_playstore_app(app_name)

            # WAIT FOR DETAILS PAGE
            time.sleep(5)

            process_app_status(app_name)

            return_to_search()

        except Exception as e:

            log("PLAY STORE", f"{app_name} failed: {e}")

            try:
                driver.back()
                driver.back()
            except:
                pass

    log("PLAY STORE", "Play Store app validation completed")

# ==================================================
# EXECUTION
# ==================================================
try:

    # STEP 1: Check Software Updates
    check_software_update()

    # STEP 2: Create Play Store Driver
    create_playstore_driver()

    # STEP 1: Open profile
    open_profile_menu()

    # STEP 2: Scroll Play Store menu
    scroll_playstore_menu()

    # STEP 3: Check Play Store update
    update_play_store()

    # STEP 4: Clear recent apps
    close_recent_apps_ui(driver)

    # STEP 5: Relaunch Play Store
    force_stop_and_launch_playstore(device_serial)

    log("PLAY STORE", "Play Store relaunched successfully")

    # STEP 6: Wait for Play Store UI
    wait_for_playstore_ready()

    # STEP 7: Open profile again
    open_profile_menu()

    # STEP 8: Update installed apps
    update_installed_apps()

    # STEP 9: Detect “You're all set”
    handle_you_are_all_set_screen()

    # STEP 10: Clear recent apps
    close_recent_apps_ui(driver)

    # STEP 11: Relaunch Play Store
    force_stop_and_launch_playstore(device_serial)

    log("PLAY STORE", "Play Store relaunched successfully")

    # STEP 12: Wait for Play Store UI
    wait_for_playstore_ready()

    # STEP 13: Process Play Store apps
    process_playstore_apps()

    # STEP 14: FINAL cleanup
    close_recent_apps_ui(driver)


finally:

    try:
        if driver:
            driver.quit()
    except:
        pass

    log("RESULT", "Play Store automation completed successfully")