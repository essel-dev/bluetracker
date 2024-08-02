"""Unittests for bluetracker.__main__."""

from __future__ import annotations

import logging
import sys
from io import StringIO
from pathlib import Path
from signal import SIGINT
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from src.bluetracker.__main__ import create_signal_handler, main
from src.bluetracker.core import BlueScanner, BlueTracker
from src.bluetracker.models.device import Device, DeviceType


class MainTestCase(TestCase):
    """Unittests for __main__."""

    file_ = Path.cwd().joinpath('bluetracker_config.toml')
    file_backup = None

    @classmethod
    def setUpClass(cls) -> None:
        """Inititalize before all tests."""
        logging.disable()

        if cls.file_.exists():
            cls.file_backup = cls.file_.rename(f'{cls.file_}.bak')

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up after all tests."""
        if cls.file_.exists():
            cls.file_.unlink()

        if cls.file_backup and cls.file_backup.exists():
            cls.file_backup.rename(cls.file_backup.name.removesuffix('.bak'))

    @patch('bluetracker.__main__.BlueTracker')
    def test_main_new_config(self, _: Mock) -> None:
        """Test create new configuration file."""
        if self.file_.exists():
            self.file_.unlink()

        with (
            patch.object(sys, 'stdout', StringIO()) as output,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn('First run, configuration file copied to', output.getvalue())
        self.assertIn('Modify as required and restart.', output.getvalue())
        self.assertIn('.toml', output.getvalue())

    @patch('bluetracker.utils.homeassistant.is_homeassistant_running')
    @patch('bluetracker.utils.config._validate_mqtt')
    @patch('src.bluetracker.__main__.BlueTracker')
    def test_main_existing_config(self, mock_bluetracker_class: Mock, *_: Mock) -> None:
        """Test use existing configuration file."""
        mock_bluetracker = mock_bluetracker_class.return_value
        mock_bluetracker.run = MagicMock()

        if self.file_.exists():
            self.file_.unlink()

            with (
                self.assertRaises(SystemExit),
                patch.object(sys, 'stdout', StringIO()) as output,
            ):
                main()

        existing_content = self.file_.read_text()
        new_content = "environment = 'development'\n" + existing_content
        self.file_.write_text(new_content)

        with patch.object(sys, 'stdout', StringIO()) as output:
            main()
        self.assertIn('Configuration file found at', output.getvalue())
        self.assertIn('.toml', output.getvalue())

    @patch('bluetracker.__main__.BlueTracker')
    def test_main_config_error(self, _: Mock) -> None:
        """Test error in configuration file."""
        if not self.file_.exists():
            with patch.object(sys, 'stdout', StringIO()), self.assertRaises(SystemExit):
                main()

        self.file_.write_text('new_content = "fiction"')

        with (
            patch.object(sys, 'stdout', StringIO()) as output,
            self.assertRaises(SystemExit),
        ):
            main()
        self.assertIn('Fatal error', output.getvalue())

    @patch('src.bluetracker.core.isinstance', return_value=True)
    @patch('src.bluetracker.core.BlueTracker.stop')
    @patch('src.bluetracker.__main__._LOGGER')
    @patch('src.bluetracker.__main__.sys.exit')
    def test_signal_handler(
        self,
        mock_exit: Mock,
        mock_logger: Mock,
        mock_tracker_stop: Mock,
        _: Mock,
    ) -> None:
        """Test the signal handler function."""
        devices_dict = [
            {'name': 'Device 1', 'mac': 'aa:bb:cc:dd:ee:ff'},
            {'name': 'Device 2', 'mac': 'aa:bb:cc:dd:ee:ff'},
        ]
        devices = [
            Device(device['name'], device['mac'], DeviceType.BLUETOOTH)
            for device in devices_dict
        ]

        bluescanner = BlueScanner(
            scan_interval=12,
            scan_timeout=3,
            consider_away=180,
        )

        tracker_instance = BlueTracker(bluescanner, Mock(), devices)

        handler = create_signal_handler(tracker_instance)  # type: ignore[arg-type]
        handler(SIGINT, None)  # Trigger the signal handler

        mock_logger.info.assert_any_call(
            'SIGINT received. Initiating graceful shutdown...',
        )
        mock_tracker_stop.assert_called_once()  # This should now pass
        mock_logger.info.assert_called_with(
            '%s shutdown complete',
            tracker_instance.__class__.__name__,
        )
        mock_exit.assert_called_once_with(0)

    @patch('src.bluetracker.__main__._LOGGER')
    def test_signal_handler_already_called(self, mock_logger: Mock) -> None:
        """Test the signal handler when already called."""
        mock_tracker = Mock(spec=BlueTracker)

        handler = create_signal_handler(mock_tracker)
        handler.called = True  # type: ignore[attr-defined]

        handler(SIGINT, None)

        mock_logger.info.assert_called_once_with(
            'BlueTracker already shutting down. This may take a few moments.',
        )
        mock_tracker.stop.assert_not_called()
