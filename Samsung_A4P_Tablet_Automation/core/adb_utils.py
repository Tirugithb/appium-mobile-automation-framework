import subprocess
import time


def get_connected_device_serial():
    result = subprocess.run(
        ["adb", "devices"],
        capture_output=True,
        text=True
    )

    lines = result.stdout.strip().split("\n")[1:]
    devices = [
        line.split()[0]
        for line in lines
        if line.strip().endswith("device")
    ]

    if not devices:
        raise RuntimeError("No connected Android device found.")

    return devices[0]


def is_device_locked():
    """
    Returns True if device is locked, False if unlocked.
    """
    result = subprocess.run(
        ["adb", "shell", "dumpsys", "window"],
        capture_output=True,
        text=True
    )

    output = result.stdout
    return (
        "mDreamingLockscreen=true" in output
        or "mShowingLockscreen=true" in output
    )


def unlock_device_with_password(password, retries=3):
    """
    Tries to unlock the device using password.
    Verifies unlock success before returning.
    """
    for attempt in range(1, retries + 1):
        print(f"Unlock attempt {attempt}...")

        # Wake screen
        subprocess.run(["adb", "shell", "input", "keyevent", "26"])
        time.sleep(1)

        # Swipe up
        subprocess.run(
            ["adb", "shell", "input", "swipe", "500", "1600", "500", "600"]
        )
        time.sleep(1)

        # Type password (space-safe)
        safe_password = password.replace(" ", "%s")
        subprocess.run(
            ["adb", "shell", "input", "text", safe_password]
        )
        time.sleep(0.5)

        # Enter
        subprocess.run(["adb", "shell", "input", "keyevent", "66"])
        time.sleep(2)

        # VERIFY UNLOCK
        if not is_device_locked():
            print("🔓 Device successfully unlocked.")
            return

        print("Unlock failed, retrying...")

    raise RuntimeError("Failed to unlock device after multiple attempts")
