import subprocess
import os
from datetime import datetime
import time
from appium import webdriver
from appium.options.android import UiAutomator2Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from appium.webdriver.common.appiumby import AppiumBy as By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.actions.action_builder import ActionBuilder
from selenium.webdriver.common.actions.pointer_input import PointerInput
from selenium.webdriver.common.actions import interaction
import socket
import sys
from appium_manager import AppiumManager

sys.stdout.reconfigure(encoding="utf-8")

# ================= LOGGING =================
def log(section, message):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{section:<14}] {message}")


# ================= START APPIUM =================
def is_port_open(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def start_appium():
    if is_port_open(4723):
        log("APPIUM", "Appium already running on port 4723")
        return

    log("APPIUM", "Starting Appium Server...")
    # subprocess.Popen("start cmd /k appium", shell=True)
    subprocess.Popen(
        "appium -a 127.0.0.1 -p 4723",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(10)

    time.sleep(10)  # give Appium time to bind the port
    log("APPIUM", "Appium started")



# ================= DEVICE DETECT =================
def detect_device():
    result = subprocess.check_output("adb devices", shell=True).decode()
    for line in result.splitlines():
        if "\tdevice" in line:
            serial = line.split()[0]
            log("DEVICE", f"Detected device → {serial}")
            return serial
    raise RuntimeError("No Android device connected")


# ================= DEVICE UNLOCK =================
def unlock_device(serial):
    log("DEVICE", "Ensuring device is awake/unlocked")

    subprocess.run(f"adb -s {serial} shell input keyevent 26", shell=True)
    time.sleep(1)

    subprocess.run(f"adb -s {serial} shell input swipe 500 1600 500 300", shell=True)
    time.sleep(1.5)

    lock_state = subprocess.check_output(
        f"adb -s {serial} shell dumpsys window | findstr mDreamingLockscreen",
        shell=True
    ).decode(errors="ignore")

    if "true" in lock_state.lower():
        log("DEVICE", "Lock screen detected — trying PIN unlock")

        PIN = "Medtronic1"

        for digit in PIN:
            subprocess.run(f"adb -s {serial} shell input text {digit}", shell=True)
            time.sleep(0.3)

        subprocess.run(f"adb -s {serial} shell input keyevent 66", shell=True)
        time.sleep(2)

    log("DEVICE", "Device unlock sequence completed")


# ================= OS INFO =================
def get_os_info(serial):
    model = subprocess.check_output(f"adb -s {serial} shell getprop ro.product.model", shell=True).decode().strip()
    android = subprocess.check_output(f"adb -s {serial} shell getprop ro.build.version.release", shell=True).decode().strip()
    patch = subprocess.check_output(f"adb -s {serial} shell getprop ro.build.version.security_patch", shell=True).decode().strip()

    return {"model": model, "android": android, "patch": patch}


def swipe_up_left_side(driver):
    size = driver.get_window_size()
    start_x = size['width'] * 0.2
    start_y = size['height'] * 0.8
    end_y = size['height'] * 0.2
    actions = ActionChains(driver)
    pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
    actions.w3c_actions = ActionBuilder(driver, mouse=pointer)
    actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
    actions.w3c_actions.pointer_action.pointer_down()
    actions.w3c_actions.pointer_action.move_to_location(start_x, end_y)
    actions.w3c_actions.pointer_action.release()
    actions.perform()
    time.sleep(1)


def scroll_to_top_left(driver, max_swipes=3):
    for _ in range(max_swipes):
        swipe_up_left_side(driver)
        time.sleep(1)

def swipe_up_software_panel(driver):
    size = driver.get_window_size()

    start_x = int(size['width'] * 0.75)  # RIGHT PANEL
    start_y = int(size['height'] * 0.85)
    end_y   = int(size['height'] * 0.35)

    pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
    actions = ActionBuilder(driver, mouse=pointer)

    # Move to start
    actions.pointer_action.move_to_location(start_x, start_y)

    # Touch down
    actions.pointer_action.pointer_down()

    # Slow swipe
    actions.pointer_action.pause(0.6)
    actions.pointer_action.move_to_location(start_x, end_y)
    actions.pointer_action.pause(0.6)

    # Release
    actions.pointer_action.pointer_up()

    # Correct call
    actions.perform()

    # Pause after swipe
    time.sleep(1.2)


def find_and_click_about_tablet(driver, max_swipes=6):
    for i in range(max_swipes):
        try:
            element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@text,'About tablet')]")
                )
            )
            element.click()
            log("SYSTEM UPDATE", "Clicked About tablet")
            return True
        except:
            #log("SYSTEM UPDATE", f"Swipe attempt {i+1}")
            swipe_up_left_side(driver)

    raise RuntimeError("Could not find About tablet after scrolling")


def find_and_click_software_info(driver, max_swipes=2):
    for i in range(max_swipes):
        try:
            element = WebDriverWait(driver, 3).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[contains(@text,'Software information')]")
                )
            )
            element.click()
            log("SYSTEM UPDATE", "Opened Software information")
            return True
        except:
            swipe_up_left_side(driver)

    raise RuntimeError("Could not find Software information")



# ================= OPEN SOFTWARE & BATTERY UI =================
def open_battery_info(serial):
    log("ABOUT", "Opening Battery Information")

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.app_package = "com.android.settings"
    options.no_reset = True

    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True
    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)
    wait = WebDriverWait(driver, 15)

    software_btn = wait.until(
        EC.element_to_be_clickable((By.XPATH, "//*[contains(@text,'Battery information')]"))
    )
    software_btn.click()
    log("ABOUT", "Battery Info")
    time.sleep(2)

    return driver

def open_software_info(serial):
    log("ABOUT", "Opening Software Information")

    # Force stop Settings
    subprocess.run(
        f"adb -s {serial} shell monkey -p com.android.settings "
        f"-c android.intent.category.LAUNCHER 1",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    time.sleep(2)

    # Launch Settings clean
    subprocess.run(
        f"adb -s {serial} shell monkey -p com.android.settings "
        f"-c android.intent.category.LAUNCHER 1",
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(5)

    # Attach Appium AFTER Settings is visible
    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.app_package = "com.android.settings"
    options.app_activity = "com.android.settings.Settings"
    options.no_reset = True

    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True
    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    # 4️⃣ Wait for Settings UI
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located(
            (By.ID, "com.android.settings:id/recycler_view")
        )
    )
    time.sleep(2)

    # 5️⃣ Navigate correctly
    scroll_to_top_left(driver)
    find_and_click_about_tablet(driver)
    find_and_click_software_info(driver)

    return driver

# ================= SOFTWARE UI EXTRACT =================
def extract_software_info(driver):
    log("SOFTWARE", "Extracting Software UI")

    all_texts = []

    # Scroll RIGHT panel to TOP (single slow swipe)
    swipe_up_software_panel(driver)

    elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
    all_texts += [e.text.strip() for e in elements if e.text.strip()]

    # Scroll to BOTTOM
    size = driver.get_window_size()
    for _ in range(3):
        start_x = size['width'] * 0.75
        start_y = size['height'] * 0.8
        end_y = size['height'] * 0.2

        actions = ActionChains(driver)
        pointer = PointerInput(interaction.POINTER_TOUCH, "finger")
        actions.w3c_actions = ActionBuilder(driver, mouse=pointer)
        actions.w3c_actions.pointer_action.move_to_location(start_x, start_y)
        actions.w3c_actions.pointer_action.pointer_down()
        actions.w3c_actions.pointer_action.move_to_location(start_x, end_y)
        actions.w3c_actions.pointer_action.release()
        actions.perform()
        time.sleep(1)

    elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
    all_texts += [e.text.strip() for e in elements if e.text.strip()]

    # Deduplicate while preserving order
    seen = set()
    texts = [x for x in all_texts if not (x in seen or seen.add(x))]

    log("SOFTWARE", f"RAW → {texts}")

    data = {}

    for i, t in enumerate(texts):
        low = t.lower()

        if "one ui version" in low:
            data["one_ui_version"] = texts[i + 1]

        elif "android version" in low:
            data["android_version"] = texts[i + 1]

        elif "kernel version" in low:
            data["kernel_version"] = texts[i + 1]

        elif "se for android status" in low:
            data["se_android_status"] = texts[i + 1].replace("\n", " | ")

        elif "knox version" in low:
            data["knox_version"] = texts[i + 1].replace("\n", " | ")

        elif "security software version" in low:
            data["security_software"] = texts[i + 1].replace("\n", " | ")

        elif "android security patch level" in low:
            data["android_security_patch"] = texts[i + 1]

        elif "google play system update" in low:
            data["google_play_update"] = texts[i + 1] if i + 1 < len(texts) else "N/A"

    log("SOFTWARE", f"PARSED → {data}")
    return data

# ================= BATTERY UI EXTRACT =================
def extract_battery_info(driver):
    log("BATTERY", "Extracting Battery UI")

    data = {}
    elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
    texts = [e.text.strip() for e in elements if e.text.strip()]

    log("BATTERY", f"RAW → {texts}")

    for i, t in enumerate(texts):
        low = t.lower()

        if "%" in low or "level" in low:
            if "%" in t:
                data["battery_level_ui"] = t.strip()

        if "charging" in low or "discharging" in low:
            data["charging_ui"] = t

        if "health" in low:
            data["battery_health"] = texts[i + 1] if i + 1 < len(texts) else "N/A"

    log("BATTERY", f"PARSED → {data}")
    return data


# ================= ABOUT TABLET DATA =================
def get_about_tablet_info(serial):
    log("ABOUT", "Reading About Tablet UI")

    info = {"device_name": "N/A", "build_number": "N/A", "kernel": "N/A"}

    # Open Settings main screen
    subprocess.run(
        f"adb -s {serial} shell am start -a android.settings.SETTINGS",
        shell=True
    )
    time.sleep(2)

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.app_package = "com.android.settings"
    options.no_reset = True

    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True
    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    # Navigate to About Tablet
    find_and_click_about_tablet(driver)

    time.sleep(2)

    elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
    texts = [e.text.strip() for e in elements if e.text.strip()]

    log("ABOUT", f"RAW → {texts}")

    for i, t in enumerate(texts):
        low = t.lower()

        if "device name" in low:
            info["device_name"] = texts[i + 1] if i + 1 < len(texts) else "N/A"

        if "build number" in low:
            info["build_number"] = texts[i + 1] if i + 1 < len(texts) else "N/A"

        if "kernel" in low:
            info["kernel"] = texts[i + 1] if i + 1 < len(texts) else "N/A"

    driver.quit()
    return info
# ================= DEVICE HEALTH =================
def collect_health(serial):
    health = {}

    raw = subprocess.check_output(f"adb -s {serial} shell dumpsys battery", shell=True).decode(errors="ignore")

    for line in raw.splitlines():
        if "level" in line.lower():
            health["battery_level"] = line.split(":")[-1].strip()
        if "temperature" in line.lower():
            temp = int(line.split(":")[-1].strip())
            health["battery_temp_c"] = f"{temp / 10:.1f} °C"

    health["uptime"] = subprocess.check_output(f"adb -s {serial} shell uptime", shell=True).decode(errors="ignore")

    return health


# ================= REPORT =================
def safe(v):
    return v if v else "N/A"

def print_report(info):
    log("REPORT", "========= FINAL TABLET HEALTH =========")

    printed = set()

    def print_unique(section, label, value):
        key = f"{section}:{label}"
        if key not in printed and value and value != "N/A":
            printed.add(key)
            log(section, f"{label:<30} → {value}")

    # ---- OS ----
    print_unique("OS", "Model", safe(info.get("model")))
    print_unique("OS", "Android Version", safe(info.get("android")))
    print_unique("OS", "Patch Level", safe(info.get("patch")))

    # ---- ABOUT ----
    about = info.get("about", {})
    print_unique("ABOUT", "Device Name", safe(about.get("device_name")))
    print_unique("ABOUT", "Model", safe(about.get("model")))
    print_unique("ABOUT", "Serial Number", safe(about.get("serial")))
    print_unique("ABOUT", "Build Number", safe(about.get("build_number")))
    print_unique("ABOUT", "Kernel Version", safe(about.get("kernel")))

    # ---- SOFTWARE ----
    log("SOFTWARE", "----- SOFTWARE INFORMATION -----")

    ordered_software = [
        "one_ui_version",
        "android_version",
        "google_play_update",
        "kernel_version",
        "se_android_status",
        "knox_version",
        "security_software",
        "android_security_patch",
        "build_number"
    ]

    software = info.get("software_info", {})

    for key in ordered_software:
        if key in software:
            label = key.replace("_", " ").title()
            print_unique("SOFTWARE", label, software.get(key))

    # ---- BATTERY ----
    log("BATTERY", "----- BATTERY STATUS -----")
    for k, v in info.get("battery_ui", {}).items():
        label = k.replace("_", " ").title()
        print_unique("BATTERY", label, v)

    # ---- HEALTH ----
    log("HEALTH", "----- DEVICE HEALTH -----")
    for k, v in info.get("health", {}).items():
        label = k.replace("_", " ").title()
        print_unique("HEALTH", label, v)

    log("REPORT", "========= END =========")

def extract_about_from_current_screen(driver):
    log("ABOUT", "Extracting About Tablet UI")

    data = {"model": "N/A", "serial": "N/A", "device_name": "N/A"}

    driver.press_keycode(4)
    time.sleep(1)

    elements = driver.find_elements(By.CLASS_NAME, "android.widget.TextView")
    texts = [e.text.strip() for e in elements if e.text.strip()]

    log("ABOUT", f"RAW → {texts}")

    for i, t in enumerate(texts):
        low = t.lower()

        if "model name" in low or "model" in low:
            data["model"] = texts[i + 1]

        elif "serial number" in low:
            data["serial"] = texts[i + 1]

        elif "device name" in low or "product name" in low:
            data["device_name"] = texts[i + 1]

    return data

# --------------------------------------------------
# CLEANUP — CLOSE RECENT APPS
# --------------------------------------------------
def clear_recent_apps_ui(serial):
    log("CLEANUP", "Opening Recent Apps")

    options = UiAutomator2Options()
    options.platform_name = "Android"
    options.device_name = serial
    options.udid = serial
    options.no_reset = True   # IMPORTANT — keep session clean

    options.allow_running_instrumentation = True
    options.ignore_hidden_api_policy_error = True
    options.uiautomator2_server_launch_timeout = 180000
    options.uiautomator2_server_install_timeout = 180000
    options.adb_exec_timeout = 180000
    options.android_install_timeout = 180000

    driver = webdriver.Remote("http://127.0.0.1:4723", options=options)

    try:
        driver.press_keycode(187)  # Recent Apps
        time.sleep(2)

        clear_all = WebDriverWait(driver, 6).until(
            EC.element_to_be_clickable((
                By.XPATH,
                "//*[@text='Close all' or @text='Clear all' or contains(@text,'Close')]"
            ))
        )
        clear_all.click()
        time.sleep(1)

        log("CLEANUP", "Recent apps cleared successfully")

    except Exception as e:
        log("CLEANUP", f"No recent apps to clear or button not found")

    finally:
        driver.quit()

# ================= MAIN =================
def run_health_monitor():
    log("INIT", "Starting Tablet Health Monitor")

    start_appium()
    serial = detect_device()
    unlock_device(serial)

    info = {}
    info.update(get_os_info(serial))

    # ---- OPEN SOFTWARE SCREEN FIRST ----
    driver = open_software_info(serial)

    info["software_info"] = extract_software_info(driver)
    info["about"] = extract_about_from_current_screen(driver)

    driver.quit()

    # ---- OPEN BATTERY SCREEN NEXT ----
    driver = open_battery_info(serial)
    info["battery_ui"] = extract_battery_info(driver)
    driver.quit()

    # ---- ABOUT TABLET ----
    #info["about"] = get_about_tablet_info(serial)


    # ---- APPS ----
    #info["apps"] = get_app_versions(serial)

    # ---- DEVICE HEALTH ----
    info["health"] = collect_health(serial)

    print_report(info)

    log("RESULT", "Pipeline completed successfully")

    clear_recent_apps_ui(serial)



# ================= RUN =================
if __name__ == "__main__":
    AppiumManager.start()
    run_health_monitor()
