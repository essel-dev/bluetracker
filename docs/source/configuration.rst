Configuration Options
=====================

On first startup, BlueTracker copies the default configuration from ``config.toml``
to ``bluetracker_config.toml``.

This provides a template configuration file that users can easily modify to suit their
specific MQTT broker settings and the devices they want to track.

.. literalinclude:: ../../src/bluetracker/config.toml
    :language: python


The available options are shown in the table below.



.. list-table:: BlueTracker configuration
   :widths: auto
   :header-rows: 1

   * - Name
     - Description
   * - ``environment``
     - Sets the environment for the application (production, development, or testing).

       This affects logging levels and other behaviors. Not required, defaults to production.
   * - ``bluetooth``
     - .. list-table:: Bluetooth settings
          :widths: auto
          :header-rows: 1

          * - Name
            - Description
          * - ``consider_away``
            - Seconds to wait to mark a device as away.
          * - ``scan_interval``
            - Seconds to wait between scans.
          * - ``scan_timeout``
            - Seconds to wait for a device response.
   * - ``mqtt``
     - .. list-table:: MQTT settings
          :widths: auto
          :header-rows: 1

          * - Name
            - Description
          * - ``discovery_topic_prefix``
            - Discovery prefix for Home Assistant.
          * - ``homeassistant_token``
            - Home Assistant token.
          * - ``host``
            - Host ip address.
          * - ``password``
            - Password.
          * - ``port``
            - Port.
          * - ``username``
            - Username.
   * - ``devices``
     - .. list-table:: Bluetooth devices
          :widths: auto
          :header-rows: 1

          * - Name
            - Description
          * - ``mac``
            - Unique device mac address.
          * - ``name``
            - Unique device name.
