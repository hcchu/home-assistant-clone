"""
homeassistant.components.thermostat.zwave
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Interfaces with Z-Wave thermostats.

For more details about this platform, please refer to the documentation
at https://home-assistant.io/components/zwave/
"""
# Because we do not compile openzwave on CI
# pylint: disable=import-error
import logging
import datetime
from urllib.error import URLError

import homeassistant.components.zwave as zwave
from homeassistant.helpers.entity import Entity
from homeassistant.components.thermostat import (ThermostatDevice, STATE_COOL,
                                                 STATE_IDLE, STATE_HEAT)
from homeassistant.const import (CONF_HOST, TEMP_FAHRENHEIT)

def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Sets up Z-Wave thermostat. """

    # Return on empty `discovery_info`. Given you configure HA with:
    #
    # sensor:
    #   platform: zwave
    #
    # `setup_platform` will be called without `discovery_info`.
    if discovery_info is None:
        return

    node = zwave.NETWORK.nodes[discovery_info[zwave.ATTR_NODE_ID]]
    value = node.values[discovery_info[zwave.ATTR_VALUE_ID]]

    if value.command_class != zwave.COMMAND_CLASS_THERMOSTAT_SETPOINT:
        return

    value.set_change_verified(False)

    # if 1 in groups and (zwave.NETWORK.controller.node_id not in
    #                     groups[1].associations):
    #     node.groups[1].add_association(zwave.NETWORK.controller.node_id)


    add_devices([ZwaveThermostat(value)])


class ZwaveThermostat(Entity):
    """ Represents a Z-Wave thermostat. """

    def __init__(self, setpoint_value):
        from openzwave.network import ZWaveNetwork
        from pydispatch import dispatcher

        self._value = setpoint_value
        self._node = setpoint_value.node

        dispatcher.connect(
            self.value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)

        # how to change setpoint
        #if setpoint_value.parent_id == 3 and setpoint_value.label == "Heating 1":
        #    setpoint_value.data = 69

    @property
    def should_poll(self):
        """ False because we will push our own state to HA when changed. """
        return False

    @property
    def unique_id(self):
        """ Returns a unique id. """
        return "ZWAVE-{}-{}".format(self._node.node_id, self._value.object_id)

    @property
    def name(self):
        """ Returns the name of the device. """
        name = self._node.name or "{} {}".format(
            self._node.manufacturer_name, self._node.product_name)

        return "{} {}".format(name, self._value.label)

    @property
    def state(self):
        """ Returns the state of the sensor. """
        return self._value.data

    @property
    def state_attributes(self):
        """ Returns the state attributes. """
        attrs = {
            zwave.ATTR_NODE_ID: self._node.node_id,
        }

        battery_level = self._node.get_battery_level()

        if battery_level is not None:
            attrs[ATTR_BATTERY_LEVEL] = battery_level

        location = self._node.location

        if location:
            attrs[ATTR_LOCATION] = location

        return attrs

    @property
    def unit_of_measurement(self):
        return self._value.units

    def value_changed(self, value):
        """ Called when a value has changed on the network. """
        if self._value.value_id == value.value_id:
            self.update_ha_state()
