"""
Allows the creation of a sensor that breaks out state_attributes
from other entities.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.template/
"""
import logging

from homeassistant.components.sensor import DOMAIN
from homeassistant.const import (
    ATTR_FRIENDLY_NAME, ATTR_UNIT_OF_MEASUREMENT, CONF_VALUE_TEMPLATE)
from homeassistant.core import EVENT_STATE_CHANGED
from homeassistant.exceptions import TemplateError
from homeassistant.helpers.entity import Entity, generate_entity_id
from homeassistant.helpers import template
from homeassistant.util import slugify

ENTITY_ID_FORMAT = DOMAIN + '.{}'

_LOGGER = logging.getLogger(__name__)
CONF_SENSORS = 'sensors'
STATE_ERROR = 'error'


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Sets up the sensors."""

    sensors = []
    if config.get(CONF_SENSORS) is None:
        _LOGGER.error("Missing configuration data for sensor platform")
        return False

    for device, device_config in config[CONF_SENSORS].items():

        if device != slugify(device):
            _LOGGER.error("Found invalid key for sensor.template: %s. "
                          "Use %s instead", device, slugify(device))
            continue

        if not isinstance(device_config, dict):
            _LOGGER.error("Missing configuration data for sensor %s", device)
            continue

        friendly_name = device_config.get(ATTR_FRIENDLY_NAME, device)
        unit_of_measurement = device_config.get(ATTR_UNIT_OF_MEASUREMENT)
        state_template = device_config.get(CONF_VALUE_TEMPLATE)
        if state_template is None:
            _LOGGER.error(
                "Missing %s for sensor %s", CONF_VALUE_TEMPLATE, device)
            continue

        sensors.append(
            SensorTemplate(
                hass,
                device,
                friendly_name,
                unit_of_measurement,
                state_template)
            )
    if not sensors:
        _LOGGER.error("No sensors added")
        return False
    add_devices(sensors)
    return True


class SensorTemplate(Entity):
    """Represents a Template Sensor."""

    # pylint: disable=too-many-arguments
    def __init__(self,
                 hass,
                 device_id,
                 friendly_name,
                 unit_of_measurement,
                 state_template):

        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, device_id,
            hass=hass)

        self.hass = hass
        self._name = friendly_name
        self._unit_of_measurement = unit_of_measurement
        self._template = state_template
        self.update()

        def _update_callback(_event):
            """ Called when the target device changes state. """
            self.update_ha_state(True)

        self.hass.bus.listen(EVENT_STATE_CHANGED, _update_callback)

    @property
    def name(self):
        """Returns the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Returns the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Returns the unit_of_measurement of the device."""
        return self._unit_of_measurement

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    def update(self):
        """Gets the latest data and updates the states."""
        try:
            self._state = template.render(self.hass, self._template)
        except TemplateError as ex:
            self._state = STATE_ERROR
            if ex.args and ex.args[0].startswith(
                    "UndefinedError: 'None' has no attribute"):
                # Common during HA startup - so just a warning
                _LOGGER.warning(ex)
                return
            _LOGGER.error(ex)
