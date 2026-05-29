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


def log(section, message):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{section:<14}] {message}")


# --------------------------------------------------
# Resolve device serial
# --------------------------------------------------
device_serial = os.environ.get("DEVICE_SERIAL") or get_connected_device_serial()

if not is_device_allowed(device_serial):
    raise RuntimeError(f"Unauthorized A4P device connected: {device_serial}")

device_name = get_device_name(device_serial)
# print(f"Authorized device detected: {device_name} ({device_serial})")
log("DEVICE", f"Authorized device detected: {device_name} ({device_serial})")

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

# --------------------------------------------------
# Launch Play Store BEFORE driver
# --------------------------------------------------
# force_stop_and_launch_playstore(device_serial)
# Clear cache before Play Store launch
clear_playstore_cache(device_serial)
# check_playstore_cache(device_serial)

# Launch Play Store
force_stop_and_launch_playstore(device_serial)
# driver = webdriver.Remote("http://localhost:4723", options=options)
driver = webdriver.Remote("http://127.0.0.1:4723", options=options)


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


# def open_profile_menu():
#     # print("Opening Play Store profile menu...")
#     log("PLAY STORE", "Opening Play Store profile menu")
#
#     wait_for_playstore_ready()
#
#     locators = [
#         (By.ACCESSIBILITY_ID, "Account"),
#         (By.ACCESSIBILITY_ID, "Profile"),
#         (By.ID, "com.android.vending:id/profile_avatar"),
#         (By.ID, "com.android.vending:id/avatar"),
#         (By.XPATH, "//android.widget.ImageView[contains(@content-desc,'Account')]"),
#         (By.XPATH, "//android.widget.ImageView[contains(@content-desc,'account')]"),
#     ]
#
#     for by, value in locators:
#         try:
#             el = WebDriverWait(driver, 6).until(
#                 EC.element_to_be_clickable((by, value))
#             )
#             el.click()
#             time.sleep(2)
#             # print("Profile menu opened")
#             log("PLAY STORE", "Profile menu opened")
#             return
#         except Exception:
#             continue
#
#     # --------------------------------------------------
#     # FINAL FALLBACK: COORDINATE TAP (IMAGE-CALIBRATED)
#     # --------------------------------------------------
#     # print("Fallback: coordinate tap (avatar)")
#
#     size = driver.get_window_size()
#     orientation = driver.orientation
#
#     # Tuned for Samsung tablet Play Store UI
#     if orientation == "LANDSCAPE":
#         x = int(size["width"] * 0.965)
#         y = int(size["height"] * 0.085)
#     else:
#         x = int(size["width"] * 0.94)
#         y = int(size["height"] * 0.07)
#
#     finger = PointerInput(interaction.POINTER_TOUCH, "finger")
#     actions = ActionBuilder(driver, mouse=finger)
#     actions.pointer_action.move_to_location(x, y)
#     actions.pointer_action.pointer_down()
#     actions.pointer_action.release()
#     actions.perform()
#
#     time.sleep(2)
#     # print("Profile menu opened (coordinate)")

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

# def update_installed_apps():
#     try:
#         # Open Manage apps & device
#         WebDriverWait(driver, 10).until(
#             EC.element_to_be_clickable(
#                 (
#                     By.XPATH,
#                     '//android.widget.TextView[@resource-id="com.android.vending:id/0_resource_name_obfuscated" and @text="Manage apps & device"]'
#                 )
#             )
#         ).click()
#
#         # Open Updates
#         WebDriverWait(driver, 10).until(
#             EC.element_to_be_clickable(
#                 (By.XPATH, "//android.widget.TextView[contains(@text,'Update')]")
#             )
#         ).click()
#
#         time.sleep(3)
#         log("UPDATES", "Updates screen opened")
#
#         try:
#             update_all_button = WebDriverWait(driver, 5).until(
#                 EC.element_to_be_clickable(
#                     (By.ANDROID_UIAUTOMATOR, 'new UiSelector().text("Update all")')
#                 )
#             )
#
#             update_all_button.click()
#             log("UPDATES", "Update All button clicked")
#
#         except:
#             log("UPDATES", "No updates available")
#
#     except Exception:
#         log("UPDATES", "Update check skipped")

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


def get_app_name_from_details():
    try:
        title = WebDriverWait(driver, 8).until(
            EC.presence_of_element_located((
                By.XPATH,
                "//android.widget.TextView[string-length(@text) > 10 and not(@clickable='true')]"
            ))
        )
        return title.text.strip()
    except Exception:
        return "UNKNOWN_APP"


def is_app_details_page():
    return bool(
        driver.find_elements(
            By.XPATH,
            "//*[contains(@text,'Install') or contains(@text,'Open')]"
        )
    )


def wait_for_apps_grid(timeout=30):
    """
    Wait until the first app tile (index 1 – Adobe) is visible.
    This guarantees the apps grid is fully loaded.
    """
    log("APPS GRID", "Waiting for apps grid to load")

    first_app_xpath = f"{APPS_BASE_XPATH}[1]"

    WebDriverWait(driver, timeout).until(
        EC.presence_of_element_located((By.XPATH, first_app_xpath))
    )

    log("APPS GRID", "Apps grid loaded")


def process_apps_using_compose_xpath():
    print("Processing apps using Compose index-based XPath")

    index = 1
    processed = set()

    while True:
        app_xpath = f"{APPS_BASE_XPATH}[{index}]"

        try:
            app = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, app_xpath))
            )

        except Exception:

            log("APPS GRID", "App not visible — scrolling")

            try:
                app = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.XPATH, app_xpath))
                )
            except Exception:
                # print("No more apps found — stopping")
                log("APPS GRID", "No more apps found — stopping")
                break

            # try:
            #     driver.find_element(
            #         By.ANDROID_UIAUTOMATOR,
            #         'new UiScrollable(new UiSelector().scrollable(true)).scrollForward(1)'
            #     )
            #
            #     time.sleep(2)
            #
            #     app = WebDriverWait(driver, 5).until(
            #         EC.presence_of_element_located((By.XPATH, app_xpath))
            #     )
            #
            # except Exception:
            #     log("APPS GRID", "No more apps found — stopping")
            #     break

        log("APPS GRID", f"Opening app index {index}")

        app.click()
        time.sleep(2)

        app_name = get_app_name_from_details()

        if app_name in processed:
            log("APPS GRID", f"{app_name} already processed — stopping")
            driver.back()
            break

        processed.add(app_name)

        if driver.find_elements(By.XPATH, "//*[contains(@text,'Install')]"):
            log("APPS GRID", f"{app_name} → Install initiated")
            driver.find_element(By.XPATH, "//*[contains(@text,'Install')]").click()
            time.sleep(3)

        elif driver.find_elements(By.XPATH, "//*[contains(@text,'Open')]"):
            log("APPS GRID", f"{app_name} → Installed")

        driver.back()
        time.sleep(2)
        index += 1

    log("RESULT", "Finished processing all apps")

def clear_recent_apps_ui(driver):
    try:
        # Open Recent Apps
        driver.press_keycode(187)
        time.sleep(2)

        # Click "Close all" / "Clear all"
        clear_all = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//android.widget.Button[contains(@text,'Close')] | //android.widget.Button[contains(@text,'Clear')]"
            ))
        )
        clear_all.click()

        print("Recent apps cleared via UI.")

    except Exception as e:
        print(f"Clear recent apps failed: {e}")


# ==================================================
# EXECUTION
# ==================================================
try:

    # STEP 1: Open profile
    open_profile_menu()

    # STEP 2: Scroll menu
    scroll_playstore_menu()

    # STEP 3: Check Play Store update
    update_play_store()

    # STEP 4: Clear recent apps
    clear_recent_apps_ui(driver)

    # STEP 5: Relaunch Play Store
    force_stop_and_launch_playstore(device_serial)
    log("PLAY STORE", "Play Store relaunched successfully")

    wait_for_playstore_ready()

    # STEP 6: Open profile again
    open_profile_menu()

    # STEP 7: Update installed apps
    update_installed_apps()

    # STEP 8: Detect "You're all set"
    handle_you_are_all_set_screen()

    # STEP 9: Clear recent apps
    clear_recent_apps_ui(driver)
    log("DEVICE", "Recent apps closed")

    # STEP 10: Open Play Store again
    force_stop_and_launch_playstore(device_serial)
    log("PLAY STORE", "Play Store opened again successfully")

    wait_for_playstore_ready()

    # STEP 11: Wait for apps grid
    wait_for_apps_grid()

    # STEP 12: Process apps
    process_apps_using_compose_xpath()

    # STEP 13: FINAL cleanup
    clear_recent_apps_ui(driver)
    log("DEVICE", "Recent apps closed (final cleanup)")

finally:
    driver.quit()
    log("RESULT", "Play Store automation completed successfully")