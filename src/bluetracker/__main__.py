"""Start BlueTracker application."""

import sys
from importlib.resources import files
from pathlib import Path
from shutil import copyfile

from bluetracker import BlueTracker
from bluetracker.core import BlueScanner
from bluetracker.helpers.mqtt_client import MqttClient
from bluetracker.models.device import Device, DeviceType
from bluetracker.utils.config import BlueTrackerConfig, ConfigError, load_config
from bluetracker.utils.logging import set_logging


def _create_bluescanner(config: dict[str, int]) -> BlueScanner:
    return BlueScanner(
        int(config['scan_interval']),
        int(config['scan_timeout']),
        int(config['consider_away']),
    )


def _create_mqtt_client(config: dict[str, str | int]) -> MqttClient:
    return MqttClient(
        config['host'],
        int(config['port']),
        config['username'],
        config['password'],
        config['homeassistant_token'],
        config['discovery_topic_prefix'],
    )


def _create_devices(devices: list[dict[str, str]]) -> list[Device]:
    return [
        Device(device['name'].title(), device['mac'].lower(), DeviceType.BLUETOOTH)
        for device in devices
    ]


def _config_path() -> str:
    src_config = files('bluetracker').joinpath('config.toml')
    dst_config = Path.cwd().joinpath('bluetracker_config.toml')

    if not dst_config.exists():
        copyfile(src_config, dst_config)
        print(f'First run, configuration file copied to {dst_config}')
        print('Modify as required and restart.')
        sys.exit(0)
    else:
        print(f'Configuration file found at {dst_config}')

    return dst_config


def main() -> None:
    """Main entry point of the BlueTracker application.

    - Loads configuration,
    - sets up logging,
    - creates scanner, MQTT client and devices,
    - starts the BlueTracker instance.
    """
    config_path = _config_path()

    try:
        config: BlueTrackerConfig = load_config(config_path)
    except ConfigError as error:
        print(f'Fatal error: {error}')
        sys.exit(1)

    set_logging(config.environment)

    scanner = _create_bluescanner(config.bluetooth)
    mqtt_client = _create_mqtt_client(config.mqtt)
    devices: list[Device] = _create_devices(config.devices)

    bluetracker = BlueTracker(scanner, mqtt_client, devices)
    bluetracker.run()  # Start BlueTracker


if __name__ == '__main__':
    main()  # pragma: no cover
