"""Tests Home Assistant location helpers."""
# pylint: disable=too-many-public-methods
import unittest

from homeassistant.const import ATTR_LATITUDE, ATTR_LONGITUDE
from homeassistant.core import State
from homeassistant.helpers import location


class TestHelpersLocation(unittest.TestCase):
    """Setup the tests."""

    def test_has_location_with_invalid_states(self):
        """Setup the tests."""
        for state in (None, 1, "hello", object):
            self.assertFalse(location.has_location(state))

    def test_has_location_with_states_with_invalid_locations(self):
        """Setup the tests."""
        state = State('hello.world', 'invalid', {
            ATTR_LATITUDE: 'no number',
            ATTR_LONGITUDE: 123.12
        })
        self.assertFalse(location.has_location(state))

    def test_has_location_with_states_with_valid_location(self):
        """Setup the tests."""
        state = State('hello.world', 'invalid', {
            ATTR_LATITUDE: 123.12,
            ATTR_LONGITUDE: 123.12
        })
        self.assertTrue(location.has_location(state))

    def test_closest_with_no_states_with_location(self):
        """Setup the tests."""
        state = State('light.test', 'on')
        state2 = State('light.test', 'on', {
            ATTR_LATITUDE: 'invalid',
            ATTR_LONGITUDE: 123.45,
        })
        state3 = State('light.test', 'on', {
            ATTR_LONGITUDE: 123.45,
        })

        self.assertIsNone(
            location.closest(123.45, 123.45, [state, state2, state3]))

    def test_closest_returns_closest(self):
        """Test ."""
        state = State('light.test', 'on', {
            ATTR_LATITUDE: 124.45,
            ATTR_LONGITUDE: 124.45,
        })
        state2 = State('light.test', 'on', {
            ATTR_LATITUDE: 125.45,
            ATTR_LONGITUDE: 125.45,
        })

        self.assertEqual(
            state, location.closest(123.45, 123.45, [state, state2]))
