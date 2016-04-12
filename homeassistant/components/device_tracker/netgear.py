"""
Support for Netgear routers.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/device_tracker.netgear/
"""
import logging
import threading
from datetime import timedelta

from homeassistant.components.device_tracker import DOMAIN
from homeassistant.const import CONF_HOST, CONF_PASSWORD, CONF_USERNAME, \
 CONF_PORT
from homeassistant.util import Throttle

# Return cached results if last scan was less then this time ago.
MIN_TIME_BETWEEN_SCANS = timedelta(seconds=5)

_LOGGER = logging.getLogger(__name__)
REQUIREMENTS = ['pynetgear==0.3.3']


def get_scanner(hass, config):
    """Validate the configuration and returns a Netgear scanner."""
    info = config[DOMAIN]
    host = info.get(CONF_HOST)
    username = info.get(CONF_USERNAME)
    password = info.get(CONF_PASSWORD)
    port = info.get(CONF_PORT)

    if password is not None and host is None:
        _LOGGER.warning('Found username or password but no host')
        return None

    scanner = NetgearDeviceScanner(host, username, password, port)

    return scanner if scanner.success_init else None


class NetgearDeviceScanner(object):
    """Queries a Netgear wireless router using the SOAP-API."""

    def __init__(self, host, username, password, port):
        """Initialize the scanner."""
        import pynetgear

        self.last_results = []
        self.lock = threading.Lock()

        if host is None:
            self._api = pynetgear.Netgear()
        elif username is None:
            self._api = pynetgear.Netgear(password, host)
        elif port is None:
            self._api = pynetgear.Netgear(password, host, username)
        else:
            self._api = pynetgear.Netgear(password, host, username, port)

        _LOGGER.info("Logging in")

        results = self._api.get_attached_devices()

        self.success_init = results is not None

        if self.success_init:
            self.last_results = results
        else:
            _LOGGER.error("Failed to Login")

    def scan_devices(self):
        """Scan for new devices and return a list with found device IDs."""
        self._update_info()

        return (device.mac for device in self.last_results)

    def get_device_name(self, mac):
        """Return the name of the given device or None if we don't know."""
        try:
            return next(device.name for device in self.last_results
                        if device.mac == mac)
        except StopIteration:
            return None

    @Throttle(MIN_TIME_BETWEEN_SCANS)
    def _update_info(self):
        """Retrieve latest information from the Netgear router.

        Returns boolean if scanning successful.
        """
        if not self.success_init:
            return

        with self.lock:
            _LOGGER.info("Scanning")

            results = self._api.get_attached_devices()

            if results is None:
                _LOGGER.warning('Error scanning devices')

            self.last_results = results or []
