"""Communicate with MQTT broker."""

import sys
from logging import getLogger
from socket import gaierror, gethostname
from time import sleep
from typing import Any

from paho.mqtt.client import Client

# mypy: disable-error-code="import-untyped"
from paho.mqtt.enums import CallbackAPIVersion

from bluetracker.utils.homeassistant import is_homeassistant_running

_LOGGER = getLogger(__name__)


class MqttClient:
    """A client to connect to an MQTT broker to publish messages."""

    def __init__(  # noqa: PLR0913
        self,
        host: str,
        port: int,
        username: str,
        password: str,
        homeassistant_token: str,
        discovery_topic_prefix: str = 'homeassistant',
    ) -> None:
        """Initialize the MQTT client.

        Args:
            host: The MQTT host.
            port: The MQTT port.
            username: The MQTT username.
            password: The MQTT password.
            homeassistant_token: The Home Assistant token.
            discovery_topic_prefix: The MQTT discovery prefix for Home Assistant.
        """
        client_id = f'bluetracker_{gethostname()}'

        self._host: str = host
        self._port: int = port

        self._client: Client = Client(CallbackAPIVersion.VERSION2, client_id=client_id)
        self._client.username_pw_set(username, password)

        self._discovery_topic_prefix = discovery_topic_prefix

        self._homeassistant_token = homeassistant_token

        self._client.on_connect = self._on_connect
        self._client.on_disconnect = self._on_disconnect
        self._client.on_message = self._on_message  # type: ignore[assignment]

        self.is_connected: bool = False
        """Indicates whether the client is currently connected to the MQTT broker."""

        self.is_homeassistant_online: bool = False
        """Indicates whether Home Assistant is currently online based on the
        received MQTT messages.

        This attribute is typically updated by the `_on_message` method
        when receiving status messages from Home Assistant.
        """

        self._client.will_set(f'{client_id}/status', b'offline', retain=True)

    def _on_connect(  # type: ignore[no-untyped-def]
        self,
        client,  # noqa: ARG002, ANN001
        userdata: str,  # noqa: ARG002
        flags,  # noqa: ARG002, ANN001
        rc: int,
        properties=None,  # noqa: ARG002, ANN001
    ) -> None:
        """Handles the CONNACK response from the MQTT broker.

        Updates internal state and subscribes to the discovery topic on successful
        connection.

        Args:
            client: The MQTT client object (unused).
            userdata: The user data provided to the client (optional, unused).
            flags: The flags included in the CONNACK response (unused).
            rc: The reason code for the connection attempt.
            properties: The connection acknowledgment properties (optional, unused).
        """
        if rc == 0:
            self.is_connected = True
            self.is_homeassistant_online = is_homeassistant_running(
                self._host,
                self._homeassistant_token,
            )

            # Subscribing in on_connect() means that if we lose the connection and
            # reconnect then subscriptions will be renewed.
            self._client.subscribe(f'{self._discovery_topic_prefix}/status')

            _LOGGER.info('Connected to MQTT broker: %s', rc)
        else:
            self.is_connected = False
            self.is_homeassistant_online = False

            _LOGGER.critical('Failed to connect to MQTT broker: %s', rc)

    def _on_disconnect(  # type: ignore[no-untyped-def]
        self,
        client,  # noqa: ARG002, ANN001
        userdata,  # noqa: ARG002, ANN001
        flags,  # noqa: ARG002, ANN001
        rc,  # noqa: ARG002, ANN001
        properties=None,  # noqa: ARG002, ANN001
    ) -> None:
        """Reconnect on disconnect.

        Args:
            client: The client.
            userdata: The user data.
            flags: The flags.
            rc: The response code.
            properties: The properties.
        """
        self.is_connected = False
        self.is_homeassistant_online = False

        _LOGGER.info('Reconnecting to MQTT broker...')

    def _on_message(self, client: Client, userdata: Any, message: bytes) -> None:  # noqa: ARG002,ANN401  # type: ignore[no-untyped-def]
        """On message set Home Assistant status.

        When a PUBLISH message is received from the server.

        Args:
            client: The client.
            userdata: The user data.
            message: The message.
        """
        status = message.payload.decode()  # type: ignore[attr-defined]
        self.is_homeassistant_online = status == 'online'

        _LOGGER.debug('Home Assistant online: %s', self.is_homeassistant_online)

    def publish(self, topic: str, payload: str, *, retain: bool = False) -> bool:
        """Publish a message to the MQTT broker.

        Waits for connection if not already connected and returns success based
        on the publish result code.

        Args:
            topic: The MQTT topic to publish to.
            payload: The message to publish.
            retain: Whether the message should be retained by the broker.

        Returns:
            `True` if the message was published successfully, `False` otherwise.
        """
        result = self._client.publish(topic, payload, retain=retain)

        if result[0] == 0:
            success = True
            _LOGGER.debug('Published %s', topic)
        else:
            success = False
            _LOGGER.error('Failed to publish %s', topic)

        return success

    def start(self) -> None:
        """Start a connection to the MQTT broker."""
        _LOGGER.info('Connecting to MQTT broker...')

        self._client.loop_start()

        reconnect_delay = 1
        max_delay = 60
        result = None
        while result != 0 and not self.is_homeassistant_online:
            try:
                result = self._client.connect(self._host, self._port, keepalive=120)
            except (gaierror, ConnectionError) as error:
                _LOGGER.critical(error)
                self.stop()
                sys.exit(1)
            except (TimeoutError, ConnectionRefusedError) as error:
                _LOGGER.critical(error)

                _LOGGER.critical('Retrying in %s seconds', reconnect_delay)
                sleep(reconnect_delay)

                reconnect_delay *= 2
                reconnect_delay = min(reconnect_delay, max_delay)

    def stop(self) -> None:
        """Stop the connection to the MQTT broker."""
        self._client.disconnect()
        self._client.loop_stop()
