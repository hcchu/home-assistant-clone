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

    value.set_change_verified(False)

    if value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_OPERATING_STATE:
        add_devices([ZwaveThermostat(value)])
    #elif value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_MODE:
    #    thermostat_group[node.node_id][value.command_class] = value
    #elif value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_SETPOINT:
    #    thermostat_group[node.node_id][value.command_class] = value



    # if 1 in groups and (zwave.NETWORK.controller.node_id not in
    #                     groups[1].associations):
    #     node.groups[1].add_association(zwave.NETWORK.controller.node_id)




class ZwaveThermostat(ThermostatDevice):
    """ Represents a Z-Wave thermostat. """

    def __init__(self, value):
        from openzwave.network import ZWaveNetwork
        from pydispatch import dispatcher
        import homeassistant.components.zwave as zwave
        from time import sleep

        mode_value = None
        setpoints = {}
        sleep(5)
        for n in zwave.NETWORK.nodes:
            if n == value.node.node_id: # this is a thermostat
                zwave.NETWORK.nodes[n].refresh_info()
                print(zwave.NETWORK.nodes[n].get_values_for_command_class(64))
                for k, v in zwave.NETWORK.nodes[n].values.items():
                    if v.command_class == zwave.COMMAND_CLASS_THERMOSTAT_SETPOINT:
                        setpoints[v.label] = v
                    elif v.command_class == zwave.COMMAND_CLASS_SENSOR_MULTILEVEL:
                        sensor_value = v
                    elif v.command_class == zwave.COMMAND_CLASS_THERMOSTAT_MODE:
                        mode_value = v

        #for setpoint in setpoints:
        #    print(setpoint.label, setpoint.data)

    #    print("--------  {0}  -----------".format(setpoint_value))
        self._value = value
        self._node = value.node
        self._sensor = sensor_value
        if mode_value:
            self._mode = mode_value
        else:
            self._mode = "UNKNOWN"
        self._setpoints = setpoints

        dispatcher.connect(
            self.value_changed, ZWaveNetwork.SIGNAL_VALUE_CHANGED)

        # how to change setpoint
        #if setpoint_value.parent_id == 3 and setpoint_value.label == "Heating 1":
        #    setpoint_value.data = 69

    @property
    def should_poll(self):
        """ False because we will push our own state to HA when changed. """
        return True

    @property
    def unique_id(self):
        """ Returns a unique id. """
        return "ZWAVE-{}-{}".format(self._node.node_id, self._value.object_id)

    @property
    def name(self):
        """ Returns the name of the device. """
        name = self._node.name or "{} {}".format(
            self._node.manufacturer_name, self._node.product_name)

        #return "{} {}".format(name, self._value.label)
        return "{}".format(name)

    @property
    def operation(self):
        return self._value.data

    @property
    def current_temperature(self):
        return int(self._sensor.data)

    @property
    def target_temperature(self):
        if abs(self._sensor.data - self._setpoints["Heating 1"].data) < abs(self._sensor.data - self._setpoints["Cooling 1"].data):
            return self._setpoints["Heating 1"].data
        else:
            return self._setpoints["Cooling 1"].data

    @property
    def state(self):
        """ Returns the state of the sensor. """
        return int(self._sensor.data)

    def set_temperature(self, temperature):
        if self._mode.data == "Heat":
            self._setpoints["Heating 1"].data = int(temperature)
        elif self._mode.data == "Cool":
            self._setpoints["Cooling 1"].data = int(temperature)
        else: # take best guess whether to heat or cool
            if temperature < self._setpoints["Heating 1"].data and temperature < self._setpoints["Cooling 1"].data:
                self._setpoints["Heating 1"].data = int(temperature)
            elif temperature > self._setpoints["Heating 1"].data and temperature < self._setpoints["Cooling 1"].data: 
                self._setpoints["Heating 1"].data = int(temperature)
            elif temperature > self._setpoints["Cooling 1"].data and temperature > self._setpoints["Cooling 1"].data: 
                self._setpoints["Cooling 1"].data = int(temperature)

    @property
    def device_state_attributes(self):
        if self._mode.data:
            mode = self._mode.data
        else:
            mode = "Unknown"
        return {
                "mode": mode,
                "node_id": self._node.node_id
                }


    @property
    def unit_of_measurement(self):
        return TEMP_FAHRENHEIT

    def value_changed(self, value):
        """ Called when a value has changed on the network. """
        if value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_SETPOINT:
            self._setpoints[value.label] = value
        elif value.command_class == zwave.COMMAND_CLASS_SENSOR_MULTILEVEL:
            self._sensor = value
            self._current_temperature = value.data
        elif value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_MODE:
            self._mode = value

    def update(self):
        import homeassistant.components.zwave as zwave

        zwave.NETWORK.nodes[self._node.node_id].refresh_info()
        for k, value in zwave.NETWORK.nodes[self._node.node_id].values.items():
            if value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_SETPOINT:
                self._setpoints[value.label] = value
            elif value.command_class == zwave.COMMAND_CLASS_SENSOR_MULTILEVEL:
                self._sensor = value
                self._current_temperature = value.data
            elif value.command_class == zwave.COMMAND_CLASS_THERMOSTAT_MODE:
                self._mode = value


