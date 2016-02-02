"""
homeassistant.components.frontend
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Provides a frontend for Home Assistant.
"""
import re
import os
import logging

from . import version, mdi_version
import homeassistant.util as util
from homeassistant.const import URL_ROOT, HTTP_OK

DOMAIN = 'frontend'
DEPENDENCIES = ['api']

INDEX_PATH = os.path.join(os.path.dirname(__file__), 'index.html.template')

_LOGGER = logging.getLogger(__name__)

FRONTEND_URLS = [
    URL_ROOT, '/logbook', '/history', '/map', '/devService', '/devState',
    '/devEvent', '/devInfo', '/devTemplate',
    re.compile(r'/states(/([a-zA-Z\._\-0-9/]+)|)'),
]

_FINGERPRINT = re.compile(r'^(\w+)-[a-z0-9]{32}\.(\w+)$', re.IGNORECASE)


def setup(hass, config):
    """ Setup serving the frontend. """
    if 'http' not in hass.config.components:
        _LOGGER.error('Dependency http is not loaded')
        return False

    for url in FRONTEND_URLS:
        hass.http.register_path('GET', url, _handle_get_root, False)

    hass.http.register_path('GET', '/service_worker.js',
                            _handle_get_service_worker, False)

    # Static files
    hass.http.register_path(
        'GET', re.compile(r'/static/(?P<file>[a-zA-Z\._\-0-9/]+)'),
        _handle_get_static, False)
    hass.http.register_path(
        'HEAD', re.compile(r'/static/(?P<file>[a-zA-Z\._\-0-9/]+)'),
        _handle_get_static, False)
    hass.http.register_path(
        'GET', re.compile(r'/local/(?P<file>[a-zA-Z\._\-0-9/]+)'),
        _handle_get_local, False)

    return True


def _handle_get_root(handler, path_match, data):
    """ Renders the frontend. """
    handler.send_response(HTTP_OK)
    handler.send_header('Content-type', 'text/html; charset=utf-8')
    handler.end_headers()

    if handler.server.development:
        app_url = "home-assistant-polymer/src/home-assistant.html"
    else:
        app_url = "frontend-{}.html".format(version.VERSION)

    # auto login if no password was set, else check api_password param
    auth = ('no_password_set' if handler.server.api_password is None
            else data.get('api_password', ''))

    with open(INDEX_PATH) as template_file:
        template_html = template_file.read()

    template_html = template_html.replace('{{ app_url }}', app_url)
    template_html = template_html.replace('{{ auth }}', auth)
    template_html = template_html.replace('{{ icons }}', mdi_version.VERSION)

    handler.wfile.write(template_html.encode("UTF-8"))


def _handle_get_service_worker(handler, path_match, data):
    """ Returns service worker for the frontend. """
    if handler.server.development:
        sw_path = "home-assistant-polymer/build/service_worker.js"
    else:
        sw_path = "service_worker.js"

    handler.write_file(os.path.join(os.path.dirname(__file__), 'www_static',
                                    sw_path))


def _handle_get_static(handler, path_match, data):
    """ Returns a static file for the frontend. """
    req_file = util.sanitize_path(path_match.group('file'))

    # Strip md5 hash out
    fingerprinted = _FINGERPRINT.match(req_file)
    if fingerprinted:
        req_file = "{}.{}".format(*fingerprinted.groups())

    path = os.path.join(os.path.dirname(__file__), 'www_static', req_file)

    handler.write_file(path)


def _handle_get_local(handler, path_match, data):
    """
    Returns a static file from the hass.config.path/www for the frontend.
    """
    req_file = util.sanitize_path(path_match.group('file'))

    path = handler.server.hass.config.path('www', req_file)

    handler.write_file(path)
