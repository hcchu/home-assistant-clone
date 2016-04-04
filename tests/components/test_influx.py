"""The tests for the InfluxDB component."""
import copy
import unittest
from unittest import mock

import influxdb as influx_client

import homeassistant.components.influxdb as influxdb
from homeassistant.const import STATE_ON, STATE_OFF, EVENT_STATE_CHANGED


class TestInfluxDB(unittest.TestCase):
    """Test the InfluxDB component."""

    @mock.patch('influxdb.InfluxDBClient')
    def test_setup_config_full(self, mock_client):
        """Test the setup with full configuration."""
        config = {
            'influxdb': {
                'host': 'host',
                'port': 123,
                'database': 'db',
                'username': 'user',
                'password': 'password',
                'ssl': 'False',
                'verify_ssl': 'False',
            }
        }
        hass = mock.MagicMock()
        self.assertTrue(influxdb.setup(hass, config))
        self.assertTrue(hass.bus.listen.called)
        self.assertEqual(EVENT_STATE_CHANGED,
                         hass.bus.listen.call_args_list[0][0][0])
        self.assertTrue(mock_client.return_value.query.called)

    @mock.patch('influxdb.InfluxDBClient')
    def test_setup_config_defaults(self, mock_client):
        """Test the setup with default configuration."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
            }
        }
        hass = mock.MagicMock()
        self.assertTrue(influxdb.setup(hass, config))
        self.assertTrue(hass.bus.listen.called)
        self.assertEqual(EVENT_STATE_CHANGED,
                         hass.bus.listen.call_args_list[0][0][0])

    @mock.patch('influxdb.InfluxDBClient')
    def test_setup_missing_keys(self, mock_client):
        """Test the setup with missing keys."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
            }
        }
        hass = mock.MagicMock()
        for missing in config['influxdb'].keys():
            config_copy = copy.deepcopy(config)
            del config_copy['influxdb'][missing]
            self.assertFalse(influxdb.setup(hass, config_copy))

    @mock.patch('influxdb.InfluxDBClient')
    def test_setup_query_fail(self, mock_client):
        """Test the setup for query failures."""
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
            }
        }
        hass = mock.MagicMock()
        mock_client.return_value.query.side_effect = \
            influx_client.exceptions.InfluxDBClientError('fake')
        self.assertFalse(influxdb.setup(hass, config))

    def _setup(self, mock_influx):
        """Setup the client."""
        self.mock_client = mock_influx.return_value
        config = {
            'influxdb': {
                'host': 'host',
                'username': 'user',
                'password': 'pass',
                'blacklist': ['fake.blacklisted']
            }
        }
        self.hass = mock.MagicMock()
        influxdb.setup(self.hass, config)
        self.handler_method = self.hass.bus.listen.call_args_list[0][0][1]

    @mock.patch('influxdb.InfluxDBClient')
    def test_event_listener(self, mock_influx):
        """Test the event listener."""
        self._setup(mock_influx)

        valid = {'1': 1,
                 '1.0': 1.0,
                 STATE_ON: 1,
                 STATE_OFF: 0,
                 'foo': 'foo'}
        for in_, out in valid.items():
            attrs = {'unit_of_measurement': 'foobars'}
            state = mock.MagicMock(state=in_,
                                   domain='fake',
                                   object_id='entity',
                                   attributes=attrs)
            event = mock.MagicMock(data={'new_state': state},
                                   time_fired=12345)
            body = [{
                'measurement': 'foobars',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'value': out,
                },
            }]
            self.handler_method(event)
            self.mock_client.write_points.assert_called_once_with(body)
            self.mock_client.write_points.reset_mock()

    @mock.patch('influxdb.InfluxDBClient')
    def test_event_listener_no_units(self, mock_influx):
        """Test the event listener for missing units."""
        self._setup(mock_influx)

        for unit in (None, ''):
            if unit:
                attrs = {'unit_of_measurement': unit}
            else:
                attrs = {}
            state = mock.MagicMock(state=1,
                                   domain='fake',
                                   entity_id='entity-id',
                                   object_id='entity',
                                   attributes=attrs)
            event = mock.MagicMock(data={'new_state': state},
                                   time_fired=12345)
            body = [{
                'measurement': 'entity-id',
                'tags': {
                    'domain': 'fake',
                    'entity_id': 'entity',
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            self.mock_client.write_points.assert_called_once_with(body)
            self.mock_client.write_points.reset_mock()

    @mock.patch('influxdb.InfluxDBClient')
    def test_event_listener_fail_write(self, mock_influx):
        """Test the event listener for write failures."""
        self._setup(mock_influx)

        state = mock.MagicMock(state=1,
                               domain='fake',
                               entity_id='entity-id',
                               object_id='entity',
                               attributes={})
        event = mock.MagicMock(data={'new_state': state},
                               time_fired=12345)
        self.mock_client.write_points.side_effect = \
            influx_client.exceptions.InfluxDBClientError('foo')
        self.handler_method(event)

    @mock.patch('influxdb.InfluxDBClient')
    def test_event_listener_blacklist(self, mock_influx):
        """Test the event listener against a blacklist."""
        self._setup(mock_influx)

        for entity_id in ('ok', 'blacklisted'):
            state = mock.MagicMock(state=1,
                                   domain='fake',
                                   entity_id='fake.{}'.format(entity_id),
                                   object_id=entity_id,
                                   attributes={})
            event = mock.MagicMock(data={'new_state': state},
                                   time_fired=12345)
            body = [{
                'measurement': 'fake.{}'.format(entity_id),
                'tags': {
                    'domain': 'fake',
                    'entity_id': entity_id,
                },
                'time': 12345,
                'fields': {
                    'value': 1,
                },
            }]
            self.handler_method(event)
            if entity_id == 'ok':
                self.mock_client.write_points.assert_called_once_with(body)
            else:
                self.assertFalse(self.mock_client.write_points.called)
            self.mock_client.write_points.reset_mock()
