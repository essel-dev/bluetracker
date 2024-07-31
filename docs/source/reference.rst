API Reference
=============

.. currentmodule:: bluetracker

The main function of the ``BlueTracker`` instance is to monitor all the
devices and publish their state to Home Assistant.

#. The BlueTracker-project contains a default ``config.toml`` that shoud be copied and
   adapted.
   See :ref:`configuration<configuration>` options.

#. The :py:meth:`~BlueTracker.__init__` method initializes a
   :py:class:`~BlueTracker` and creates multiple
   :py:class:`~Device` s to track.

#. The :py:meth:`~BlueTracker.run` method continuously scans devices and
   publishes them to MQTT.


Example:

.. literalinclude:: ../../src/bluetracker/__main__.py
    :language: python


The BlueTracker Class
---------------------

.. autoclass:: BlueTracker
.. autoclass:: BlueTrackerTypeError


The BlueScanner Class
---------------------

.. autoclass:: BlueScanner


The MQTT Client
---------------

.. autoclass:: MqttClient


Device state and attributes
---------------------------

.. autoclass:: Device

|

.. autoclass:: DeviceType

|

.. autoclass:: DeviceState

|

.. autoclass:: DeviceResponse
