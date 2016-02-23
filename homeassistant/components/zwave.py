"""
homeassistant.components.zwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Connects Home Assistant to a Z-Wave network.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/zwave/
"""
import os.path
import sys
from pprint import pprint

from homeassistant import bootstrap
from homeassistant.const import (
    ATTR_BATTERY_LEVEL, ATTR_DISCOVERED, ATTR_ENTITY_ID, ATTR_LOCATION,
    ATTR_SERVICE, CONF_CUSTOMIZE, EVENT_HOMEASSISTANT_START,
    EVENT_HOMEASSISTANT_STOP, EVENT_PLATFORM_DISCOVERED)
from homeassistant.util import convert, slugify

DOMAIN = "zwave"
REQUIREMENTS = ['pydispatcher==2.0.5']

CONF_USB_STICK_PATH = "usb_path"
DEFAULT_CONF_USB_STICK_PATH = "/zwaveusbstick"
CONF_DEBUG = "debug"
CONF_POLLING_INTERVAL = "polling_interval"
CONF_POLLING_INTENSITY = "polling_intensity"
DEFAULT_ZWAVE_CONFIG_PATH = os.path.join(sys.prefix, 'share',
                                         'python-openzwave', 'config')

SERVICE_ADD_NODE = "add_node"
SERVICE_REMOVE_NODE = "remove_node"

DISCOVER_SENSORS = "zwave.sensors"
DISCOVER_SWITCHES = "zwave.switch"
DISCOVER_LIGHTS = "zwave.light"
DISCOVER_THERMOSTATS = "zwave.thermostat"
DISCOVER_BINARY_SENSORS = 'zwave.binary_sensor'

EVENT_SCENE_ACTIVATED = "zwave.scene_activated"

COMMAND_CLASS_SWITCH_MULTILEVEL = 38

COMMAND_CLASS_SWITCH_BINARY = 37
COMMAND_CLASS_SENSOR_BINARY = 48
COMMAND_CLASS_SENSOR_MULTILEVEL = 49
COMMAND_CLASS_METER = 50
COMMAND_CLASS_BATTERY = 128
COMMAND_CLASS_ALARM = 113  # 0x71
COMMAND_CLASS_THERMOSTAT_OPERATING_STATE = 66
COMMAND_CLASS_THERMOSTAT_SETPOINT = 67 
COMMAND_CLASS_THERMOSTAT_MODE = 64 

GENRE_WHATEVER = None
GENRE_USER = "User"

TYPE_WHATEVER = None
TYPE_BYTE = "Byte"
TYPE_BOOL = "Bool"
TYPE_DECIMAL = "Decimal"


# list of tuple (DOMAIN, discovered service, supported command
# classes, value type)
DISCOVERY_COMPONENTS = [
    ('sensor',
     DISCOVER_SENSORS,
     [COMMAND_CLASS_SENSOR_MULTILEVEL,
      COMMAND_CLASS_METER,
      COMMAND_CLASS_ALARM],
     TYPE_WHATEVER,
     GENRE_USER),
    ('light',
     DISCOVER_LIGHTS,
     [COMMAND_CLASS_SWITCH_MULTILEVEL],
     TYPE_BYTE,
     GENRE_USER),
    ('switch',
     DISCOVER_SWITCHES,
     [COMMAND_CLASS_SWITCH_BINARY],
     TYPE_BOOL,
     GENRE_USER),
    ('thermostat',
        DISCOVER_THERMOSTATS,
         [COMMAND_CLASS_THERMOSTAT_OPERATING_STATE,
          COMMAND_CLASS_THERMOSTAT_MODE,
          COMMAND_CLASS_THERMOSTAT_SETPOINT],
        TYPE_WHATEVER,
        GENRE_USER),
    ('binary_sensor',
     DISCOVER_BINARY_SENSORS,
     [COMMAND_CLASS_SENSOR_BINARY],
     TYPE_BOOL,
     GENRE_USER)
]


ATTR_NODE_ID = "node_id"
ATTR_VALUE_ID = "value_id"

ATTR_SCENE_ID = "scene_id"

NETWORK = None


def _obj_to_dict(obj):
    """ Converts an obj into a hash for debug. """
    return {key: getattr(obj, key) for key
            in dir(obj)
            if key[0] != '_' and not hasattr(getattr(obj, key), '__call__')}


def _node_name(node):
    """ Returns the name of the node. """
    return node.name or "{} {}".format(
        node.manufacturer_name, node.product_name)


def _value_name(value):
    """ Returns the name of the value. """
    return "{} {}".format(_node_name(value.node), value.label)


def _object_id(value):
    """ Returns the object_id of the device value.
    The object_id contains node_id and value instance id
    to not collide with other entity_ids"""

    object_id = "{}_{}".format(slugify(_value_name(value)),
                               value.node.node_id)

    # Add the instance id if there is more than one instance for the value
    if value.instance > 1:
        return "{}_{}".format(object_id, value.instance)

    return object_id


def nice_print_node(node):
    """ Prints a nice formatted node to the output (debug method). """
    node_dict = _obj_to_dict(node)
    node_dict['values'] = {value_id: _obj_to_dict(value)
                           for value_id, value in node.values.items()}

    print("\n\n\n")
    print("FOUND NODE", node.product_name)
    pprint(node_dict)
    print("\n\n\n")


def get_config_value(node, value_index):
    """ Returns the current config value for a specific index. """

    try:
        for value in node.values.values():
            # 112 == config command class
            if value.command_class == 112 and value.index == value_index:
                return value.data
    except RuntimeError:
        # If we get an runtime error the dict has changed while
        # we was looking for a value, just do it again
        return get_config_value(node, value_index)


def setup(hass, config):
    """
    Setup Z-wave.
    Will automatically load components to support devices found on the network.
    """
    # pylint: disable=global-statement, import-error
    global NETWORK

    from pydispatch import dispatcher
    from openzwave.option import ZWaveOption
    from openzwave.network import ZWaveNetwork

    # Load configuration
    use_debug = str(config[DOMAIN].get(CONF_DEBUG)) == '1'
    customize = config[DOMAIN].get(CONF_CUSTOMIZE, {})

    # Setup options
    options = ZWaveOption(
        config[DOMAIN].get(CONF_USB_STICK_PATH, DEFAULT_CONF_USB_STICK_PATH),
        user_path=hass.config.config_dir,
        config_path=config[DOMAIN].get('config_path',
                                       DEFAULT_ZWAVE_CONFIG_PATH),)

    options.set_console_output(use_debug)
    options.lock()

    NETWORK = ZWaveNetwork(options, autostart=False)

    if use_debug:
        def log_all(signal, value=None):
            """ Log all the signals. """
            print("")
            print("SIGNAL *****", signal)
            if value and signal in (ZWaveNetwork.SIGNAL_VALUE_CHANGED,
                                    ZWaveNetwork.SIGNAL_VALUE_ADDED):
                pprint(_obj_to_dict(value))

            print("")

        dispatcher.connect(log_all, weak=False)

    def value_added(node, value):
        """ Called when a value is added to a node on the network. """

        for (component,
             discovery_service,
             command_ids,
             value_type,
             value_genre) in DISCOVERY_COMPONENTS:

            if value.command_class not in command_ids:
                continue
            if value_type is not None and value_type != value.type:
                continue
            if value_genre is not None and value_genre != value.genre:
                continue

            # Ensure component is loaded
            bootstrap.setup_component(hass, component, config)

            # Configure node
            name = "{}.{}".format(component, _object_id(value))

            node_config = customize.get(name, {})
            polling_intensity = convert(
                node_config.get(CONF_POLLING_INTENSITY), int)
            if polling_intensity is not None:
                value.enable_poll(polling_intensity)

            # Fire discovery event
            hass.bus.fire(EVENT_PLATFORM_DISCOVERED, {
                ATTR_SERVICE: discovery_service,
                ATTR_DISCOVERED: {
                    ATTR_NODE_ID: node.node_id,
                    ATTR_VALUE_ID: value.value_id,
                }
            })

    def scene_activated(node, scene_id):
        """ Called when a scene is activated on any node in the network. """
        name = _node_name(node)
        object_id = "{}_{}".format(slugify(name), node.node_id)

        hass.bus.fire(EVENT_SCENE_ACTIVATED, {
            ATTR_ENTITY_ID: object_id,
            ATTR_SCENE_ID: scene_id
        })

    dispatcher.connect(
        value_added, ZWaveNetwork.SIGNAL_VALUE_ADDED, weak=False)
    dispatcher.connect(
        scene_activated, ZWaveNetwork.SIGNAL_SCENE_EVENT, weak=False)

    def add_node(event):
        """ Switch into inclusion mode """
        NETWORK.controller.begin_command_add_device()

    def remove_node(event):
        """ Switch into exclusion mode"""
        NETWORK.controller.begin_command_remove_device()

    def stop_zwave(event):
        """ Stop Z-wave. """
        NETWORK.stop()

    def start_zwave(event):
        """ Called when Home Assistant starts up. """
        NETWORK.start()

        polling_interval = convert(
            config[DOMAIN].get(CONF_POLLING_INTERVAL), int)
        if polling_interval is not None:
            NETWORK.set_poll_interval(polling_interval, False)

        hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_zwave)

        # register add / remove node services for zwave sticks without
        # hardware inclusion button
        hass.services.register(DOMAIN, SERVICE_ADD_NODE, add_node)
        hass.services.register(DOMAIN, SERVICE_REMOVE_NODE, remove_node)

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_zwave)

    return True


class ZWaveDeviceEntity:
    """ Represents a ZWave node entity within Home Assistant. """
    def __init__(self, value, domain):
        self._value = value
        self.entity_id = "{}.{}".format(domain, self._object_id())

    @property
    def should_poll(self):
        """ False because we will push our own state to HA when changed. """
        return False

    @property
    def unique_id(self):
        """ Returns a unique id. """
        return "ZWAVE-{}-{}".format(self._value.node.node_id,
                                    self._value.object_id)

    @property
    def name(self):
        """ Returns the name of the device. """
        return _value_name(self._value)

    def _object_id(self):
        """ Returns the object_id of the device value.
        The object_id contains node_id and value instance id
        to not collide with other entity_ids"""

        return _object_id(self._value)

    @property
    def device_state_attributes(self):
        """ Returns device specific state attributes. """
        attrs = {
            ATTR_NODE_ID: self._value.node.node_id,
        }

        battery_level = self._value.node.get_battery_level()

        if battery_level is not None:
            attrs[ATTR_BATTERY_LEVEL] = battery_level

        location = self._value.node.location

        if location:
            attrs[ATTR_LOCATION] = location

        return attrs
