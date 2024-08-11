"""Unittests for bluetracker.helpers.mqtt."""

import logging
from itertools import cycle
from socket import gaierror
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from src.bluetracker.helpers.mqtt_client import MqttClient


class MqttClientTestCase(TestCase):
    """Unittests for MqttClient."""

    @classmethod
    def setUpClass(cls) -> None:
        """Inititalize before all tests."""
        logging.disable()

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up after all tests."""

    def setUp(self) -> None:
        """Inititalize before each test."""
        self.patcher_ha_api_running = patch(
            'src.bluetracker.helpers.mqtt_client.is_homeassistant_running',
        )
        self.mock_ha_api_running = self.patcher_ha_api_running.start()

        self.mqttc = MqttClient('127.0.0.1', 1883, '', '', 'a_token')

    def tearDown(self) -> None:
        """Clean up after each test."""
        self.mqttc.stop()
        self.patcher_ha_api_running.stop()

    @patch('src.bluetracker.helpers.mqtt_client._LOGGER.info')
    def test_on_disconnect(self, mock_logger_info: Mock) -> None:
        """Test on disconnect."""
        self.mqttc.is_connected = True
        self.mqttc.is_homeassistant_online = True

        self.mqttc._on_disconnect(None, None, None, 1)  # noqa: SLF001

        self.assertFalse(self.mqttc.is_connected)
        self.assertFalse(self.mqttc.is_homeassistant_online)
        mock_logger_info.assert_called_once_with('Reconnecting to MQTT broker...')

    def test_on_connect_succes(self) -> None:
        """Test on connect success."""
        with (
            patch.object(self.mqttc._client, 'subscribe') as mock_subscribe,  # noqa: SLF001
            patch('src.bluetracker.helpers.mqtt_client._LOGGER') as mock_logger,
        ):
            self.mqttc._on_connect(None, None, None, 0)  # type: ignore[arg-type]  # noqa: SLF001

            self.assertTrue(self.mqttc.is_connected)
            self.assertTrue(self.mqttc.is_homeassistant_online)
            mock_subscribe.assert_called_once_with(
                f'{self.mqttc._discovery_topic_prefix}/status',  # noqa: SLF001
            )
            mock_logger.info.assert_called_once_with('Connected to MQTT broker: %s', 0)

    @patch('src.bluetracker.helpers.mqtt_client.Client.connect')
    def test_gaierror_handling(self, mock_connect: Mock) -> None:
        """Test invalid host should cause exit."""
        mock_connect.side_effect = gaierror

        with self.assertRaises(SystemExit) as cm:
            config = {
                'host': 'invalid_host',
                'port': 1234,
                'username': 'your_username',
                'password': 'your_password',
                'discovery_topic_prefix': 'homeassistant',
                'homeassistant_token': 'your_token',
            }

            client = MqttClient(**config)  # type: ignore[arg-type]
            client.start()

        self.assertEqual(cm.exception.code, 1)

    def test_on_connect_failure(self) -> None:
        """Test on connect."""
        with patch('src.bluetracker.helpers.mqtt_client._LOGGER') as mock_logger:
            self.mqttc._on_connect(None, None, None, 1)  # type: ignore[arg-type]  # noqa: SLF001

            self.assertFalse(self.mqttc.is_connected)
            self.assertFalse(self.mqttc.is_homeassistant_online)
            mock_logger.critical.assert_called_once_with(
                'Failed to connect to MQTT broker: %s',
                1,
            )

    @patch('src.bluetracker.helpers.mqtt_client._LOGGER')
    def test_start_timeout_error(self, mock_logger: Mock) -> None:
        """Test TimeoutError handling in start method."""
        mock_connect = Mock()

        mock_connect.side_effect = cycle(
            [TimeoutError('Connection timeout'), TimeoutError('Connection timeout'), 0],
        )

        with patch.object(self.mqttc._client, 'connect', mock_connect) as mock_connect:  # noqa: SLF001
            self.mqttc._client.loop_start = Mock()  # type: ignore[method-assign]  # noqa: SLF001

            self.mqttc.start()

            self.assertEqual(
                str(mock_logger.critical.call_args_list[0][0][0]),
                'Connection timeout',
            )
            self.assertEqual(
                str(mock_logger.critical.call_args_list[1][0][0]),
                'Retrying in %s seconds',
            )
        self.assertEqual(
            str(mock_logger.critical.call_args_list[2][0][0]),
            'Connection timeout',
        )
        self.assertEqual(
            str(mock_logger.critical.call_args_list[3][0][0]),
            'Retrying in %s seconds',
        )

    def test_publish(self) -> None:
        """Test publish."""
        with patch.object(self.mqttc._client, 'publish') as mock_publish:  # noqa: SLF001
            mock_result = MagicMock()
            mock_result.is_published.return_value = True
            mock_publish.return_value = mock_result

            result = self.mqttc.publish('unittest/test', 'testing', retain=False)
            self.assertTrue(result)

        with patch.object(self.mqttc._client, 'publish') as mock_publish:  # noqa: SLF001
            mock_result = MagicMock()
            mock_result.is_published.return_value = False
            mock_publish.return_value = mock_result

            result = self.mqttc.publish('unittest/test', 'testing', retain=False)
            self.assertFalse(result)

    @patch('src.bluetracker.helpers.mqtt_client._LOGGER')
    def test_on_message_online_status(self, mock_logger: Mock) -> None:
        """Tests the _on_message function when HA is online."""
        client = MagicMock()
        userdata = None
        message = MagicMock()
        message.payload = b'online'

        self.mqttc._on_message(client, userdata, message)  # noqa: SLF001

        self.assertTrue(self.mqttc.is_homeassistant_online)
        mock_logger.debug.assert_called_once_with('Home Assistant online: %s', True)  # noqa: FBT003

    @patch('src.bluetracker.helpers.mqtt_client._LOGGER')
    def test_on_message_offline_status(self, mock_logger: Mock) -> None:
        """Tests the _on_message function when HA is offline."""
        client = MagicMock()
        userdata = None
        message = MagicMock()
        message.payload = b'offline'

        self.mqttc._on_message(client, userdata, message)  # noqa: SLF001

        self.assertFalse(self.mqttc.is_homeassistant_online)
        mock_logger.debug.assert_called_once_with('Home Assistant online: %s', False)  # noqa: FBT003
