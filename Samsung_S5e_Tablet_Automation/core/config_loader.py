import configparser
import os


def load_device_password():
    project_root = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..")
    )

    config_path = os.path.join(project_root, "config", "config.ini")

    if not os.path.exists(config_path):
        raise RuntimeError("config.ini not found")

    config = configparser.ConfigParser()
    config.read(config_path)

    if "DEVICE" not in config or "PASSWORD" not in config["DEVICE"]:
        raise RuntimeError("DEVICE.PASSWORD missing in config.ini")

    return config["DEVICE"]["PASSWORD"]
