"""Unittests for bluetracker.models.device."""

import logging
from datetime import UTC, datetime
from unittest import TestCase

from src.bluetracker.models.device import (
    Device,
    DeviceResponse,
    DeviceState,
    DeviceType,
)

SECONDS = 3


class DeviceTestCase(TestCase):
    """Unittests for Device model."""

    def setUp(self) -> None:
        """Initialize."""
        self.device = Device('Device 1', 'aa:bb:cc:dd:ee:ff', DeviceType.BLUETOOTH)
        logging.disable()

    def tearDown(self) -> None:
        """Clean up after tests."""

    def test_default_state(self) -> None:
        """Test default state on init()."""
        self.assertTrue(
            (datetime.now(UTC) - self.device.last_seen).total_seconds() < SECONDS,
        )
        self.assertEqual(self.device.state, DeviceState.NOT_HOME)
        self.assertEqual(self.device.reason, DeviceResponse.SETUP)

    def test_to_dict(self) -> None:
        """Test to_dict."""
        device = self.device.to_dict()

        expected_keys = [
            'name',
            'mac',
            'last_seen',
            'state',
            'reason',
            'source_type',
        ]
        self.assertEqual(sorted(device.keys()), sorted(expected_keys))

    def test_str_representation(self) -> None:
        """Test __str__."""
        expected_str = f'{self.device.name} ({self.device.mac})'
        self.assertEqual(str(self.device), expected_str)
