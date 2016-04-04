"""Test zone component."""
import unittest

from homeassistant.components import zone

from tests.common import get_test_home_assistant


class TestComponentZone(unittest.TestCase):
    """Test the zone component."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_setup(self):
        """Test setup."""
        info = {
            'name': 'Test Zone',
            'latitude': 32.880837,
            'longitude': -117.237561,
            'radius': 250,
            'passive': True
        }
        assert zone.setup(self.hass, {
            'zone': info
        })

        state = self.hass.states.get('zone.test_zone')
        assert info['name'] == state.name
        assert info['latitude'] == state.attributes['latitude']
        assert info['longitude'] == state.attributes['longitude']
        assert info['radius'] == state.attributes['radius']
        assert info['passive'] == state.attributes['passive']

    def test_active_zone_skips_passive_zones(self):
        """Test active and passive zones."""
        assert zone.setup(self.hass, {
            'zone': [
                {
                    'name': 'Passive Zone',
                    'latitude': 32.880600,
                    'longitude': -117.237561,
                    'radius': 250,
                    'passive': True
                },
            ]
        })

        active = zone.active_zone(self.hass, 32.880600, -117.237561)
        assert active is None

        assert zone.setup(self.hass, {
            'zone': [
                {
                    'name': 'Active Zone',
                    'latitude': 32.880800,
                    'longitude': -117.237561,
                    'radius': 500,
                },
            ]
        })

        active = zone.active_zone(self.hass, 32.880700, -117.237561)
        assert 'zone.active_zone' == active.entity_id

    def test_active_zone_prefers_smaller_zone_if_same_distance(self):
        """Test zone size preferences."""
        latitude = 32.880600
        longitude = -117.237561
        assert zone.setup(self.hass, {
            'zone': [
                {
                    'name': 'Small Zone',
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': 250,
                },
                {
                    'name': 'Big Zone',
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': 500,
                },
            ]
        })

        active = zone.active_zone(self.hass, latitude, longitude)
        assert 'zone.small_zone' == active.entity_id

        assert zone.setup(self.hass, {
            'zone': [
                {
                    'name': 'Smallest Zone',
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': 50,
                },
            ]
        })

        active = zone.active_zone(self.hass, latitude, longitude)
        assert 'zone.smallest_zone' == active.entity_id

    def test_in_zone_works_for_passive_zones(self):
        """Test working in passive zones."""
        latitude = 32.880600
        longitude = -117.237561
        assert zone.setup(self.hass, {
            'zone': [
                {
                    'name': 'Passive Zone',
                    'latitude': latitude,
                    'longitude': longitude,
                    'radius': 250,
                    'passive': True
                },
            ]
        })

        assert zone.in_zone(self.hass.states.get('zone.passive_zone'),
                            latitude, longitude)
