"""
Support to interface with Sonos players (via SoCo).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/media_player.sonos/
"""
import datetime
import logging

from homeassistant.components.media_player import (
    MEDIA_TYPE_MUSIC, SUPPORT_NEXT_TRACK, SUPPORT_PAUSE,
    SUPPORT_PLAY_MEDIA, SUPPORT_PREVIOUS_TRACK, SUPPORT_SEEK,
    SUPPORT_VOLUME_MUTE, SUPPORT_VOLUME_SET,
    MediaPlayerDevice)
from homeassistant.const import (
    STATE_IDLE, STATE_PAUSED, STATE_PLAYING, STATE_UNKNOWN)

REQUIREMENTS = ['SoCo==0.11.1']

_LOGGER = logging.getLogger(__name__)

# The soco library is excessively chatty when it comes to logging and
# causes a LOT of spam in the logs due to making a http connection to each
# speaker every 10 seconds. Quiet it down a bit to just actual problems.
_SOCO_LOGGER = logging.getLogger('soco')
_SOCO_LOGGER.setLevel(logging.ERROR)
_REQUESTS_LOGGER = logging.getLogger('requests')
_REQUESTS_LOGGER.setLevel(logging.ERROR)

SUPPORT_SONOS = SUPPORT_PAUSE | SUPPORT_VOLUME_SET | SUPPORT_VOLUME_MUTE |\
    SUPPORT_PREVIOUS_TRACK | SUPPORT_NEXT_TRACK | SUPPORT_PLAY_MEDIA |\
    SUPPORT_SEEK


# pylint: disable=unused-argument
def setup_platform(hass, config, add_devices, discovery_info=None):
    """Setup the Sonos platform."""
    import soco
    import socket

    if discovery_info:
        add_devices([SonosDevice(hass, soco.SoCo(discovery_info))])
        return True

    players = None
    hosts = config.get('hosts', None)
    if hosts:
        # Support retro compatibility with comma separated list of hosts
        # from config
        hosts = hosts.split(',') if isinstance(hosts, str) else hosts
        players = []
        for host in hosts:
            players.append(soco.SoCo(socket.gethostbyname(host)))

    if not players:
        players = soco.discover(interface_addr=config.get('interface_addr',
                                                          None))

    if not players:
        _LOGGER.warning('No Sonos speakers found.')
        return False

    add_devices(SonosDevice(hass, p) for p in players)
    _LOGGER.info('Added %s Sonos speakers', len(players))

    return True


def only_if_coordinator(func):
    """Decorator for coordinator.

    If used as decorator, avoid calling the decorated method if player is not
    a coordinator. If not, a grouped speaker (not in coordinator role) will
    throw soco.exceptions.SoCoSlaveException
    """
    def wrapper(*args, **kwargs):
        """Decorator wrapper."""
        if args[0].is_coordinator:
            return func(*args, **kwargs)
        else:
            _LOGGER.debug('Ignore command "%s" for Sonos device "%s" '
                          '(not coordinator)',
                          func.__name__, args[0].name)

    return wrapper


# pylint: disable=too-many-instance-attributes, too-many-public-methods
# pylint: disable=abstract-method
class SonosDevice(MediaPlayerDevice):
    """Representation of a Sonos device."""

    # pylint: disable=too-many-arguments
    def __init__(self, hass, player):
        """Initialize the Sonos device."""
        self.hass = hass
        self.volume_increment = 5
        super(SonosDevice, self).__init__()
        self._player = player
        self.update()

    @property
    def should_poll(self):
        """No polling needed."""
        return True

    def update_sonos(self, now):
        """Update state, called by track_utc_time_change."""
        self.update_ha_state(True)

    @property
    def name(self):
        """Return the name of the device."""
        return self._name

    @property
    def unique_id(self):
        """Return a unique ID."""
        return "{}.{}".format(self.__class__, self._player.uid)

    @property
    def state(self):
        """Return the state of the device."""
        if self._status == 'PAUSED_PLAYBACK':
            return STATE_PAUSED
        if self._status == 'PLAYING':
            return STATE_PLAYING
        if self._status == 'STOPPED':
            return STATE_IDLE
        return STATE_UNKNOWN

    @property
    def is_coordinator(self):
        """Return true if player is a coordinator."""
        return self._player.is_coordinator

    def update(self):
        """Retrieve latest state."""
        self._name = self._player.get_speaker_info()['zone_name'].replace(
            ' (R)', '').replace(' (L)', '')
        self._status = self._player.get_current_transport_info().get(
            'current_transport_state')
        self._trackinfo = self._player.get_current_track_info()

    @property
    def volume_level(self):
        """Volume level of the media player (0..1)."""
        return self._player.volume / 100.0

    @property
    def is_volume_muted(self):
        """Return true if volume is muted."""
        return self._player.mute

    @property
    def media_content_id(self):
        """Content ID of current playing media."""
        return self._trackinfo.get('title', None)

    @property
    def media_content_type(self):
        """Content type of current playing media."""
        return MEDIA_TYPE_MUSIC

    @property
    def media_duration(self):
        """Duration of current playing media in seconds."""
        dur = self._trackinfo.get('duration', '0:00')

        # If the speaker is playing from the "line-in" source, getting
        # track metadata can return NOT_IMPLEMENTED, which breaks the
        # volume logic below
        if dur == 'NOT_IMPLEMENTED':
            return None

        return sum(60 ** x[0] * int(x[1]) for x in
                   enumerate(reversed(dur.split(':'))))

    @property
    def media_image_url(self):
        """Image url of current playing media."""
        if 'album_art' in self._trackinfo:
            return self._trackinfo['album_art']

    @property
    def media_title(self):
        """Title of current playing media."""
        if 'artist' in self._trackinfo and 'title' in self._trackinfo:
            return '{artist} - {title}'.format(
                artist=self._trackinfo['artist'],
                title=self._trackinfo['title']
            )
        if 'title' in self._status:
            return self._trackinfo['title']

    @property
    def supported_media_commands(self):
        """Flag of media commands that are supported."""
        return SUPPORT_SONOS

    def volume_up(self):
        """Volume up media player."""
        self._player.volume += self.volume_increment

    def volume_down(self):
        """Volume down media player."""
        self._player.volume -= self.volume_increment

    def set_volume_level(self, volume):
        """Set volume level, range 0..1."""
        self._player.volume = str(int(volume * 100))

    def mute_volume(self, mute):
        """Mute (true) or unmute (false) media player."""
        self._player.mute = mute

    @only_if_coordinator
    def turn_off(self):
        """Turn off media player."""
        self._player.pause()

    @only_if_coordinator
    def media_play(self):
        """Send play command."""
        self._player.play()

    @only_if_coordinator
    def media_pause(self):
        """Send pause command."""
        self._player.pause()

    @only_if_coordinator
    def media_next_track(self):
        """Send next track command."""
        self._player.next()

    @only_if_coordinator
    def media_previous_track(self):
        """Send next track command."""
        self._player.previous()

    @only_if_coordinator
    def media_seek(self, position):
        """Send seek command."""
        self._player.seek(str(datetime.timedelta(seconds=int(position))))

    @only_if_coordinator
    def turn_on(self):
        """Turn the media player on."""
        self._player.play()

    @only_if_coordinator
    def play_media(self, media_type, media_id):
        """Send the play_media command to the media player."""
        self._player.play_uri(media_id)
