"""Home Assistant utilities module."""

from contextlib import suppress
from logging import getLogger
from socket import gaierror

from requests import JSONDecodeError, RequestException, get

_LOGGER = getLogger(__name__)

STATUS_OK = 200
API_RUNNING_MESSAGE = 'API running.'


def is_homeassistant_running(ip_address: str, token: str) -> bool:
    """Is Home Asisstant running.

    Obtain a Home Asisstant access token ("Long-Lived Access Token") by logging into
    the frontend using a web browser, and going to your profile
    http://IP_ADDRESS:8123/profile/security.

    More info: https://www.home-assistant.io/docs/authentication/#your-account-profile

    Args:
        ip_address: The IP address.
        token: The access token.

    Returns:
        `True` if Home Assistant is running, `False` otherwise.
    """
    is_online = False

    url = f'http://{ip_address}:8123/api/'
    headers = {
        'Authorization': f'Bearer {token}',
        'content-type': 'application/json',
    }

    with suppress(gaierror, RequestException):
        response = get(url, headers=headers, timeout=10)

        if response.status_code == STATUS_OK:
            with suppress(JSONDecodeError):
                is_online = response.json().get('message') == API_RUNNING_MESSAGE

    _LOGGER.debug('Home Assistant online: %s', is_online)

    return is_online
