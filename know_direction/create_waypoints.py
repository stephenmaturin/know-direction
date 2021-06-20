import logging
import sys
from pathlib import Path
from typing import Tuple

import networkx
from more_itertools import windowed

from know_direction.travel_speed import SpeedInfo, DEFAULT_SPEED_INFO
from know_direction.waypoint_graph import WaypointGraph
from know_direction.world_geography import GeoPoint, WorldGeography

logging.basicConfig(level=logging.DEBUG)


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

    world_geography = WorldGeography.from_directory(data_dir)
    waypoint_graph = WaypointGraph.create_from(world_geography)


    logging.info("Computing travel times for each segment")
    decorate_with_travel_time_in_place(waypoint_graph.graph, DEFAULT_SPEED_INFO)


    print("Enter source city:")
    source_city = world_geography.city_name_to_city[input()]
    print("Enter destination city:")
    destination_city = world_geography.city_name_to_city[input()]

    path = networkx.shortest_path(waypoint_graph, source_city, destination_city)
    pretty_print_path(waypoint_graph.graph, path)



