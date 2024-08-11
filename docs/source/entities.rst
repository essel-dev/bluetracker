Home Assistant Entities
=======================

Entities are automatically added to Home Assistant using the
`MQTT Discovery protocol <https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery>`_.

Find them under the MQTT devices section in Home Assistant:

.. image:: https://my.home-assistant.io/badges/integration.svg
    :target: https://my.home-assistant.io/redirect/integration/?domain=mqtt
    :alt: Open your Home Assistant instance and show an integration.

.. note::
  Within each server running ``BlueTracker``, entities are grouped together. These groups
  are identified by names that begin with ``bluetracker_`` followed by the unique server
  hostname, such as ``bluetracker_penguin_``.

The following entities are available:

.. list-table::
   :header-rows: 1

   * - Sensor
     - Type
     - Description

   * - Device
     - ``device_tracker``
     - The bluetooth device to track.

   * - Running
     - ``binary_sensor``
     - Whether BlueTracker is running or not.

   * - Consider Away
     - ``sensor``
     - Seconds to wait to mark a device as away.

   * - Scan Interval
     - ``sensor``
     - Seconds to wait between scans.

   * - Scan Timeout
     - ``sensor``
     - Seconds to wait for a device response.

   * - IP Address
     - ``sensor``
     - The server IP address

   * - Tracking Devices
     - ``sensor``
     - The number of devices being tracked.
