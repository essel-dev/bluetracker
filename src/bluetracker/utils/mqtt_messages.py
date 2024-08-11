"""MQTT client utilities module."""

from collections.abc import Collection
from dataclasses import dataclass, field
from enum import Enum, StrEnum
from importlib.metadata import version as get_version
from json import dumps
from socket import (
    AF_INET,
    SOCK_DGRAM,
    gethostname,
    socket,
)
from typing import Final, cast
from uuid import getnode

from ..helpers.mqtt_client import MqttClient  # noqa: TID252
from ..models.device import Device, DeviceType  # noqa: TID252

MAC: Final = ':'.join(f'{getnode():012x}'[i : i + 2] for i in range(0, 12, 2))

HOSTNAME: Final = gethostname()

s = socket(AF_INET, SOCK_DGRAM)
s.connect(('1.1.1.1', 0))
IP_ADDRESS: Final = s.getsockname()[0]

OBJECT_ID: Final = f'bluetracker_{HOSTNAME}'

DEVICE: Final = {
    'identifiers': OBJECT_ID,
    'connections': [['mac', MAC]],
    'manufacturer': 'BlueTracker',
    'name': f'BlueTracker {HOSTNAME.title()}',
    'sw_version': get_version('bluetracker-hass-mqtt'),
}


class TopicType(Enum):
    """The MQTT topic."""

    CONFIG = 'config'
    STATE = 'state'
    AVAIL = 'availability'
    ATTR = 'attributes'


@dataclass
class TopicConfiguration:
    """The MQTT topic configuration."""

    name: str
    unique_id: str
    topic: str
    state_topic: str = field(default=f'~/{TopicType.STATE.value}')
    availability_topic: str = field(default=f'~/{TopicType.AVAIL.value}')
    json_attributes_topic: str = field(default=f'~/{TopicType.ATTR.value}')
    device: dict[str, dict[str, str]] = field(default_factory=lambda: DEVICE)  # type: ignore[arg-type,return-value]
    source_type: str | None = field(default=None)
    device_class: str | None = field(default=None)
    entity_category: str | None = field(default=None)
    state_class: str | None = field(default=None)

    def to_dict(self) -> dict[str, Collection[str]]:
        """Get the topic configuration as a dictionary.

        Returns:
            The topic configuratio as a dictionary.
        """
        config = {
            'name': self.name,
            'unique_id': self.unique_id,
            '~': self.topic,
            'state_topic': self.state_topic,
            'availability_topic': self.availability_topic,
            'json_attributes_topic': self.json_attributes_topic,
            'device': self.device,
        }

        if self.source_type:
            config['source_type'] = self.source_type
        if self.device_class:
            config['device_class'] = self.device_class
        if self.entity_category:
            config['entity_category'] = self.entity_category
        if self.state_class:
            config['state_class'] = self.state_class

        return config


@dataclass
class Message:
    """The MQTT message."""

    topic: str
    payload: str


class MessageType(StrEnum):
    """The MQTT message type."""

    DEVICE = 'Device'
    SERVER_CONFIG = 'Server Config'
    SERVER_STATUS = 'Server Status'


def publish(
    item: str | dict[str, Collection[object]] | Device,
    message_type: MessageType,
    topic_type: TopicType,
    mqttc: MqttClient,
) -> None:
    """Publish a message to an MQTT broker.

    Args:
        item: The item that should be published.
        message_type: The MQTT message type.
        topic_type: The MQTT topic type to publish.
        mqttc: The MQTT client.
    """
    topic_prefix = mqttc._discovery_topic_prefix  # noqa: SLF001

    messages: list[Message] = []

    match message_type:
        case MessageType.DEVICE:
            messages = _device(cast(Device, item), topic_prefix, topic_type)
        case MessageType.SERVER_STATUS:
            messages = _server_status(cast(str, item), topic_prefix, topic_type)
        case MessageType.SERVER_CONFIG:
            ip = _server_ip(topic_prefix)
            bluetooth = _bluetooth_config(
                cast(dict[str, str], item['bluetooth']),  # type: ignore[index]
                topic_prefix,
            )
            devices = _tracking_devices_total(
                cast(list[Device], item['devices']),  # type: ignore[index]
                topic_prefix,
            )

            messages = ip + bluetooth + devices

    for message in messages:
        mqttc.publish(message.topic, message.payload, retain=False)


def _device(
    device: Device,
    topic_prefix: str,
    topic_type: TopicType,
) -> list[Message]:
    device_name = device.name.lower().replace(' ', '_')
    topic = f'{topic_prefix}/device_tracker/{OBJECT_ID}/{HOSTNAME}_{device_name}'

    messages: list[Message] = []

    # https://github.com/python/mypy/issues/12545 match case with enums
    match topic_type:
        case topic_type.CONFIG | topic_type.AVAIL:
            config = TopicConfiguration(  # type: ignore[unreachable]
                name=f'{device.name}',
                unique_id=f'{HOSTNAME}_{device.name}',
                topic=topic,
                source_type=DeviceType.BLUETOOTH.value,
            )

            messages = [
                Message(
                    topic=f'{topic}/{TopicType.CONFIG.value}',
                    payload=dumps(config.to_dict()),
                ),
                Message(
                    topic=f'{topic}/{TopicType.AVAIL.value}',
                    payload='online',
                ),
            ]

        case topic_type.STATE | topic_type.ATTR:
            messages = [  # type: ignore[unreachable]
                Message(
                    topic=f'{topic}/{TopicType.STATE.value}',
                    payload=device.state.value,
                ),
                Message(
                    topic=f'{topic}/{TopicType.ATTR.value}',
                    payload=dumps(device.to_dict()),
                ),
            ]

    return messages


def _server_status(
    state: str,
    topic_prefix: str,
    topic_type: TopicType,
) -> list[Message]:
    topic = f'{topic_prefix}/binary_sensor/{OBJECT_ID}/{HOSTNAME}_running'

    messages: list[Message] = []

    # https://github.com/python/mypy/issues/12545 match case with enums
    match topic_type:
        case topic_type.CONFIG | topic_type.AVAIL:
            config = TopicConfiguration(  # type: ignore[unreachable]
                name='Running',
                unique_id=f'{HOSTNAME}_running',
                device_class='running',
                topic=topic,
            )

            messages = [
                Message(
                    topic=f'{topic}/{TopicType.CONFIG.value}',
                    payload=dumps(config.to_dict()),
                ),
                Message(
                    topic=f'{topic}/{TopicType.AVAIL.value}',
                    payload='online',
                ),
            ]

        case topic_type.STATE | topic_type.ATTR:
            messages = [  # type: ignore[unreachable]
                Message(
                    topic=f'{topic}/{TopicType.STATE.value}',
                    payload=state,
                ),
            ]

    return messages


def _server_ip(topic_prefix: str) -> list[Message]:
    topic = f'{topic_prefix}/sensor/{OBJECT_ID}/{HOSTNAME}_ip_address'

    messages: list[Message] = []

    config = TopicConfiguration(
        name='IP Address',
        unique_id=f'{HOSTNAME}_ip_address',
        entity_category='diagnostic',
        topic=topic,
    )

    messages.append(
        Message(
            topic=f'{topic}/{TopicType.CONFIG.value}',
            payload=dumps(config.to_dict()),
        ),
    )
    messages.append(
        Message(
            topic=f'{topic}/{TopicType.AVAIL.value}',
            payload='online',
        ),
    )
    messages.append(
        Message(
            topic=f'{topic}/{TopicType.STATE.value}',
            payload=IP_ADDRESS,
        ),
    )

    return messages


def _bluetooth_config(
    bluetooth_config: dict[str, str],
    topic_prefix: str,
) -> list[Message]:
    messages: list[Message] = []

    for key, value in bluetooth_config.items():
        topic = f'{topic_prefix}/sensor/{OBJECT_ID}/{HOSTNAME}_{key}'
        config = TopicConfiguration(
            name=f'{key.replace("_", " ").title()}',
            unique_id=f'{HOSTNAME}_{key}',
            entity_category='diagnostic',
            topic=topic,
        )

        messages.append(
            Message(
                topic=f'{topic}/{TopicType.CONFIG.value}',
                payload=dumps(config.to_dict()),
            ),
        )
        messages.append(
            Message(
                topic=f'{topic}/{TopicType.AVAIL.value}',
                payload='online',
            ),
        )
        messages.append(
            Message(
                topic=f'{topic}/{TopicType.STATE.value}',
                payload=value,
            ),
        )

    return messages


def _tracking_devices_total(
    devices: list[Device],
    topic_prefix: str,
) -> list[Message]:
    messages: list[Message] = []

    topic = f'{topic_prefix}/sensor/{OBJECT_ID}/{HOSTNAME}_tracking_devices'
    config = TopicConfiguration(
        name='Tracking Devices',
        unique_id=f'{HOSTNAME}_tracking_devices',
        state_class='total',
        entity_category='diagnostic',
        topic=topic,
    )

    messages.append(
        Message(
            topic=f'{topic}/{TopicType.CONFIG.value}',
            payload=dumps(config.to_dict()),
        ),
    )
    messages.append(
        Message(
            topic=f'{topic}/{TopicType.AVAIL.value}',
            payload='online',
        ),
    )
    messages.append(
        Message(
            topic=f'{topic}/{TopicType.STATE.value}',
            payload=str(len(devices)),
        ),
    )

    devices_dict = [{'name': device.name, 'mac': device.mac} for device in devices]
    messages.append(
        Message(
            topic=f'{topic}/{TopicType.ATTR.value}',
            payload=dumps({'devices': devices_dict}),
        ),
    )

    return messages
