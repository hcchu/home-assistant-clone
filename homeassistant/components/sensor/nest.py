"""
Support for Nest Thermostat Sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.nest/
"""
import logging
import socket

import homeassistant.components.nest as nest
from homeassistant.const import TEMP_CELCIUS
from homeassistant.helpers.entity import Entity

DEPENDENCIES = ['nest']
SENSOR_TYPES = ['humidity',
                'mode',
                'last_ip',
                'local_ip',
                'last_connection',
                'battery_level']

WEATHER_VARIABLES = ['weather_condition', 'weather_temperature',
                     'weather_humidity',
                     'wind_speed', 'wind_direction']

JSON_VARIABLE_NAMES = {'weather_humidity': 'humidity',
                       'weather_temperature': 'temperature',
                       'weather_condition': 'condition',
                       'wind_speed': 'kph',
                       'wind_direction': 'direction'}

SENSOR_UNITS = {'humidity': '%', 'battery_level': 'V',
                'kph': 'kph', 'temperature': '°C'}

SENSOR_TEMP_TYPES = ['temperature', 'target']


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Nest Sensor."""
    logger = logging.getLogger(__name__)
    try:
        for structure in nest.NEST.structures:
            for device in structure.devices:
                for variable in config['monitored_conditions']:
                    if variable in SENSOR_TYPES:
                        add_devices([NestBasicSensor(structure,
                                                     device,
                                                     variable)])
                    elif variable in SENSOR_TEMP_TYPES:
                        add_devices([NestTempSensor(structure,
                                                    device,
                                                    variable)])
                    elif variable in WEATHER_VARIABLES:
                        json_variable = JSON_VARIABLE_NAMES.get(variable, None)
                        add_devices([NestWeatherSensor(structure,
                                                       device,
                                                       json_variable)])
                    else:
                        logger.error('Nest sensor type: "%s" does not exist',
                                     variable)
    except socket.error:
        logger.error(
            "Connection error logging into the nest web service."
        )


class NestSensor(Entity):
    """Representation of a Nest sensor."""

    def __init__(self, structure, device, variable):
        """Initialize the sensor."""
        self.structure = structure
        self.device = device
        self.variable = variable

    @property
    def name(self):
        """Return the name of the nest, if any."""
        location = self.device.where
        name = self.device.name
        if location is None:
            return "{} {}".format(name, self.variable)
        else:
            if name == '':
                return "{} {}".format(location.capitalize(), self.variable)
            else:
                return "{}({}){}".format(location.capitalize(),
                                         name,
                                         self.variable)


class NestBasicSensor(NestSensor):
    """Representation a basic Nest sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        return getattr(self.device, self.variable)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SENSOR_UNITS.get(self.variable, None)


class NestTempSensor(NestSensor):
    """Representation of a Nest Temperature sensor."""

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return TEMP_CELCIUS

    @property
    def state(self):
        """Return the state of the sensor."""
        temp = getattr(self.device, self.variable)
        if temp is None:
            return None

        return round(temp, 1)


class NestWeatherSensor(NestSensor):
    """Representation a basic Nest Weather Conditions sensor."""

    @property
    def state(self):
        """Return the state of the sensor."""
        if self.variable == 'kph' or self.variable == 'direction':
            return getattr(self.structure.weather.current.wind, self.variable)
        else:
            return getattr(self.structure.weather.current, self.variable)

    @property
    def unit_of_measurement(self):
        """Return the unit the value is expressed in."""
        return SENSOR_UNITS.get(self.variable, None)
