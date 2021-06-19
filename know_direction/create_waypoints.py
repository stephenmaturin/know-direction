import sys
from enum import Enum, auto
from math import radians, sin, cos, asin, sqrt
from pathlib import Path
from typing import Optional, Collection, Tuple

import networkx
from attr import attrs, attrib
from attr.validators import instance_of, optional
from fastkml import kml
from more_itertools import windowed


class TravelMode(Enum):
    OVERLAND = auto()
    UPSTREAM = auto()
    DOWNSTREAM = auto()
    SEA = auto()

@attrs(kw_only=True)
class OverlandSpeedInfo:
    overland_speed_in_mile_per_day: float = attrib(validator=instance_of(float))

@attrs(kw_only=True)
class RiverSpeedInfo:
    upstream_speed_in_miles_per_day: float = attrib(validator=instance_of(float))
    downstream_speed_in_miles_per_day: float = attrib(validator=instance_of(float))

@attrs(kw_only=True)
class SeaSpeedInfo:
    seas_speed_in_miles_per_day: float = attrib(validator=instance_of(float))


@attrs(kw_only=True)
class SpeedInfo:
    overland_speeds: OverlandSpeedInfo = attrib(validator=instance_of(OverlandSpeedInfo))
    river_speeds: RiverSpeedInfo = attrib(validator=instance_of(RiverSpeedInfo))
    sea_speeds: SeaSpeedInfo = attrib(validator=instance_of(SeaSpeedInfo))

    def distance_to_travel_time_in_days(self, *, distance_in_miles: float, travel_mode: TravelMode) -> float:
        if travel_mode == TravelMode.OVERLAND:
            return distance_in_miles / self.overland_speeds.overland_speed_in_mile_per_day
        elif travel_mode == TravelMode.DOWNSTREAM:
            return distance_in_miles / self.river_speeds.downstream_speed_in_miles_per_day
        elif travel_mode == TravelMode.UPSTREAM:
            return distance_in_miles / self.river_speeds.upstream_speed_in_miles_per_day
        elif travel_mode == TravelMode.SEA:
            return distance_in_miles / self.sea_speeds.seas_speed_in_miles_per_day
        else:
            raise RuntimeError(f"Unknown travel mode {travel_mode}")

ON_FOOT = OverlandSpeedInfo(overland_speed_in_mile_per_day = 20.0)

NORMAL_RIVER = RiverSpeedInfo(
upstream_speed_in_miles_per_day = 40.0,
downstream_speed_in_miles_per_day=15.0
)

NORMAL_SEA = SeaSpeedInfo(
seas_speed_in_miles_per_day = 100.0
)

DEFAULT_SPEED_INFO = SpeedInfo(
    overland_speeds = ON_FOOT,
    river_speeds=NORMAL_RIVER,
    sea_speeds=NORMAL_SEA
)

@attrs(kw_only=True, eq=False)
class GeoPoint:
    latitude: float = attrib(validator=instance_of(float))
    longitude: float = attrib(validator=instance_of(float))

    def pretty_string(self) -> str:
        return f"({self.latitude:.2f}, {self.latitude:.2f})"


@attrs(kw_only=True, eq=False)
class PopulatedPlace(GeoPoint):
    name: str = attrib(validator=instance_of(str))
    population: Optional[int] = attrib(validator=optional(instance_of(int)))

    def pretty_string(self) -> str:
        return self.name


def load_cities(city_kml_path: Path) -> Collection[PopulatedPlace]:
    raw_city_kml = city_kml_path.read_text(encoding="utf-8")
    city_kml = kml.KML()
    city_kml.from_string(raw_city_kml.encode(encoding="utf-8"))

    top_level_features = tuple(city_kml.features())
    if len(top_level_features) != 1:
        raise RuntimeError("Expected a single root document element")

    document_root = top_level_features[0]
    document_children = tuple(document_root.features())

    if len(document_children) != 1:
        raise RuntimeError("Expected a single folder of cities")

    city_folder = document_children[0]

    cities = []

    for city_placemark in city_folder.features():
        city_coordinates = city_placemark.geometry.coords
        if len(city_coordinates) != 1:
            raise RuntimeError("Expected a city to have only one set of coordinates")
        city_point = city_coordinates[0]
        (latitiude, longitude, population) = city_point
        cities.append(PopulatedPlace(name=city_placemark.name,
                                     population = int(population) if population else None,
                                     latitude = latitiude,
                                     longitude = longitude))

    return cities


def add_city_to_city_connections(cities: Collection[PopulatedPlace], waypoint_graph: networkx.DiGraph) -> None:
    for city in cities:
        for other_city in cities:
            if city != other_city:
                distance_between_cities = great_circle_distance_in_miles(city, other_city)
                waypoint_graph.add_edge(city, other_city, distance=distance_between_cities,
                                        travel_mode=TravelMode.OVERLAND)
                waypoint_graph.add_edge(other_city, city, distance=distance_between_cities,
                                        travel_mode=TravelMode.OVERLAND)


def great_circle_distance_in_miles(source: GeoPoint, target: GeoPoint) -> float:
    """
    From https://stackoverflow.com/a/15737218
    """
    # convert decimal degrees to radians
    lon1, lat1, lon2, lat2 = map(radians, [source.longitude, source.latitude, target.longitude, target.latitude])
    # haversine formula
    dlon = lon2 - lon1
    dlat = lat2 - lat1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    # Radius of earth in miles is 3958.8
    return 3958.8 * c

TIME_ATTRIBUTE = "travel_time_in_day"
DISTANCE_ATTRIBUTE = "distance"
TRAVEL_MODE = "travel_mode"


def decorate_with_travel_time_in_place(waypoint_graph: networkx.DiGraph, speeds: SpeedInfo) -> None:
    for (_, _, edge_attributes) in waypoint_graph.edges.data():
        edge_attributes[TIME_ATTRIBUTE] = speeds.distance_to_travel_time_in_days(
            distance_in_miles=edge_attributes[DISTANCE_ATTRIBUTE],
            travel_mode=edge_attributes[TRAVEL_MODE]
        )

def pretty_print_path(wayppint_graph: networkx.DiGraph, path: Tuple[GeoPoint]) -> None:
    if len(path) < 2:
        raise RuntimeError("Path length cannot be less than 2")
    print(f"Start in {path[0].pretty_string()}")
    for (segment_source, segment_destination) in windowed(path, 2):
        edge = waypoint_graph.edges[segment_source, segment_destination]
        print(f"Travel from {segment_source.pretty_string()} to {segment_destination.pretty_string()} by "
              f"{edge[TRAVEL_MODE]} ({edge[TIME_ATTRIBUTE]} days)\n")



if __name__ == '__main__':
    data_dir = Path(sys.argv[1])
    cities = load_cities(data_dir / "golarion_city.kml")
    waypoint_graph = networkx.DiGraph()
    waypoint_graph.add_nodes_from(cities)

    add_city_to_city_connections(cities, waypoint_graph)

    decorate_with_travel_time_in_place(waypoint_graph, DEFAULT_SPEED_INFO)

    city_name_to_city = {
        city.name : city
        for city in cities
    }

    print("Enter source city:")
    source_city = city_name_to_city[input()]
    print("Enter destination city:")
    destination_city = city_name_to_city[input()]

    path = networkx.shortest_path(waypoint_graph, source_city, destination_city)
    pretty_print_path(waypoint_graph, path)



