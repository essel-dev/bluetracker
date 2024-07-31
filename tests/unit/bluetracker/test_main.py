"""Unittests for bluetracker.__main__."""

from __future__ import annotations

import logging
import sys
from io import StringIO
from pathlib import Path
from unittest import TestCase
from unittest.mock import MagicMock, Mock, patch

from src.bluetracker.__main__ import main


class MainTestCase(TestCase):
    """Unittests for __main__."""

    @classmethod
    def setUpClass(cls) -> None:
        """Inititalize before all tests."""
        logging.disable()

        cls.file_ = Path.cwd().joinpath('bluetracker_config.toml')
        cls.file_backup = None

        if cls.file_.exists():
            cls.file_backup = cls.file_.rename(f'{cls.file_}.bak')

    @classmethod
    def tearDownClass(cls) -> None:
        """Clean up after all tests."""
        if cls.file_ and cls.file_.exists:
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
