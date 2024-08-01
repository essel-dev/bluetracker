"""Tracking bluetooth devices and publish to an MQTT broker."""

from datetime import UTC, datetime
from logging import getLogger
from signal import SIG_IGN, SIGINT, signal
from subprocess import CalledProcessError, TimeoutExpired, run
from time import sleep
from typing import Any

from .helpers.mqtt_client import MqttClient
from .models.device import Device, DeviceResponse, DeviceState
from .utils.mqtt_messages import (
    MessageType,
    TopicType,
    publish,
)

_LOGGER = getLogger(__name__)


class BlueScanner:
    """Scan bluetooth classic devices."""

    def __init__(
        self,
        scan_interval: int,
        scan_timeout: int,
        consider_away: int,
    ) -> None:
        """Initialize the scanner.

        Args:
            scan_interval: Seconds to wait between scans.
            scan_timeout: Seconds to wait for a device response.
            consider_away: Seconds to wait to mark a device as away.
        """
        self.scan_interval = scan_interval
        self.scan_timeout = scan_timeout
        self.consider_away = consider_away

    def config_as_dict(self) -> dict[str, int]:
        """Get the bluetooth config as a dictionary.

        Returns:
            A dictionary representation of the config.
        """
        return {
            'scan_interval': self.scan_interval,
            'scan_timeout': self.scan_timeout,
            'consider_away': self.consider_away,
        }

    def scan(self, device: Device) -> Device:
        """Scan a device.

        Args:
            device: The device to scan.

        Returns:
            The device with its new state.
        """
        result = None
        try:
            command = run(  # noqa: S602
                f'/usr/bin/hcitool name {device.mac}',
                shell=True,
                check=True,
                capture_output=True,
                timeout=self.scan_timeout,
            )
            result = command.stdout.decode()
            _LOGGER.debug(result)

            if result == 'Device is not available.':
                result = None
                _LOGGER.critical('Bluetooth is not running')
        except TimeoutExpired:
            pass
        except CalledProcessError:
            _LOGGER.critical('No bluetooth adapter found')

        now = datetime.now(UTC)

        if result:
            device.state = DeviceState.HOME
            device.last_seen = now
            device.reason = DeviceResponse.RESPONDED
        else:
            recently_seen = (now - device.last_seen).seconds <= self.consider_away
            consider_home = device.state == DeviceState.HOME and recently_seen

            if consider_home:
                device.state = DeviceState.HOME
                device.reason = DeviceResponse.CONSIDERED_HOME
            else:
                device.state = DeviceState.NOT_HOME
                device.reason = DeviceResponse.NO_RESPONSE

        _LOGGER.debug('Scan result for %s: %s', device.name, device.state.value)

        return device

    def stop(self, device: Device) -> Device:
        """Stop a device scan.

        Sets a device state to :py:obj:`~.DeviceState.NOT_HOME`.

        Args:
            device: The device to stop.

        Returns:
            The device with its new state.
        """
        device.state = DeviceState.NOT_HOME
        device.last_seen = datetime.now(UTC)
        device.reason = DeviceResponse.SHUTDOWN

        return device


class BlueTrackerError(Exception):
    """Custom exception when an error is encountered in `BlueTracker` operations."""

    def __init__(self, message: str) -> None:
        """Initialize.

        Args:
            message: The error message.
        """
        super().__init__(message)


class BlueTrackerTypeError(BlueTrackerError):
    """Custom exception when invalid type is encountered in `BlueTracker`."""

    def __init__(self, value: Any) -> None:  # noqa: ANN401
        """Initialize.

        Args:
            value: The object with an invalid type that triggered the exception.
        """
        message = f'Invalid type, got {value.__class__.__name__}'
        super().__init__(message)


class BlueTracker:
    """Tracks Bluetooth devices and reports their status to Home Assistant via MQTT."""

    def __init__(
        self,
        scanner: BlueScanner,
        mqtt_client: MqttClient,
        devices: list[Device],
    ) -> None:
        """Initializes the BlueTracker.

        Args:
            scanner: Object responsible for Bluetooth scanning.
            mqtt_client: Object responsible for MQTT communication with an MQTT broker.
            devices: A list of objects representing tracked devices.

        Raises:
            BlueTrackerTypeError: If any argument has an unexpected type.
        """
        if not isinstance(scanner, BlueScanner):
            raise BlueTrackerTypeError(scanner)

        if not isinstance(mqtt_client, MqttClient):
            raise BlueTrackerTypeError(mqtt_client)

        if not isinstance(devices, list):
            raise BlueTrackerTypeError(devices)

        for device in devices:
            if not isinstance(device, Device):
                raise BlueTrackerTypeError(device)

        self.bluescanner = scanner
        self.mqtt_client = mqtt_client
        self.devices = devices

    def __str__(self) -> str:
        """Returns a string representation of tracked devices.

        Returns:
            The string representation.
        """
        all_devices_str = ', '.join(str(dev) for dev in self.devices)
        return f'Tracking devices: {all_devices_str}'

    def run(self) -> None:
        """Main execution loop for the BlueTracker service.

        - Initiates the MQTT client connection,
        - initializes tracked entities,
        - continuously scans for Bluetooth devices.

        Discovered devices are published via MQTT to Home Assistant.
        The scan interval is determined by the configured `scan_interval` in the
        BlueScanner instance.

        The loop waits for Home Assistant to come online if it is unavailable.

        In case of a KeyboardInterrupt (e.g., Ctrl+C), the tracking process is stopped
        gracefully and the MQTT client connection is closed.
        """
        _LOGGER.info('%s startup', self.__class__.__name__)

        try:
            self.mqtt_client.start()
            while not self.mqtt_client.is_homeassistant_online:
                self._wait_until_homeassistant_online()
            self._initialize_entities()

            while True:
                if self.mqtt_client.is_homeassistant_online:
                    self._scan_devices()
                    self._publish_devices()

                    _LOGGER.info('Sleeping %s seconds', self.bluescanner.scan_interval)
                    sleep(self.bluescanner.scan_interval)
                else:
                    self._wait_until_homeassistant_online()  # type: ignore[unreachable]
                    self._initialize_entities()
        except KeyboardInterrupt:
            s = signal(SIGINT, SIG_IGN)

            self._publish_stop_tracking()

            self.mqtt_client.stop()

            _LOGGER.info('%s shutdown', self.__class__.__name__)

            signal(SIGINT, s)

    def _publish_stop_tracking(self) -> None:
        """Sends MQTT messages to indicate server offline and device not_home status."""
        _LOGGER.info('Stopping %s...', self.__class__.__name__)

        for device in self.devices:
            self.bluescanner.stop(device)

        if self.mqtt_client.is_connected:
            self._publish_server_offline()
            self._publish_devices()

    def _initialize_entities(self) -> None:
        """Initialize entities."""
        publish('', MessageType.SERVER_STATUS, TopicType.CONFIG, self.mqtt_client)
        self._publish_server_online()

        config = {
            'bluetooth': self.bluescanner.config_as_dict(),
            'devices': self.devices,
        }
        publish(config, MessageType.SERVER_CONFIG, TopicType.CONFIG, self.mqtt_client)

        for device in self.devices:
            publish(device, MessageType.DEVICE, TopicType.CONFIG, self.mqtt_client)

        _LOGGER.debug('Entities initialized')

    def _publish_server_online(self) -> None:
        """Publishes a message indicating server is online."""
        publish('ON', MessageType.SERVER_STATUS, TopicType.STATE, self.mqtt_client)

    def _publish_server_offline(self) -> None:
        """Publishes a message indicating server is offline."""
        publish('OFF', MessageType.SERVER_STATUS, TopicType.STATE, self.mqtt_client)

    def _scan_devices(self) -> None:
        """Scans all tracked devices and set their states."""
        _LOGGER.info('Scanning %s devices', len(self.devices))

        for device in self.devices:
            self.bluescanner.scan(device)

    def _publish_devices(self) -> None:
        """Publishes the states of the scanned devices to an MQTT broker."""
        _LOGGER.info('Publishing %s devices', len(self.devices))

        for device in self.devices:
            publish(device, MessageType.DEVICE, TopicType.STATE, self.mqtt_client)

    def _wait_until_homeassistant_online(self) -> None:
        """Waits until Home Assistant comes online."""
        delay = 1
        max_delay = 60

        while not self.mqtt_client.is_homeassistant_online:
            _LOGGER.info('Awaiting Home Assistant online, sleeping %s seconds', delay)
            sleep(delay)

            delay *= 2
            delay = min(delay, max_delay)

        _LOGGER.info('Home Assistant online')
