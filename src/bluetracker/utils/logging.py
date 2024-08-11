"""Set logging."""

from logging import DEBUG, INFO, basicConfig, getLogger
from sys import stdout

from .config import Environment

_LOGGER = getLogger(__name__)


def set_logging(environment: Environment) -> None:
    """Set logging.

    Args:
        environment: The config environment.
    """
    output = '%(asctime)s:%(name)-31s:%(lineno)-3d: %(levelname)-8s: %(message)s'

    if environment != Environment.PROD:
        basicConfig(stream=stdout, level=DEBUG, format=output)
    else:
        basicConfig(stream=stdout, level=INFO, format=output)

    _LOGGER.debug('Logging set')
