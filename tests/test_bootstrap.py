"""Test the bootstrapping."""
# pylint: disable=too-many-public-methods,protected-access
import os
import tempfile
from unittest import mock
import threading

import voluptuous as vol

from homeassistant import bootstrap, loader
from homeassistant.const import (__version__, CONF_LATITUDE, CONF_LONGITUDE,
                                 CONF_NAME, CONF_CUSTOMIZE)
import homeassistant.util.dt as dt_util
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.config_validation import PLATFORM_SCHEMA

from tests.common import get_test_home_assistant, MockModule, MockPlatform

ORIG_TIMEZONE = dt_util.DEFAULT_TIME_ZONE


class TestBootstrap:
    """Test the bootstrap utils."""

    def setup_method(self, method):
        """Setup the test."""
        if method == self.test_from_config_file:
            return

        self.hass = get_test_home_assistant()
        self.backup_cache = loader._COMPONENT_CACHE

    def teardown_method(self, method):
        """Clean up."""
        dt_util.DEFAULT_TIME_ZONE = ORIG_TIMEZONE

        if method == self.test_from_config_file:
            return

        self.hass.stop()
        loader._COMPONENT_CACHE = self.backup_cache

    def test_from_config_file(self):
        """Test with configuration file."""
        components = ['browser', 'conversation', 'script']
        with tempfile.NamedTemporaryFile() as fp:
            for comp in components:
                fp.write('{}:\n'.format(comp).encode('utf-8'))
            fp.flush()

            hass = bootstrap.from_config_file(fp.name)

            components.append('group')

            assert sorted(components) == sorted(hass.config.components)

    def test_remove_lib_on_upgrade(self):
        """Test removal of library on upgrade."""
        with tempfile.TemporaryDirectory() as config_dir:
            version_path = os.path.join(config_dir, '.HA_VERSION')
            lib_dir = os.path.join(config_dir, 'deps')
            check_file = os.path.join(lib_dir, 'check')

            with open(version_path, 'wt') as outp:
                outp.write('0.7.0')

            os.mkdir(lib_dir)

            with open(check_file, 'w'):
                pass

            self.hass.config.config_dir = config_dir

            assert os.path.isfile(check_file)
            bootstrap.process_ha_config_upgrade(self.hass)
            assert not os.path.isfile(check_file)

    def test_not_remove_lib_if_not_upgrade(self):
        """Test removal of library with no upgrade."""
        with tempfile.TemporaryDirectory() as config_dir:
            version_path = os.path.join(config_dir, '.HA_VERSION')
            lib_dir = os.path.join(config_dir, 'deps')
            check_file = os.path.join(lib_dir, 'check')

            with open(version_path, 'wt') as outp:
                outp.write(__version__)

            os.mkdir(lib_dir)

            with open(check_file, 'w'):
                pass

            self.hass.config.config_dir = config_dir

            bootstrap.process_ha_config_upgrade(self.hass)

            assert os.path.isfile(check_file)

    def test_entity_customization(self):
        """Test entity customization through configuration."""
        config = {CONF_LATITUDE: 50,
                  CONF_LONGITUDE: 50,
                  CONF_NAME: 'Test',
                  CONF_CUSTOMIZE: {'test.test': {'hidden': True}}}

        bootstrap.process_ha_core_config(self.hass, config)

        entity = Entity()
        entity.entity_id = 'test.test'
        entity.hass = self.hass
        entity.update_ha_state()

        state = self.hass.states.get('test.test')

        assert state.attributes['hidden']

    def test_handle_setup_circular_dependency(self):
        """Test the setup of circular dependencies."""
        loader.set_component('comp_b', MockModule('comp_b', ['comp_a']))

        def setup_a(hass, config):
            """Setup the another component."""
            bootstrap.setup_component(hass, 'comp_b')
            return True

        loader.set_component('comp_a', MockModule('comp_a', setup=setup_a))

        bootstrap.setup_component(self.hass, 'comp_a')
        assert ['comp_a'] == self.hass.config.components

    def test_validate_component_config(self):
        """Test validating component configuration."""
        config_schema = vol.Schema({
            'comp_conf': {
                'hello': str
            }
        }, required=True)
        loader.set_component(
            'comp_conf', MockModule('comp_conf', config_schema=config_schema))

        assert not bootstrap._setup_component(self.hass, 'comp_conf', {})

        assert not bootstrap._setup_component(self.hass, 'comp_conf', {
            'comp_conf': None
        })

        assert not bootstrap._setup_component(self.hass, 'comp_conf', {
            'comp_conf': {}
        })

        assert not bootstrap._setup_component(self.hass, 'comp_conf', {
            'comp_conf': {
                'hello': 'world',
                'invalid': 'extra',
            }
        })

        assert bootstrap._setup_component(self.hass, 'comp_conf', {
            'comp_conf': {
                'hello': 'world',
            }
        })

    def test_validate_platform_config(self):
        """Test validating platform configuration."""
        platform_schema = PLATFORM_SCHEMA.extend({
            'hello': str,
        })
        loader.set_component(
            'platform_conf',
            MockModule('platform_conf', platform_schema=platform_schema))

        loader.set_component(
            'platform_conf.whatever', MockPlatform('whatever'))

        assert not bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': None
        })

        assert not bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': {}
        })

        assert not bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': {
                'hello': 'world',
                'invalid': 'extra',
            }
        })

        assert not bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': {
                'platform': 'whatever',
                'hello': 'world',
            },

            'platform_conf 2': {
                'invalid': True
            }
        })

        assert not bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': {
                'platform': 'not_existing',
                'hello': 'world',
            }
        })

        assert bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': {
                'platform': 'whatever',
                'hello': 'world',
            }
        })

        assert bootstrap._setup_component(self.hass, 'platform_conf', {
            'platform_conf': [{
                'platform': 'whatever',
                'hello': 'world',
            }]
        })

    def test_component_not_found(self):
        """setup_component should not crash if component doesn't exist."""
        assert not bootstrap.setup_component(self.hass, 'non_existing')

    def test_component_not_double_initialized(self):
        """Test we do not setup a component twice."""

        mock_setup = mock.MagicMock()

        loader.set_component('comp', MockModule('comp', setup=mock_setup))

        assert bootstrap.setup_component(self.hass, 'comp')
        assert mock_setup.called

        mock_setup.reset_mock()

        assert bootstrap.setup_component(self.hass, 'comp')
        assert not mock_setup.called

    @mock.patch('homeassistant.util.package.install_package',
                return_value=False)
    def test_component_not_installed_if_requirement_fails(self, mock_install):
        """Component setup should fail if requirement can't install."""
        loader.set_component(
            'comp', MockModule('comp', requirements=['package==0.0.1']))

        assert not bootstrap.setup_component(self.hass, 'comp')
        assert 'comp' not in self.hass.config.components

    def test_component_not_setup_twice_if_loaded_during_other_setup(self):
        """
        Test component that gets setup while waiting for lock is not setup
        twice.
        """
        loader.set_component('comp', MockModule('comp'))

        result = []

        def setup_component():
            result.append(bootstrap.setup_component(self.hass, 'comp'))

        with bootstrap._SETUP_LOCK:
            thread = threading.Thread(target=setup_component)
            thread.start()
            self.hass.config.components.append('comp')

        thread.join()

        assert len(result) == 1
        assert result[0]

    def test_component_not_setup_missing_dependencies(self):
        """Test we do not setup a component if not all dependencies loaded."""
        deps = ['non_existing']
        loader.set_component('comp', MockModule('comp', dependencies=deps))

        assert not bootstrap._setup_component(self.hass, 'comp', None)
        assert 'comp' not in self.hass.config.components

        self.hass.config.components.append('non_existing')

        assert bootstrap._setup_component(self.hass, 'comp', None)

    def test_component_failing_setup(self):
        """Test component that fails setup."""
        loader.set_component(
            'comp', MockModule('comp', setup=lambda hass, config: False))

        assert not bootstrap._setup_component(self.hass, 'comp', None)
        assert 'comp' not in self.hass.config.components

    def test_component_exception_setup(self):
        """Test component that raises exception during setup."""
        def exception_setup(hass, config):
            """Setup that raises exception."""
            raise Exception('fail!')

        loader.set_component('comp', MockModule('comp', setup=exception_setup))

        assert not bootstrap._setup_component(self.hass, 'comp', None)
        assert 'comp' not in self.hass.config.components

    @mock.patch('homeassistant.bootstrap.process_ha_core_config')
    def test_home_assistant_core_config_validation(self, mock_process):
        """Test if we pass in wrong information for HA conf."""
        # Extensive HA conf validation testing is done in test_config.py
        assert None is bootstrap.from_config_dict({
            'homeassistant': {
                'latitude': 'some string'
            }
        })
        assert not mock_process.called

    def test_component_setup_with_validation_and_dependency(self):
        """Test all config is passed to dependencies."""

        def config_check_setup(hass, config):
            """Setup method that tests config is passed in."""
            if config.get('comp_a', {}).get('valid', False):
                return True
            raise Exception('Config not passed in: {}'.format(config))

        loader.set_component('comp_a',
                             MockModule('comp_a', setup=config_check_setup))

        loader.set_component('switch.platform_a', MockPlatform('comp_b',
                                                               ['comp_a']))

        bootstrap.setup_component(self.hass, 'switch', {
            'comp_a': {
                'valid': True
            },
            'switch': {
                'platform': 'platform_a',
            }
        })
        assert 'comp_a' in self.hass.config.components

    def test_platform_specific_config_validation(self):
        """Test platform that specifies config."""

        platform_schema = PLATFORM_SCHEMA.extend({
            'valid': True,
        }, extra=vol.PREVENT_EXTRA)

        loader.set_component(
            'switch.platform_a',
            MockPlatform('comp_b', platform_schema=platform_schema))

        assert not bootstrap.setup_component(self.hass, 'switch', {
            'switch': {
                'platform': 'platform_a',
                'invalid': True
            }
        })

        assert not bootstrap.setup_component(self.hass, 'switch', {
            'switch': {
                'platform': 'platform_a',
                'valid': True,
                'invalid_extra': True,
            }
        })

        assert bootstrap.setup_component(self.hass, 'switch', {
            'switch': {
                'platform': 'platform_a',
                'valid': True
            }
        })
