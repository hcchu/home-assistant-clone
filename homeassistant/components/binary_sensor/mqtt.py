"""
Support for MQTT binary sensors.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/binary_sensor.mqtt/
"""
import logging

import voluptuous as vol

import homeassistant.components.mqtt as mqtt
from homeassistant.components.binary_sensor import (BinarySensorDevice,
                                                    SENSOR_CLASSES)
from homeassistant.const import CONF_NAME, CONF_VALUE_TEMPLATE
from homeassistant.components.mqtt import CONF_STATE_TOPIC, CONF_QOS
from homeassistant.helpers import template
import homeassistant.helpers.config_validation as cv

_LOGGER = logging.getLogger(__name__)

DEPENDENCIES = ['mqtt']

CONF_SENSOR_CLASS = 'sensor_class'
CONF_PAYLOAD_ON = 'payload_on'
CONF_PAYLOAD_OFF = 'payload_off'

DEFAULT_NAME = 'MQTT Binary sensor'
DEFAULT_PAYLOAD_ON = 'ON'
DEFAULT_PAYLOAD_OFF = 'OFF'

PLATFORM_SCHEMA = mqtt.MQTT_RO_PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    vol.Optional(CONF_SENSOR_CLASS, default=None):
        vol.Any(vol.In(SENSOR_CLASSES), vol.SetTo(None)),
    vol.Optional(CONF_PAYLOAD_ON, default=DEFAULT_PAYLOAD_ON): cv.string,
    vol.Optional(CONF_PAYLOAD_OFF, default=DEFAULT_PAYLOAD_OFF): cv.string,
})


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Add MQTT binary sensor."""
    add_devices([MqttBinarySensor(
        hass,
        config[CONF_NAME],
        config[CONF_STATE_TOPIC],
        config[CONF_SENSOR_CLASS],
        config[CONF_QOS],
        config[CONF_PAYLOAD_ON],
        config[CONF_PAYLOAD_OFF],
        config.get(CONF_VALUE_TEMPLATE)
    )])


# pylint: disable=too-many-arguments, too-many-instance-attributes
class MqttBinarySensor(BinarySensorDevice):
    """Representation a binary sensor that is updated by MQTT."""

    def __init__(self, hass, name, state_topic, sensor_class, qos, payload_on,
                 payload_off, value_template):
        """Initialize the MQTT binary sensor."""
        self._hass = hass
        self._name = name
        self._state = False
        self._state_topic = state_topic
        self._sensor_class = sensor_class
        self._payload_on = payload_on
        self._payload_off = payload_off
        self._qos = qos

        def message_received(topic, payload, qos):
            """A new MQTT message has been received."""
            if value_template is not None:
                payload = template.render_with_possible_json_value(
                    hass, value_template, payload)
            if payload == self._payload_on:
                self._state = True
                self.update_ha_state()
            elif payload == self._payload_off:
                self._state = False
                self.update_ha_state()

        mqtt.subscribe(hass, self._state_topic, message_received, self._qos)

    @property
    def should_poll(self):
        """No polling needed."""
        return False

    @property
    def name(self):
        """Return the name of the binary sensor."""
        return self._name

    @property
    def is_on(self):
        """Return true if the binary sensor is on."""
        return self._state

    @property
    def sensor_class(self):
        """Return the class of this sensor."""
        return self._sensor_class
