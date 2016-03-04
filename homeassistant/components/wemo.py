"""
homeassistant.components.wemo
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
WeMo device discovery.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/wemo/
"""
import logging

from homeassistant.components import discovery
from homeassistant.const import EVENT_HOMEASSISTANT_STOP

REQUIREMENTS = ['pywemo==0.3.12']

DOMAIN = 'wemo'
DISCOVER_LIGHTS = 'wemo.light'
DISCOVER_MOTION = 'wemo.motion'
DISCOVER_SWITCHES = 'wemo.switch'

# mapping from Wemo model_name to service
WEMO_MODEL_DISPATCH = {
    'Bridge':  DISCOVER_LIGHTS,
    'Insight': DISCOVER_SWITCHES,
    'Maker':   DISCOVER_SWITCHES,
    'Motion':  DISCOVER_MOTION,
    'Socket':  DISCOVER_SWITCHES,
    'LightSwitch': DISCOVER_SWITCHES
}
WEMO_SERVICE_DISPATCH = {
    DISCOVER_LIGHTS: 'light',
    DISCOVER_MOTION: 'binary_sensor',
    DISCOVER_SWITCHES: 'switch',
}

SUBSCRIPTION_REGISTRY = None
KNOWN_DEVICES = []

_LOGGER = logging.getLogger(__name__)


# pylint: disable=unused-argument, too-many-function-args
def setup(hass, config):
    """Common set up for WeMo devices."""
    import pywemo

    global SUBSCRIPTION_REGISTRY
    SUBSCRIPTION_REGISTRY = pywemo.SubscriptionRegistry()
    SUBSCRIPTION_REGISTRY.start()

    def stop_wemo(event):
        """Shutdown Wemo subscriptions and subscription thread on exit."""
        _LOGGER.info("Shutting down subscriptions.")
        SUBSCRIPTION_REGISTRY.stop()

    hass.bus.listen_once(EVENT_HOMEASSISTANT_STOP, stop_wemo)

    def discovery_dispatch(service, discovery_info):
        """Dispatcher for WeMo discovery events."""
        # name, model, location, mac
        _, model_name, url, _ = discovery_info

        # Only register a device once
        if url in KNOWN_DEVICES:
            return
        KNOWN_DEVICES.append(url)

        service = WEMO_MODEL_DISPATCH.get(model_name) or DISCOVER_SWITCHES
        component = WEMO_SERVICE_DISPATCH.get(service)

        discovery.discover(hass, service, discovery_info,
                           component, config)

    discovery.listen(hass, discovery.SERVICE_WEMO, discovery_dispatch)

    _LOGGER.info("Scanning for WeMo devices.")
    devices = [(device.host, device) for device in pywemo.discover_devices()]

    # Add static devices from the config file
    devices.extend((address, None)
                   for address in config.get(DOMAIN, {}).get('static', []))

    for address, device in devices:
        port = pywemo.ouimeaux_device.probe_wemo(address)
        if not port:
            _LOGGER.warning('Unable to probe wemo at %s', address)
            continue
        _LOGGER.info('Adding wemo at %s:%i', address, port)

        url = 'http://%s:%i/setup.xml' % (address, port)
        if device is None:
            device = pywemo.discovery.device_from_description(url, None)

        discovery_info = (device.name, device.model_name, url, device.mac)
        discovery.discover(hass, discovery.SERVICE_WEMO, discovery_info)
    return True
