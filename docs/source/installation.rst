BlueTracker Installation Guide
==============================


.. note:: Tested on Debian and Raspbian with Raspberry Zero W Rev 1.1 and Zero 2.

   While BlueTracker should work on other Linux distributions with BlueZ installed,
   it has only been tested on the specified configurations.


Prerequisites
*************

Before you begin, ensure you have the following:

    - Hardware:

      - A Linux system with Bluetooth.
      - BlueZ must be installed, including the ``hciconfig`` and ``hcitool`` commands.

    - Software:

      - Home Assistant with MQTT Add-on and MQTT Integration installed.


Installation on Home Assistant
******************************

Ensure following add-on and integration are installed on Home Assistant:

- `MQTT Add-on <https://github.com/home-assistant/addons/blob/master/mosquitto/DOCS.md/>`_: Broker to send/receive data from MQTT clients.
- `MQTT Integration <https://www.home-assistant.io/integrations/mqtt/>`_: Receive updates from the MQTT broker add-on.

Installation on Linux
*********************

#. Verify BlueZ Installation:

   Before proceeding, make sure that BlueZ is correctly installed on your system::

      dpkg -l | grep bluez


#. Verify Bluetooth is running::

      hciconfig


   The output should look similar to this, indicating that your Bluetooth adapter is recognized and enabled::

      hci0:	Type: Primary  Bus: UART
         BD Address: XX:XX:XX:XX:XX:XX  ACL MTU: 1021:8  SCO MTU: 64:1
         UP RUNNING
         RX bytes:2911 acl:0 sco:0 events:217 errors:0
         TX bytes:33155 acl:0 sco:0 commands:217 errors:0

#. Create a Virtual Environment::

      cd && mkdir bluetracker && cd bluetracker
      python -m venv .env
      source .env/bin/activate

#. Install BlueTracker from PyPi::

      pip install --upgrade pip setuptools bluetracker


Configuration
*************

#. Create Configuration File:

   Run BlueTracker once to generate the configuration file (``bluetracker_config.toml``)::

      bluetracker

#. Edit Configuration:

   - Open the config file using a text editor::

       nano bluetracker_config.toml

   - For more information, please refer to the complete :doc:`BlueTracker configuration documentation <../configuration>`.

Running BlueTracker
*******************

#. Start BlueTracker::

      bluetracker

#. Check Home Assistant:

   Once BlueTracker is running, bluetooth devices with their
   state (``home`` or ``not_home``) and attributes are automatically added to
   Home Assistant using the
   `MQTT Discovery protocol <https://www.home-assistant.io/integrations/mqtt/#mqtt-discovery>`_.

   For more detailed information on the entities created and their attributes, refer to
   :doc:`Entities Explained in Detail <../entities>`.

   Find them under the MQTT devices section in Home Assistant:

   .. image:: https://my.home-assistant.io/badges/integration.svg
      :target: https://my.home-assistant.io/redirect/integration/?domain=mqtt
      :alt: Open your Home Assistant instance and show an integration.

Running on System Startup
*************************

To guarantee that BlueTracker automatically launches every time your system boots up
and continues to run without interruption, you can configure a systemd service
(responsible for initiating the program at boot time) and a cron job
(tasked with regularly verifying that the program remains active).

#. To run BlueTracker on system startup, create a systemd service.

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
      Restart=always
      KillSignal=SIGINT

      [Install]
      WantedBy=multi-user.target

#. Load the service::

      sudo systemctl daemon-reload
      sudo systemctl enable bluetracker --now

#. Check the status::

      sudo systemctl status bluetracker

#. Check the output:

   .. code-block:: console

      journalctl -u bluetracker -n 10

   .. code-block:: console

      journalctl -u bluetracker -f

#. Schedule with Cron:

   - Open your crontab file::

        sudo crontab -u root -e

   - Add the following lines to run the script every 5 minutes::

        */5 * * * * pgrep -x bluetracker || /usr/sbin/service bluetracker start 2>&1
