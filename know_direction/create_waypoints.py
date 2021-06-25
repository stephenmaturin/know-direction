import logging
import sys
from pathlib import Path
from typing import Tuple, Mapping, Iterable, Any, Optional

import networkx
from attr import attrib, attrs
from attr.validators import instance_of, optional
from more_itertools import windowed

from know_direction.travel_speed import SpeedInfo, DEFAULT_SPEED_INFO, TravelMode
from know_direction.waypoint_graph import WaypointGraph
from know_direction.world_geography import GeoPoint, WorldGeography, RiverPoint

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

    print(f"Start in {path[0].pretty_string()}")

    steps = _to_canonical_step_sequence(path)

    total_time = 0.0
    for step in steps:
        print(f"Travel from {step.source.pretty_string()} to {step.destination.pretty_string()} by "
              f"{step.travel_mode} ({step.distance} miles; {step.travel_time} days)\n")
        total_time += step.travel_time
    print(f"Total time: {total_time} days")



@attrs
class DirectionsStep:
    source: GeoPoint = attrib(validator=instance_of(GeoPoint))
    destination: GeoPoint = attrib(validator=instance_of(GeoPoint))
    distance: float = attrib(validator=instance_of(float))
    travel_time: float = attrib(validator=instance_of(float))
    travel_mode: TravelMode = attrib(validator=instance_of(TravelMode))
    river_name: Optional[str] = attrib(validator=optional(instance_of(str)),
                                       default=None, kw_only=True)


def _to_canonical_step_sequence(path: Tuple[GeoPoint]) -> Iterable[DirectionsStep]:
    if len(path) < 2:
        raise RuntimeError("Path length cannot be less than 2")
    river_buffer = []
    steps = []

    def should_extend_river_buffer_with(step: DirectionsStep) -> bool:
        is_river_edge = isinstance(step.source, RiverPoint) and isinstance(step.destination, RiverPoint)
        if is_river_edge:
            if not river_buffer:
                return True
            current_river_name = river_buffer[0].river_name if river_buffer else None
            is_from_same_river_as_current_buffer = step.source.river_name == current_river_name and step.destination.river_name == current_river_name
            current_travel_mode = river_buffer[0].travel_mode
            is_same_travel_mode = step.travel_mode == current_travel_mode
            return is_from_same_river_as_current_buffer and is_same_travel_mode
        return False

    def clear_river_buffer():
        if river_buffer:
            steps.append(DirectionsStep(
                river_buffer[0].source,
                river_buffer[-1].destination,
                travel_mode = river_buffer[0].travel_mode,
                distance = sum(step.distance for step in river_buffer),
                travel_time = sum(step.travel_time for step in river_buffer)
            ))
            print(f"Collapsing {len(river_buffer)} segments into {steps[-1]}")

        river_buffer.clear()

    for (i, (segment_source, segment_destination)) in enumerate(windowed(path, 2)):
        edge_attributes = min(waypoint_graph.graph.get_edge_data(segment_source, segment_destination).values(),
                              key=lambda x: x[TIME_ATTRIBUTE])
        step = DirectionsStep(
            segment_source, segment_destination,
            travel_mode=edge_attributes[TRAVEL_MODE],
            distance=edge_attributes[DISTANCE_ATTRIBUTE],
            travel_time=edge_attributes[TIME_ATTRIBUTE],
            river_name=segment_source.river_name if isinstance(segment_source, RiverPoint) else None
        )

        if step.distance == 0:
            continue

        if should_extend_river_buffer_with(step):
            river_buffer.append(step)
        else:
            clear_river_buffer()
            steps.append(step)
    clear_river_buffer()
    return steps


if __name__ == '__main__':
    data_dir = Path(sys.argv[1])

    world_geography = WorldGeography.from_directory(data_dir)
    waypoint_graph = WaypointGraph.create_from(world_geography)

    print(f"Number of connected components: {networkx.number_strongly_connected_components(waypoint_graph.graph)}")

    logging.info("Computing travel times for each segment")
    decorate_with_travel_time_in_place(waypoint_graph.graph, DEFAULT_SPEED_INFO)

    while True:
        print("Enter source city:")
        source_city = world_geography.city_name_to_city[input()]
        print("Enter destination city:")
        destination_city = world_geography.city_name_to_city[input()]

        path = networkx.shortest_path(waypoint_graph.graph, source_city, destination_city,
                                      weight=TIME_ATTRIBUTE)
        pretty_print_path(waypoint_graph.graph, path)



