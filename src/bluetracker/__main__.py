"""Start BlueTracker application."""

import sys
from collections.abc import Callable
from importlib.resources import files
from logging import getLogger
from pathlib import Path
from shutil import copyfile
from signal import SIGINT, signal
from types import FrameType

from bluetracker import BlueTracker
from bluetracker.core import BlueScanner
from bluetracker.helpers.mqtt_client import MqttClient
from bluetracker.models.device import Device, DeviceType
from bluetracker.utils.config import BlueTrackerConfig, ConfigError, load_config
from bluetracker.utils.logging import set_logging

_LOGGER = getLogger(__name__)


def _create_bluescanner(config: dict[str, int]) -> BlueScanner:
    return BlueScanner(
        config['scan_interval'],
        config['scan_timeout'],
        config['consider_away'],
    )


def _create_mqtt_client(config: dict[str, str | int]) -> MqttClient:
    return MqttClient(
        str(config['host']),
        int(config['port']),
        str(config['username']),
        str(config['password']),
        str(config['homeassistant_token']),
        str(config['discovery_topic_prefix']),
    )


def _create_devices(devices: list[dict[str, str]]) -> list[Device]:
    return [
        Device(device['name'].title(), device['mac'].lower(), DeviceType.BLUETOOTH)
        for device in devices
    ]


def _config_path() -> str:
    src_config = str(files('bluetracker').joinpath('config.toml'))
    dst_config = Path.cwd().joinpath('bluetracker_config.toml')

    if not dst_config.exists():
        copyfile(src_config, dst_config)
        print(f'First run, configuration file copied to {dst_config}')
        print('Modify as required and restart.')
        sys.exit(0)
    else:
        print(f'Configuration file found at {dst_config}')

    return dst_config.as_posix()


def create_signal_handler(
    tracker_instance: BlueTracker,
) -> Callable[[int, FrameType | None], None]:
    """Creates a signal handler for graceful shutdown on SIGINT.

    This function returns a signal handler that is designed to be registered
    for the SIGINT signal (e.g., triggered by Ctrl+C). When the signal is
    received, the handler stops the BlueTracker instance, logs shutdown messages,
    and then exits the application.

    Args:
        tracker_instance: The BlueTracker instance to stop on shutdown.

    Returns:
        A signal handler function.
    """

    def signal_handler(_signum: int, _frame: FrameType | None) -> None:
        if signal_handler.called:  # type: ignore[attr-defined]
            _LOGGER.info(
                'BlueTracker already shutting down. This may take a few moments.',
            )
            return

        signal_handler.called = True  # type: ignore[attr-defined]
        _LOGGER.info('SIGINT received. Initiating graceful shutdown...')
        tracker_instance.stop()
        _LOGGER.info('%s shutdown complete', tracker_instance.__class__.__name__)
        sys.exit(0)

    signal_handler.called = False  # type: ignore[attr-defined]
    return signal_handler


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

    signal(SIGINT, create_signal_handler(bluetracker))

    bluetracker.run()


if __name__ == '__main__':
    main()  # pragma: no cover
