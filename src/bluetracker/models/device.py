"""Device state and attributes."""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, unique


@unique
class DeviceState(Enum):
    """Device states."""

    HOME = 'home'
    NOT_HOME = 'not_home'


@unique
class DeviceResponse(Enum):
    """Device responses."""

    NO_RESPONSE = 'no response'
    RESPONDED = 'responded'
    CONSIDERED_HOME = 'considered home'
    SETUP = 'server setup'
    SHUTDOWN = 'server shutdown'


@unique
class DeviceType(Enum):
    """Device types."""

    BLUETOOTH = 'bluetooth'


@dataclass
class Device:
    """Device model."""

    name: str
    mac: str
    source_type: DeviceType
    last_seen: datetime = field(default_factory=lambda: datetime.now(UTC))
    state: DeviceState = DeviceState.NOT_HOME
    reason: DeviceResponse = DeviceResponse.SETUP

    def to_dict(self) -> dict[str, str]:
        """Get the device as a dictionary.

        Returns:
            A dictionary representation of the device.
        """
        return {
            'name': self.name,
            'mac': self.mac,
            'source_type': self.source_type.value,
            'last_seen': self.last_seen.isoformat(),
            'state': self.state.value,
            'reason': self.reason.value,
        }

    def __str__(self) -> str:
        """The device as a string.

        Returns:
            The device as a string.
        """
        return f'{self.name} ({self.mac})'
