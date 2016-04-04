"""The tests for the Yr sensor platform."""
from datetime import datetime
from unittest.mock import patch

import pytest

import homeassistant.components.sensor as sensor
import homeassistant.util.dt as dt_util

from tests.common import get_test_home_assistant


@pytest.mark.usefixtures('betamax_session')
class TestSensorYr:
    """Test the Yr sensor."""

    def setup_method(self, method):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.hass.config.latitude = 32.87336
        self.hass.config.longitude = 117.22743

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()

    def test_default_setup(self, betamax_session):
        """Test the default setup."""
        now = datetime(2016, 1, 5, 1, tzinfo=dt_util.UTC)

        with patch('homeassistant.components.sensor.yr.requests.Session',
                   return_value=betamax_session):
            with patch('homeassistant.components.sensor.yr.dt_util.utcnow',
                       return_value=now):
                assert sensor.setup(self.hass, {
                    'sensor': {
                        'platform': 'yr',
                        'elevation': 0,
                    }
                })

        state = self.hass.states.get('sensor.yr_symbol')

        assert '46' == state.state
        assert state.state.isnumeric()
        assert state.attributes.get('unit_of_measurement') is None

    def test_custom_setup(self, betamax_session):
        """Test a custom setup."""
        now = datetime(2016, 1, 5, 1, tzinfo=dt_util.UTC)

        with patch('homeassistant.components.sensor.yr.requests.Session',
                   return_value=betamax_session):
            with patch('homeassistant.components.sensor.yr.dt_util.utcnow',
                       return_value=now):
                assert sensor.setup(self.hass, {
                    'sensor': {
                        'platform': 'yr',
                        'elevation': 0,
                        'monitored_conditions': {
                            'pressure',
                            'windDirection',
                            'humidity',
                            'fog',
                            'windSpeed'
                        }
                    }
                })

        state = self.hass.states.get('sensor.yr_pressure')
        assert 'hPa' == state.attributes.get('unit_of_measurement')
        assert '1025.1' == state.state

        state = self.hass.states.get('sensor.yr_wind_direction')
        assert '°' == state.attributes.get('unit_of_measurement')
        assert '81.8' == state.state

        state = self.hass.states.get('sensor.yr_humidity')
        assert '%' == state.attributes.get('unit_of_measurement')
        assert '79.6' == state.state

        state = self.hass.states.get('sensor.yr_fog')
        assert '%' == state.attributes.get('unit_of_measurement')
        assert '0.0' == state.state

        state = self.hass.states.get('sensor.yr_wind_speed')
        assert 'm/s', state.attributes.get('unit_of_measurement')
        assert '4.3' == state.state
