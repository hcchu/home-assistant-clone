"""
homeassistant.components.switch.vera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Vera switches.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/switch.vera/
"""
import logging
from requests.exceptions import RequestException
import homeassistant.util.dt as dt_util

from homeassistant.components.switch import SwitchDevice

from homeassistant.const import (
    ATTR_BATTERY_LEVEL,
    ATTR_TRIPPED,
    ATTR_ARMED,
    ATTR_LAST_TRIP_TIME,
    EVENT_HOMEASSISTANT_STOP,
    STATE_ON,
    STATE_OFF)

REQUIREMENTS = ['pyvera==0.2.7']

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def get_devices(hass, config):
    """ Find and return Vera switches. """
    import pyvera as veraApi

    base_url = config.get('vera_controller_url')
    if not base_url:
        _LOGGER.error(
            "The required parameter 'vera_controller_url'"
            " was not found in config"
        )
        return False

    device_data = config.get('device_data', {})

    vera_controller, created = veraApi.init_controller(base_url)

    if created:
        def stop_subscription(event):
            """ Shutdown Vera subscriptions and subscription thread on exit"""
            _LOGGER.info("Shutting down subscriptions.")
            vera_controller.stop()

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_subscription)

    devices = []
    try:
        devices = vera_controller.get_devices([
            'Switch', 'Armable Sensor', 'On/Off Switch'])
    except RequestException:
        # There was a network related error connecting to the vera controller.
        _LOGGER.exception("Error communicating with Vera API")
        return False

    vera_switches = []
    for device in devices:
        extra_data = device_data.get(device.device_id, {})
        exclude = extra_data.get('exclude', False)

        if exclude is not True:
            vera_switches.append(
                VeraSwitch(device, vera_controller, extra_data))

    return vera_switches


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Find and return Vera lights. """
    add_devices(get_devices(hass, config))


class VeraSwitch(SwitchDevice):
    """ Represents a Vera Switch. """

    def __init__(self, vera_device, controller, extra_data=None):
        self.vera_device = vera_device
        self.extra_data = extra_data
        self.controller = controller
        if self.extra_data and self.extra_data.get('name'):
            self._name = self.extra_data.get('name')
        else:
            self._name = self.vera_device.name
        self._state = STATE_OFF

        self.controller.register(vera_device, self._update_callback)
        self.update()

    def _update_callback(self, _device):
        self.update_ha_state(True)

    @property
    def name(self):
        """ Get the mame of the switch. """
        return self._name

    @property
    def state_attributes(self):
        attr = super().state_attributes or {}

        if self.vera_device.has_battery:
            attr[ATTR_BATTERY_LEVEL] = self.vera_device.battery_level + '%'

        if self.vera_device.is_armable:
            armed = self.vera_device.is_armed
            attr[ATTR_ARMED] = 'True' if armed else 'False'

        if self.vera_device.is_trippable:
            last_tripped = self.vera_device.last_trip
            if last_tripped is not None:
                utc_time = dt_util.utc_from_timestamp(int(last_tripped))
                attr[ATTR_LAST_TRIP_TIME] = dt_util.datetime_to_str(
                    utc_time)
            else:
                attr[ATTR_LAST_TRIP_TIME] = None
            tripped = self.vera_device.is_tripped
            attr[ATTR_TRIPPED] = 'True' if tripped else 'False'

        attr['Vera Device Id'] = self.vera_device.vera_device_id

        return attr

    def turn_on(self, **kwargs):
        self.vera_device.switch_on()
        self._state = STATE_ON
        self.update_ha_state()

    def turn_off(self, **kwargs):
        self.vera_device.switch_off()
        self._state = STATE_OFF
        self.update_ha_state()

    @property
    def should_poll(self):
        """ Tells Home Assistant not to poll this entity. """
        return False

    @property
    def is_on(self):
        """ True if device is on. """
        return self._state == STATE_ON

    def update(self):
        """ Called by the vera device callback to update state. """
        if self.vera_device.is_switched_on():
            self._state = STATE_ON
        else:
            self._state = STATE_OFF
