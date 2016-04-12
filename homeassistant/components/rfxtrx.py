"""
Support for RFXtrx components.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/rfxtrx/
"""
import logging
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.util import slugify
from homeassistant.const import EVENT_HOMEASSISTANT_STOP
from homeassistant.helpers.entity import Entity
from homeassistant.const import ATTR_ENTITY_ID

REQUIREMENTS = ['pyRFXtrx==0.6.5']

DOMAIN = "rfxtrx"

ATTR_AUTOMATIC_ADD = 'automatic_add'
ATTR_DEVICE = 'device'
ATTR_DEBUG = 'debug'
ATTR_STATE = 'state'
ATTR_NAME = 'name'
ATTR_PACKETID = 'packetid'
ATTR_FIREEVENT = 'fire_event'
ATTR_DATA_TYPE = 'data_type'
ATTR_DUMMY = 'dummy'
CONF_SIGNAL_REPETITIONS = 'signal_repetitions'
CONF_DEVICES = 'devices'
DEFAULT_SIGNAL_REPETITIONS = 1

EVENT_BUTTON_PRESSED = 'button_pressed'

RECEIVED_EVT_SUBSCRIBERS = []
RFX_DEVICES = {}
_LOGGER = logging.getLogger(__name__)
RFXOBJECT = None


def validate_packetid(value):
    """Validate that value is a valid packet id for rfxtrx."""
    if get_rfx_object(value):
        return value
    else:
        raise vol.Invalid('invalid packet id for {}'.format(value))

# Share between rfxtrx platforms
VALID_DEVICE_ID = vol.All(cv.string, vol.Lower)
VALID_SENSOR_DEVICE_ID = vol.All(VALID_DEVICE_ID,
                                 vol.truth(lambda val:
                                           val.startswith('sensor_')))

DEVICE_SCHEMA = vol.Schema({
    vol.Required(ATTR_NAME): cv.string,
    vol.Required(ATTR_PACKETID): validate_packetid,
    vol.Optional(ATTR_FIREEVENT, default=False): cv.boolean,
})

DEFAULT_SCHEMA = vol.Schema({
    vol.Required("platform"): DOMAIN,
    vol.Required(CONF_DEVICES): {cv.slug: DEVICE_SCHEMA},
    vol.Optional(ATTR_AUTOMATIC_ADD, default=False):  cv.boolean,
    vol.Optional(CONF_SIGNAL_REPETITIONS, default=DEFAULT_SIGNAL_REPETITIONS):
        vol.Coerce(int),
})

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(ATTR_DEVICE): VALID_DEVICE_ID,
        vol.Optional(ATTR_DEBUG, default=False): cv.boolean,
        vol.Optional(ATTR_DUMMY, default=False): cv.boolean,
    }),
}, extra=vol.ALLOW_EXTRA)


def setup(hass, config):
    """Setup the RFXtrx component."""
    # Declare the Handle event
    def handle_receive(event):
        """Callback all subscribers for RFXtrx gateway."""
        # Log RFXCOM event
        if not event.device.id_string:
            return
        entity_id = slugify(event.device.id_string.lower())
        packet_id = "".join("{0:02x}".format(x) for x in event.data)
        entity_name = "%s : %s" % (entity_id, packet_id)
        _LOGGER.info("Receive RFXCOM event from %s => %s",
                     event.device, entity_name)

        # Callback to HA registered components.
        for subscriber in RECEIVED_EVT_SUBSCRIBERS:
            subscriber(event)

    # Try to load the RFXtrx module.
    import RFXtrx as rfxtrxmod

    # Init the rfxtrx module.
    global RFXOBJECT

    device = config[DOMAIN][ATTR_DEVICE]
    debug = config[DOMAIN][ATTR_DEBUG]
    dummy_connection = config[DOMAIN][ATTR_DUMMY]

    if dummy_connection:
        RFXOBJECT =\
            rfxtrxmod.Core(device, handle_receive, debug=debug,
                           transport_protocol=rfxtrxmod.DummyTransport2)
    else:
        RFXOBJECT = rfxtrxmod.Core(device, handle_receive, debug=debug)

    def _shutdown_rfxtrx(event):
        RFXOBJECT.close_connection()
    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, _shutdown_rfxtrx)

    return True


def get_rfx_object(packetid):
    """Return the RFXObject with the packetid."""
    import RFXtrx as rfxtrxmod

    binarypacket = bytearray.fromhex(packetid)

    pkt = rfxtrxmod.lowlevel.parse(binarypacket)
    if pkt is not None:
        if isinstance(pkt, rfxtrxmod.lowlevel.SensorPacket):
            obj = rfxtrxmod.SensorEvent(pkt)
        elif isinstance(pkt, rfxtrxmod.lowlevel.Status):
            obj = rfxtrxmod.StatusEvent(pkt)
        else:
            obj = rfxtrxmod.ControlEvent(pkt)

        return obj

    return None


def get_devices_from_config(config, device):
    """Read rfxtrx configuration."""
    signal_repetitions = config[CONF_SIGNAL_REPETITIONS]

    devices = []
    for device_id, entity_info in config[CONF_DEVICES].items():
        if device_id in RFX_DEVICES:
            continue
        _LOGGER.info("Add %s rfxtrx", entity_info[ATTR_NAME])

        # Check if i must fire event
        fire_event = entity_info[ATTR_FIREEVENT]
        datas = {ATTR_STATE: False, ATTR_FIREEVENT: fire_event}

        rfxobject = get_rfx_object(entity_info[ATTR_PACKETID])
        new_device = device(entity_info[ATTR_NAME], rfxobject, datas,
                            signal_repetitions)
        RFX_DEVICES[device_id] = new_device
        devices.append(new_device)
    return devices


def get_new_device(event, config, device):
    """Add entity if not exist and the automatic_add is True."""
    device_id = slugify(event.device.id_string.lower())
    if device_id not in RFX_DEVICES:
        automatic_add = config[ATTR_AUTOMATIC_ADD]
        if not automatic_add:
            return

        _LOGGER.info(
            "Automatic add %s rfxtrx device (Class: %s Sub: %s)",
            device_id,
            event.device.__class__.__name__,
            event.device.subtype
        )
        pkt_id = "".join("{0:02x}".format(x) for x in event.data)
        entity_name = "%s : %s" % (device_id, pkt_id)
        datas = {ATTR_STATE: False, ATTR_FIREEVENT: False}
        signal_repetitions = config[CONF_SIGNAL_REPETITIONS]
        new_device = device(entity_name, event, datas,
                            signal_repetitions)
        RFX_DEVICES[device_id] = new_device
        return new_device


def apply_received_command(event):
    """Apply command from rfxtrx."""
    device_id = slugify(event.device.id_string.lower())
    # Check if entity exists or previously added automatically
    if device_id in RFX_DEVICES:
        _LOGGER.debug(
            "EntityID: %s light_update. Command: %s",
            device_id,
            event.values['Command']
        )

        if event.values['Command'] == 'On'\
                or event.values['Command'] == 'Off':

            # Update the rfxtrx device state
            is_on = event.values['Command'] == 'On'
            # pylint: disable=protected-access
            RFX_DEVICES[device_id]._state = is_on
            RFX_DEVICES[device_id].update_ha_state()

        elif hasattr(RFX_DEVICES[device_id], 'brightness')\
                and event.values['Command'] == 'Set level':
            # pylint: disable=protected-access
            RFX_DEVICES[device_id]._brightness = \
                (event.values['Dim level'] * 255 // 100)

            # Update the rfxtrx device state
            is_on = RFX_DEVICES[device_id]._brightness > 0
            RFX_DEVICES[device_id]._state = is_on
            RFX_DEVICES[device_id].update_ha_state()

        # Fire event
        if RFX_DEVICES[device_id].should_fire_event:
            RFX_DEVICES[device_id].hass.bus.fire(
                EVENT_BUTTON_PRESSED, {
                    ATTR_ENTITY_ID:
                        RFX_DEVICES[device_id].entity_id,
                    ATTR_STATE: event.values['Command'].lower()
                }
            )


class RfxtrxDevice(Entity):
    """Represents a Rfxtrx device.

    Contains the common logic for all Rfxtrx devices.

    """

    def __init__(self, name, event, datas, signal_repetitions):
        """Initialize the device."""
        self._name = name
        self._event = event
        self._state = datas[ATTR_STATE]
        self._should_fire_event = datas[ATTR_FIREEVENT]
        self.signal_repetitions = signal_repetitions
        self._brightness = 0

    @property
    def should_poll(self):
        """No polling needed for a RFXtrx switch."""
        return False

    @property
    def name(self):
        """Return the name of the device if any."""
        return self._name

    @property
    def should_fire_event(self):
        """Return is the device must fire event."""
        return self._should_fire_event

    @property
    def is_on(self):
        """Return true if light is on."""
        return self._state

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return True

    def turn_off(self, **kwargs):
        """Turn the light off."""
        self._send_command("turn_off")

    def _send_command(self, command, brightness=0):
        if not self._event:
            return

        if command == "turn_on":
            for _ in range(self.signal_repetitions):
                self._event.device.send_on(RFXOBJECT.transport)
            self._state = True

        elif command == "dim":
            for _ in range(self.signal_repetitions):
                self._event.device.send_dim(RFXOBJECT.transport,
                                            brightness)
            self._state = True

        elif command == 'turn_off':
            for _ in range(self.signal_repetitions):
                self._event.device.send_off(RFXOBJECT.transport)
            self._state = False
            self._brightness = 0

        self.update_ha_state()
