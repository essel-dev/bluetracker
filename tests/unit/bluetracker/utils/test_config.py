"""Unittests for bluetracker.utils.config."""

from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from src.bluetracker.utils.config import (
    _LOGGER,
    BluetoothConfigError,
    BluetoothNotFoundConfigError,
    BluetoothNotRunningConfigError,
    DeviceConfigError,
    DeviceUniqueConfigError,
    Environment,
    HomeAssistantConfigError,
    InvalidMacConfigError,
    MqttConfigError,
    NoDevicesFoundConfigError,
    PathConfigError,
    _validate_mqtt,
    load_config,
)


class ConfigTestCase(TestCase):
    """Unittests for config."""

    def setUp(self) -> None:
        """Inititalize before each test."""
        self.patcher_ha_api_running = patch(
            'src.bluetracker.utils.config.is_homeassistant_running',
            return_value=True,
        )
        self.mock_ha_api_running = self.patcher_ha_api_running.start()

    def tearDown(self) -> None:
        """Clean up after each test."""
        self.patcher_ha_api_running.stop()

    def test_load_config(self) -> None:
        """Test load config."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_testing.toml'
        config = load_config(config_path)

        self.assertEqual(config.environment, Environment.TEST)
        self.assertTrue(config.bluetooth)
        self.assertTrue(config.mqtt)
        self.assertTrue(config.devices)

    def test_load_config_fail(self) -> None:
        """Test load config should fail."""
        config_path = f'{Path.cwd()}/tests/fixtures/fiction.toml'

        with self.assertRaisesRegex(PathConfigError, 'does not exist'):
            load_config(config_path)

    def test_environment_default(self) -> None:
        """Test environment default."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_env_fail.toml'

        with self.assertRaises(BluetoothNotFoundConfigError):
            config = load_config(config_path)
            self.assertEqual(config.environment, Environment.PROD)

    @patch('src.bluetracker.utils.config.run')
    def test_validate_bluetooth_fail_adapter_down(self, subprocess_mock: Mock) -> None:
        """Test validate bluetooth fail adapter."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{'stdout.decode.return_value': 'DOWN'})
        subprocess_mock.return_value = mock_stdout

        config_path = f'{Path.cwd()}/tests/fixtures/config_production.toml'

        with self.assertRaisesRegex(
            BluetoothNotRunningConfigError,
            'Bluetooth adapter not running',
        ):
            load_config(config_path)

    @patch('src.bluetracker.utils.config.run')
    def test_validate_bluetooth_fail_adapter_not_running(
        self,
        subprocess_mock: Mock,
    ) -> None:
        """Test validate bluetooth fail adapter."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{'stdout.decode.return_value': ''})
        subprocess_mock.return_value = mock_stdout

        config_path = f'{Path.cwd()}/tests/fixtures/config_production.toml'

        with self.assertRaisesRegex(
            BluetoothNotRunningConfigError,
            'Bluetooth adapter not running',
        ):
            load_config(config_path)

    @patch('src.bluetracker.utils.config.run')
    def test_validate_bluetooth_fail_expected_keys(self, subprocess_mock: Mock) -> None:
        """Test validate bluetooth fail expected keys."""
        mock_stdout = MagicMock()
        mock_stdout.configure_mock(**{'stdout.decode.return_value': 'UP RUNNING'})
        subprocess_mock.return_value = mock_stdout

        config_path = f'{Path.cwd()}/tests/fixtures/config_bluetooth_fail_config.toml'

        with self.assertRaisesRegex(
            BluetoothConfigError,
            'Invalid bluetooth config: expected keys:',
        ):
            load_config(config_path)

    def test_validate_mqtt_fail_expected_keys(self) -> None:
        """Test validate mqtt fail expected keys."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_mqtt_fail.toml'

        with self.assertRaisesRegex(
            MqttConfigError,
            'Invalid MQTT config: expected keys:',
        ):
            load_config(config_path)

    @patch('src.bluetracker.utils.config.is_homeassistant_running')
    def test_validate_mqtt_success(self, mock_is_running: Mock) -> None:
        """Test MQTT config is valid."""
        mock_is_running.return_value = True
        config = {
            'host': 'your_host',
            'port': 1234,
            'username': 'your_username',
            'password': 'your_password',
            'discovery_topic_prefix': 'homeassistant',
            'homeassistant_token': 'your_token',
        }

        with patch.object(_LOGGER, 'info') as mock_log_info:
            _validate_mqtt(config)

        mock_is_running.assert_called_once_with(
            config['host'],
            config['homeassistant_token'],
        )
        mock_log_info.assert_called_once_with('MQTT configuration found')

    @patch('src.bluetracker.utils.config.is_homeassistant_running', return_value=False)
    def test_validate_mqtt_connection_error(self, _: Mock) -> None:
        """Test MQTT config with connection error should fail."""
        config = {
            'host': 'localhost',
            'port': 1234,
            'username': 'your_username',
            'password': 'your_password',
            'discovery_topic_prefix': 'homeassistant',
            'homeassistant_token': 'your_token',
        }

        with self.assertRaises(HomeAssistantConfigError):
            _validate_mqtt(config)

    def test_validate_devices_fail_amount(self) -> None:
        """Test validate devices amount should fail."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_devices_fail_amount.toml'

        with self.assertRaisesRegex(NoDevicesFoundConfigError, 'no devices found'):
            load_config(config_path)

    def test_validate_devices_fail_expected_keys(self) -> None:
        """Test validate devices expected keys should fail."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_devices_fail_config.toml'

        with self.assertRaisesRegex(
            DeviceConfigError,
            'Invalid devices config: expected keys:',
        ):
            load_config(config_path)

    def test_validate_devices_fail(self) -> None:
        """Test validate devices should fail."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_devices_fail_mac.toml'

        with self.assertRaisesRegex(InvalidMacConfigError, 'Invalid mac address'):
            load_config(config_path)

    def test_validate_devices_fail_unique_name(self) -> None:
        """Test validate devices unique name should fail."""
        config_path = (
            f'{Path.cwd()}/tests/fixtures/config_devices_fail_unique_name.toml'
        )

        with self.assertRaisesRegex(DeviceUniqueConfigError, 'name'):
            load_config(config_path)

    def test_validate_devices_fail_unique_mac(self) -> None:
        """Test validate devices unique mac should fail."""
        config_path = f'{Path.cwd()}/tests/fixtures/config_devices_fail_unique_mac.toml'

        with self.assertRaisesRegex(DeviceUniqueConfigError, 'mac'):
            load_config(config_path)
