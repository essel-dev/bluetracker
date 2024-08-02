"""BlueTracker - Bluetooth Device Presence Tracking via MQTT.

This Python package provides classes for tracking the presence of Bluetooth devices and
reporting their status (home/not_home) to Home Assistant using MQTT.

Introduction
------------

Key Components
~~~~~~~~~~~~~~

* :py:class:`BlueScanner`: Handles the actual Bluetooth scanning process.
* :py:class:`BlueTracker`: Manages the tracking of devices and interaction with Home
  Assistant via MQTT.
* :py:class:`Device`: Represents a Bluetooth device being tracked (name, MAC address,
  state).
* :py:class:`MqttClient`: Handles communication with the MQTT broker.


Functionality
~~~~~~~~~~~~~

* BlueTracker periodically scans for Bluetooth devices using BlueScanner.
* Device states (home/not_home) and attributes are published to Home Assistant via MQTT.
* BlueTracker actively monitors the connection to Home Assistant. If the connection is
  lost, scanning will pause and automatically resume when the connection is restored.


Programmatic Usage
~~~~~~~~~~~~~~~~~~

#. Create a :py:class:`BlueScanner` instance for Bluetooth scanning.
#. Create an :py:class:`MqttClient` instance to connect to your MQTT broker.
#. Create a list of :py:class:`Device` objects representing the devices to track.
#. Instantiate :py:class:`BlueTracker` with the scanner, MQTT client, and device list.
#. Call the :py:class:`BlueTracker.run()` to start tracking.
#. When finished, call :py:class:`BlueTracker.stop()` to gracefully stop the service.


Example Code
~~~~~~~~~~~~

.. code-block:: python

    from bluetracker import BlueTracker, BlueScanner, MqttClient, Device, DeviceType

    devices = [
        Device("My Phone", "AA:BB:CC:DD:EE:FF"),
        Device("My Tablet", "11:22:33:44:55:66")
    ]

    scanner = BlueScanner(scan_interval=30, scan_timeout=5, consider_away=60)
    mqttc = MqttClient(host="your_mqtt_broker", port=1883, ...)

    tracker = BlueTracker(scanner, mqttc, devices)

    try:
        tracker.run()
    except KeyboardInterrupt:  # Graceful shutdown on Ctrl+C
        tracker.stop()


Automatic Setup and Execution with __main__.py
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

BlueTracker uses a ``bluetracker_config.toml`` file for configuration.  If it doesn't
exist, a default one will be created on the first run.

#. Install BlueTracker: ``pip install bluetracker``
#. Edit the Configuration: modify the bluetracker_config.toml file according to your
   MQTT broker settings and the devices you want to track.
#. Run BlueTracker: Execute bluetracker in your terminal.
#. A signal handler is provided for graceful shutdown on SIGINT (e.g., Ctrl+C).

.. literalinclude:: ../../src/bluetracker/__main__.py
    :language: python
"""

from bluetracker.helpers.mqtt_client import MqttClient

from .core import BlueScanner, BlueTracker, BlueTrackerTypeError
from .models.device import (
    Device,
    DeviceResponse,
    DeviceState,
    DeviceType,
)

__all__ = [
    'BlueTracker',
    'BlueTrackerTypeError',
    'BlueScanner',
    'MqttClient',
    'Device',
    'DeviceState',
    'DeviceResponse',
    'DeviceType',
]
