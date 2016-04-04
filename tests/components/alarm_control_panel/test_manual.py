"""The tests for the manual Alarm Control Panel component."""
from datetime import timedelta
import unittest
from unittest.mock import patch

from homeassistant.const import (
    STATE_ALARM_DISARMED, STATE_ALARM_ARMED_HOME, STATE_ALARM_ARMED_AWAY,
    STATE_ALARM_PENDING, STATE_ALARM_TRIGGERED)
from homeassistant.components import alarm_control_panel
import homeassistant.util.dt as dt_util

from tests.common import fire_time_changed, get_test_home_assistant

CODE = 'HELLO_CODE'


class TestAlarmControlPanelManual(unittest.TestCase):
    """Test the manual alarm module."""

    def setUp(self):  # pylint: disable=invalid-name
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def tearDown(self):  # pylint: disable=invalid-name
        """Stop down everything that was started."""
        self.hass.stop()

    def test_arm_home_no_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 0
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_home(self.hass, CODE)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_ARMED_HOME,
                         self.hass.states.get(entity_id).state)

    def test_arm_home_with_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 1
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_home(self.hass, CODE, entity_id)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=1)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_ARMED_HOME,
                         self.hass.states.get(entity_id).state)

    def test_arm_home_with_invalid_code(self):
        """Attempt to arm home without a valid code."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 1
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_home(self.hass, CODE + '2')
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

    def test_arm_away_no_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 0
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_away(self.hass, CODE, entity_id)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_ARMED_AWAY,
                         self.hass.states.get(entity_id).state)

    def test_arm_away_with_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 1
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_away(self.hass, CODE)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=1)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_ARMED_AWAY,
                         self.hass.states.get(entity_id).state)

    def test_arm_away_with_invalid_code(self):
        """Attempt to arm away without a valid code."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'code': CODE,
                'pending_time': 1
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_arm_away(self.hass, CODE + '2')
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

    def test_trigger_no_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'trigger_time': 0
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_trigger(self.hass, entity_id=entity_id)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_TRIGGERED,
                         self.hass.states.get(entity_id).state)

    def test_trigger_with_pending(self):
        """Test arm home method."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'pending_time': 2,
                'trigger_time': 3
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_trigger(self.hass)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=2)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_TRIGGERED,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

    def test_disarm_while_pending_trigger(self):
        """Test disarming while pending state."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'trigger_time': 5
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_trigger(self.hass)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_disarm(self.hass, entity_id=entity_id)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

    def test_disarm_during_trigger_with_invalid_code(self):
        """Test disarming while code is invalid."""
        self.assertTrue(alarm_control_panel.setup(self.hass, {
            'alarm_control_panel': {
                'platform': 'manual',
                'name': 'test',
                'pending_time': 5,
                'code': CODE + '2'
            }}))

        entity_id = 'alarm_control_panel.test'

        self.assertEqual(STATE_ALARM_DISARMED,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_trigger(self.hass)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        alarm_control_panel.alarm_disarm(self.hass, entity_id=entity_id)
        self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_PENDING,
                         self.hass.states.get(entity_id).state)

        future = dt_util.utcnow() + timedelta(seconds=5)
        with patch(('homeassistant.components.alarm_control_panel.manual.'
                    'dt_util.utcnow'), return_value=future):
            fire_time_changed(self.hass, future)
            self.hass.pool.block_till_done()

        self.assertEqual(STATE_ALARM_TRIGGERED,
                         self.hass.states.get(entity_id).state)
