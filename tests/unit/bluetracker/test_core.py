"""Unittests for bluetracker.core."""

import logging
from pathlib import Path
from subprocess import CalledProcessError, TimeoutExpired
from unittest import TestCase
from unittest.mock import MagicMock, Mock, PropertyMock, call, patch

from src.bluetracker.core import BlueScanner, BlueTracker, BlueTrackerTypeError
from src.bluetracker.helpers.mqtt_client import MqttClient
from src.bluetracker.models.device import (
    Device,
    DeviceResponse,
    DeviceState,
    DeviceType,
)
from src.bluetracker.utils.config import BlueTrackerConfig, load_config
from src.bluetracker.utils.mqtt_messages import (
    MessageType,
    TopicType,
)


class BlueScannerTestCase(TestCase):
    """Unittests for BlueScanner."""

    def setUp(self) -> None:
        """Initialize."""
        logging.disable()

        devices = [
            {'name': 'Device 1', 'mac': 'aa:bb:cc:dd:ee:ff'},
            {'name': 'Device 2', 'mac': 'aa:bb:cc:dd:ee:ff'},
        ]
        self.devices = [
            Device(device['name'], device['mac'], DeviceType.BLUETOOTH)
            for device in devices
        ]

        self.bluescanner = BlueScanner(
            scan_interval=12,
            scan_timeout=3,
            consider_away=180,
        )

    def tearDown(self) -> None:
        """Clean up after each test."""

    def test_setup(self) -> None:
        """Test scan device is home."""
        for device in self.devices:
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.SETUP)
            self.assertEqual(device.source_type, DeviceType.BLUETOOTH)

    @patch('src.bluetracker.core.run')
    def test_scan_home(self, subprocess_mock: Mock) -> None:
        """Test scan device is home."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{'stdout.decode.return_value': 'a name'})
        subprocess_mock.return_value = mock_stdout

        for device in self.devices:
            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.HOME)
            self.assertEqual(device.reason, DeviceResponse.RESPONDED)

    @patch('src.bluetracker.core.run')
    def test_scan_not_home(self, subprocess_mock: Mock) -> None:
        """Test scan device is not_home."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{'stdout.decode.return_value': None})
        subprocess_mock.return_value = mock_stdout

        for device in self.devices:
            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.NO_RESPONSE)

    def test_scan_consider_home(self) -> None:
        """Test scan device is consider_home."""
        device = self.devices[0]

        with patch('src.bluetracker.core.run') as subprocess_mock:
            mock_stdout = MagicMock()
            mock_stdout.configure_mock(**{'stdout.decode.return_value': 'name'})
            subprocess_mock.return_value = mock_stdout

            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.HOME)
            self.assertEqual(device.reason, DeviceResponse.RESPONDED)

        with patch('src.bluetracker.core.run') as subprocess_mock:
            mock_stdout = MagicMock()
            mock_stdout.configure_mock(**{'stdout.decode.return_value': None})
            subprocess_mock.return_value = mock_stdout

            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.HOME)
            self.assertEqual(device.reason, DeviceResponse.CONSIDERED_HOME)

    @patch('src.bluetracker.core.run')
    def test_scan_fail_bluetooth_not_running(self, subprocess_mock: Mock) -> None:
        """Test scan shoould fail when bluetooth is not running."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(
            **{'stdout.decode.return_value': 'Device is not available.'},
        )
        subprocess_mock.return_value = mock_stdout

        for device in self.devices:
            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.NO_RESPONSE)

    @patch('src.bluetracker.core.run')
    def test_scan_fail_timeout(self, subprocess_mock: Mock) -> None:
        """Test scan shoould fail when timeout."""
        subprocess_mock.side_effect = TimeoutExpired(
            cmd=['/usr/bin/hcitool', 'name', 'any_mac'],
            timeout=self.bluescanner.scan_timeout,
        )

        for device in self.devices:
            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.NO_RESPONSE)

    @patch('src.bluetracker.core.run')
    def test_scan_fail_no_bluetooth_adapter(self, subprocess_mock: Mock) -> None:
        """Test scan shoould fail when no bluetooth adapter is found."""
        subprocess_mock.side_effect = CalledProcessError(
            returncode=1,
            cmd=['/usr/bin/hcitool', 'name', 'any_mac'],
        )

        for device in self.devices:
            self.bluescanner.scan(device)
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.NO_RESPONSE)

    def test_stop(self) -> None:
        """Test stop."""
        for device in self.devices:
            self.bluescanner.stop(device)
            self.assertEqual(device.state, DeviceState.NOT_HOME)
            self.assertEqual(device.reason, DeviceResponse.SHUTDOWN)


class BlueTrackerTestCase(TestCase):
    """Unittests for BlueTracker."""

    def setUp(self) -> None:
        """Inititalize before each test."""
        logging.disable()

        self.patcher_ha_api_running = patch(
            'src.bluetracker.utils.config.is_homeassistant_running',
            return_value=True,
        )
        self.mock_ha_api_running = self.patcher_ha_api_running.start()

        config_path = f'{Path.cwd()}/tests/fixtures/config_testing.toml'
        config: BlueTrackerConfig = load_config(config_path)

        self.bluescanner = BlueScanner(
            int(config.bluetooth['scan_interval']),
            int(config.bluetooth['scan_timeout']),
            int(config.bluetooth['consider_away']),
        )

        self.mqtt_client = MqttClient(
            config.mqtt['host'],
            int(config.mqtt['port']),
            config.mqtt['username'],
            config.mqtt['password'],
            config.mqtt['homeassistant_token'],
            config.mqtt['discovery_topic_prefix'],
        )

        self.devices = [
            Device(device['name'].title(), device['mac'].lower(), DeviceType.BLUETOOTH)
            for device in config.devices
        ]

    def tearDown(self) -> None:
        """Clean up after each test."""
        self.patcher_ha_api_running.stop()

    def test_init_with_expected_arguments(self) -> None:
        """Test successful initialization with expected arguments."""
        bluetracker = BlueTracker(self.bluescanner, self.mqtt_client, self.devices)

        self.assertEqual(bluetracker.bluescanner, self.bluescanner)
        self.assertEqual(bluetracker.mqtt_client, self.mqtt_client)
        self.assertEqual(bluetracker.devices, self.devices)

    def test_init_with_unexpected_arguments(self) -> None:
        """Test failure with unexpected arguments."""
        unexpected_argument = 'unexpected_value'

        with self.assertRaises(BlueTrackerTypeError):
            BlueTracker(unexpected_argument, self.mqtt_client, self.devices)

        with self.assertRaises(BlueTrackerTypeError):
            BlueTracker(self.bluescanner, unexpected_argument, self.devices)

        with self.assertRaises(BlueTrackerTypeError):
            BlueTracker(self.bluescanner, self.mqtt_client, unexpected_argument)

        with self.assertRaises(BlueTrackerTypeError):
            BlueTracker(self.bluescanner, self.mqtt_client, ['not a device', 0])

    def test_str(self) -> None:
        """Test __str__."""
        tracker = BlueTracker(self.bluescanner, self.mqtt_client, self.devices)

        expected_str = (
            'Tracking devices: Device 1 (aa:bb:cc:dd:ee:f0), Device 2'
            ' (aa:bb:cc:dd:ee:f1)'
        )

        self.assertEqual(str(tracker), expected_str)

    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.publish')
    @patch('src.bluetracker.core._LOGGER.info')
    def test__publish_devices(
        self,
        mock_logger: Mock,
        mock_publish: Mock,
        _: Mock,
    ) -> None:
        """Tests _stop_tracking behavior when connected."""
        mock_mqtt_client = MagicMock()
        mock_mqtt_client.is_connected = True
        mock_mqtt_client.discovery_topic_prefix = 'homeassistant'
        mock_mqtt_client.publish.side_effect = (
            lambda topic,
            payload,  # noqa: ARG005
            retain=False:  # noqa: ARG005
            topic.replace('homeassistant/', ''),
        )

        mock_scanner = MagicMock()
        tracked_devices = self.devices

        test_tracker = BlueTracker(mock_scanner, mock_mqtt_client, tracked_devices)

        test_tracker._publish_devices()

        self.assertTrue(mock_publish.call_count, 5)

        mock_logger.assert_called_once_with('Publishing %s devices', 2)

        expected_calls = [
            call(
                self.devices[0],
                MessageType.DEVICE,
                TopicType.STATE,
                mock_mqtt_client,
            ),
            call(
                self.devices[1],
                MessageType.DEVICE,
                TopicType.STATE,
                mock_mqtt_client,
            ),
        ]
        mock_publish.assert_has_calls(expected_calls)

    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.publish')
    def test_initialize_entities_publishes_messages(
        self,
        mock_publish: Mock,
        _: Mock,
    ) -> None:
        """Test initialize entities."""
        tracker = BlueTracker(self.bluescanner, Mock(), self.devices)

        tracker._initialize_entities()

        expected_server_config = {
            'bluetooth': self.bluescanner.config_as_dict(),
            'devices': self.devices,
        }

        expected_calls = [
            call('', MessageType.SERVER_STATUS, TopicType.CONFIG, tracker.mqtt_client),
            call('ON', MessageType.SERVER_STATUS, TopicType.STATE, tracker.mqtt_client),
            call(
                expected_server_config,
                MessageType.SERVER_CONFIG,
                TopicType.CONFIG,
                tracker.mqtt_client,
            ),
            call(
                self.devices[0],
                MessageType.DEVICE,
                TopicType.CONFIG,
                tracker.mqtt_client,
            ),
            call(
                self.devices[1],
                MessageType.DEVICE,
                TopicType.CONFIG,
                tracker.mqtt_client,
            ),
        ]

        mock_publish.assert_has_calls(expected_calls)

    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.BlueScanner')
    @patch('src.bluetracker.core.sleep')
    @patch('src.bluetracker.core.BlueTracker._initialize_entities')
    @patch('src.bluetracker.core.BlueTracker._scan_devices')
    @patch('src.bluetracker.core.BlueTracker._publish_devices')
    def test_run_one_loop(
        self,
        mock_publish_devices: Mock,
        mock_scan_devices: Mock,
        mock_init_entities: Mock,
        mock_sleep: Mock,
        mock_bluescanner: Mock,
        _: Mock,
    ) -> None:
        """Test one successful loop."""
        with patch('src.bluetracker.core.MqttClient') as mock_mqtt_client:
            type(mock_mqtt_client).is_homeassistant_online = PropertyMock(
                return_value=True,
            )
            mock_sleep.side_effect = KeyboardInterrupt

            bluetracker = BlueTracker(mock_bluescanner, mock_mqtt_client, self.devices)
            bluetracker.run()

            mock_mqtt_client.start.assert_called_once()
            mock_init_entities.assert_called_once()

            mock_scan_devices.assert_called_once()
            self.assertEqual(mock_publish_devices.call_count, 2)
            mock_sleep.assert_called_once_with(mock_bluescanner.scan_interval)

            mock_mqtt_client.stop.assert_called()

    @patch('src.bluetracker.core.publish')
    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.BlueScanner')
    @patch('src.bluetracker.core.sleep')
    @patch('src.bluetracker.core.BlueTracker._initialize_entities')
    @patch('src.bluetracker.core.BlueTracker._scan_devices')
    @patch('src.bluetracker.core.BlueTracker._publish_devices')
    @patch('src.bluetracker.core.BlueTracker._wait_until_homeassistant_online')
    def test_run_ha_offline(  # noqa:PLR0913
        self,
        mock_wait_until_homeassistant_online: Mock,
        mock_publish_devices: Mock,
        mock_scan_devices: Mock,
        mock_init_entities: Mock,
        mock_sleep: Mock,
        mock_bluescanner: Mock,
        *_: Mock,
    ) -> None:
        """Test MQTT broker is online and HA is offline."""
        with patch('src.bluetracker.core.MqttClient', autospec=True) as mock_mqttc:
            mock_mqtt_instance = mock_mqttc.return_value

            type(mock_mqtt_instance).is_homeassistant_online = PropertyMock(
                return_value=False,
            )
            type(mock_mqtt_instance).is_connected = PropertyMock(return_value=True)

            mock_wait_until_homeassistant_online.side_effect = KeyboardInterrupt

            tracker = BlueTracker(mock_bluescanner, mock_mqtt_instance, self.devices)
            tracker.run()

            mock_mqtt_instance.start.assert_called_once()
            self.assertEqual(mock_init_entities.call_count, 0)
            mock_wait_until_homeassistant_online.assert_called_once()

            mock_scan_devices.assert_not_called()
            mock_publish_devices.assert_called_once()
            mock_sleep.assert_not_called()

            mock_mqtt_instance.stop.assert_called()

    @patch('src.bluetracker.core.publish')
    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.BlueScanner')
    @patch('src.bluetracker.core.BlueTracker._scan_devices')
    @patch('src.bluetracker.core.BlueTracker._publish_devices')
    @patch('src.bluetracker.core.BlueTracker._wait_until_homeassistant_online')
    def test_run_ha_offline_initializes_entities(
        self,
        mock_wait_until_homeassistant_online: Mock,
        mock_publish_devices: Mock,
        mock_scan_devices: Mock,
        mock_bluescanner: Mock,
        *_: Mock,
    ) -> None:
        """Test republish entities when Home Assistant is back online."""
        with patch('src.bluetracker.core.MqttClient', autospec=True) as mock_mqttc:
            mock_mqtt_instance = mock_mqttc.return_value

            is_ha_online_values = [False, True, True, False, False, True]
            is_ha_online_iter = iter(is_ha_online_values)

            def get_is_ha_online() -> bool:
                try:
                    return next(is_ha_online_iter)
                except StopIteration:
                    # If no more values, simulate HA staying online
                    return True

            type(mock_mqtt_instance).is_connected = PropertyMock(return_value=True)
            type(mock_mqtt_instance).is_homeassistant_online = PropertyMock(
                side_effect=get_is_ha_online,
            )

            mock_bluescanner.scan_interval = 5

            mock_init_entities = MagicMock()
            mock_wait_until_homeassistant_online.return_value = True

            tracker = BlueTracker(mock_bluescanner, mock_mqtt_instance, [])
            tracker._initialize_entities = mock_init_entities
            tracker._wait_until_homeassistant_online = (
                mock_wait_until_homeassistant_online
            )

            with patch('src.bluetracker.core.sleep') as mock_sleep:
                mock_sleep.side_effect = [None, None, KeyboardInterrupt]
                tracker.run()

            mock_mqtt_instance.start.assert_called_once()
            self.assertEqual(mock_init_entities.call_count, 3)
            mock_wait_until_homeassistant_online.assert_called()
            mock_scan_devices.assert_called()
            mock_publish_devices.assert_called()
            mock_mqtt_instance.stop.assert_called_once()

    @patch('src.bluetracker.core.isinstance', return_value=True)
    def test_scan_devices(self, _: Mock) -> None:
        """Test scan devices."""
        bluetracker = BlueTracker(MagicMock(), MagicMock(), self.devices)
        bluetracker._scan_devices()

        bluetracker.bluescanner.scan.assert_has_calls(
            [call(self.devices[0]), call(self.devices[1])],
        )

    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.sleep')
    @patch('src.bluetracker.core._LOGGER')
    def test_wait_until_homeassistant_online_reconnect_delay(
        self,
        mock_logger: Mock,
        mock_sleep: Mock,
        _: Mock,
    ) -> None:
        """Test HA offline and reconnecting."""
        with patch('src.bluetracker.core.MqttClient', autospec=True) as mock_mqttc:
            mock_mqtt_instance = mock_mqttc.return_value
            call_count = 0
            min_call_count = 3

            def is_ha_online_side_effect() -> bool:
                nonlocal call_count
                call_count += 1
                return call_count > min_call_count

            type(mock_mqtt_instance).is_homeassistant_online = PropertyMock(
                side_effect=is_ha_online_side_effect,
            )

            bluetracker = BlueTracker(MagicMock(), mock_mqtt_instance, self.devices)

            bluetracker._wait_until_homeassistant_online()

            expected_delays = [1, 2, 4]
            for delay in expected_delays:
                mock_sleep.assert_any_call(delay)

            mock_logger.info.assert_has_calls(
                [
                    call('Awaiting Home Assistant online, sleeping %s seconds', 1),
                    call('Awaiting Home Assistant online, sleeping %s seconds', 2),
                    call('Awaiting Home Assistant online, sleeping %s seconds', 4),
                    call('Home Assistant online'),
                ],
            )

            self.assertTrue(bluetracker.mqtt_client.is_homeassistant_online)
