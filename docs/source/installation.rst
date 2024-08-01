Installation
============

.. note:: Instructions below have been tested on a Raspberry Pi Zero W Rev 1.1 and Zero 2.


On Home Assistant
*****************

Ensure following add-on and integration are installed on Home Assistant:

- `MQTT Add-on <https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md/>`_: Broker to send/receive data from MQTT clients.
- `MQTT Integration <https://www.home-assistant.io/integrations/mqtt/>`_: Receive updates from the MQTT broker add-on.

On Raspberry
*************

BlueTracker
~~~~~~~~~~~

Ensure bluetooth is working:

.. code-block:: console

	hciconfig

Set up a virtual environment:

.. code-block:: console

    cd && mkdir bluetracker && cd bluetracker
    python -m venv .env
    source .env/bin/activate

Install the ``bluetracker`` package from PyPi:

.. code-block:: console

    pip install --upgrade pip setuptools
    pip install bluetracker

Run in the console:

.. code-block:: console

    bluetracker

On the first run BlueTracker will create a configuration file in the current directory.

Modify to:

- update the Home Assistant MQTT server settings.
- add bluetooth classic devices that should be tracked.

Configuration options are avalable :doc:`here <../configuration>`.

.. code-block:: console

    nano bluetracker_config.toml

Run again in the console:

.. code-block:: console

    bluetracker

Once BlueTracker is running, bluetooth devices with their
state (``home`` or ``not_home``) and attributes are automatically added to
Home Assistant using the
`MQTT Discovery protocol <https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery>`_.

Find them under the MQTT devices section in Home Assistant:

.. image:: https://my.home-assistant.io/badges/integration.svg
    :target: https://my.home-assistant.io/redirect/integration/?domain=mqtt
    :alt: Open your Home Assistant instance and show an integration.


systemd.service
~~~~~~~~~~~~~~~

To run BlueTracker on system startup, create a systemd service.

.. code-block:: console

    sudo nano /etc/systemd/system/bluetracker.service

.. code-block:: console

    [Unit]
    Description=BlueTracker
    After=network.target

    [Service]
    Type=idle
    User=pi
    WorkingDirectory=/home/pi/bluetracker/
    Environment="VIRTUAL_ENV=/home/pi/bluetracker/.env"
    Environment="Environment=PATH=$VIRTUAL_ENV/bin:$PATH"
    ExecStart=/home/pi/bluetracker/.env/bin/python .env/bin/bluetracker
    Restart=on-failure
    StartLimitInterval=60
    StartLimitBurst=5
    KillSignal=SIGINT

    [Install]
    WantedBy=multi-user.target

Load the service.

.. code-block:: console

    sudo systemctl daemon-reload
    sudo systemctl enable bluetracker.service --now

Check the status.

.. code-block:: console

    sudo systemctl status bluetracker.service

Check the output.

.. code-block:: console

    journalctl -u bluetracker.service -n 10
