"""Th tests for the Rfxtrx component."""
# pylint: disable=too-many-public-methods,protected-access
import unittest
import time

from homeassistant.bootstrap import _setup_component
from homeassistant.components import rfxtrx as rfxtrx
from tests.common import get_test_home_assistant


class TestRFXTRX(unittest.TestCase):
    """Test the Rfxtrx component."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant(0)

    def tearDown(self):
        """Stop everything that was started."""
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS = []
        rfxtrx.RFX_DEVICES = {}
        if rfxtrx.RFXOBJECT:
            rfxtrx.RFXOBJECT.close_connection()
        self.hass.stop()

    def test_default_config(self):
        """Test configuration."""
        self.assertTrue(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True}
        }))

        self.assertTrue(_setup_component(self.hass, 'sensor', {
            'sensor': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices': {}}}))

        while len(rfxtrx.RFX_DEVICES) < 2:
            time.sleep(0.1)

        self.assertEqual(len(rfxtrx.RFXOBJECT.sensors()), 2)

    def test_valid_config(self):
        """Test configuration."""
        self.assertTrue(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True}}))

        self.assertTrue(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True,
                'debug': True}}))

    def test_invalid_config(self):
        """Test configuration."""
        self.assertFalse(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {}
        }))

        self.assertFalse(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'invalid_key': True}}))

    def test_fire_event(self):
        """Test fire event."""

        self.assertTrue(_setup_component(self.hass, 'rfxtrx', {
            'rfxtrx': {
                'device': '/dev/serial/by-id/usb' +
                          '-RFXCOM_RFXtrx433_A1Y0NJGR-if00-port0',
                'dummy': True}
        }))
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'213c7f216': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51',
                               rfxtrx.ATTR_FIREEVENT: True}
                            }}}))

        calls = []

        def record_event(event):
            """Add recorded event to set."""
            calls.append(event)

        self.hass.bus.listen(rfxtrx.EVENT_BUTTON_PRESSED, record_event)

        entity = rfxtrx.RFX_DEVICES['213c7f216']
        self.assertEqual('Test', entity.name)
        self.assertEqual('off', entity.state)
        self.assertTrue(entity.should_fire_event)

        event = rfxtrx.get_rfx_object('0b1100cd0213c7f210010f51')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x10, 0x01, 0x18,
                                0xcd, 0xea, 0x01, 0x01, 0x0f, 0x70])
        rfxtrx.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.hass.pool.block_till_done()

        self.assertEqual(event.values['Command'], "On")
        self.assertEqual('on', entity.state)
        self.assertEqual(1, len(rfxtrx.RFX_DEVICES))
        self.assertEqual(1, len(calls))
        self.assertEqual(calls[0].data,
                         {'entity_id': 'switch.test', 'state': 'on'})
