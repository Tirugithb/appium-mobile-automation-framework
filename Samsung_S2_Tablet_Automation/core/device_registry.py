import configparser
import os


def _get_allowed_devices_path():
    """
    Returns absolute path to config/allowed_devices.ini
    regardless of where the script is run from.
    """
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )
    return os.path.join(project_root, "config", "allowed_devices.ini")


def is_device_allowed(device_serial):
    file_path = _get_allowed_devices_path()

    if not os.path.exists(file_path):
        raise RuntimeError("allowed_devices.ini file not found")

    config = configparser.ConfigParser()
    config.read(file_path)

    if "ALLOWED_DEVICES" not in config:
        raise RuntimeError("ALLOWED_DEVICES section missing in allowed_devices.ini")

    return device_serial in config["ALLOWED_DEVICES"]


def get_device_name(device_serial):
    file_path = _get_allowed_devices_path()

    config = configparser.ConfigParser()
    config.read(file_path)

    return config["ALLOWED_DEVICES"].get(device_serial, "Unknown_Device")
