"""The tests for the location automation."""
import unittest

from homeassistant.components import automation, zone

from tests.common import get_test_home_assistant


class TestAutomationZone(unittest.TestCase):
    """Test the event automation."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()
        zone.setup(self.hass, {
            'zone': {
                'name': 'test',
                'latitude': 32.880837,
                'longitude': -117.237561,
                'radius': 250,
            }
        })

        self.calls = []

        def record_call(service):
            self.calls.append(service)

        self.hass.services.register('test', 'automation', record_call)

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop everything that was started."""
        self.hass.stop()

    def test_if_fires_on_zone_enter(self):
        """Test for firing on zone enter."""
        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.881011,
            'longitude': -117.234758
        })
        self.hass.pool.block_till_done()

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'zone',
                    'entity_id': 'test.entity',
                    'zone': 'zone.test',
                    'event': 'enter',
                },
                'action': {
                    'service': 'test.automation',
                }
            }
        }))

        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.880586,
            'longitude': -117.237564
        })
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

    def test_if_not_fires_for_enter_on_zone_leave(self):
        """Test for not firing on zone leave."""
        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.880586,
            'longitude': -117.237564
        })
        self.hass.pool.block_till_done()

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'zone',
                    'entity_id': 'test.entity',
                    'zone': 'zone.test',
                    'event': 'enter',
                },
                'action': {
                    'service': 'test.automation',
                }
            }
        }))

        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.881011,
            'longitude': -117.234758
        })
        self.hass.pool.block_till_done()

        self.assertEqual(0, len(self.calls))

    def test_if_fires_on_zone_leave(self):
        """Test for firing on zone leave."""
        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.880586,
            'longitude': -117.237564
        })
        self.hass.pool.block_till_done()

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'zone',
                    'entity_id': 'test.entity',
                    'zone': 'zone.test',
                    'event': 'leave',
                },
                'action': {
                    'service': 'test.automation',
                }
            }
        }))

        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.881011,
            'longitude': -117.234758
        })
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

    def test_if_not_fires_for_leave_on_zone_enter(self):
        """Test for not firing on zone enter."""
        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.881011,
            'longitude': -117.234758
        })
        self.hass.pool.block_till_done()

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'zone',
                    'entity_id': 'test.entity',
                    'zone': 'zone.test',
                    'event': 'leave',
                },
                'action': {
                    'service': 'test.automation',
                }
            }
        }))

        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.880586,
            'longitude': -117.237564
        })
        self.hass.pool.block_till_done()

        self.assertEqual(0, len(self.calls))

    def test_zone_condition(self):
        """Test for zone condition."""
        self.hass.states.set('test.entity', 'hello', {
            'latitude': 32.880586,
            'longitude': -117.237564
        })
        self.hass.pool.block_till_done()

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'event',
                    'event_type': 'test_event'
                },
                'condition': {
                    'platform': 'zone',
                    'entity_id': 'test.entity',
                    'zone': 'zone.test',
                },
                'action': {
                    'service': 'test.automation',
                }
            }
        }))

        self.hass.bus.fire('test_event')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))
