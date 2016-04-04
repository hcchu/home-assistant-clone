"""
Support for functionality to keep track of the sun.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/sun/
"""
import logging
from datetime import timedelta

import homeassistant.util as util
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    track_point_in_utc_time, track_utc_time_change)
from homeassistant.util import dt as dt_util
from homeassistant.util import location as location_util

REQUIREMENTS = ['astral==0.9']
DOMAIN = "sun"
ENTITY_ID = "sun.sun"

CONF_ELEVATION = 'elevation'

STATE_ABOVE_HORIZON = "above_horizon"
STATE_BELOW_HORIZON = "below_horizon"

STATE_ATTR_NEXT_RISING = "next_rising"
STATE_ATTR_NEXT_SETTING = "next_setting"
STATE_ATTR_ELEVATION = "elevation"

_LOGGER = logging.getLogger(__name__)


def is_on(hass, entity_id=None):
    """Test if the sun is currently up based on the statemachine."""
    entity_id = entity_id or ENTITY_ID

    return hass.states.is_state(entity_id, STATE_ABOVE_HORIZON)


def next_setting(hass, entity_id=None):
    """Local datetime object of the next sun setting."""
    utc_next = next_setting_utc(hass, entity_id)

    return dt_util.as_local(utc_next) if utc_next else None


def next_setting_utc(hass, entity_id=None):
    """UTC datetime object of the next sun setting."""
    entity_id = entity_id or ENTITY_ID

    state = hass.states.get(ENTITY_ID)

    try:
        return dt_util.str_to_datetime(
            state.attributes[STATE_ATTR_NEXT_SETTING])
    except (AttributeError, KeyError):
        # AttributeError if state is None
        # KeyError if STATE_ATTR_NEXT_SETTING does not exist
        return None


def next_rising(hass, entity_id=None):
    """Local datetime object of the next sun rising."""
    utc_next = next_rising_utc(hass, entity_id)

    return dt_util.as_local(utc_next) if utc_next else None


def next_rising_utc(hass, entity_id=None):
    """UTC datetime object of the next sun rising."""
    entity_id = entity_id or ENTITY_ID

    state = hass.states.get(ENTITY_ID)

    try:
        return dt_util.str_to_datetime(
            state.attributes[STATE_ATTR_NEXT_RISING])
    except (AttributeError, KeyError):
        # AttributeError if state is None
        # KeyError if STATE_ATTR_NEXT_RISING does not exist
        return None


def setup(hass, config):
    """Track the state of the sun in HA."""
    if None in (hass.config.latitude, hass.config.longitude):
        _LOGGER.error("Latitude or longitude not set in Home Assistant config")
        return False

    latitude = util.convert(hass.config.latitude, float)
    longitude = util.convert(hass.config.longitude, float)
    errors = []

    if latitude is None:
        errors.append('Latitude needs to be a decimal value')
    elif -90 > latitude < 90:
        errors.append('Latitude needs to be -90 .. 90')

    if longitude is None:
        errors.append('Longitude needs to be a decimal value')
    elif -180 > longitude < 180:
        errors.append('Longitude needs to be -180 .. 180')

    if errors:
        _LOGGER.error('Invalid configuration received: %s', ", ".join(errors))
        return False

    platform_config = config.get(DOMAIN, {})

    elevation = platform_config.get(CONF_ELEVATION)
    if elevation is None:
        elevation = location_util.elevation(latitude, longitude)

    from astral import Location

    location = Location(('', '', latitude, longitude, hass.config.time_zone,
                         elevation))

    sun = Sun(hass, location)
    sun.point_in_time_listener(dt_util.utcnow())

    return True


class Sun(Entity):
    """Representation of the Sun."""

    entity_id = ENTITY_ID

    def __init__(self, hass, location):
        """Initialize the Sun."""
        self.hass = hass
        self.location = location
        self._state = self.next_rising = self.next_setting = None
        track_utc_time_change(hass, self.timer_update, second=30)

    @property
    def name(self):
        """Return the name."""
        return "Sun"

    @property
    def state(self):
        """Return the state of the sun."""
        if self.next_rising > self.next_setting:
            return STATE_ABOVE_HORIZON

        return STATE_BELOW_HORIZON

    @property
    def state_attributes(self):
        """Return the state attributes of the sun."""
        return {
            STATE_ATTR_NEXT_RISING:
                dt_util.datetime_to_str(self.next_rising),
            STATE_ATTR_NEXT_SETTING:
                dt_util.datetime_to_str(self.next_setting),
            STATE_ATTR_ELEVATION: round(self.solar_elevation, 2)
        }

    @property
    def next_change(self):
        """Datetime when the next change to the state is."""
        return min(self.next_rising, self.next_setting)

    @property
    def solar_elevation(self):
        """Angle the sun is above the horizon."""
        from astral import Astral
        return Astral().solar_elevation(
            dt_util.utcnow(),
            self.location.latitude,
            self.location.longitude)

    def update_as_of(self, utc_point_in_time):
        """Calculate sun state at a point in UTC time."""
        mod = -1
        while True:
            next_rising_dt = self.location.sunrise(
                utc_point_in_time + timedelta(days=mod), local=False)
            if next_rising_dt > utc_point_in_time:
                break
            mod += 1

        mod = -1
        while True:
            next_setting_dt = (self.location.sunset(
                utc_point_in_time + timedelta(days=mod), local=False))
            if next_setting_dt > utc_point_in_time:
                break
            mod += 1

        self.next_rising = next_rising_dt
        self.next_setting = next_setting_dt

    def point_in_time_listener(self, now):
        """Called when the state of the sun has changed."""
        self.update_as_of(now)
        self.update_ha_state()

        # Schedule next update at next_change+1 second so sun state has changed
        track_point_in_utc_time(
            self.hass, self.point_in_time_listener,
            self.next_change + timedelta(seconds=1))

    def timer_update(self, time):
        """Needed to update solar elevation."""
        self.update_ha_state()
