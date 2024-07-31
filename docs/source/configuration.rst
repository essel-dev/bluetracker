Configuration
=============

On first startup, BlueTracker copies the default configuration from ``config.toml``
to ``bluetracker_config.toml``:

.. literalinclude:: ../../src/bluetracker/config.toml
    :language: python


The available options are shown in the table below.



.. list-table:: BlueTracker configuration
   :widths: auto
   :header-rows: 1

   * - Name
     - Description
   * - ``environment``
     - Environment to use. Supported formats are ``production``, ``development`` or ``testing``.
       Not required.
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
