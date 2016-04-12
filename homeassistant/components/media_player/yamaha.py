"""
Support for Yamaha Receivers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.yamaha/
"""
import logging

from homeassistant.components.media_player import (
    SUPPORT_TURN_OFF, SUPPORT_TURN_ON, SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    MediaPlayerDevice)
from homeassistant.const import STATE_OFF, STATE_ON
REQUIREMENTS = ['rxv==0.1.11']
_LOGGER = logging.getLogger(__name__)

SUPPORT_YAMAHA = SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE | \
    SUPPORT_TURN_ON | SUPPORT_TURN_OFF


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Yamaha platform."""
    import rxv
    add_devices(YamahaDevice(config.get("name"), receiver)
                for receiver in rxv.find())


class YamahaDevice(MediaPlayerDevice):
    """Representation of a Yamaha device."""

    # pylint: disable=too-many-public-methods, abstract-method
    def __init__(self, name, receiver):
        """Initialize the Yamaha Receiver."""
        self._receiver = receiver
        self._muted = False
        self._volume = 0
        self._pwstate = STATE_OFF
        self.update()
        self._name = name

    def update(self):
        """Get the latest details from the device."""
        if self._receiver.on:
            self._pwstate = STATE_ON
        else:
            self._pwstate = STATE_OFF
        self._muted = self._receiver.mute
        self._volume = (self._receiver.volume/100) + 1

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def state(self):
        """Return the state of the device."""
        return self._pwstate

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._volume

    @property
    def is_volume_muted(self):
        """Boolean if volume is currently muted."""
        return self._muted

    @property
    def supported_media_commands(self):
        """Flag of media commands that are supported."""
        return SUPPORT_YAMAHA

    def turn_off(self):
        """Turn off media player."""
        self._receiver.on = False

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        receiver_vol = 100-(volume * 100)
        negative_receiver_vol = -receiver_vol
        self._receiver.volume = negative_receiver_vol

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._receiver.mute = mute

    def turn_on(self):
        """Turn the media player on."""
        self._receiver.on = True
        self._volume = (self._receiver.volume/100) + 1
