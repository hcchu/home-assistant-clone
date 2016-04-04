"""The tests for the device tracker component."""
# pylint: disable=protected-access,too-many-public-methods
import unittest
from unittest.mock import patch
from datetime import datetime, timedelta
import os

from homeassistant.loader import get_component
import homeassistant.util.dt as dt_util
from homeassistant.const import (
    ATTR_ENTITY_ID, ATTR_ENTITY_PICTURE, ATTR_FRIENDLY_NAME, ATTR_HIDDEN,
    STATE_HOME, STATE_NOT_HOME, CONF_PLATFORM)
import homeassistant.components.device_tracker as device_tracker

from tests.common import (
    get_test_home_assistant, fire_time_changed, fire_service_discovered)


class TestComponentsDeviceTracker(unittest.TestCase):
    """Test the Device tracker."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        self.yaml_devices = self.hass.config.path(device_tracker.YAML_DEVICES)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        try:
            os.remove(self.yaml_devices)
        except FileNotFoundError:
            pass

        self.hass.stop()

    def test_is_on(self):
        """Test is_on method."""
        entity_id = device_tracker.ENTITY_ID_FORMAT.format('test')

        self.hass.states.set(entity_id, STATE_HOME)

        self.assertTrue(device_tracker.is_on(self.hass, entity_id))

        self.hass.states.set(entity_id, STATE_NOT_HOME)

        self.assertFalse(device_tracker.is_on(self.hass, entity_id))

    def test_reading_yaml_config(self):
        """Test the rendering of the YAML configuration."""
        dev_id = 'test'
        device = device_tracker.Device(
            self.hass, timedelta(seconds=180), 0, True, dev_id,
            'AB:CD:EF:GH:IJ', 'Test name', 'http://test.picture', True)
        device_tracker.update_config(self.yaml_devices, dev_id, device)
        self.assertTrue(device_tracker.setup(self.hass, {}))
        config = device_tracker.load_config(self.yaml_devices, self.hass,
                                            device.consider_home, 0)[0]
        self.assertEqual(device.dev_id, config.dev_id)
        self.assertEqual(device.track, config.track)
        self.assertEqual(device.mac, config.mac)
        self.assertEqual(device.config_picture, config.config_picture)
        self.assertEqual(device.away_hide, config.away_hide)
        self.assertEqual(device.consider_home, config.consider_home)

    def test_setup_without_yaml_file(self):
        """Test with no YAML file."""
        self.assertTrue(device_tracker.setup(self.hass, {}))

    def test_adding_unknown_device_to_config(self):
        """Test the adding of unknown devices to configuration file."""
        scanner = get_component('device_tracker.test').SCANNER
        scanner.reset()
        scanner.come_home('DEV1')

        self.assertTrue(device_tracker.setup(self.hass, {
            device_tracker.DOMAIN: {CONF_PLATFORM: 'test'}}))
        config = device_tracker.load_config(self.yaml_devices, self.hass,
                                            timedelta(seconds=0), 0)
        assert len(config) == 1
        assert config[0].dev_id == 'dev1'
        assert config[0].track

    def test_discovery(self):
        """Test discovery."""
        scanner = get_component('device_tracker.test').SCANNER

        with patch.dict(device_tracker.DISCOVERY_PLATFORMS, {'test': 'test'}):
            with patch.object(scanner, 'scan_devices') as mock_scan:
                self.assertTrue(device_tracker.setup(self.hass, {
                    device_tracker.DOMAIN: {CONF_PLATFORM: 'test'}}))
                fire_service_discovered(self.hass, 'test', {})
                self.assertTrue(mock_scan.called)

    def test_update_stale(self):
        """Test stalled update."""
        scanner = get_component('device_tracker.test').SCANNER
        scanner.reset()
        scanner.come_home('DEV1')

        register_time = datetime(2015, 9, 15, 23, tzinfo=dt_util.UTC)
        scan_time = datetime(2015, 9, 15, 23, 1, tzinfo=dt_util.UTC)

        with patch('homeassistant.components.device_tracker.dt_util.utcnow',
                   return_value=register_time):
            self.assertTrue(device_tracker.setup(self.hass, {
                'device_tracker': {
                    'platform': 'test',
                    'consider_home': 59,
                }}))

        self.assertEqual(STATE_HOME,
                         self.hass.states.get('device_tracker.dev1').state)

        scanner.leave_home('DEV1')

        with patch('homeassistant.components.device_tracker.dt_util.utcnow',
                   return_value=scan_time):
            fire_time_changed(self.hass, scan_time)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_NOT_HOME,
                         self.hass.states.get('device_tracker.dev1').state)

    def test_entity_attributes(self):
        """Test the entity attributes."""
        dev_id = 'test_entity'
        entity_id = device_tracker.ENTITY_ID_FORMAT.format(dev_id)
        friendly_name = 'Paulus'
        picture = 'http://placehold.it/200x200'

        device = device_tracker.Device(
            self.hass, timedelta(seconds=180), 0, True, dev_id, None,
            friendly_name, picture, away_hide=True)
        device_tracker.update_config(self.yaml_devices, dev_id, device)

        self.assertTrue(device_tracker.setup(self.hass, {}))

        attrs = self.hass.states.get(entity_id).attributes

        self.assertEqual(friendly_name, attrs.get(ATTR_FRIENDLY_NAME))
        self.assertEqual(picture, attrs.get(ATTR_ENTITY_PICTURE))

    def test_device_hidden(self):
        """Test hidden devices."""
        dev_id = 'test_entity'
        entity_id = device_tracker.ENTITY_ID_FORMAT.format(dev_id)
        device = device_tracker.Device(
            self.hass, timedelta(seconds=180), 0, True, dev_id, None,
            away_hide=True)
        device_tracker.update_config(self.yaml_devices, dev_id, device)

        scanner = get_component('device_tracker.test').SCANNER
        scanner.reset()

        self.assertTrue(device_tracker.setup(self.hass, {
            device_tracker.DOMAIN: {CONF_PLATFORM: 'test'}}))

        self.assertTrue(self.hass.states.get(entity_id)
                            .attributes.get(ATTR_HIDDEN))

    def test_group_all_devices(self):
        """Test grouping of devices."""
        dev_id = 'test_entity'
        entity_id = device_tracker.ENTITY_ID_FORMAT.format(dev_id)
        device = device_tracker.Device(
            self.hass, timedelta(seconds=180), 0, True, dev_id, None,
            away_hide=True)
        device_tracker.update_config(self.yaml_devices, dev_id, device)

        scanner = get_component('device_tracker.test').SCANNER
        scanner.reset()

        self.assertTrue(device_tracker.setup(self.hass, {
            device_tracker.DOMAIN: {CONF_PLATFORM: 'test'}}))

        state = self.hass.states.get(device_tracker.ENTITY_ID_ALL_DEVICES)
        self.assertIsNotNone(state)
        self.assertEqual(STATE_NOT_HOME, state.state)
        self.assertSequenceEqual((entity_id,),
                                 state.attributes.get(ATTR_ENTITY_ID))

    @patch('homeassistant.components.device_tracker.DeviceTracker.see')
    def test_see_service(self, mock_see):
        """Test the see service."""
        self.assertTrue(device_tracker.setup(self.hass, {}))
        mac = 'AB:CD:EF:GH'
        dev_id = 'some_device'
        host_name = 'example.com'
        location_name = 'Work'
        gps = [.3, .8]

        device_tracker.see(self.hass, mac, dev_id, host_name, location_name,
                           gps)

        self.hass.pool.block_till_done()

        mock_see.assert_called_once_with(
            mac=mac, dev_id=dev_id, host_name=host_name,
            location_name=location_name, gps=gps)
