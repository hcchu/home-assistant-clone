"""
Demo platform that offers a fake thermostat.

For more details about this platform, please refer to the documentation
https://home-assistant.io/components/demo/
"""
from homeassistant.components.thermostat import ThermostatDevice
from homeassistant.const import TEMP_CELCIUS, TEMP_FAHRENHEIT


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Demo thermostats."""
    add_devices([
        DemoThermostat("Nest", 21, TEMP_CELCIUS, False, 19),
        DemoThermostat("Thermostat", 68, TEMP_FAHRENHEIT, True, 77),
    ])


# pylint: disable=too-many-arguments
class DemoThermostat(ThermostatDevice):
    """Represents a HeatControl thermostat."""
    def __init__(self, name, target_temperature, unit_of_measurement,
                 away, current_temperature):
        self._name = name
        self._target_temperature = target_temperature
        self._unit_of_measurement = unit_of_measurement
        self._away = away
        self._current_temperature = current_temperature

    @property
    def should_poll(self):
        """No polling needed for a demo thermostat."""
        return False

    @property
    def name(self):
        """Return the thermostat."""
        return self._name

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return self._unit_of_measurement

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self._current_temperature

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        return self._target_temperature

    @property
    def is_away_mode_on(self):
        """Return if away mode is on."""
        return self._away

    def set_temperature(self, temperature):
        """Set new target temperature."""
        self._target_temperature = temperature

    def turn_away_mode_on(self):
        """Turn away mode on."""
        self._away = True

    def turn_away_mode_off(self):
        """Turn away mode off."""
        self._away = False
