"""
tests.components.automation.test_state
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Tests state automation.
"""
import unittest
from datetime import timedelta
from unittest.mock import patch

import homeassistant.util.dt as dt_util
import homeassistant.components.automation as automation
import homeassistant.components.automation.state as state

from tests.common import fire_time_changed, get_test_home_assistant


class TestAutomationState(unittest.TestCase):
    """ Test the event automation. """

    def setUp(self):  # pylint: disable=invalid-name
        self.hass = get_test_home_assistant()
        self.hass.states.set('test.entity', 'hello')
        self.calls = []

        def record_call(service):
            self.calls.append(service)

        self.hass.services.register('test', 'automation', record_call)

    def tearDown(self):  # pylint: disable=invalid-name
        """ Stop down stuff we started. """
        self.hass.stop()

    def test_old_config_if_fires_on_entity_change(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_old_config_if_fires_on_entity_change_with_from_filter(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'state_from': 'hello',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_old_config_if_fires_on_entity_change_with_to_filter(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'state_to': 'world',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_old_config_if_fires_on_entity_change_with_both_filters(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'state_from': 'hello',
                'state_to': 'world',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_old_config_if_not_fires_if_to_filter_not_match(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'state_from': 'hello',
                'state_to': 'world',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'moon')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_old_config_if_not_fires_if_from_filter_not_match(self):
        self.hass.states.set('test.entity', 'bye')

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.entity',
                'state_from': 'hello',
                'state_to': 'world',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_old_config_if_not_fires_if_entity_not_match(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'state',
                'state_entity_id': 'test.another_entity',
                'execute_service': 'test.automation'
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_old_config_if_action(self):
        entity_id = 'domain.test_entity'
        test_state = 'new_state'
        automation.setup(self.hass, {
            automation.DOMAIN: {
                'platform': 'event',
                'event_type': 'test_event',
                'execute_service': 'test.automation',
                'if': [{
                    'platform': 'state',
                    'entity_id': entity_id,
                    'state': test_state,
                }]
            }
        })

        self.hass.states.set(entity_id, test_state)
        self.hass.bus.fire('test_event')
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

        self.hass.states.set(entity_id, test_state + 'something')
        self.hass.bus.fire('test_event')
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_entity_change(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_entity_change_with_from_filter(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'from': 'hello'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_entity_change_with_to_filter(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'to': 'world'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_entity_change_with_state_filter(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'state': 'world'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_entity_change_with_both_filters(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'from': 'hello',
                    'to': 'world'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_not_fires_if_to_filter_not_match(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'from': 'hello',
                    'to': 'world'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'moon')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_if_not_fires_if_from_filter_not_match(self):
        self.hass.states.set('test.entity', 'bye')

        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'from': 'hello',
                    'to': 'world'
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_if_not_fires_if_entity_not_match(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.anoter_entity',
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_if_action(self):
        entity_id = 'domain.test_entity'
        test_state = 'new_state'
        automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'event',
                    'event_type': 'test_event',
                },
                'condition': [{
                    'platform': 'state',
                    'entity_id': entity_id,
                    'state': test_state
                }],
                'action': {
                    'service': 'test.automation'
                }
            }
        })

        self.hass.states.set(entity_id, test_state)
        self.hass.bus.fire('test_event')
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

        self.hass.states.set(entity_id, test_state + 'something')
        self.hass.bus.fire('test_event')
        self.hass.pool.block_till_done()

        self.assertEqual(1, len(self.calls))

    def test_if_fails_setup_if_to_boolean_value(self):
        self.assertFalse(state.trigger(
            self.hass, {
                'platform': 'state',
                'entity_id': 'test.entity',
                'to': True,
            }, lambda x: x))

    def test_if_fails_setup_if_from_boolean_value(self):
        self.assertFalse(state.trigger(
            self.hass, {
                'platform': 'state',
                'entity_id': 'test.entity',
                'from': True,
            }, lambda x: x))

    def test_if_fails_setup_bad_for(self):
        self.assertFalse(state.trigger(
            self.hass, {
                'platform': 'state',
                'entity_id': 'test.entity',
                'to': 'world',
                'for': {
                    'invalid': 5
                },
            }, lambda x: x))

    def test_if_fails_setup_for_without_to(self):
        self.assertFalse(state.trigger(
            self.hass, {
                'platform': 'state',
                'entity_id': 'test.entity',
                'for': {
                    'seconds': 5
                },
            }, lambda x: x))

    def test_if_not_fires_on_entity_change_with_for(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'to': 'world',
                    'for': {
                        'seconds': 5
                    },
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        self.hass.states.set('test.entity', 'not_world')
        self.hass.pool.block_till_done()
        fire_time_changed(self.hass, dt_util.utcnow() + timedelta(seconds=10))
        self.hass.pool.block_till_done()
        self.assertEqual(0, len(self.calls))

    def test_if_fires_on_entity_change_with_for(self):
        self.assertTrue(automation.setup(self.hass, {
            automation.DOMAIN: {
                'trigger': {
                    'platform': 'state',
                    'entity_id': 'test.entity',
                    'to': 'world',
                    'for': {
                        'seconds': 5
                    },
                },
                'action': {
                    'service': 'test.automation'
                }
            }
        }))

        self.hass.states.set('test.entity', 'world')
        self.hass.pool.block_till_done()
        fire_time_changed(self.hass, dt_util.utcnow() + timedelta(seconds=10))
        self.hass.pool.block_till_done()
        self.assertEqual(1, len(self.calls))

    def test_if_fires_on_for_condition(self):
        point1 = dt_util.utcnow()
        point2 = point1 + timedelta(seconds=10)
        with patch('homeassistant.core.dt_util.utcnow') as mock_utcnow:
            mock_utcnow.return_value = point1
            self.hass.states.set('test.entity', 'on')
            self.assertTrue(automation.setup(self.hass, {
                automation.DOMAIN: {
                    'trigger': {
                        'platform': 'event',
                        'event_type': 'test_event',
                    },
                    'condition': {
                        'platform': 'state',
                        'entity_id': 'test.entity',
                        'state': 'on',
                        'for': {
                            'seconds': 5
                        },
                    },

                    'action': {
                        'service': 'test.automation'
                    }
                }
            }))

            # not enough time has passed
            self.hass.bus.fire('test_event')
            self.hass.pool.block_till_done()
            self.assertEqual(0, len(self.calls))

            # Time travel 10 secs into the future
            mock_utcnow.return_value = point2
            self.hass.bus.fire('test_event')
            self.hass.pool.block_till_done()
            self.assertEqual(1, len(self.calls))

    def test_if_fails_setup_for_without_time(self):
        self.assertIsNone(state.if_action(
            self.hass, {
                'platform': 'state',
                'entity_id': 'test.entity',
                'state': 'on',
                'for': {},
            }))

    def test_if_fails_setup_for_without_entity(self):
        self.assertIsNone(state.if_action(
            self.hass, {
                'platform': 'state',
                'state': 'on',
                'for': {
                    'seconds': 5
                },
            }))
