"""Unittests for bluetracker.utils.homeassistant."""

from socket import gaierror
from unittest import TestCase
from unittest.mock import Mock, patch

from requests import Response
from requests.exceptions import ConnectionError, JSONDecodeError

from src.bluetracker.utils.homeassistant import is_homeassistant_running


class HomeAssistantTestCase(TestCase):
    """Unittests for homeassistant."""

    @patch('src.bluetracker.utils.homeassistant.get')
    def test_api_running(self, mock_get: Mock) -> None:
        """Test Home Assistant is running."""

        def mock_json() -> dict[str, str]:
            return {'message': 'API running.'}

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json = mock_json

        mock_get.return_value = mock_response

        self.assertTrue(is_homeassistant_running('your_host', 'your_token'))

    @patch('src.bluetracker.utils.homeassistant.get')
    def test_api_not_running(self, mock_get: Mock) -> None:
        """Test Home Assistant is not running."""
        mock_response = Response()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        self.assertFalse(is_homeassistant_running('your_host', 'your_token'))

    @patch('src.bluetracker.utils.homeassistant.get')
    def test_invalid_json_response(self, mock_get: Mock) -> None:
        """Test is Home Assistant running should fail."""
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = JSONDecodeError(
            'Expecting value',
            'invalid json',
            0,
        )
        mock_get.return_value = mock_response

        self.assertFalse(is_homeassistant_running('your_host', 'your_token'))

    @patch('src.bluetracker.utils.homeassistant.get', side_effect=gaierror)
    def test_gaierror(self, _: Mock) -> None:
        """Test is Home Assistant running with invalid host should fail."""
        self.assertFalse(is_homeassistant_running('your_host', 'your_token'))

    @patch('src.bluetracker.utils.homeassistant.get', side_effect=ConnectionError)
    def test_connectionerror(self, _: Mock) -> None:
        """Test is Home Assistant running with connection error should fail."""
        self.assertFalse(is_homeassistant_running('your_host', 'your_token'))
