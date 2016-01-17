"""
homeassistant.components.sensor.vera
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Support for Vera sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.vera/
"""
import logging
from requests.exceptions import RequestException
import homeassistant.util.dt as dt_util

from homeassistant.helpers.entity import Entity
from homeassistant.const import (
    ATTR_BATTERY_LEVEL, ATTR_TRIPPED, ATTR_ARMED, ATTR_LAST_TRIP_TIME,
    TEMP_CELCIUS, TEMP_FAHRENHEIT, EVENT_HOMEASSISTANT_STOP)

REQUIREMENTS = ['pyvera==0.2.7']

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument
def get_devices(hass, config):
    """ Find and return Vera Sensors. """
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

    categories = ['Temperature Sensor',
                  'Light Sensor',
                  'Humidity Sensor',
                  'Sensor']
    devices = []
    try:
        devices = vera_controller.get_devices(categories)
    except RequestException:
        # There was a network related error connecting to the vera controller
        _LOGGER.exception("Error communicating with Vera API")
        return False

    vera_sensors = []
    for device in devices:
        extra_data = device_data.get(device.device_id, {})
        exclude = extra_data.get('exclude', False)

        if exclude is not True:
            vera_sensors.append(
                VeraSensor(device, vera_controller, extra_data))

    return vera_sensors


def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Performs setup for Vera controller devices. """
    add_devices(get_devices(hass, config))


class VeraSensor(Entity):
    """ Represents a Vera Sensor. """

    def __init__(self, vera_device, controller, extra_data=None):
        self.vera_device = vera_device
        self.controller = controller
        self.extra_data = extra_data
        if self.extra_data and self.extra_data.get('name'):
            self._name = self.extra_data.get('name')
        else:
            self._name = self.vera_device.name
        self.current_value = ''
        self._temperature_units = None

        self.controller.register(vera_device, self._update_callback)
        self.update()

    def _update_callback(self, _device):
        """ Called by the vera device callback to update state. """
        self.update_ha_state(True)

    def __str__(self):
        return "%s %s %s" % (self.name, self.vera_device.device_id, self.state)

    @property
    def state(self):
        return self.current_value

    @property
    def name(self):
        """ Get the mame of the sensor. """
        return self._name

    @property
    def unit_of_measurement(self):
        """ Unit of measurement of this entity, if any. """
        if self.vera_device.category == "Temperature Sensor":
            return self._temperature_units
        elif self.vera_device.category == "Light Sensor":
            return 'lux'
        elif self.vera_device.category == "Humidity Sensor":
            return '%'

    @property
    def state_attributes(self):
        attr = {}
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

    @property
    def should_poll(self):
        """ Tells Home Assistant not to poll this entity. """
        return False

    def update(self):
        if self.vera_device.category == "Temperature Sensor":
            current_temp = self.vera_device.temperature
            vera_temp_units = (
                self.vera_device.vera_controller.temperature_units)

            if vera_temp_units == 'F':
                self._temperature_units = TEMP_FAHRENHEIT
            else:
                self._temperature_units = TEMP_CELCIUS

            if self.hass:
                temp = self.hass.config.temperature(
                    current_temp,
                    self._temperature_units)

                current_temp, self._temperature_units = temp

            self.current_value = current_temp
        elif self.vera_device.category == "Light Sensor":
            self.current_value = self.vera_device.light
        elif self.vera_device.category == "Humidity Sensor":
            self.current_value = self.vera_device.humidity
        elif self.vera_device.category == "Sensor":
            tripped = self.vera_device.is_tripped
            self.current_value = 'Tripped' if tripped else 'Not Tripped'
        else:
            self.current_value = 'Unknown'
