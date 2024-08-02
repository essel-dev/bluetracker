"""Unittests for bluetracker.utils.mqtt_messages."""

from itertools import cycle
from socket import gethostname
from unittest import TestCase
from unittest.mock import call, patch

from src.bluetracker.models.device import Device, DeviceType
from src.bluetracker.utils.config import BlueTrackerConfig, Environment
from src.bluetracker.utils.mqtt_messages import MessageType, TopicType, publish


class MqttMessagesTestCase(TestCase):
    """Unittests for Mqtt messages."""

    def setUp(self) -> None:
        """Inititalize before each test."""
        self.patcher_mqttc = patch('src.bluetracker.helpers.mqtt_client.MqttClient')
        self.mqttc_mock = self.patcher_mqttc.start()
        self.mqttc_mock._discovery_topic_prefix = 'homeassistant'

        self.patcher_sleep = patch('src.bluetracker.utils.mqtt_messages.sleep')
        self.mock_sleep = self.patcher_sleep.start()

    def tearDown(self) -> None:
        """Clean up after each test."""
        self.patcher_mqttc.stop()
        self.patcher_sleep.stop()

    def test_publish_device_tracker(self) -> None:
        """Test publish device_tracker config and state."""
        device = Device('test device', 'aa:bb:cc:dd:ee:ff', DeviceType.BLUETOOTH)
        hostname = gethostname()
        device_name = device.name.replace(' ', '_')
        topic = (
            f'{self.mqttc_mock._discovery_topic_prefix}/device_tracker/'
            f'bluetracker_{hostname}/{hostname}_{device_name}'
        )

        publish(device, MessageType.DEVICE, TopicType.CONFIG, self.mqttc_mock)
        call_1, call_2 = self.mqttc_mock.publish.call_args_list

        self.assertEqual(self.mqttc_mock.publish.call_count, 2)

        self.assertEqual(call_1[0][0], f'{topic}/config')
        self.assertEqual(call_1[1], {'retain': False})

        self.assertEqual(call_2[0][0], f'{topic}/availability')
        self.assertEqual(call_2[1], {'retain': False})

        self.mqttc_mock.reset_mock()

        publish(device, MessageType.DEVICE, TopicType.STATE, self.mqttc_mock)
        call_1, call_2 = self.mqttc_mock.publish.call_args_list

        self.assertEqual(self.mqttc_mock.publish.call_count, 2)

        self.assertEqual(call_1[0][0], f'{topic}/state')
        self.assertEqual(call_1[0][1], 'not_home')
        self.assertEqual(call_1[1], {'retain': False})

        self.assertEqual(call_2[0][0], f'{topic}/attributes')
        self.assertEqual(call_2[1], {'retain': False})

    def test_publish_server_status(self) -> None:
        """Test publish server status config and state."""
        hostname = gethostname()
        topic = (
            f'{self.mqttc_mock._discovery_topic_prefix}/binary_sensor/'
            f'bluetracker_{hostname}/{hostname}_running'
        )

        publish('', MessageType.SERVER_STATUS, TopicType.CONFIG, self.mqttc_mock)
        call_1, call_2 = self.mqttc_mock.publish.call_args_list

        self.assertEqual(self.mqttc_mock.publish.call_count, 2)

        self.assertEqual(call_1[0][0], f'{topic}/config')
        self.assertEqual(call_1[1], {'retain': False})

        self.assertEqual(call_2[0][0], f'{topic}/availability')
        self.assertEqual(call_2[1], {'retain': False})

        self.mqttc_mock.reset_mock()

        publish('ON', MessageType.SERVER_STATUS, TopicType.STATE, self.mqttc_mock)
        call_1 = self.mqttc_mock.publish.call_args_list[0]

        self.assertEqual(self.mqttc_mock.publish.call_count, 1)

        self.assertEqual(call_1[0][0], f'{topic}/state')
        self.assertEqual(call_1[0][1], 'ON')
        self.assertEqual(call_1[1], {'retain': False})

    def test_publish_server_config(self) -> None:
        """Test publish server config and state."""
        bluetracker_config = BlueTrackerConfig(
            environment=Environment.DEV,
            bluetooth={'consider_away': 180, 'scan_interval': 12, 'scan_timeout': 3},
            mqtt={
                'host': '127.0.0.1',
                'password': 'a_password',
                'port': 1883,
                'user': 'a_user',
            },
            devices=[
                {'mac': 'aa:bb:cc:dd:ee:f0', 'name': 'Device 1'},
                {'mac': 'aa:bb:cc:dd:ee:f1', 'name': 'Device 2'},
            ],
        )
        hostname = gethostname()
        topic = (
            f'{self.mqttc_mock._discovery_topic_prefix}/sensor/'
            f'bluetracker_{hostname}/{hostname}'
        )

        server_config = {
            'bluetooth': bluetracker_config.bluetooth,
            'devices': [
                Device('test device', 'aa:bb:cc:dd:ee:ff', DeviceType.BLUETOOTH),
            ],
        }

        publish(
            server_config,
            MessageType.SERVER_CONFIG,
            TopicType.CONFIG,
            self.mqttc_mock,
        )
        calls = self.mqttc_mock.publish.call_args_list

        self.assertEqual(self.mqttc_mock.publish.call_count, 4 * 3 + 1 * 4)
        # 4 config and state + 1 config, state and attr

        ip_address = f'{topic}_ip_address'
        self.assertEqual(calls[0][0][0], f'{ip_address}/config')
        self.assertEqual(calls[0][1], {'retain': False})

        self.assertEqual(calls[1][0][0], f'{ip_address}/availability')
        self.assertEqual(calls[1][1], {'retain': False})

        self.assertEqual(calls[2][0][0], f'{ip_address}/state')
        self.assertEqual(calls[2][1], {'retain': False})

        # skip bluetooth

        tracking_devices = f'{topic}_tracking_devices'
        self.assertEqual(calls[12][0][0], f'{tracking_devices}/config')
        self.assertEqual(calls[12][1], {'retain': False})

        self.assertEqual(calls[13][0][0], f'{tracking_devices}/availability')
        self.assertEqual(calls[13][1], {'retain': False})

        self.assertEqual(calls[14][0][0], f'{tracking_devices}/state')
        self.assertEqual(calls[14][1], {'retain': False})

        self.assertEqual(calls[15][0][0], f'{tracking_devices}/attributes')
        self.assertEqual(calls[15][1], {'retain': False})

    def test_publish_with_retries(self) -> None:
        """Test that the publish function correctly retries when it fails."""
        self.mqttc_mock.publish.side_effect = cycle([False, True])
        device = Device('test device', 'aa:bb:cc:dd:ee:ff', DeviceType.BLUETOOTH)

        publish(device, MessageType.DEVICE, TopicType.CONFIG, self.mqttc_mock)

        self.assertEqual(self.mqttc_mock.publish.call_count, 4)
        self.mock_sleep.assert_has_calls([call(0.1), call(0.1)])
