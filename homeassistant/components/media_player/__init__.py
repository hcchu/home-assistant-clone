"""
homeassistant.components.media_player
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Component to interface with various media players.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/media_player/
"""
import logging
import os

from homeassistant.components import discovery
from homeassistant.config import load_yaml_config_file
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.const import (
    STATE_OFF, STATE_UNKNOWN, STATE_PLAYING, STATE_IDLE,
    ATTR_ENTITY_ID, ATTR_ENTITY_PICTURE, SERVICE_TURN_OFF, SERVICE_TURN_ON,
    SERVICE_VOLUME_UP, SERVICE_VOLUME_DOWN, SERVICE_VOLUME_SET,
    SERVICE_VOLUME_MUTE, SERVICE_TOGGLE,
    SERVICE_MEDIA_PLAY_PAUSE, SERVICE_MEDIA_PLAY, SERVICE_MEDIA_PAUSE,
    SERVICE_MEDIA_NEXT_TRACK, SERVICE_MEDIA_PREVIOUS_TRACK, SERVICE_MEDIA_SEEK)

DOMAIN = 'media_player'
SCAN_INTERVAL = 10

ENTITY_ID_FORMAT = DOMAIN + '.{}'

DISCOVERY_PLATFORMS = {
    discovery.SERVICE_CAST: 'cast',
    discovery.SERVICE_SONOS: 'sonos',
    discovery.SERVICE_PLEX: 'plex',
}

SERVICE_PLAY_MEDIA = 'play_media'

ATTR_MEDIA_VOLUME_LEVEL = 'volume_level'
ATTR_MEDIA_VOLUME_MUTED = 'is_volume_muted'
ATTR_MEDIA_SEEK_POSITION = 'seek_position'
ATTR_MEDIA_CONTENT_ID = 'media_content_id'
ATTR_MEDIA_CONTENT_TYPE = 'media_content_type'
ATTR_MEDIA_DURATION = 'media_duration'
ATTR_MEDIA_TITLE = 'media_title'
ATTR_MEDIA_ARTIST = 'media_artist'
ATTR_MEDIA_ALBUM_NAME = 'media_album_name'
ATTR_MEDIA_ALBUM_ARTIST = 'media_album_artist'
ATTR_MEDIA_TRACK = 'media_track'
ATTR_MEDIA_SERIES_TITLE = 'media_series_title'
ATTR_MEDIA_SEASON = 'media_season'
ATTR_MEDIA_EPISODE = 'media_episode'
ATTR_MEDIA_CHANNEL = 'media_channel'
ATTR_MEDIA_PLAYLIST = 'media_playlist'
ATTR_APP_ID = 'app_id'
ATTR_APP_NAME = 'app_name'
ATTR_SUPPORTED_MEDIA_COMMANDS = 'supported_media_commands'

MEDIA_TYPE_MUSIC = 'music'
MEDIA_TYPE_TVSHOW = 'tvshow'
MEDIA_TYPE_VIDEO = 'movie'
MEDIA_TYPE_EPISODE = 'episode'
MEDIA_TYPE_CHANNEL = 'channel'
MEDIA_TYPE_PLAYLIST = 'playlist'

SUPPORT_PAUSE = 1
SUPPORT_SEEK = 2
SUPPORT_VOLUME_SET = 4
SUPPORT_VOLUME_MUTE = 8
SUPPORT_PREVIOUS_TRACK = 16
SUPPORT_NEXT_TRACK = 32

SUPPORT_TURN_ON = 128
SUPPORT_TURN_OFF = 256
SUPPORT_PLAY_MEDIA = 512
SUPPORT_VOLUME_STEP = 1024

SERVICE_TO_METHOD = {
    SERVICE_TURN_ON: 'turn_on',
    SERVICE_TURN_OFF: 'turn_off',
    SERVICE_TOGGLE: 'toggle',
    SERVICE_VOLUME_UP: 'volume_up',
    SERVICE_VOLUME_DOWN: 'volume_down',
    SERVICE_MEDIA_PLAY_PAUSE: 'media_play_pause',
    SERVICE_MEDIA_PLAY: 'media_play',
    SERVICE_MEDIA_PAUSE: 'media_pause',
    SERVICE_MEDIA_NEXT_TRACK: 'media_next_track',
    SERVICE_MEDIA_PREVIOUS_TRACK: 'media_previous_track',
    SERVICE_PLAY_MEDIA: 'play_media',
}

ATTR_TO_PROPERTY = [
    ATTR_MEDIA_VOLUME_LEVEL,
    ATTR_MEDIA_VOLUME_MUTED,
    ATTR_MEDIA_CONTENT_ID,
    ATTR_MEDIA_CONTENT_TYPE,
    ATTR_MEDIA_DURATION,
    ATTR_MEDIA_TITLE,
    ATTR_MEDIA_ARTIST,
    ATTR_MEDIA_ALBUM_NAME,
    ATTR_MEDIA_ALBUM_ARTIST,
    ATTR_MEDIA_TRACK,
    ATTR_MEDIA_SERIES_TITLE,
    ATTR_MEDIA_SEASON,
    ATTR_MEDIA_EPISODE,
    ATTR_MEDIA_CHANNEL,
    ATTR_MEDIA_PLAYLIST,
    ATTR_APP_ID,
    ATTR_APP_NAME,
    ATTR_SUPPORTED_MEDIA_COMMANDS,
]


def is_on(hass, entity_id=None):
    """ Returns true if specified media player entity_id is on.
    Will check all media player if no entity_id specified. """
    entity_ids = [entity_id] if entity_id else hass.states.entity_ids(DOMAIN)
    return any(not hass.states.is_state(entity_id, STATE_OFF)
               for entity_id in entity_ids)


def turn_on(hass, entity_id=None):
    """ Will turn on specified media player or all. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_TURN_ON, data)


def turn_off(hass, entity_id=None):
    """ Will turn off specified media player or all. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_TURN_OFF, data)


def toggle(hass, entity_id=None):
    """ Will toggle specified media player or all. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_TOGGLE, data)


def volume_up(hass, entity_id=None):
    """ Send the media player the command for volume up. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_VOLUME_UP, data)


def volume_down(hass, entity_id=None):
    """ Send the media player the command for volume down. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_VOLUME_DOWN, data)


def mute_volume(hass, mute, entity_id=None):
    """ Send the media player the command for volume down. """
    data = {ATTR_MEDIA_VOLUME_MUTED: mute}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_VOLUME_MUTE, data)


def set_volume_level(hass, volume, entity_id=None):
    """ Send the media player the command for volume down. """
    data = {ATTR_MEDIA_VOLUME_LEVEL: volume}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_VOLUME_SET, data)


def media_play_pause(hass, entity_id=None):
    """ Send the media player the command for play/pause. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_MEDIA_PLAY_PAUSE, data)


def media_play(hass, entity_id=None):
    """ Send the media player the command for play/pause. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_MEDIA_PLAY, data)


def media_pause(hass, entity_id=None):
    """ Send the media player the command for play/pause. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_MEDIA_PAUSE, data)


def media_next_track(hass, entity_id=None):
    """ Send the media player the command for next track. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_MEDIA_NEXT_TRACK, data)


def media_previous_track(hass, entity_id=None):
    """ Send the media player the command for prev track. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    hass.services.call(DOMAIN, SERVICE_MEDIA_PREVIOUS_TRACK, data)


def media_seek(hass, position, entity_id=None):
    """ Send the media player the command to seek in current playing media. """
    data = {ATTR_ENTITY_ID: entity_id} if entity_id else {}
    data[ATTR_MEDIA_SEEK_POSITION] = position
    hass.services.call(DOMAIN, SERVICE_MEDIA_SEEK, data)


def play_media(hass, media_type, media_id, entity_id=None):
    """ Send the media player the command for playing media. """
    data = {"media_type": media_type, "media_id": media_id}

    if entity_id:
        data[ATTR_ENTITY_ID] = entity_id

    hass.services.call(DOMAIN, SERVICE_PLAY_MEDIA, data)


def setup(hass, config):
    """ Track states and offer events for media_players. """
    component = EntityComponent(
        logging.getLogger(__name__), DOMAIN, hass, SCAN_INTERVAL,
        DISCOVERY_PLATFORMS)

    component.setup(config)

    descriptions = load_yaml_config_file(
        os.path.join(os.path.dirname(__file__), 'services.yaml'))

    def media_player_service_handler(service):
        """ Maps services to methods on MediaPlayerDevice. """
        target_players = component.extract_from_service(service)

        method = SERVICE_TO_METHOD[service.service]

        for player in target_players:
            getattr(player, method)()

            if player.should_poll:
                player.update_ha_state(True)

    for service in SERVICE_TO_METHOD:
        hass.services.register(DOMAIN, service, media_player_service_handler,
                               descriptions.get(service))

    def volume_set_service(service):
        """ Set specified volume on the media player. """
        target_players = component.extract_from_service(service)

        if ATTR_MEDIA_VOLUME_LEVEL not in service.data:
            return

        volume = service.data[ATTR_MEDIA_VOLUME_LEVEL]

        for player in target_players:
            player.set_volume_level(volume)

            if player.should_poll:
                player.update_ha_state(True)

    hass.services.register(DOMAIN, SERVICE_VOLUME_SET, volume_set_service,
                           descriptions.get(SERVICE_VOLUME_SET))

    def volume_mute_service(service):
        """ Mute (true) or unmute (false) the media player. """
        target_players = component.extract_from_service(service)

        if ATTR_MEDIA_VOLUME_MUTED not in service.data:
            return

        mute = service.data[ATTR_MEDIA_VOLUME_MUTED]

        for player in target_players:
            player.mute_volume(mute)

            if player.should_poll:
                player.update_ha_state(True)

    hass.services.register(DOMAIN, SERVICE_VOLUME_MUTE, volume_mute_service,
                           descriptions.get(SERVICE_VOLUME_MUTE))

    def media_seek_service(service):
        """ Seek to a position. """
        target_players = component.extract_from_service(service)

        if ATTR_MEDIA_SEEK_POSITION not in service.data:
            return

        position = service.data[ATTR_MEDIA_SEEK_POSITION]

        for player in target_players:
            player.media_seek(position)

            if player.should_poll:
                player.update_ha_state(True)

    hass.services.register(DOMAIN, SERVICE_MEDIA_SEEK, media_seek_service,
                           descriptions.get(SERVICE_MEDIA_SEEK))

    def play_media_service(service):
        """ Plays specified media_id on the media player. """
        media_type = service.data.get('media_type')
        media_id = service.data.get('media_id')

        if media_type is None:
            return

        if media_id is None:
            return

        for player in component.extract_from_service(service):
            player.play_media(media_type, media_id)

            if player.should_poll:
                player.update_ha_state(True)

    hass.services.register(
        DOMAIN, SERVICE_PLAY_MEDIA, play_media_service,
        descriptions.get(SERVICE_PLAY_MEDIA))

    return True


class MediaPlayerDevice(Entity):
    """ ABC for media player devices. """
    # pylint: disable=too-many-public-methods,no-self-use

    # Implement these for your media player

    @property
    def state(self):
        """ State of the player. """
        return STATE_UNKNOWN

    @property
    def volume_level(self):
        """ Volume level of the media player (0..1). """
        return None

    @property
    def is_volume_muted(self):
        """ Boolean if volume is currently muted. """
        return None

    @property
    def media_content_id(self):
        """ Content ID of current playing media. """
        return None

    @property
    def media_content_type(self):
        """ Content type of current playing media. """
        return None

    @property
    def media_duration(self):
        """ Duration of current playing media in seconds. """
        return None

    @property
    def media_image_url(self):
        """ Image url of current playing media. """
        return None

    @property
    def media_title(self):
        """ Title of current playing media. """
        return None

    @property
    def media_artist(self):
        """ Artist of current playing media. (Music track only) """
        return None

    @property
    def media_album_name(self):
        """ Album name of current playing media. (Music track only) """
        return None

    @property
    def media_album_artist(self):
        """ Album arist of current playing media. (Music track only) """
        return None

    @property
    def media_track(self):
        """ Track number of current playing media. (Music track only) """
        return None

    @property
    def media_series_title(self):
        """ Series title of current playing media. (TV Show only)"""
        return None

    @property
    def media_season(self):
        """ Season of current playing media. (TV Show only) """
        return None

    @property
    def media_episode(self):
        """ Episode of current playing media. (TV Show only) """
        return None

    @property
    def media_channel(self):
        """ Channel currently playing. """
        return None

    @property
    def media_playlist(self):
        """ Title of Playlist currently playing. """
        return None

    @property
    def app_id(self):
        """  ID of the current running app. """
        return None

    @property
    def app_name(self):
        """  Name of the current running app. """
        return None

    @property
    def supported_media_commands(self):
        """ Flags of media commands that are supported. """
        return 0

    def turn_on(self):
        """ turn the media player on. """
        raise NotImplementedError()

    def turn_off(self):
        """ turn the media player off. """
        raise NotImplementedError()

    def mute_volume(self, mute):
        """ mute the volume. """
        raise NotImplementedError()

    def set_volume_level(self, volume):
        """ set volume level, range 0..1. """
        raise NotImplementedError()

    def media_play(self):
        """ Send play commmand. """
        raise NotImplementedError()

    def media_pause(self):
        """ Send pause command. """
        raise NotImplementedError()

    def media_previous_track(self):
        """ Send previous track command. """
        raise NotImplementedError()

    def media_next_track(self):
        """ Send next track command. """
        raise NotImplementedError()

    def media_seek(self, position):
        """ Send seek command. """
        raise NotImplementedError()

    def play_media(self, media_type, media_id):
        """ Plays a piece of media. """
        raise NotImplementedError()

    # No need to overwrite these.
    @property
    def support_pause(self):
        """ Boolean if pause is supported. """
        return bool(self.supported_media_commands & SUPPORT_PAUSE)

    @property
    def support_seek(self):
        """ Boolean if seek is supported. """
        return bool(self.supported_media_commands & SUPPORT_SEEK)

    @property
    def support_volume_set(self):
        """ Boolean if setting volume is supported. """
        return bool(self.supported_media_commands & SUPPORT_VOLUME_SET)

    @property
    def support_volume_mute(self):
        """ Boolean if muting volume is supported. """
        return bool(self.supported_media_commands & SUPPORT_VOLUME_MUTE)

    @property
    def support_previous_track(self):
        """ Boolean if previous track command supported. """
        return bool(self.supported_media_commands & SUPPORT_PREVIOUS_TRACK)

    @property
    def support_next_track(self):
        """ Boolean if next track command supported. """
        return bool(self.supported_media_commands & SUPPORT_NEXT_TRACK)

    @property
    def support_play_media(self):
        """ Boolean if play media command supported. """
        return bool(self.supported_media_commands & SUPPORT_PLAY_MEDIA)

    def toggle(self):
        """ Toggles the power on the media player. """
        if self.state in [STATE_OFF, STATE_IDLE]:
            self.turn_on()
        else:
            self.turn_off()

    def volume_up(self):
        """ volume_up media player. """
        if self.volume_level < 1:
            self.set_volume_level(min(1, self.volume_level + .1))

    def volume_down(self):
        """ volume_down media player. """
        if self.volume_level > 0:
            self.set_volume_level(max(0, self.volume_level - .1))

    def media_play_pause(self):
        """ media_play_pause media player. """
        if self.state == STATE_PLAYING:
            self.media_pause()
        else:
            self.media_play()

    @property
    def state_attributes(self):
        """ Return the state attributes. """
        if self.state == STATE_OFF:
            state_attr = {
                ATTR_SUPPORTED_MEDIA_COMMANDS: self.supported_media_commands,
            }
        else:
            state_attr = {
                attr: getattr(self, attr) for attr
                in ATTR_TO_PROPERTY if getattr(self, attr) is not None
            }

            if self.media_image_url:
                state_attr[ATTR_ENTITY_PICTURE] = self.media_image_url

        return state_attr
