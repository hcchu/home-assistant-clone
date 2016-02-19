"""
homeassistant.components.group
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
Provides functionality to group devices that can be turned on or off.

For more details about this component, please refer to the documentation at
https://home-assistant.io/components/group/
"""
import homeassistant.core as ha
from homeassistant.const import (
    ATTR_ENTITY_ID, CONF_ICON, CONF_NAME, STATE_CLOSED, STATE_HOME,
    STATE_NOT_HOME, STATE_OFF, STATE_ON, STATE_OPEN, STATE_UNKNOWN)
from homeassistant.helpers.entity import (
    Entity, generate_entity_id, split_entity_id)
from homeassistant.helpers.event import track_state_change

DOMAIN = 'group'

ENTITY_ID_FORMAT = DOMAIN + '.{}'

CONF_ENTITIES = 'entities'
CONF_VIEW = 'view'

ATTR_AUTO = 'auto'
ATTR_ORDER = 'order'
ATTR_VIEW = 'view'

# List of ON/OFF state tuples for groupable states
_GROUP_TYPES = [(STATE_ON, STATE_OFF), (STATE_HOME, STATE_NOT_HOME),
                (STATE_OPEN, STATE_CLOSED)]


def _get_group_on_off(state):
    """ Determine the group on/off states based on a state. """
    for states in _GROUP_TYPES:
        if state in states:
            return states

    return None, None


def is_on(hass, entity_id):
    """ Returns if the group state is in its ON-state. """
    state = hass.states.get(entity_id)

    if state:
        group_on, _ = _get_group_on_off(state.state)

        # If we found a group_type, compare to ON-state
        return group_on is not None and state.state == group_on

    return False


def expand_entity_ids(hass, entity_ids):
    """ Returns the given list of entity ids and expands group ids into
        the entity ids it represents if found. """
    found_ids = []

    for entity_id in entity_ids:
        if not isinstance(entity_id, str):
            continue

        entity_id = entity_id.lower()

        try:
            # If entity_id points at a group, expand it
            domain, _ = split_entity_id(entity_id)

            if domain == DOMAIN:
                found_ids.extend(
                    ent_id for ent_id
                    in expand_entity_ids(hass, get_entity_ids(hass, entity_id))
                    if ent_id not in found_ids)

            else:
                if entity_id not in found_ids:
                    found_ids.append(entity_id)

        except AttributeError:
            # Raised by split_entity_id if entity_id is not a string
            pass

    return found_ids


def get_entity_ids(hass, entity_id, domain_filter=None):
    """ Get the entity ids that make up this group. """
    entity_id = entity_id.lower()

    try:
        entity_ids = hass.states.get(entity_id).attributes[ATTR_ENTITY_ID]

        if domain_filter:
            domain_filter = domain_filter.lower()

            return [ent_id for ent_id in entity_ids
                    if ent_id.startswith(domain_filter)]
        else:
            return entity_ids

    except (AttributeError, KeyError):
        # AttributeError if state did not exist
        # KeyError if key did not exist in attributes
        return []


def setup(hass, config):
    """ Sets up all groups found definded in the configuration. """
    for object_id, conf in config.get(DOMAIN, {}).items():
        if not isinstance(conf, dict):
            conf = {CONF_ENTITIES: conf}

        name = conf.get(CONF_NAME, object_id)
        entity_ids = conf.get(CONF_ENTITIES)
        icon = conf.get(CONF_ICON)
        view = conf.get(CONF_VIEW)

        if isinstance(entity_ids, str):
            entity_ids = [ent.strip() for ent in entity_ids.split(",")]

        Group(hass, name, entity_ids, icon=icon, view=view,
              object_id=object_id)

    return True


class Group(Entity):
    """ Tracks a group of entity ids. """

    # pylint: disable=too-many-instance-attributes, too-many-arguments

    def __init__(self, hass, name, entity_ids=None, user_defined=True,
                 icon=None, view=False, object_id=None):
        self.hass = hass
        self._name = name
        self._state = STATE_UNKNOWN
        self._order = len(hass.states.entity_ids(DOMAIN))
        self._user_defined = user_defined
        self._icon = icon
        self._view = view
        self.entity_id = generate_entity_id(
            ENTITY_ID_FORMAT, object_id or name, hass=hass)
        self.tracking = []
        self.group_on = None
        self.group_off = None

        if entity_ids is not None:
            self.update_tracked_entity_ids(entity_ids)
        else:
            self.update_ha_state(True)

    @property
    def should_poll(self):
        return False

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def icon(self):
        return self._icon

    @property
    def hidden(self):
        return not self._user_defined or self._view

    @property
    def state_attributes(self):
        data = {
            ATTR_ENTITY_ID: self.tracking,
            ATTR_ORDER: self._order,
        }
        if not self._user_defined:
            data[ATTR_AUTO] = True
        if self._view:
            data[ATTR_VIEW] = True
        return data

    def update_tracked_entity_ids(self, entity_ids):
        """ Update the tracked entity IDs. """
        self.stop()
        self.tracking = tuple(ent_id.lower() for ent_id in entity_ids)
        self.group_on, self.group_off = None, None

        self.update_ha_state(True)

        self.start()

    def start(self):
        """ Starts the tracking. """
        track_state_change(
            self.hass, self.tracking, self._state_changed_listener)

    def stop(self):
        """ Unregisters the group from Home Assistant. """
        self.hass.states.remove(self.entity_id)

        self.hass.bus.remove_listener(
            ha.EVENT_STATE_CHANGED, self._state_changed_listener)

    def update(self):
        """ Query all the tracked states and determine current group state. """
        self._state = STATE_UNKNOWN

        for entity_id in self.tracking:
            state = self.hass.states.get(entity_id)

            if state is not None:
                self._process_tracked_state(state)

    def _state_changed_listener(self, entity_id, old_state, new_state):
        """ Listener to receive state changes of tracked entities. """
        self._process_tracked_state(new_state)
        self.update_ha_state()

    def _process_tracked_state(self, tr_state):
        """ Updates group state based on a new state of a tracked entity. """

        # We have not determined type of group yet
        if self.group_on is None:
            self.group_on, self.group_off = _get_group_on_off(tr_state.state)

            if self.group_on is not None:
                # New state of the group is going to be based on the first
                # state that we can recognize
                self._state = tr_state.state

            return

        # There is already a group state
        cur_gr_state = self._state
        group_on, group_off = self.group_on, self.group_off

        # if cur_gr_state = OFF and tr_state = ON: set ON
        # if cur_gr_state = ON and tr_state = OFF: research
        # else: ignore

        if cur_gr_state == group_off and tr_state.state == group_on:
            self._state = group_on

        elif cur_gr_state == group_on and tr_state.state == group_off:

            # Set to off if no other states are on
            if not any(self.hass.states.is_state(ent_id, group_on)
                       for ent_id in self.tracking
                       if tr_state.entity_id != ent_id):
                self._state = group_off
