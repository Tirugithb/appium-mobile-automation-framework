import os
import sys
import time
import subprocess
from appium import webdriver
from appium.options.android import UiAutomator2Options
from datetime import datetime
from selenium.webdriver.common.actions.action_builder import ActionBuilder
import shutil
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
SCRIPT_START_TIME = time.time()
SCREENSHOT_COUNT = 0



# # BASE_SCREENSHOT_DIR = r"C:\Users\SVC-Systems-TestPC\Log_Screenshot_files"
# BASE_SCREENSHOT_DIR = r"C:\Users\mandat3\OneDrive - Medtronic PLC\Desktop\Appium\App Ver Auto Fill"
#
# # Delete old Run_* folders
# for folder in os.listdir(BASE_SCREENSHOT_DIR):
#     if folder.startswith("Run_"):
#         full_path = os.path.join(BASE_SCREENSHOT_DIR, folder)
#         if os.path.isdir(full_path):
#             shutil.rmtree(full_path)
#
# # Create only latest run folder
# RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
# RUN_SCREENSHOT_DIR = os.path.join(BASE_SCREENSHOT_DIR, f"Run_{RUN_TS}")
#
# os.makedirs(RUN_SCREENSHOT_DIR, exist_ok=True)

# BASE_SCREENSHOT_DIR = r"C:\Users\SVC-Systems-TestPC\Log_Screenshot_files"
BASE_SCREENSHOT_DIR = r"C:\Users\mandat3\OneDrive - Medtronic PLC\Desktop\Appium\App Ver Auto Fill"

# Create only latest run folder
RUN_TS = datetime.now().strftime("%Y%m%d_%H%M%S")
RUN_SCREENSHOT_DIR = os.path.join(BASE_SCREENSHOT_DIR, f"Run_{RUN_TS}")

os.makedirs(RUN_SCREENSHOT_DIR, exist_ok=True)

# --------------------------------------------------
# Fix Python path for your folder structure
# --------------------------------------------------

PROJECT_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "Samsung_S2_Tablet_Automation")
)

sys.path.append(PROJECT_ROOT)

# --------------------------------------------------
# Core imports
# --------------------------------------------------

from core.device_registry import is_device_allowed, get_device_name
from core.adb_utils import (
    get_connected_device_serial,
    is_device_locked,
    unlock_device_with_password
)
from core.config_loader import load_device_password
from appiumManager.appium_manager import AppiumManager

def log(section, message):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{section:<12}] {message}")

def perform_swipe(driver, start_x, start_y, end_x, end_y, duration=150):

    actions = ActionBuilder(driver)

    actions.pointer_action.move_to_location(start_x, start_y)
    actions.pointer_action.pointer_down()
    actions.pointer_action.pause(0.02)  # fast swipe
    actions.pointer_action.move_to_location(end_x, end_y)
    actions.pointer_action.release()

    actions.perform()
    time.sleep(0.8)

def print_test_summary(opened, failed, page_count):

    runtime = round(time.time() - SCRIPT_START_TIME, 2)

    print("\n")
    print("===================================================")
    print("                 TEST EXECUTION SUMMARY")
    print("===================================================")

    print(f"Device           : {device_name}")
    print(f"Apps Verified    : {len(opened)}")
    print(f"Apps Failed      : {len(failed)}")
    print(f"App Pages Found  : {page_count}")
    global SCREENSHOT_COUNT
    # print(f"DEBUG SCREENSHOT COUNT = {SCREENSHOT_COUNT}")
    print(f"Screenshots Taken: {SCREENSHOT_COUNT}")
    print(f"Runtime          : {runtime} seconds")

    if failed:
        print("Result           : FAIL")
    else:
        print("Result           : PASS")

    print("===================================================")

# --------------------------------------------------
# Screenshot function
# --------------------------------------------------
def capture_recent_apps_screenshot():

    log("TABLET", "Opening Recent Apps view")

    # Open Recent Apps screen
    driver.press_keycode(187)   # KEYCODE_APP_SWITCH
    time.sleep(1.2)

    # screenshot_dir = r"C:\Users\mandat3\OneDrive - Medtronic PLC\Desktop\Appium\ThirdParty_Screenshots"
    screenshot_dir = RUN_SCREENSHOT_DIR

    # os.makedirs(screenshot_dir, exist_ok=True)

    screenshot_path = os.path.join(
        screenshot_dir,
        "Background_Apps.png"
    )

    driver.save_screenshot(screenshot_path)
    global SCREENSHOT_COUNT
    SCREENSHOT_COUNT += 1

    log("SCREENSHOT", f"Background Apps screenshot saved: {screenshot_path}")

    # Return to Home
    driver.press_keycode(3)

def open_app_drawer():

    driver.press_keycode(3)
    time.sleep(1)

    size = driver.get_window_size()

    # simple swipe up (this was working earlier)
    perform_swipe(
        driver,
        int(size["width"] * 0.5),
        int(size["height"] * 0.9),
        int(size["width"] * 0.5),
        int(size["height"] * 0.2),
        150
    )

    time.sleep(2)

    # simple validation
    apps = driver.find_elements("xpath", "//android.widget.TextView")

    if len(apps) > 5:
        log("SUCCESS", "App Drawer opened")
        return True

    log("ERROR", "App Drawer not opened")
    return False


def capture_app_pages():

    log("TABLET", "Opening App Drawer")

    size = driver.get_window_size()
    time.sleep(2)

    if not open_app_drawer():
        log("FATAL", "Cannot proceed without App Drawer")
        return 0

    time.sleep(1.5)

    # go to first page
    go_to_first_app_page()

    screenshot_dir = RUN_SCREENSHOT_DIR
    os.makedirs(screenshot_dir, exist_ok=True)

    page = 1
    previous_apps = set()
    MAX_PAGES = 5

    while True:

        elements = driver.find_elements("xpath", "//android.widget.TextView")
        current_apps = tuple(sorted([e.text for e in elements if e.text.strip()]))

        if current_apps == previous_apps:
            break

        previous_apps = current_apps

        screenshot_path = os.path.join(
            screenshot_dir,
            f"Apps_Installed_{page}.png"
        )

        driver.save_screenshot(screenshot_path)
        global SCREENSHOT_COUNT
        SCREENSHOT_COUNT += 1
        log("SCREENSHOT", f"Saved {screenshot_path}")

        # FIXED horizontal swipe
        y = int(size["height"] * 0.5)

        before = driver.page_source

        perform_swipe(
            driver,
            int(size["width"] * 0.8),
            y,
            int(size["width"] * 0.2),
            y,
            150
        )

        time.sleep(1)

        after = driver.page_source

        # retry if swipe failed
        if before == after:
            log("RETRY", "Swipe failed retrying")

            perform_swipe(
                driver,
                int(size["width"] * 0.8),
                y,
                int(size["width"] * 0.2),
                y,
                150
            )
            time.sleep(1)

        page += 1

        if page > MAX_PAGES:
            log("WARNING", "Max page limit reached")
            break

    page_count = page - 1
    log("RESULT", f"Total App Pages Captured: {page_count}")

    driver.press_keycode(3)

    return page_count


def go_to_first_app_page():

    size = driver.get_window_size()

    for _ in range(5):  # increased attempts

        before = driver.page_source

        perform_swipe(
            driver,
            int(size["width"] * 0.10),
            int(size["height"] * 0.5),
            int(size["width"] * 0.90),
            int(size["height"] * 0.5),
            200
        )

        time.sleep(1)

        after = driver.page_source

        # stop if already at first page
        if before == after:
            break

# --------------------------------------------------
# Resolve device
# --------------------------------------------------

device_serial = os.environ.get("DEVICE_SERIAL") or get_connected_device_serial()

if not is_device_allowed(device_serial):
    raise RuntimeError(f"Unauthorized device: {device_serial}")

device_name = get_device_name(device_serial)

log("DEVICE", f"Authorized device detected: {device_name} ({device_serial})")


# --------------------------------------------------
# Unlock device
# --------------------------------------------------

if is_device_locked():
    unlock_device_with_password(load_device_password())
else:
    log("DEVICE", "Device already unlocked")


# --------------------------------------------------
# Start Appium
# --------------------------------------------------

AppiumManager.start()
log("APPIUM", "Appium server started")


# --------------------------------------------------
# Appium driver
# --------------------------------------------------

options = UiAutomator2Options()
options.platform_name = "Android"
options.automation_name = "UiAutomator2"
options.device_name = device_serial
options.udid = device_serial
options.no_reset = True

driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

PERMISSION_APPS = {
        "Adobe Acrobat": "com.adobe.reader"
        # "Xerox Print Service": "com.xerox.printservice",
        # "Epson iPrint": "epson.print",
        # "HP Print Service Plugin": "com.hp.android.printservice",
        # "Content": "com.airwatch.contentlocker",
        # "Gallery": "com.sec.android.gallery3d",
        # "Web": "com.airwatch.browser",
        # "Mopria Print Service": "org.mopria.printplugin",
}

NON_PERMISSION_APPS = {
    "Brother Print Service Plugin": "com.brother.printservice"
    # "Calculator": "com.sec.android.app.popupcalculator",
    # "Camera": "com.sec.android.app.camera",
    # "Canon Print Service": "jp.co.canon.android.printservice.plugin",
    # "Clock": "com.sec.android.app.clockpackage",
    # "Google Play Store": "com.android.vending",
    # "Hub": "com.airwatch.androidagent",
    # "My Files": "com.sec.android.app.myfiles"
    # # "Chrome"
    # # "Samsung Print Service Plugin"
    # # "Zoom"
}

# --------------------------------------------------
# Launch apps
# --------------------------------------------------
def open_app_and_capture(name, package, screenshot_name):

    try:
        log("APP", f"Opening {name}")

        # Open app
        driver.activate_app(package)
        time.sleep(3)  # wait for app UI

        # Create screenshot path with custom name
        screenshot_path = os.path.join(
            RUN_SCREENSHOT_DIR,
            f"{screenshot_name}.png"
        )

        # Take screenshot
        driver.save_screenshot(screenshot_path)
        global SCREENSHOT_COUNT
        SCREENSHOT_COUNT += 1

        log("SCREENSHOT", f"{name} screenshot saved: {screenshot_path}")

        # Go back to Home
        driver.press_keycode(3)
        time.sleep(1)

    except Exception as e:
        log("ERROR", f"{name} failed: {e}")

def handle_all_popups(driver, timeout=6):

    end_time = time.time() + timeout

    while time.time() < end_time:

        try:
            #  Step 1: Check if dialog exists
            dialogs = driver.find_elements("xpath", "//android.app.Dialog")

            if not dialogs:
                return False  # No popup  EXIT

            #  Step 2: Get buttons inside dialog ONLY
            buttons = driver.find_elements(
                "xpath",
                "//android.app.Dialog//android.widget.Button"
            )

            if not buttons:
                return False

            texts = [btn.text.lower() for btn in buttons]

            # Case 1: System permission
            for btn in buttons:
                if any(k in btn.text.lower() for k in ["allow", "while using", "only this time"]):
                    log("POPUP", f"Clicking ALLOW: {btn.text}")
                    btn.click()
                    return True

            #  Case 2: Not Now
            for btn in buttons:
                if "not now" in btn.text.lower():
                    log("POPUP", "Clicking NOT NOW")
                    btn.click()
                    return True

            # Case 3: OK button
            if len(buttons) >= 2:
                ok_btn = buttons[-1]
                log("POPUP", f"Clicking OK: {ok_btn.text}")
                ok_btn.click()
                return True

        except Exception:
            pass

        time.sleep(1)

    return False

def handle_epson_full_flow(driver, max_attempts=10):

    log("EPSON", "Starting smart Epson handling")

    for _ in range(max_attempts):

        handled = False

        # STEP 1: Terms  Agree
        if is_terms_screen(driver):
            if smart_click(driver, ["agree"], exact=True):
                handled = True
                time.sleep(2)
                continue
            else:
                log("EPSON", "Agree not found")
                break

        # STEP 2: Exit if main screen
        if "printer is not selected" in driver.page_source.lower():
            log("EPSON", "Main screen reached  exiting")
            break

        # STEP 3: Flow
        if smart_click(driver, ["ok"], exact=True):
            handled = True

        elif smart_click(driver, ["allow"], exact=True) or \
             smart_click(driver, ["while using", "only this time"]):
            handled = True

        elif smart_click(driver, ["next"], exact=True):
            handled = True

        if not handled:
            log("EPSON", "No more steps  exiting")
            break

        time.sleep(2)

    log("EPSON", "Flow completed")

def is_terms_screen(driver):
    try:
        texts = driver.find_elements("xpath", "//android.widget.TextView")
        all_texts = " ".join([el.text.lower() for el in texts])

        if "terms of use" in all_texts or "license agreement" in all_texts:
            return True

    except:
        pass

    return False

# log("CONTENT", "Waiting for onboarding screen")
# time.sleep(10)

def wait_for_app_screen(driver, timeout=20):

    log("WAIT", "Waiting for App screen to load")

    start = time.time()

    while time.time() - start < timeout:
        try:
            src = driver.page_source
            if src:
                log("WAIT", "Screen loaded")
                return True
        except:
            pass

        time.sleep(1)

    log("WAIT", "Timeout waiting for screen")
    return False   # VERY IMPORTANT

def smart_click(driver, keywords, exact=False, timeout=5):

    end_time = time.time() + timeout

    while time.time() < end_time:
        try:
            elements = driver.find_elements("xpath", "//*")

            for el in elements:
                text = (el.text or "").lower().strip()

                if not text:
                    continue

                if exact:
                    if text in keywords:
                        log("ACTION", f"Clicking EXACT: {el.text}")
                        el.click()
                        time.sleep(2)
                        return True
                else:
                    if any(k in text for k in keywords):
                        log("ACTION", f"Clicking: {el.text}")
                        el.click()
                        time.sleep(2)
                        return True

        except:
            pass

        time.sleep(1)

    return False

def handle_xerox_flow(driver, max_attempts=8):

    log("XEROX", "Starting Xerox handling")

    for i in range(max_attempts):

        time.sleep(1)
        handled = False
        page = driver.page_source.lower()

        log("XEROX", "Checking screen...")

        # --------------------------------------------------
        #  STEP 1: Notification popup (HIGHEST PRIORITY)
        # --------------------------------------------------
        try:
            allow_btn = driver.find_element(
                "id",
                "com.android.permissioncontroller:id/permission_allow_button"
            )
            log("XEROX", "Notification popup  clicking Allow (resource-id)")
            allow_btn.click()

            handled = True
            time.sleep(2)
            continue

        except:
            try:
                allow_btn = driver.find_element(
                    "xpath",
                    "//*[@text='Allow' or @content-desc='Allow']"
                )
                log("XEROX", "Notification popup  clicking Allow (XPath)")
                allow_btn.click()

                handled = True
                time.sleep(2)
                continue

            except:
                pass

        # --------------------------------------------------
        #  STEP 2: Upgrade popup  CANCEL
        # --------------------------------------------------
        if "xps upgrade coming soon" in page:
            log("XEROX", "Upgrade popup  clicking CANCEL")

            if smart_click(driver, ["cancel"], exact=True):
                handled = True
                time.sleep(2)
                continue

        # --------------------------------------------------
        #  STEP 3: Full screen permission popup
        # --------------------------------------------------
        if "full screen notification" in page:
            log("XEROX", "Full screen popup  going to settings")

            if smart_click(driver, ["go to app info"]):
                handled = True
                time.sleep(2)
                continue

        # --------------------------------------------------
        #  STEP 4: Settings screen  enable toggle
        # --------------------------------------------------
        if "full screen alerts" in page:
            log("XEROX", "Enabling full screen alerts")

            if enable_xerox_full_screen_alert(driver):
                handled = True

                #  Go back to app
                for _ in range(2):
                    driver.press_keycode(4)
                    time.sleep(2)

                continue

        # --------------------------------------------------
        #  STEP 5: Cancel fallback
        # --------------------------------------------------
        if smart_click(driver, ["cancel"], exact=True):
            log("XEROX", "Fallback  clicking CANCEL")
            handled = True
            time.sleep(2)
            continue

        # --------------------------------------------------
        #  STEP 6: OK fallback
        # --------------------------------------------------
        if smart_click(driver, ["ok"], exact=True):
            log("XEROX", "Fallback  clicking OK")
            handled = True
            time.sleep(2)
            continue

        # --------------------------------------------------
        #  STEP 7: MAIN SCREEN DETECTION (FINAL POSITION)
        # --------------------------------------------------
        if "find a printer" in page or "discover printers" in page:
            log("XEROX", "Main screen detected  exiting")
            break

        # --------------------------------------------------
        #  STEP 8: EXIT CONTROL
        # --------------------------------------------------
        if not handled:

            if i > 3:
                log("XEROX", "No popup detected  exiting early")
                break

            log("XEROX", "No action  retrying...")
            time.sleep(2)
            continue

        time.sleep(2)

    log("XEROX", "Flow completed")


def enable_xerox_full_screen_alert(driver):
    try:
        log("XEROX", "Enabling Full Screen Alert")

        # Get correct row
        row = driver.find_element(
            "xpath",
            "//android.widget.TextView[contains(@text,'Xerox Print Service')]"
            "/ancestor::android.view.ViewGroup[1]"
        )

        loc = row.location
        size = row.size

        log("DEBUG", f"Row location={loc}, size={size}")

        # Tap on toggle area (RIGHT side)
        x = loc['x'] + int(size['width'] * 0.92)
        y = loc['y'] + int(size['height'] * 0.5)

        log("XEROX", f"Tapping at ({x},{y})")

        driver.tap([(x, y)])

        time.sleep(3)

        # VERIFY toggle state
        try:
            toggle = driver.find_element(
                "xpath",
                "//android.widget.TextView[contains(@text,'Xerox Print Service')]"
                "/following::android.widget.Switch[1]"
            )

            state = toggle.get_attribute("checked")
            log("XEROX", f"Toggle state after click: {state}")

        except:
            log("XEROX", "Toggle verification skipped")

        return True

    except Exception as e:
        log("ERROR", f"Toggle failed: {e}")
        return False

def handle_hp_flow(driver):

    log("HP", "Starting HP setup flow")

    try:

        time.sleep(5)

        # --------------------------------------------------
        # Select first checkbox
        # --------------------------------------------------
        checkbox1 = driver.find_element(
            "xpath",
            "(//android.widget.CheckBox)[1]"
        )

        checkbox1.click()

        log("HP", "First checkbox selected")

        time.sleep(2)

        # --------------------------------------------------
        # Select second checkbox
        # --------------------------------------------------
        checkbox2 = driver.find_element(
            "xpath",
            "(//android.widget.CheckBox)[2]"
        )

        checkbox2.click()

        log("HP", "Second checkbox selected")

        time.sleep(2)

        # --------------------------------------------------
        # Click START
        # --------------------------------------------------
        start_btn = driver.find_element(
            "xpath",
            "//*[@text='Start']"
        )

        start_btn.click()

        log("HP", "START clicked")

        time.sleep(5)

        log("HP", "HP flow completed")

    except Exception as e:

        log("HP", f"HP flow failed: {e}")

def handle_content_flow(driver):

    log("CONTENT", "Starting Content setup flow")

    wait = WebDriverWait(driver, 60)

    try:

        # --------------------------------------------------
        # WAIT FOR CONTENT APP TO FULLY LOAD
        # --------------------------------------------------
        log("CONTENT", "Waiting for onboarding screen")

        understand_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[@text='I UNDERSTAND']")
            )
        )

        # --------------------------------------------------
        # STEP 1 : I UNDERSTAND
        # --------------------------------------------------
        understand_btn.click()

        log("CONTENT", "Clicked I UNDERSTAND")

        time.sleep(5)

        # --------------------------------------------------
        # STEP 2 : I AGREE
        # --------------------------------------------------
        agree_btn = wait.until(
            EC.element_to_be_clickable(
                (By.XPATH, "//*[@text='I AGREE']")
            )
        )

        agree_btn.click()

        log("CONTENT", "Clicked I AGREE")

        time.sleep(5)

        # --------------------------------------------------
        # STEP 3 : Keep clicking NEXT
        # --------------------------------------------------
        for _ in range(6):

            try:

                next_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable(
                        (By.XPATH, "//*[@text='NEXT']")
                    )
                )

                next_btn.click()

                log("CONTENT", "Clicked NEXT")

                time.sleep(3)

            except:

                log("CONTENT", "No more NEXT screens")

                break

        # --------------------------------------------------
        # STEP 4 : GOT IT
        # --------------------------------------------------
        try:

            got_it_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[@text='GOT IT']")
                )
            )

            got_it_btn.click()

            log("CONTENT", "Clicked GOT IT")

            time.sleep(5)

        except:

            log("CONTENT", "GOT IT button not found")

        log("CONTENT", "Content flow completed")

    except Exception as e:

        log("CONTENT", f"Content flow failed: {e}")

def handle_gallery_flow(driver):

    log("GALLERY", "Starting Gallery permission flow")

    try:

        time.sleep(5)

        # --------------------------------------------------
        # LOCATION POPUP : Allow
        # --------------------------------------------------
        allow_btn = driver.find_element(
            "xpath",
            "//*[@text='Allow']"
        )

        allow_btn.click()

        log("GALLERY", "Clicked Allow")

        time.sleep(3)

        log("GALLERY", "Gallery flow completed")

    except Exception as e:

        log("GALLERY", f"Gallery flow failed: {e}")

def handle_web_flow(driver):

    log("WEB", "Starting Web app setup flow")

    wait = WebDriverWait(driver, 60)

    try:

        # --------------------------------------------------
        # WAIT FOR APP LOAD
        # --------------------------------------------------
        log("WEB", "Waiting for onboarding screen")

        time.sleep(10)

        # --------------------------------------------------
        # STEP 1 : I UNDERSTAND
        # --------------------------------------------------
        try:

            understand_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[@text='I UNDERSTAND']")
                )
            )

            understand_btn.click()

            log("WEB", "Clicked I UNDERSTAND")

            time.sleep(5)

        except:
            log("WEB", "I UNDERSTAND not found")

        # --------------------------------------------------
        # STEP 2 : I AGREE
        # --------------------------------------------------
        try:

            agree_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//*[@text='I AGREE']")
                )
            )

            agree_btn.click()

            log("WEB", "Clicked I AGREE")

            time.sleep(5)

        except:
            log("WEB", "I AGREE not found")


        log("WEB", "Web app flow completed")

    except Exception as e:

        log("WEB", f"Web flow failed: {e}")

def handle_mopria_flow(driver):

    log("MOPRIA", "Starting Mopria onboarding flow")

    try:

        time.sleep(5)

        size = driver.get_window_size()

        # --------------------------------------------------
        # Swipe through onboarding pages
        # --------------------------------------------------
        for i in range(5):

            driver.swipe(
                int(size['width'] * 0.8),
                int(size['height'] * 0.5),
                int(size['width'] * 0.2),
                int(size['height'] * 0.5),
                300
            )

            log("MOPRIA", f"Swipe NEXT page {i + 1}")

            time.sleep(2)

        # --------------------------------------------------
        # Select first checkbox
        # --------------------------------------------------
        checkbox1 = driver.find_element(
            "xpath",
            "(//android.widget.CheckBox)[1]"
        )

        checkbox1.click()

        log("MOPRIA", "First checkbox selected")

        # Wait for I AGREE button to enable
        time.sleep(3)

        # --------------------------------------------------
        # Click I AGREE
        # --------------------------------------------------
        agree_btn = driver.find_element(
            "xpath",
            "//*[@text='I AGREE']"
        )

        agree_btn.click()

        log("MOPRIA", "Clicked I AGREE")

        time.sleep(5)

        log("MOPRIA", "Mopria flow completed")

    except Exception as e:

        log("MOPRIA", f"Mopria flow failed: {e}")

def handle_adobe_flow(driver):

    log("ADOBE", "Starting Adobe Acrobat flow")

    wait = WebDriverWait(driver, 30)

    try:

        time.sleep(5)

        # --------------------------------------------------
        # STEP 1 : Click X close button
        # --------------------------------------------------
        try:

            # Try content-desc first
            close_btn = wait.until(
                EC.element_to_be_clickable(
                    (
                        By.XPATH,
                        "//*[@content-desc='Close' or @content-desc='Cancel']"
                    )
                )
            )

            close_btn.click()

            log("ADOBE", "Clicked X button using content-desc")

            time.sleep(3)

        except:

            log("ADOBE", "Content-desc X not found")

            # --------------------------------------------------
            # Fallback : Tap top-right corner
            # --------------------------------------------------
            size = driver.get_window_size()

            x = int(size['width'] * 0.95)
            y = int(size['height'] * 0.10)

            driver.tap([(x, y)])

            log("ADOBE", "Tapped X button using coordinates")

            time.sleep(3)

        log("ADOBE", "Adobe flow completed")

    except Exception as e:

        log("ADOBE", f"Adobe flow failed: {e}")

def open_apps():
    global SCREENSHOT_COUNT

    total_apps = len(NON_PERMISSION_APPS) + len(PERMISSION_APPS)
    log("APPS", f"Opening {total_apps} apps")

    opened = []
    failed = []

    # --------------------------------------------------
    # NON-PERMISSION APPS
    # --------------------------------------------------
    log("APPS", "Running NON Permission apps")

    for name, pkg in NON_PERMISSION_APPS.items():

        try:
            log("APPS", f"Opening {name}")

            driver.activate_app(pkg)

            log("WAIT", f"Waiting for {name} app to load")

            time.sleep(5)

            handle_all_popups(driver)

            state = driver.query_app_state(pkg)

            if state in [3, 4]:
                log("SUCCESS", f"{name} opened")
                opened.append(name)
            else:
                log("WARNING", f"{name} not foreground")
                failed.append(name)

        except Exception as e:
            log("ERROR", f"{name} failed: {e}")
            failed.append(name)

    # --------------------------------------------------
    # COOL DOWN
    # --------------------------------------------------
    time.sleep(5)

    # --------------------------------------------------
    # PERMISSION APPS
    # --------------------------------------------------
    log("APPS", "Running PERMISSION apps")

    for name, pkg in PERMISSION_APPS.items():

        try:
            log("APPS", f"Opening {name}")

            driver.activate_app(pkg)
            time.sleep(3)

            # CRITICAL FIX
            if not wait_for_app_screen(driver):
                log("WARNING", f"{name} screen not loaded skipping")
                failed.append(name)
                continue

            # Handle system popups first
            for _ in range(2):
                handle_all_popups(driver)
                time.sleep(1)

            # App-specific flows

            if name == "Xerox Print Service":
                handle_xerox_flow(driver)

            elif name == "Epson iPrint":
                handle_epson_full_flow(driver)

            elif name == "HP Print Service Plugin":
                handle_hp_flow(driver)

            elif name == "Content":
                handle_content_flow(driver)

            elif name == "Gallery":
                handle_gallery_flow(driver)

            elif name == "Web":
                handle_web_flow(driver)

            elif name == "Mopria Print Service":
                handle_mopria_flow(driver)

            elif name == "Adobe Acrobat":
                handle_adobe_flow(driver)

            state = driver.query_app_state(pkg)

            if state in [3, 4]:
                log("SUCCESS", f"{name} opened")
                opened.append(name)
            else:
                log("WARNING", f"{name} not foreground")
                failed.append(name)

        except Exception as e:
            log("ERROR", f"{name} failed: {e}")
            failed.append(name)

    # # --------------------------------------------------
    # # FINAL STEPS
    # # --------------------------------------------------
    # try:
    #     driver.press_keycode(3)
    #     log("TABLET", "Returned to Home screen")
    # except:
    #     log("ERROR", "Driver crashed before HOME")
    #
    # capture_recent_apps_screenshot()
    # page_count = capture_app_pages()
    #
    # open_app_and_capture(
    #     "Google Play Store",
    #     "com.android.vending",
    #     "TestCase8B_Play_Store_Screen"
    # )
    #
    # try:
    #
    #     log("HUB", "Opening Hub Enrollment page")
    #
    #     driver.activate_app("com.airwatch.androidagent")
    #
    #     time.sleep(8)
    #
    #     # --------------------------------------------------
    #     # Profile
    #     # --------------------------------------------------
    #     profile_icon = driver.find_element(
    #         "id",
    #         "com.airwatch.androidagent:id/user_initials_tv"
    #     )
    #
    #     profile_icon.click()
    #
    #     log("HUB", "Clicked Profile")
    #
    #     time.sleep(3)
    #
    #     # --------------------------------------------------
    #     # This Device
    #     # --------------------------------------------------
    #     device_entry = driver.find_element(
    #         "id",
    #         "com.airwatch.androidagent:id/device_tv"
    #     )
    #
    #     device_entry.click()
    #
    #     log("HUB", "Clicked This Device")
    #
    #     time.sleep(3)
    #
    #     # --------------------------------------------------
    #     # Enrollment
    #     # --------------------------------------------------
    #     enrollment = driver.find_element(
    #         "xpath",
    #         "//android.widget.TextView[@text='Enrollment']"
    #     )
    #
    #     enrollment.click()
    #
    #     log("HUB", "Opened Enrollment page")
    #
    #     time.sleep(5)
    #
    #     # --------------------------------------------------
    #     # Screenshot
    #     # --------------------------------------------------
    #     screenshot_path = os.path.join(
    #         RUN_SCREENSHOT_DIR,
    #         "Hub_Enrollment_Details.png"
    #     )
    #
    #     driver.save_screenshot(screenshot_path)
    #
    #     SCREENSHOT_COUNT += 1
    #
    #     log("SCREENSHOT", f"Hub screenshot saved: {screenshot_path}")
    #
    #     driver.press_keycode(3)
    #
    # except Exception as e:
    #
    #     log("HUB", f"Hub screenshot failed: {e}")
    #
    # log("DEBUG", f"Opened apps list: {opened}")
    #
    # log("RESULT", f"Apps opened successfully: {len(opened)}")
    # log("RESULT", f"Apps failed: {len(failed)}")
    #
    # if failed:
    #     log("WARNING", f"Failed apps: {failed}")
    # else:
    #     log("RESULT", "All target apps verified successfully")
    #
    # print_test_summary(opened, failed, page_count)

# --------------------------------------------------
# Execution
# --------------------------------------------------

try:

    open_apps()

    log("RESULT", "App launch completed")

finally:

    driver.quit()

    log("RESULT", "Driver closed")