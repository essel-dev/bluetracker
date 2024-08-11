"""Unittests for bluetracker.utils.logging."""

from logging import INFO, disable
from sys import stdout
from unittest import TestCase
from unittest.mock import Mock, patch

from src.bluetracker.utils.config import Environment
from src.bluetracker.utils.logging import set_logging


class LoggingTestCase(TestCase):
    """Unittests for logging."""

    @classmethod
    def setUpClass(cls) -> None:
        """Inititalize before all tests."""
        disable()

    def test_set_logging_debug(self) -> None:
        """Tests set_logging for DEBUG level in non-PROD environment."""
        environment = Environment.DEV

        set_logging(environment)

    @patch('src.bluetracker.utils.logging.basicConfig')
    def test_set_logging_info(self, mock_basicConfig: Mock) -> None:  # noqa: N803
        """Tests set_logging for INFO level in PROD environment."""
        environment = Environment.PROD

        set_logging(environment)

        mock_basicConfig.assert_called_once_with(
            stream=stdout,
            level=INFO,
            format='%(asctime)s:%(name)-31s:%(lineno)-3d: %(levelname)-8s: %(message)s',
        )
