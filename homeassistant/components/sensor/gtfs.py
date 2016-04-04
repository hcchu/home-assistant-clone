"""
Support for GTFS (Google/General Transport Format Schema).

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.gtfs/
"""
import os
import logging
import datetime

from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

REQUIREMENTS = ["https://github.com/robbiet480/pygtfs/archive/"
                "6b40d5fb30fd410cfaf637c901b5ed5a08c33e4c.zip#"
                "pygtfs==0.1.2"]

ICON = "mdi:train"

TIME_FORMAT = "%Y-%m-%d %H:%M:%S"

# pylint: disable=too-many-locals


def get_next_departure(sched, start_station_id, end_station_id):
    """Get the next departure for the given sched."""
    origin_station = sched.stops_by_id(start_station_id)[0]
    destination_station = sched.stops_by_id(end_station_id)[0]

    now = datetime.datetime.now()
    day_name = now.strftime("%A").lower()
    now_str = now.strftime("%H:%M:%S")

    from sqlalchemy.sql import text

    sql_query = text("""
    SELECT trip.trip_id, trip.route_id,
           time(origin_stop_time.departure_time),
           time(destination_stop_time.arrival_time),
           time(origin_stop_time.arrival_time),
           time(origin_stop_time.departure_time),
           origin_stop_time.drop_off_type,
           origin_stop_time.pickup_type,
           origin_stop_time.shape_dist_traveled,
           origin_stop_time.stop_headsign,
           origin_stop_time.stop_sequence,
           time(destination_stop_time.arrival_time),
           time(destination_stop_time.departure_time),
           destination_stop_time.drop_off_type,
           destination_stop_time.pickup_type,
           destination_stop_time.shape_dist_traveled,
           destination_stop_time.stop_headsign,
           destination_stop_time.stop_sequence
    FROM trips trip
    INNER JOIN calendar calendar
               ON trip.service_id = calendar.service_id
    INNER JOIN stop_times origin_stop_time
               ON trip.trip_id = origin_stop_time.trip_id
    INNER JOIN stops start_station
               ON origin_stop_time.stop_id = start_station.stop_id
    INNER JOIN stop_times destination_stop_time
               ON trip.trip_id = destination_stop_time.trip_id
    INNER JOIN stops end_station
               ON destination_stop_time.stop_id = end_station.stop_id
    WHERE calendar.{day_name} = 1
               AND time(origin_stop_time.departure_time) > time(:now_str)
    AND start_station.stop_id = :origin_station_id
               AND end_station.stop_id = :end_station_id
    ORDER BY origin_stop_time.departure_time LIMIT 1;
    """.format(day_name=day_name))
    result = sched.engine.execute(sql_query, now_str=now_str,
                                  origin_station_id=origin_station.id,
                                  end_station_id=destination_station.id)
    item = {}
    for row in result:
        item = row

    today = datetime.datetime.today().strftime("%Y-%m-%d")
    departure_time_string = "{} {}".format(today, item[2])
    arrival_time_string = "{} {}".format(today, item[3])
    departure_time = datetime.datetime.strptime(departure_time_string,
                                                TIME_FORMAT)
    arrival_time = datetime.datetime.strptime(arrival_time_string,
                                              TIME_FORMAT)

    seconds_until = (departure_time-datetime.datetime.now()).total_seconds()
    minutes_until = int(seconds_until / 60)

    route = sched.routes_by_id(item[1])[0]

    origin_stoptime_arrival_time = "{} {}".format(today, item[4])

    origin_stoptime_departure_time = "{} {}".format(today, item[5])

    dest_stoptime_arrival_time = "{} {}".format(today, item[11])

    dest_stoptime_depart_time = "{} {}".format(today, item[12])

    origin_stop_time_dict = {
        "Arrival Time": origin_stoptime_arrival_time,
        "Departure Time": origin_stoptime_departure_time,
        "Drop Off Type": item[6], "Pickup Type": item[7],
        "Shape Dist Traveled": item[8], "Headsign": item[9],
        "Sequence": item[10]
    }

    destination_stop_time_dict = {
        "Arrival Time": dest_stoptime_arrival_time,
        "Departure Time": dest_stoptime_depart_time,
        "Drop Off Type": item[13], "Pickup Type": item[14],
        "Shape Dist Traveled": item[15], "Headsign": item[16],
        "Sequence": item[17]
    }

    return {
        "trip_id": item[0],
        "trip": sched.trips_by_id(item[0])[0],
        "route": route,
        "agency": sched.agencies_by_id(route.agency_id)[0],
        "origin_station": origin_station,
        "departure_time": departure_time,
        "destination_station": destination_station,
        "arrival_time": arrival_time,
        "seconds_until_departure": seconds_until,
        "minutes_until_departure": minutes_until,
        "origin_stop_time": origin_stop_time_dict,
        "destination_stop_time": destination_stop_time_dict
    }


def setup_platform(hass, config, add_devices, discovery_info=None):
    """Get the GTFS sensor."""
    if config.get("origin") is None:
        _LOGGER.error("Origin must be set in the GTFS configuration!")
        return False

    if config.get("destination") is None:
        _LOGGER.error("Destination must be set in the GTFS configuration!")
        return False

    if config.get("data") is None:
        _LOGGER.error("Data must be set in the GTFS configuration!")
        return False

    gtfs_dir = hass.config.path("gtfs")

    if not os.path.exists(gtfs_dir):
        os.makedirs(gtfs_dir)

    if not os.path.exists(os.path.join(gtfs_dir, config["data"])):
        _LOGGER.error("The given GTFS data file/folder was not found!")
        return False

    dev = []
    dev.append(GTFSDepartureSensor(config["data"], gtfs_dir,
                                   config["origin"], config["destination"]))
    add_devices(dev)

# pylint: disable=too-many-instance-attributes,too-few-public-methods


class GTFSDepartureSensor(Entity):
    """Implementation of an GTFS departures sensor."""

    def __init__(self, data_source, gtfs_folder, origin, destination):
        """Initialize the sensor."""
        self._data_source = data_source
        self._gtfs_folder = gtfs_folder
        self.origin = origin
        self.destination = destination
        self._name = "GTFS Sensor"
        self._unit_of_measurement = "min"
        self._state = 0
        self._attributes = {}
        self.update()

    @property
    def name(self):
        """Return the name of the sensor."""
        return self._name

    @property
    def state(self):
        """Return the state of the sensor."""
        return self._state

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement of this entity, if any."""
        return self._unit_of_measurement

    @property
    def device_state_attributes(self):
        """Return the state attributes."""
        return self._attributes

    @property
    def icon(self):
        """Icon to use in the frontend, if any."""
        return ICON

    def update(self):
        """Get the latest data from GTFS and update the states."""
        import pygtfs

        split_file_name = os.path.splitext(self._data_source)

        sqlite_file = "{}.sqlite".format(split_file_name[0])
        gtfs = pygtfs.Schedule(os.path.join(self._gtfs_folder, sqlite_file))

        # pylint: disable=no-member
        if len(gtfs.feeds) < 1:
            pygtfs.append_feed(gtfs, os.path.join(self._gtfs_folder,
                                                  self._data_source))

        self._departure = get_next_departure(gtfs, self.origin,
                                             self.destination)
        self._state = self._departure["minutes_until_departure"]

        origin_station = self._departure["origin_station"]
        destination_station = self._departure["destination_station"]
        origin_stop_time = self._departure["origin_stop_time"]
        destination_stop_time = self._departure["destination_stop_time"]
        agency = self._departure["agency"]
        route = self._departure["route"]
        trip = self._departure["trip"]

        name = "{} {} to {} next departure"
        self._name = name.format(agency.agency_name,
                                 origin_station.stop_id,
                                 destination_station.stop_id)

        # Build attributes

        self._attributes = {}

        def dict_for_table(resource):
            """Return a dict for the SQLAlchemy resource given."""
            return dict((col, getattr(resource, col))
                        for col in resource.__table__.columns.keys())

        def append_keys(resource, prefix=None):
            """Properly format key val pairs to append to attributes."""
            for key, val in resource.items():
                if val == "" or val is None or key == "feed_id":
                    continue
                pretty_key = key.replace("_", " ")
                pretty_key = pretty_key.title()
                pretty_key = pretty_key.replace("Id", "ID")
                pretty_key = pretty_key.replace("Url", "URL")
                if prefix is not None and \
                   pretty_key.startswith(prefix) is False:
                    pretty_key = "{} {}".format(prefix, pretty_key)
                self._attributes[pretty_key] = val

        append_keys(dict_for_table(agency), "Agency")
        append_keys(dict_for_table(route), "Route")
        append_keys(dict_for_table(trip), "Trip")
        append_keys(dict_for_table(origin_station), "Origin Station")
        append_keys(dict_for_table(destination_station), "Destination Station")
        append_keys(origin_stop_time, "Origin Stop")
        append_keys(destination_stop_time, "Destination Stop")
