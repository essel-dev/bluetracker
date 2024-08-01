"""Load and check configuration file."""

from dataclasses import dataclass
from enum import Enum
from logging import getLogger
from pathlib import Path
from re import match
from subprocess import CalledProcessError, run
from tomllib import load
from typing import Any

from bluetracker.utils.homeassistant import is_homeassistant_running

_LOGGER = getLogger(__name__)


class ConfigError(Exception):
    """Custom exception for config errors."""

    def __init__(self, message: str) -> None:
        """Initialize.

        Args:
            message: The error message.
        """
        super().__init__(message)


class PathConfigError(ConfigError):
    """Config path does not exist."""

    def __init__(self, config_path: str) -> None:
        """Initialize.

        Args:
            config_path: The config_path.
        """
        message = f'Config path {config_path} does not exist'
        super().__init__(message)


class BluetoothConfigError(ConfigError):
    """Invalid bluetooth config."""

    def __init__(self, expected_keys: list[str]) -> None:
        """Initialize.

        Args:
            expected_keys: The expected keys.
        """
        message = f'Invalid bluetooth config: expected keys: {expected_keys}'
        super().__init__(message)


class BluetoothNotFoundConfigError(ConfigError):
    """Bluetooth adapter not found."""

    def __init__(self) -> None:
        """Initialize."""
        message = 'Bluetooth adapter not found'
        super().__init__(message)


class BluetoothNotRunningConfigError(ConfigError):
    """Bluetooth adapter not running."""

    def __init__(self) -> None:
        """Initialize."""
        message = 'Bluetooth adapter not running'
        super().__init__(message)


class MqttConfigError(ConfigError):
    """Invalid MQTT config."""

    def __init__(self, expected_keys: list[str]) -> None:
        """Initialize.

        Args:
            expected_keys: The expected keys.
        """
        message = f'Invalid MQTT config: expected keys: {expected_keys}'

        super().__init__(message)


class HomeAssistantConfigError(ConfigError):
    """Invalid HomeAssisant config."""

    def __init__(self) -> None:
        """Initialize."""
        message = (
            'Could not connect to Home Assistant, verify it is running, host ip'
            ' address and token'
        )

        super().__init__(message)


class NoDevicesFoundConfigError(ConfigError):
    """No devices found."""

    def __init__(self) -> None:
        """Initialize."""
        super().__init__('Invalid devices config: no devices found')


class DeviceConfigError(ConfigError):
    """Invalid devices config."""

    def __init__(self, expected_keys: list[str]) -> None:
        """Initialize.

        Args:
            expected_keys: The expected keys.
        """
        message = f'Invalid devices config: expected keys: {expected_keys}'

        super().__init__(message)


class InvalidMacConfigError(ConfigError):
    """Invalid device mac address."""

    def __init__(self, device: dict[str, str]) -> None:
        """Initialize.

        Args:
            device: The device.
        """
        message = f'Invalid mac address {device["mac"]} for {device["name"]}'

        super().__init__(message)


class DeviceUniqueConfigError(ConfigError):
    """Devices must be unique."""

    def __init__(self, field: str) -> None:
        """Initialize.

        Args:
            field: The field name.
        """
        message = f'Devices must have unique {field}s'

        super().__init__(message)


class Environment(Enum):
    """The configuration environment."""

    DEV = 'development'
    TEST = 'testing'
    PROD = 'production'


@dataclass
class BlueTrackerConfig:
    """Configuration for BlueTracker."""

    environment: Environment
    bluetooth: dict[str, int]
    mqtt: dict[str, str | int]
    devices: list[dict[str, str]]


def load_config(config_path: str) -> BlueTrackerConfig:
    """Load configuration file.

    Args:
        config_path: The configuration file path.

    Returns:
        The configuration.
    """
    _validate_config(config_path)

    with Path.open(Path.cwd().joinpath(config_path), 'rb') as file:
        config = load(file)

    try:
        env = Environment(config['environment'])
    except (ValueError, KeyError):
        env = Environment.PROD

    bluetooth_config: dict[str, Any] = config.get('bluetooth', {})
    mqtt_config: dict[str, Any] = config.get('mqtt', {})
    devices: list[dict[str, str]] = config.get('devices', [])

    _validate_bluetooth(env, bluetooth_config)
    _validate_mqtt(mqtt_config)
    _validate_devices(devices)

    return BlueTrackerConfig(env, bluetooth_config, mqtt_config, devices)


def _validate_config(config_path: str) -> None:
    """Validate configuration file.

    Args:
        config_path: The configuration file path.

    Raises:
        PathConfigError: Configuration file does not exist.
    """
    if not Path.cwd().joinpath(config_path).exists():
        raise PathConfigError(config_path)


def _validate_bluetooth(environment: Environment, config: dict[str, Any]) -> None:
    """Validate bluetooth.

    Args:
        environment: The config environment.
        config: The bluetooth config.

    Raises:
        BluetoothConfigError: Invalid bluetooth config.
    """
    if environment == Environment.PROD:
        _test_bluetooth_adapter()
    _LOGGER.info('Bluetooth is running')

    expected_keys = sorted(
        [
            'scan_interval',
            'scan_timeout',
            'consider_away',
        ],
    )
    if not sorted(config.keys()) == expected_keys:
        raise BluetoothConfigError(expected_keys)

    _LOGGER.info('Bluetooth configuration found')


def _validate_mqtt(config: dict[str, Any]) -> None:
    """Validate MQTT.

    Args:
        config: The MQTT config.

    Raises:
        MqttConfigError: Invalid MQTT config.
        HomeAssistantConfigError: Unable to connect to Home Assistant.
    """
    expected_keys = sorted(
        [
            'host',
            'port',
            'username',
            'password',
            'discovery_topic_prefix',
            'homeassistant_token',
        ],
    )
    if not sorted(config.keys()) == expected_keys:
        raise MqttConfigError(expected_keys)

    if not is_homeassistant_running(config['host'], config['homeassistant_token']):
        raise HomeAssistantConfigError

    _LOGGER.info('MQTT configuration found')


def _validate_devices(devices: list[dict[str, str]]) -> None:
    """Validate devices.

    Args:
        devices: The devices.

    Raises:
        NoDevicesFoundConfigError: No devices found.
        DeviceConfigError: Invalid devices config.
        InvalidMacConfigError: Invalid device mac address.
        DeviceUniqueConfigError: Devices must be unique.
    """
    amount = len(devices)
    if not amount:
        raise NoDevicesFoundConfigError

    expected_keys = sorted(
        [
            'mac',
            'name',
        ],
    )
    mac_pattern = '^(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})$'

    names = []
    macs = []
    for device in devices:
        if not sorted(device.keys()) == expected_keys:
            raise DeviceConfigError(expected_keys)

        if not match(mac_pattern, device['mac']):
            raise InvalidMacConfigError(device)

        names.append(device['name'])
        macs.append(device['mac'])

    field = 'name'
    if len(names) > len(set(names)):
        raise DeviceUniqueConfigError(field)

    field = 'mac'
    if len(macs) > len(set(macs)):
        raise DeviceUniqueConfigError(field)

    _LOGGER.info('%s device(s) found in configuration', amount)


def _test_bluetooth_adapter() -> None:
    try:
        command = run(  # noqa: S602
            ['/usr/bin/hciconfig'],
            shell=True,
            check=True,
            capture_output=True,
            timeout=10,
        )
    except (CalledProcessError, FileNotFoundError) as error:
        raise BluetoothNotFoundConfigError from error

    if 'DOWN' in command.stdout.decode():
        raise BluetoothNotRunningConfigError
