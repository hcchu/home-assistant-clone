"""The tests for the Sun component."""
# pylint: disable=too-many-public-methods,protected-access
import unittest
from datetime import timedelta

from astral import Astral

import homeassistant.core as ha
import homeassistant.util.dt as dt_util
import homeassistant.components.sun as sun

from tests.common import get_test_home_assistant


class TestSun(unittest.TestCase):
    """Test the sun module."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()

    def test_is_on(self):
        """Test is_on method."""
        self.hass.states.set(sun.ENTITY_ID, sun.STATE_ABOVE_HORIZON)
        self.assertTrue(sun.is_on(self.hass))
        self.hass.states.set(sun.ENTITY_ID, sun.STATE_BELOW_HORIZON)
        self.assertFalse(sun.is_on(self.hass))

    def test_setting_rising(self):
        """Test retrieving sun setting and rising."""
        latitude = 32.87336
        longitude = 117.22743

        # Compare it with the real data
        self.hass.config.latitude = latitude
        self.hass.config.longitude = longitude
        sun.setup(self.hass, {sun.DOMAIN: {sun.CONF_ELEVATION: 0}})

        astral = Astral()
        utc_now = dt_util.utcnow()

        mod = -1
        while True:
            next_rising = (astral.sunrise_utc(utc_now +
                           timedelta(days=mod), latitude, longitude))
            if next_rising > utc_now:
                break
            mod += 1

        mod = -1
        while True:
            next_setting = (astral.sunset_utc(utc_now +
                            timedelta(days=mod), latitude, longitude))
            if next_setting > utc_now:
                break
            mod += 1

        self.assertEqual(next_rising, sun.next_rising_utc(self.hass))
        self.assertEqual(next_setting, sun.next_setting_utc(self.hass))

        # Point it at a state without the proper attributes
        self.hass.states.set(sun.ENTITY_ID, sun.STATE_ABOVE_HORIZON)
        self.assertIsNone(sun.next_rising(self.hass))
        self.assertIsNone(sun.next_setting(self.hass))

        # Point it at a non-existing state
        self.assertIsNone(sun.next_rising(self.hass, 'non.existing'))
        self.assertIsNone(sun.next_setting(self.hass, 'non.existing'))

    def test_state_change(self):
        """Test if the state changes at next setting/rising."""
        self.hass.config.latitude = '32.87336'
        self.hass.config.longitude = '117.22743'
        sun.setup(self.hass, {sun.DOMAIN: {sun.CONF_ELEVATION: 0}})

        if sun.is_on(self.hass):
            test_state = sun.STATE_BELOW_HORIZON
            test_time = sun.next_setting(self.hass)
        else:
            test_state = sun.STATE_ABOVE_HORIZON
            test_time = sun.next_rising(self.hass)

        self.assertIsNotNone(test_time)

        self.hass.bus.fire(ha.EVENT_TIME_CHANGED,
                           {ha.ATTR_NOW: test_time + timedelta(seconds=5)})

        self.hass.pool.block_till_done()

        self.assertEqual(test_state, self.hass.states.get(sun.ENTITY_ID).state)
