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
    graph: networkx.DiGraph = attrib(validator=instance_of(networkx.DiGraph))

    @staticmethod
    def create_from(world_geography: WorldGeography) -> "WaypointGraph":
        waypoint_graph = networkx.DiGraph()

        waypoint_graph.add_nodes_from(world_geography.cities)

        logging.info("Connecting river waypoints")
        WaypointGraph._build_waypoints_from_rivers(world_geography.rivers, waypoint_graph)

        logging.info("Adding city-to-city connections")
        WaypointGraph._add_city_to_city_connections(world_geography.cities, waypoint_graph)

        logging.info("Adding connections between rivers and rivers")
        WaypointGraph._add_river_to_river_connections(world_geography.rivers, waypoint_graph)

        logging.info("Adding connections between rivers and cities")
        WaypointGraph._add_city_river_connections(cities=world_geography.cities, rivers=world_geography.rivers,
                                                  waypoint_graph=waypoint_graph)

    @staticmethod
    def _add_city_to_city_connections(cities: Collection[PopulatedPlace], waypoint_graph: networkx.DiGraph) -> None:
        for city in cities:
            for other_city in cities:
                if city != other_city:
                    distance_between_cities = city.distance_to(other_city)
                    waypoint_graph.add_edge(city, other_city, distance=distance_between_cities,
                                            travel_mode=TravelMode.OVERLAND)
                    waypoint_graph.add_edge(other_city, city, distance=distance_between_cities,
                                            travel_mode=TravelMode.OVERLAND)

    @staticmethod
    def _add_city_river_connections(*, cities: Collection[PopulatedPlace],
                                   rivers: Collection[River],
                                   waypoint_graph: networkx.DiGraph) -> None:
        for city in cities:
            for river in rivers:
                closest_point_on_river = min(
                    river.points_in_direction_of_water_flow, key=city.distance_to)
                distance_to_closest_point = city.distance_to(closest_point_on_river)

                waypoint_graph.add_edge(city, closest_point_on_river, distance=distance_to_closest_point,
                                        travel_mode=TravelMode.OVERLAND)
                waypoint_graph.add_edge(closest_point_on_river, city, distance=distance_to_closest_point,
                                        travel_mode=TravelMode.OVERLAND)


    @staticmethod
    def _add_river_to_river_connections(rivers: Collection[River], waypoint_graph: networkx.DiGraph) -> None:
        for river1 in rivers:
            for river2 in rivers:
                if river1 != river2:
                    (closest_point_on_river1, closest_point_on_river2) = min(
                        [(river1_point, river2_point)
                         for river1_point in river1.points_in_direction_of_water_flow
                         for river2_point in river2.points_in_direction_of_water_flow],
                        key=lambda p1p2: p1p2[0].distance_to(p1p2[1])
                    )
                    distance_between_rivers = closest_point_on_river1.distance_to(closest_point_on_river2)
                    waypoint_graph.add_edge(closest_point_on_river1, closest_point_on_river2,
                                            distance=distance_between_rivers,
                                            travel_mode=TravelMode.OVERLAND)
                    waypoint_graph.add_edge(closest_point_on_river2, closest_point_on_river1,
                                            distance=distance_between_rivers,
                                            travel_mode=TravelMode.OVERLAND)

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



