"""
Starts a service to scan in intervals for new devices.

Will emit EVENT_PLATFORM_DISCOVERED whenever a new service has been discovered.

Knows which components handle certain types, will make sure they are
loaded before the EVENT_PLATFORM_DISCOVERED is fired.
"""
import logging
import threading

from homeassistant import bootstrap
from homeassistant.const import (
    ATTR_DISCOVERED, ATTR_SERVICE, EVENT_HOMEASSISTANT_START,
    EVENT_PLATFORM_DISCOVERED)

DOMAIN = "discovery"
REQUIREMENTS = ['netdisco==0.6.4']

SCAN_INTERVAL = 300  # seconds

SERVICE_WEMO = 'belkin_wemo'
SERVICE_HUE = 'philips_hue'
SERVICE_CAST = 'google_cast'
SERVICE_NETGEAR = 'netgear_router'
SERVICE_SONOS = 'sonos'
SERVICE_PLEX = 'plex_mediaserver'
SERVICE_SQUEEZEBOX = 'logitech_mediaserver'
SERVICE_PANASONIC_VIERA = 'panasonic_viera'

SERVICE_HANDLERS = {
    SERVICE_WEMO: "wemo",
    SERVICE_CAST: "media_player",
    SERVICE_HUE: "light",
    SERVICE_NETGEAR: 'device_tracker',
    SERVICE_SONOS: 'media_player',
    SERVICE_PLEX: 'media_player',
    SERVICE_SQUEEZEBOX: 'media_player',
    SERVICE_PANASONIC_VIERA: 'media_player',
}


def listen(hass, service, callback):
    """Setup listener for discovery of specific service.

    Service can be a string or a list/tuple.
    """
    if isinstance(service, str):
        service = (service,)
    else:
        service = tuple(service)

    def discovery_event_listener(event):
        """Listen for discovery events."""
        if event.data[ATTR_SERVICE] in service:
            callback(event.data[ATTR_SERVICE], event.data.get(ATTR_DISCOVERED))

    hass.bus.listen(EVENT_PLATFORM_DISCOVERED, discovery_event_listener)


def discover(hass, service, discovered=None, component=None, hass_config=None):
    """Fire discovery event. Can ensure a component is loaded."""
    if component is not None:
        bootstrap.setup_component(hass, component, hass_config)

    data = {
        ATTR_SERVICE: service
    }

    if discovered is not None:
        data[ATTR_DISCOVERED] = discovered

    hass.bus.fire(EVENT_PLATFORM_DISCOVERED, data)


def setup(hass, config):
    """Start a discovery service."""
    logger = logging.getLogger(__name__)

    from netdisco.service import DiscoveryService

    # Disable zeroconf logging, it spams
    logging.getLogger('zeroconf').setLevel(logging.CRITICAL)

    lock = threading.Lock()

    def new_service_listener(service, info):
        """Called when a new service is found."""
        with lock:
            logger.info("Found new service: %s %s", service, info)

            component = SERVICE_HANDLERS.get(service)

            # We do not know how to handle this service.
            if not component:
                return

            # This component cannot be setup.
            if not bootstrap.setup_component(hass, component, config):
                return

            hass.bus.fire(EVENT_PLATFORM_DISCOVERED, {
                ATTR_SERVICE: service,
                ATTR_DISCOVERED: info
            })

    # pylint: disable=unused-argument
    def start_discovery(event):
        """Start discovering."""
        netdisco = DiscoveryService(SCAN_INTERVAL)
        netdisco.add_listener(new_service_listener)
        netdisco.start()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_START, start_discovery)

    return True
