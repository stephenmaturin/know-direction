import logging
from typing import Collection

import networkx
from attr import attrib, attrs
from attr.validators import instance_of
from more_itertools import windowed

from know_direction.travel_speed import TravelMode
from know_direction.world_geography import WorldGeography, PopulatedPlace, River


@attrs
class WaypointGraph:
    graph: networkx.MultiDiGraph = attrib(validator=instance_of(networkx.MultiDiGraph))

    @staticmethod
    def create_from(world_geography: WorldGeography) -> "WaypointGraph":
        waypoint_graph = networkx.MultiDiGraph()

        waypoint_graph.add_nodes_from(world_geography.cities)

        logging.info("Connecting river waypoints")
        WaypointGraph._build_waypoints_from_rivers(world_geography.rivers, waypoint_graph)

        logging.info("Adding city-to-city connections")
        WaypointGraph._add_city_to_city_connections(world_geography, waypoint_graph)

        logging.info("Adding connections between rivers and rivers")
        WaypointGraph._add_river_to_river_connections(world_geography=world_geography,
                                                      waypoint_graph=waypoint_graph)

        logging.info("Adding connections between rivers and cities")
        WaypointGraph._add_city_river_connections(world_geography=world_geography,
                                                  waypoint_graph=waypoint_graph)
        return WaypointGraph(waypoint_graph)


    @staticmethod
    def add_overland_connection(point1, point2, waypoint_graph):
        distance_between_cities = point1.distance_to(point2)
        waypoint_graph.add_edge(point1, point2, distance=distance_between_cities,
                                travel_mode=TravelMode.OVERLAND)
        waypoint_graph.add_edge(point2, point1, distance=distance_between_cities,
                                travel_mode=TravelMode.OVERLAND)

    @staticmethod
    def _add_city_to_city_connections(world_geography: WorldGeography,
                                      waypoint_graph: networkx.DiGraph) -> None:
        # We connect each city to the 30 closest cities
        for city in world_geography.cities:
            for other_city in world_geography.city_proximity.closest_n_points_to(city, 30):
                if city != other_city:
                    WaypointGraph.add_overland_connection(city, other_city, waypoint_graph)


    @staticmethod
    def _add_city_river_connections(*, world_geography: WorldGeography,
                                   waypoint_graph: networkx.DiGraph) -> None:
        for city in world_geography.cities:
            # We connect each city to the 30 closest river end points
            for river_end_point in world_geography.river_endpoints_proximity.closest_n_points_to(city, 30):
                WaypointGraph.add_overland_connection(city, river_end_point, waypoint_graph)
        for river in world_geography.rivers:
            for river_end_point in (river.start, river.end):
                # For each river endpoint, we connect it to its closest 30 cities
                for city in world_geography.city_proximity.closest_n_points_to(river_end_point, 30):
                    WaypointGraph.add_overland_connection(city, river_end_point, waypoint_graph)

    @staticmethod
    def _add_river_to_river_connections(*,
                                        waypoint_graph: networkx.DiGraph,
                                        world_geography: WorldGeography) -> None:
        for river in world_geography.rivers:
            # We connect each river endpoint to its 10 closest other river endpoints,
            # at most one of which can be from the same river
            for other_river_endpoint in world_geography.river_endpoints_proximity.closest_n_points_to(river.start, 10):
                WaypointGraph.add_overland_connection(river.start, other_river_endpoint, waypoint_graph)
            for other_river_endpoint in world_geography.river_endpoints_proximity.closest_n_points_to(river.end, 10):
                WaypointGraph.add_overland_connection(river.end, other_river_endpoint, waypoint_graph)

    @staticmethod
    def _build_waypoints_from_rivers(rivers: Collection[River], waypoint_graph: networkx.DiGraph) -> None:
        for river in rivers:
            waypoint_graph.add_nodes_from(river.points_in_direction_of_water_flow)
            for (river_segment_source, river_segment_destination) in windowed(river.points_in_direction_of_water_flow, 2):
                segment_distance = river_segment_source.distance_to(river_segment_destination)
                waypoint_graph.add_edge(
                    river_segment_source, river_segment_destination, travel_mode=TravelMode.DOWNSTREAM,
                    distance=segment_distance)
                waypoint_graph.add_edge(
                    river_segment_destination, river_segment_source, travel_mode=TravelMode.UPSTREAM,
                    distance=segment_distance)



