"""The tests for the Rfxtrx switch platform."""
import unittest

from homeassistant.bootstrap import _setup_component
from homeassistant.components import rfxtrx as rfxtrx_core

from tests.common import get_test_home_assistant


class TestSwitchRfxtrx(unittest.TestCase):
    """Test the Rfxtrx switch platform."""

    def setUp(self):
        """Setup things to be run when tests are started."""
        self.hass = get_test_home_assistant(0)
        self.hass.config.components = ['rfxtrx']

    def tearDown(self):
        """Stop everything that was started."""
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS = []
        rfxtrx_core.RFX_DEVICES = {}
        if rfxtrx_core.RFXOBJECT:
            rfxtrx_core.RFXOBJECT.close_connection()
        self.hass.stop()

    def test_valid_config(self):
        """Test configuration."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'213c7f216': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51',
                               rfxtrx_core.ATTR_FIREEVENT: True}
                            }}}))

    def test_invalid_config1(self):
        self.assertFalse(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'2FF7f216': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51',
                               'signal_repetitions': 3}
                            }}}))

    def test_invalid_config2(self):
        """Test configuration."""
        self.assertFalse(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'invalid_key': 'afda',
                       'devices':
                           {'213c7f216': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51',
                               rfxtrx_core.ATTR_FIREEVENT: True}
                            }}}))

    def test_invalid_config3(self):
        self.assertFalse(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'213c7f216': {
                               'name': 'Test',
                               'packetid': 'AA1100cd0213c7f210010f51',
                               rfxtrx_core.ATTR_FIREEVENT: True}
                            }}}))

    def test_invalid_config4(self):
        self.assertFalse(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'AA3c7f216': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51',
                               rfxtrx_core.ATTR_FIREEVENT: True}
                            }}}))

    def test_invalid_config5(self):
        """Test configuration."""
        self.assertFalse(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices':
                           {'213c7f216': {
                               'name': 'Test',
                               rfxtrx_core.ATTR_FIREEVENT: True}
                            }}}))

    def test_default_config(self):
        """Test with 0 switches."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'devices':
                           {}}}))
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))

    def test_one_switch(self):
        """Test with 1 switch."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'devices':
                           {'123efab1': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f210010f51'}}}}))

        import RFXtrx as rfxtrxmod
        rfxtrx_core.RFXOBJECT =\
            rfxtrxmod.Core("", transport_protocol=rfxtrxmod.DummyTransport)

        self.assertEqual(1,  len(rfxtrx_core.RFX_DEVICES))
        entity = rfxtrx_core.RFX_DEVICES['123efab1']
        self.assertEqual('Test', entity.name)
        self.assertEqual('off', entity.state)
        self.assertTrue(entity.assumed_state)
        self.assertEqual(entity.signal_repetitions, 1)
        self.assertFalse(entity.should_fire_event)
        self.assertFalse(entity.should_poll)

        self.assertFalse(entity.is_on)
        entity.turn_on()
        self.assertTrue(entity.is_on)
        entity.turn_off()
        self.assertFalse(entity.is_on)

    def test_several_switches(self):
        """Test with 3 switches."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'signal_repetitions': 3,
                       'devices':
                           {'123efab1': {
                               'name': 'Test',
                               'packetid': '0b1100cd0213c7f230010f71'},
                            '118cdea2': {
                            'name': 'Bath',
                            'packetid': '0b1100100118cdea02010f70'},
                            '213c7f216': {
                            'name': 'Living',
                            'packetid': '0b1100100118cdea02010f70'}}}}))

        self.assertEqual(3, len(rfxtrx_core.RFX_DEVICES))
        device_num = 0
        for id in rfxtrx_core.RFX_DEVICES:
            entity = rfxtrx_core.RFX_DEVICES[id]
            self.assertEqual(entity.signal_repetitions, 3)
            if entity.name == 'Living':
                device_num = device_num + 1
                self.assertEqual('off', entity.state)
                self.assertEqual('<Entity Living: off>', entity.__str__())
            elif entity.name == 'Bath':
                device_num = device_num + 1
                self.assertEqual('off', entity.state)
                self.assertEqual('<Entity Bath: off>', entity.__str__())
            elif entity.name == 'Test':
                device_num = device_num + 1
                self.assertEqual('off', entity.state)
                self.assertEqual('<Entity Test: off>', entity.__str__())

        self.assertEqual(3, device_num)

    def test_discover_switch(self):
        """Test with discovery of switches."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': True,
                       'devices': {}}}))

        event = rfxtrx_core.get_rfx_object('0b1100100118cdea02010f70')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x10, 0x01, 0x18,
                                0xcd, 0xea, 0x01, 0x01, 0x0f, 0x70])

        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        entity = rfxtrx_core.RFX_DEVICES['118cdea2']
        self.assertEqual(1, len(rfxtrx_core.RFX_DEVICES))
        self.assertEqual('<Entity 118cdea2 : 0b1100100118cdea01010f70: on>',
                         entity.__str__())

        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(1, len(rfxtrx_core.RFX_DEVICES))

        event = rfxtrx_core.get_rfx_object('0b1100100118cdeb02010f70')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x12, 0x01, 0x18,
                                0xcd, 0xea, 0x02, 0x00, 0x00, 0x70])

        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        entity = rfxtrx_core.RFX_DEVICES['118cdeb2']
        self.assertEqual(2, len(rfxtrx_core.RFX_DEVICES))
        self.assertEqual('<Entity 118cdeb2 : 0b1100120118cdea02000070: on>',
                         entity.__str__())

        # Trying to add a sensor
        event = rfxtrx_core.get_rfx_object('0a52085e070100b31b0279')
        event.data = bytearray(b'\nR\x08^\x07\x01\x00\xb3\x1b\x02y')
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(2, len(rfxtrx_core.RFX_DEVICES))

        # Trying to add a light
        event = rfxtrx_core.get_rfx_object('0b1100100118cdea02010f70')
        event.data = bytearray([0x0b, 0x11, 0x11, 0x10, 0x01, 0x18,
                                0xcd, 0xea, 0x01, 0x02, 0x0f, 0x70])
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(2, len(rfxtrx_core.RFX_DEVICES))

    def test_discover_switch_noautoadd(self):
        """Test with discovery of switch when auto add is False."""
        self.assertTrue(_setup_component(self.hass, 'switch', {
            'switch': {'platform': 'rfxtrx',
                       'automatic_add': False,
                       'devices': {}}}))

        event = rfxtrx_core.get_rfx_object('0b1100100118cdea02010f70')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x10, 0x01, 0x18,
                                0xcd, 0xea, 0x01, 0x01, 0x0f, 0x70])

        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))

        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))

        event = rfxtrx_core.get_rfx_object('0b1100100118cdeb02010f70')
        event.data = bytearray([0x0b, 0x11, 0x00, 0x12, 0x01, 0x18,
                                0xcd, 0xea, 0x02, 0x00, 0x00, 0x70])
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))

        # Trying to add a sensor
        event = rfxtrx_core.get_rfx_object('0a52085e070100b31b0279')
        event.data = bytearray(b'\nR\x08^\x07\x01\x00\xb3\x1b\x02y')
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))

        # Trying to add a light
        event = rfxtrx_core.get_rfx_object('0b1100100118cdea02010f70')
        event.data = bytearray([0x0b, 0x11, 0x11, 0x10, 0x01,
                                0x18, 0xcd, 0xea, 0x01, 0x02, 0x0f, 0x70])
        rfxtrx_core.RECEIVED_EVT_SUBSCRIBERS[0](event)
        self.assertEqual(0, len(rfxtrx_core.RFX_DEVICES))
