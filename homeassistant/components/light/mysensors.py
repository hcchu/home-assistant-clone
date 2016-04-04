"""
Support for MySensors lights.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/light.mysensors/
"""
import logging

from homeassistant.components.light import (
    ATTR_BRIGHTNESS, ATTR_RGB_COLOR, Light)
from homeassistant.const import ATTR_BATTERY_LEVEL, STATE_OFF, STATE_ON
from homeassistant.loader import get_component
from homeassistant.util.color import rgb_hex_to_rgb_list

_LOGGER = logging.getLogger(__name__)
ATTR_RGB_WHITE = 'rgb_white'
ATTR_VALUE = 'value'
ATTR_VALUE_TYPE = 'value_type'


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the mysensors platform for sensors."""
    # Only act if loaded via mysensors by discovery event.
    # Otherwise gateway is not setup.
    if discovery_info is None:
        return

    mysensors = get_component('mysensors')

    for gateway in mysensors.GATEWAYS.values():
        # Define the S_TYPES and V_TYPES that the platform should handle as
        # states. Map them in a dict of lists.
        pres = gateway.const.Presentation
        set_req = gateway.const.SetReq
        map_sv_types = {
            pres.S_DIMMER: [set_req.V_DIMMER],
        }
        device_class_map = {
            pres.S_DIMMER: MySensorsLightDimmer,
        }
        if float(gateway.version) >= 1.5:
            # Add V_RGBW when rgb_white is implemented in the frontend
            map_sv_types.update({
                pres.S_RGB_LIGHT: [set_req.V_RGB],
            })
            map_sv_types[pres.S_DIMMER].append(set_req.V_PERCENTAGE)
            device_class_map.update({
                pres.S_RGB_LIGHT: MySensorsLightRGB,
            })
        devices = {}
        gateway.platform_callbacks.append(mysensors.pf_callback_factory(
            map_sv_types, devices, add_devices, device_class_map))


class MySensorsLight(Light):
    """Represent the value of a MySensors child node."""

    # pylint: disable=too-many-arguments,too-many-instance-attributes
    def __init__(
            self, gateway, node_id, child_id, name, value_type, child_type):
        """Setup instance attributes."""
        self.gateway = gateway
        self.node_id = node_id
        self.child_id = child_id
        self._name = name
        self.value_type = value_type
        self.battery_level = 0
        self._values = {}
        self._state = None
        self._brightness = None
        self._rgb = None
        self._white = None
        self.mysensors = get_component('mysensors')

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of this entity."""
        return self._name

    @property
    def brightness(self):
        """Return the brightness of this light between 0..255."""
        return self._brightness

    @property
    def rgb_color(self):
        """Return the RGB color value [int, int, int]."""
        return self._rgb

    @property
    def rgb_white(self):  # not implemented in the frontend yet
        """Return the white value in RGBW, value between 0..255."""
        return self._white

    @property
    def device_state_attributes(self):
        """Return device specific state attributes."""
        device_attr = {
            self.mysensors.ATTR_PORT: self.gateway.port,
            self.mysensors.ATTR_NODE_ID: self.node_id,
            self.mysensors.ATTR_CHILD_ID: self.child_id,
            ATTR_BATTERY_LEVEL: self.battery_level,
        }
        for value_type, value in self._values.items():
            device_attr[self.gateway.const.SetReq(value_type).name] = value
        return device_attr

    @property
    def available(self):
        """Return true if entity is available."""
        return self.value_type in self._values

    @property
    def assumed_state(self):
        """Return true if unable to access real state of entity."""
        return self.gateway.optimistic

    @property
    def is_on(self):
        """Return true if device is on."""
        return self._state

    def _turn_on_light(self):
        """Turn on light child device."""
        set_req = self.gateway.const.SetReq

        if not self._state and set_req.V_LIGHT in self._values:
            self.gateway.set_child_value(
                self.node_id, self.child_id, set_req.V_LIGHT, 1)

        if self.gateway.optimistic:
            # optimistically assume that light has changed state
            self._state = True
            self.update_ha_state()

    def _turn_on_dimmer(self, **kwargs):
        """Turn on dimmer child device."""
        set_req = self.gateway.const.SetReq
        brightness = self._brightness

        if ATTR_BRIGHTNESS in kwargs and \
                kwargs[ATTR_BRIGHTNESS] != self._brightness:
            brightness = kwargs[ATTR_BRIGHTNESS]
            percent = round(100 * brightness / 255)
            self.gateway.set_child_value(
                self.node_id, self.child_id, set_req.V_DIMMER, percent)

        if self.gateway.optimistic:
            # optimistically assume that light has changed state
            self._brightness = brightness
            self.update_ha_state()

    def _turn_on_rgb_and_w(self, hex_template, **kwargs):
        """Turn on RGB or RGBW child device."""
        rgb = self._rgb
        white = self._white

        if ATTR_RGB_WHITE in kwargs and \
                kwargs[ATTR_RGB_WHITE] != self._white:
            white = kwargs[ATTR_RGB_WHITE]

        if ATTR_RGB_COLOR in kwargs and \
                kwargs[ATTR_RGB_COLOR] != self._rgb:
            rgb = kwargs[ATTR_RGB_COLOR]
            if white is not None and hex_template == '%02x%02x%02x%02x':
                rgb.append(white)
            hex_color = hex_template % tuple(rgb)
            self.gateway.set_child_value(
                self.node_id, self.child_id, self.value_type, hex_color)

        if self.gateway.optimistic:
            # optimistically assume that light has changed state
            self._rgb = rgb
            self._white = white
            self.update_ha_state()

    def _turn_off_light(self, value_type=None, value=None):
        """Turn off light child device."""
        set_req = self.gateway.const.SetReq
        value_type = (
            set_req.V_LIGHT
            if set_req.V_LIGHT in self._values else value_type)
        value = 0 if set_req.V_LIGHT in self._values else value
        return {ATTR_VALUE_TYPE: value_type, ATTR_VALUE: value}

    def _turn_off_dimmer(self, value_type=None, value=None):
        """Turn off dimmer child device."""
        set_req = self.gateway.const.SetReq
        value_type = (
            set_req.V_DIMMER
            if set_req.V_DIMMER in self._values else value_type)
        value = 0 if set_req.V_DIMMER in self._values else value
        return {ATTR_VALUE_TYPE: value_type, ATTR_VALUE: value}

    def _turn_off_rgb_or_w(self, value_type=None, value=None):
        """Turn off RGB or RGBW child device."""
        if float(self.gateway.version) >= 1.5:
            set_req = self.gateway.const.SetReq
            if self.value_type == set_req.V_RGB:
                value = '000000'
            elif self.value_type == set_req.V_RGBW:
                value = '00000000'
        return {ATTR_VALUE_TYPE: self.value_type, ATTR_VALUE: value}

    def _turn_off_main(self, value_type=None, value=None):
        """Turn the device off."""
        if value_type is None or value is None:
            _LOGGER.warning(
                '%s: value_type %s, value = %s, '
                'None is not valid argument when setting child value'
                '', self._name, value_type, value)
            return
        self.gateway.set_child_value(
            self.node_id, self.child_id, value_type, value)
        if self.gateway.optimistic:
            # optimistically assume that light has changed state
            self._state = False
            self.update_ha_state()

    def _update_light(self):
        """Update the controller with values from light child."""
        value_type = self.gateway.const.SetReq.V_LIGHT
        if value_type in self._values:
            self._values[value_type] = (
                STATE_ON if int(self._values[value_type]) == 1 else STATE_OFF)
            self._state = self._values[value_type] == STATE_ON

    def _update_dimmer(self):
        """Update the controller with values from dimmer child."""
        set_req = self.gateway.const.SetReq
        value_type = set_req.V_DIMMER
        if value_type in self._values:
            self._brightness = round(255 * int(self._values[value_type]) / 100)
            if self._brightness == 0:
                self._state = False
            if set_req.V_LIGHT not in self._values:
                self._state = self._brightness > 0

    def _update_rgb_or_w(self):
        """Update the controller with values from RGB or RGBW child."""
        set_req = self.gateway.const.SetReq
        value = self._values[self.value_type]
        color_list = rgb_hex_to_rgb_list(value)
        if set_req.V_LIGHT not in self._values and \
                set_req.V_DIMMER not in self._values:
            self._state = max(color_list) > 0
        if len(color_list) > 3:
            self._white = color_list.pop()
        self._rgb = color_list

    def _update_main(self):
        """Update the controller with the latest value from a sensor."""
        node = self.gateway.sensors[self.node_id]
        child = node.children[self.child_id]
        self.battery_level = node.battery_level
        for value_type, value in child.values.items():
            _LOGGER.debug(
                '%s: value_type %s, value = %s', self._name, value_type, value)
            self._values[value_type] = value


class MySensorsLightDimmer(MySensorsLight):
    """Dimmer child class to MySensorsLight."""

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._turn_on_light()
        self._turn_on_dimmer(**kwargs)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        ret = self._turn_off_dimmer()
        ret = self._turn_off_light(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])
        self._turn_off_main(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])

    def update(self):
        """Update the controller with the latest value from a sensor."""
        self._update_main()
        self._update_light()
        self._update_dimmer()


class MySensorsLightRGB(MySensorsLight):
    """RGB child class to MySensorsLight."""

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._turn_on_light()
        self._turn_on_dimmer(**kwargs)
        self._turn_on_rgb_and_w('%02x%02x%02x', **kwargs)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        ret = self._turn_off_rgb_or_w()
        ret = self._turn_off_dimmer(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])
        ret = self._turn_off_light(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])
        self._turn_off_main(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])

    def update(self):
        """Update the controller with the latest value from a sensor."""
        self._update_main()
        self._update_light()
        self._update_dimmer()
        self._update_rgb_or_w()


class MySensorsLightRGBW(MySensorsLight):
    """RGBW child class to MySensorsLight."""

    def turn_on(self, **kwargs):
        """Turn the device on."""
        self._turn_on_light()
        self._turn_on_dimmer(**kwargs)
        self._turn_on_rgb_and_w('%02x%02x%02x%02x', **kwargs)

    def turn_off(self, **kwargs):
        """Turn the device off."""
        ret = self._turn_off_rgb_or_w()
        ret = self._turn_off_dimmer(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])
        ret = self._turn_off_light(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])
        self._turn_off_main(
            value_type=ret[ATTR_VALUE_TYPE], value=ret[ATTR_VALUE])

    def update(self):
        """Update the controller with the latest value from a sensor."""
        self._update_main()
        self._update_light()
        self._update_dimmer()
        self._update_rgb_or_w()
