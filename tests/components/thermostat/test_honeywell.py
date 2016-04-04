"""The test the Honeywell thermostat module."""
import socket
import unittest
from unittest import mock

import somecomfort

from homeassistant.const import (CONF_USERNAME, CONF_PASSWORD,
                                 TEMP_CELCIUS, TEMP_FAHRENHEIT)
import homeassistant.components.thermostat.honeywell as honeywell


class TestHoneywell(unittest.TestCase):
    """A test class for Honeywell themostats."""

    @mock.patch('somecomfort.SomeComfort')
    @mock.patch('homeassistant.components.thermostat.'
                'honeywell.HoneywellUSThermostat')
    def test_setup_us(self, mock_ht, mock_sc):
        """Test for the US setup."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            'region': 'us',
        }
        bad_pass_config = {
            CONF_USERNAME: 'user',
            'region': 'us',
        }
        bad_region_config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            'region': 'un',
        }
        hass = mock.MagicMock()
        add_devices = mock.MagicMock()

        locations = [
            mock.MagicMock(),
            mock.MagicMock(),
        ]
        devices_1 = [mock.MagicMock()]
        devices_2 = [mock.MagicMock(), mock.MagicMock]
        mock_sc.return_value.locations_by_id.values.return_value = \
            locations
        locations[0].devices_by_id.values.return_value = devices_1
        locations[1].devices_by_id.values.return_value = devices_2

        result = honeywell.setup_platform(hass, bad_pass_config, add_devices)
        self.assertFalse(result)
        result = honeywell.setup_platform(hass, bad_region_config, add_devices)
        self.assertFalse(result)
        result = honeywell.setup_platform(hass, config, add_devices)
        self.assertTrue(result)
        mock_sc.assert_called_once_with('user', 'pass')
        mock_ht.assert_has_calls([
            mock.call(mock_sc.return_value, devices_1[0]),
            mock.call(mock_sc.return_value, devices_2[0]),
            mock.call(mock_sc.return_value, devices_2[1]),
        ])

    @mock.patch('somecomfort.SomeComfort')
    def test_setup_us_failures(self, mock_sc):
        """Test the US setup."""
        hass = mock.MagicMock()
        add_devices = mock.MagicMock()
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            'region': 'us',
        }

        mock_sc.side_effect = somecomfort.AuthError
        result = honeywell.setup_platform(hass, config, add_devices)
        self.assertFalse(result)
        self.assertFalse(add_devices.called)

        mock_sc.side_effect = somecomfort.SomeComfortError
        result = honeywell.setup_platform(hass, config, add_devices)
        self.assertFalse(result)
        self.assertFalse(add_devices.called)

    @mock.patch('somecomfort.SomeComfort')
    @mock.patch('homeassistant.components.thermostat.'
                'honeywell.HoneywellUSThermostat')
    def _test_us_filtered_devices(self, mock_ht, mock_sc, loc=None, dev=None):
        """Test for US filtered thermostats."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            'region': 'us',
            'location': loc,
            'thermostat': dev,
        }
        locations = {
            1: mock.MagicMock(locationid=mock.sentinel.loc1,
                              devices_by_id={
                                  11: mock.MagicMock(
                                      deviceid=mock.sentinel.loc1dev1),
                                  12: mock.MagicMock(
                                      deviceid=mock.sentinel.loc1dev2),
                              }),
            2: mock.MagicMock(locationid=mock.sentinel.loc2,
                              devices_by_id={
                                  21: mock.MagicMock(
                                      deviceid=mock.sentinel.loc2dev1),
                              }),
            3: mock.MagicMock(locationid=mock.sentinel.loc3,
                              devices_by_id={
                                  31: mock.MagicMock(
                                      deviceid=mock.sentinel.loc3dev1),
                              }),
        }
        mock_sc.return_value = mock.MagicMock(locations_by_id=locations)
        hass = mock.MagicMock()
        add_devices = mock.MagicMock()
        self.assertEqual(True,
                         honeywell.setup_platform(hass, config, add_devices))

        return mock_ht.call_args_list, mock_sc

    def test_us_filtered_thermostat_1(self):
        """Test for US filtered thermostats."""
        result, client = self._test_us_filtered_devices(
            dev=mock.sentinel.loc1dev1)
        devices = [x[0][1].deviceid for x in result]
        self.assertEqual([mock.sentinel.loc1dev1], devices)

    def test_us_filtered_thermostat_2(self):
        """Test for US filtered location."""
        result, client = self._test_us_filtered_devices(
            dev=mock.sentinel.loc2dev1)
        devices = [x[0][1].deviceid for x in result]
        self.assertEqual([mock.sentinel.loc2dev1], devices)

    def test_us_filtered_location_1(self):
        """Test for US filtered locations."""
        result, client = self._test_us_filtered_devices(
            loc=mock.sentinel.loc1)
        devices = [x[0][1].deviceid for x in result]
        self.assertEqual([mock.sentinel.loc1dev1,
                          mock.sentinel.loc1dev2], devices)

    def test_us_filtered_location_2(self):
        """Test for US filtered locations."""
        result, client = self._test_us_filtered_devices(
            loc=mock.sentinel.loc2)
        devices = [x[0][1].deviceid for x in result]
        self.assertEqual([mock.sentinel.loc2dev1], devices)

    @mock.patch('evohomeclient.EvohomeClient')
    @mock.patch('homeassistant.components.thermostat.honeywell.'
                'RoundThermostat')
    def test_eu_setup_full_config(self, mock_round, mock_evo):
        """Test the EU setup wwith complete configuration."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            honeywell.CONF_AWAY_TEMP: 20,
            'region': 'eu',
        }
        mock_evo.return_value.temperatures.return_value = [
            {'id': 'foo'}, {'id': 'bar'}]
        hass = mock.MagicMock()
        add_devices = mock.MagicMock()
        self.assertTrue(honeywell.setup_platform(hass, config, add_devices))
        mock_evo.assert_called_once_with('user', 'pass')
        mock_evo.return_value.temperatures.assert_called_once_with(
            force_refresh=True)
        mock_round.assert_has_calls([
            mock.call(mock_evo.return_value, 'foo', True, 20),
            mock.call(mock_evo.return_value, 'bar', False, 20),
        ])
        self.assertEqual(2, add_devices.call_count)

    @mock.patch('evohomeclient.EvohomeClient')
    @mock.patch('homeassistant.components.thermostat.honeywell.'
                'RoundThermostat')
    def test_eu_setup_partial_config(self, mock_round, mock_evo):
        """Test the EU setup with partial configuration."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            'region': 'eu',
        }
        mock_evo.return_value.temperatures.return_value = [
            {'id': 'foo'}, {'id': 'bar'}]
        hass = mock.MagicMock()
        add_devices = mock.MagicMock()
        self.assertTrue(honeywell.setup_platform(hass, config, add_devices))
        default = honeywell.DEFAULT_AWAY_TEMP
        mock_round.assert_has_calls([
            mock.call(mock_evo.return_value, 'foo', True, default),
            mock.call(mock_evo.return_value, 'bar', False, default),
        ])

    @mock.patch('evohomeclient.EvohomeClient')
    @mock.patch('homeassistant.components.thermostat.honeywell.'
                'RoundThermostat')
    def test_eu_setup_bad_temp(self, mock_round, mock_evo):
        """Test the EU setup with invalid temperature."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            honeywell.CONF_AWAY_TEMP: 'ponies',
            'region': 'eu',
        }
        self.assertFalse(honeywell.setup_platform(None, config, None))

    @mock.patch('evohomeclient.EvohomeClient')
    @mock.patch('homeassistant.components.thermostat.honeywell.'
                'RoundThermostat')
    def test_eu_setup_error(self, mock_round, mock_evo):
        """Test the EU setup with errors."""
        config = {
            CONF_USERNAME: 'user',
            CONF_PASSWORD: 'pass',
            honeywell.CONF_AWAY_TEMP: 20,
            'region': 'eu',
        }
        mock_evo.return_value.temperatures.side_effect = socket.error
        add_devices = mock.MagicMock()
        hass = mock.MagicMock()
        self.assertFalse(honeywell.setup_platform(hass, config, add_devices))


class TestHoneywellRound(unittest.TestCase):
    """A test class for Honeywell Round thermostats."""

    def setup_method(self, method):
        """Test the setup method."""
        def fake_temperatures(force_refresh=None):
            """Create fake temperatures."""
            temps = [
                {'id': '1', 'temp': 20, 'setpoint': 21,
                 'thermostat': 'main', 'name': 'House'},
                {'id': '2', 'temp': 21, 'setpoint': 22,
                 'thermostat': 'DOMESTIC_HOT_WATER'},
            ]
            return temps

        self.device = mock.MagicMock()
        self.device.temperatures.side_effect = fake_temperatures
        self.round1 = honeywell.RoundThermostat(self.device, '1',
                                                True, 16)
        self.round2 = honeywell.RoundThermostat(self.device, '2',
                                                False, 17)

    def test_attributes(self):
        """Test the attributes."""
        self.assertEqual('House', self.round1.name)
        self.assertEqual(TEMP_CELCIUS, self.round1.unit_of_measurement)
        self.assertEqual(20, self.round1.current_temperature)
        self.assertEqual(21, self.round1.target_temperature)
        self.assertFalse(self.round1.is_away_mode_on)

        self.assertEqual('Hot Water', self.round2.name)
        self.assertEqual(TEMP_CELCIUS, self.round2.unit_of_measurement)
        self.assertEqual(21, self.round2.current_temperature)
        self.assertEqual(None, self.round2.target_temperature)
        self.assertFalse(self.round2.is_away_mode_on)

    def test_away_mode(self):
        """Test setting the away mode."""
        self.assertFalse(self.round1.is_away_mode_on)
        self.round1.turn_away_mode_on()
        self.assertTrue(self.round1.is_away_mode_on)
        self.device.set_temperature.assert_called_once_with('House', 16)

        self.device.set_temperature.reset_mock()
        self.round1.turn_away_mode_off()
        self.assertFalse(self.round1.is_away_mode_on)
        self.device.cancel_temp_override.assert_called_once_with('House')

    def test_set_temperature(self):
        """Test setting the temperature."""
        self.round1.set_temperature(25)
        self.device.set_temperature.assert_called_once_with('House', 25)


class TestHoneywellUS(unittest.TestCase):
    """A test class for Honeywell US thermostats."""

    def setup_method(self, method):
        """Test the setup method."""
        self.client = mock.MagicMock()
        self.device = mock.MagicMock()
        self.honeywell = honeywell.HoneywellUSThermostat(
            self.client, self.device)

        self.device.fan_running = True
        self.device.name = 'test'
        self.device.temperature_unit = 'F'
        self.device.current_temperature = 72
        self.device.setpoint_cool = 78
        self.device.setpoint_heat = 65
        self.device.system_mode = 'heat'
        self.device.fan_mode = 'auto'

    def test_properties(self):
        """Test the properties."""
        self.assertTrue(self.honeywell.is_fan_on)
        self.assertEqual('test', self.honeywell.name)
        self.assertEqual(72, self.honeywell.current_temperature)

    def test_unit_of_measurement(self):
        """Test the unit of measurement."""
        self.assertEqual(TEMP_FAHRENHEIT, self.honeywell.unit_of_measurement)
        self.device.temperature_unit = 'C'
        self.assertEqual(TEMP_CELCIUS, self.honeywell.unit_of_measurement)

    def test_target_temp(self):
        """Test the target temperature."""
        self.assertEqual(65, self.honeywell.target_temperature)
        self.device.system_mode = 'cool'
        self.assertEqual(78, self.honeywell.target_temperature)

    def test_set_temp(self):
        """Test setting the temperature."""
        self.honeywell.set_temperature(70)
        self.assertEqual(70, self.device.setpoint_heat)
        self.assertEqual(70, self.honeywell.target_temperature)

        self.device.system_mode = 'cool'
        self.assertEqual(78, self.honeywell.target_temperature)
        self.honeywell.set_temperature(74)
        self.assertEqual(74, self.device.setpoint_cool)
        self.assertEqual(74, self.honeywell.target_temperature)

    def test_set_temp_fail(self):
        """Test if setting the temperature fails."""
        self.device.setpoint_heat = mock.MagicMock(
            side_effect=somecomfort.SomeComfortError)
        self.honeywell.set_temperature(123)

    def test_attributes(self):
        """Test the attributes."""
        expected = {
            'fan': 'running',
            'fanmode': 'auto',
            'system_mode': 'heat',
        }
        self.assertEqual(expected, self.honeywell.device_state_attributes)
        expected['fan'] = 'idle'
        self.device.fan_running = False
        self.assertEqual(expected, self.honeywell.device_state_attributes)

    def test_with_no_fan(self):
        """Test if there is on fan."""
        self.device.fan_running = False
        self.device.fan_mode = None
        expected = {
            'fan': 'idle',
            'fanmode': None,
            'system_mode': 'heat',
        }
        self.assertEqual(expected, self.honeywell.device_state_attributes)
