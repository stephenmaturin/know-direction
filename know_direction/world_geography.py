import logging
from collections import defaultdict
from math import sin, cos, asin, sqrt
from math import radians
from pathlib import Path
from typing import Collection, Optional, Sequence, Mapping, List, Tuple, TypeVar, Generic, Iterable

from attr import attrs, attrib, Factory
from attr.validators import deep_iterable, instance_of, optional
from fastkml import kml
from sklearn.neighbors import BallTree


@attrs(kw_only=True, eq=False)
class GeoPoint:
    latitude: float = attrib(validator=instance_of(float))
    longitude: float = attrib(validator=instance_of(float))
    latitude_radians: float = attrib(init=False)
    longitude_radians: float =attrib(init=False)

    def pretty_string(self) -> str:
        return f"({self.latitude:.2f}, {self.latitude:.2f})"

    def distance_to(self, target: "GeoPoint") -> float:
        """
        From https://stackoverflow.com/a/15737218
        """
        # convert decimal degrees to radians
        lon1, lat1, lon2, lat2 = map(radians, [self.longitude, self.latitude, target.longitude, target.latitude])
        # haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
        c = 2 * asin(sqrt(a))
        # Radius of earth in miles is 3958.8
        return 3958.8 * c

    @latitude_radians.default
    def _init_latitude_radians(self) -> float:
        return radians(self.latitude)

    @longitude_radians.default
    def _init_longitude_radians(self) -> float:
        return radians(self.longitude)


@attrs(kw_only=True, eq=False)
class RiverPoint(GeoPoint):
    river_name: Optional[str] = attrib(validator=optional(instance_of(str)))

    def pretty_string(self) -> str:
        return self.river_name or "Unnamed river"


@attrs(kw_only=True, eq=False)
class River:
    name: Optional[str] = attrib(validator=optional(instance_of(str)))
    points_in_direction_of_water_flow: Sequence[RiverPoint] = attrib(
        validator=deep_iterable(instance_of(RiverPoint))
    )
    start: RiverPoint = attrib(default=Factory(lambda self: self.points_in_direction_of_water_flow[0],
                                               takes_self=True))
    end: RiverPoint = attrib(default=Factory(lambda self: self.points_in_direction_of_water_flow[-1],
                                             takes_self=True))


    @staticmethod
    def load_rivers(river_kml_path: Path) -> Collection["River"]:
        logging.info("Loading rivers from %s", river_kml_path)
        river_kml = load_kml(river_kml_path)

        top_level_features = tuple(river_kml.features())
        if len(top_level_features) != 1:
            raise RuntimeError("Expected a single root document element")

        document_root = top_level_features[0]
        document_children = tuple(document_root.features())

        if len(document_children) != 1:
            raise RuntimeError("Expected a single folder of river")

        river_folder = document_children[0]

        rivers = []

        for river_placemark in river_folder.features():
            river_coordinates = river_placemark.geometry.coords
            if len(river_coordinates) < 2:
                raise RuntimeError("A river must have at least two points")
            river_points = [
                RiverPoint(latitude=latitude, longitude=longitude, river_name=river_placemark.name)
                for (latitude, longitude, _) in river_coordinates
            ]
            rivers.append(River(name=river_placemark.name, points_in_direction_of_water_flow=river_points))

        logging.info("Loaded %s rivers", len(rivers))
        return rivers


@attrs(kw_only=True, eq=False)
class PopulatedPlace(GeoPoint):
    name: str = attrib(validator=instance_of(str))
    population: Optional[int] = attrib(validator=optional(instance_of(int)))

    def pretty_string(self) -> str:
        return self.name

    @staticmethod
    def load_cities(city_kml_path: Path) -> Collection["PopulatedPlace"]:
        logging.info("Loading cities from %s...", city_kml_path)

        city_kml = load_kml(city_kml_path)

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
                                         population=int(population) if population else None,
                                         latitude=latitiude,
                                         longitude=longitude))

        logging.info("Loaded %s cities", len(cities))

        return cities


_T = TypeVar(name="_T", bound=GeoPoint)


@attrs
class GeoPointProximity(Generic[_T]):
    _ball_tree: BallTree = attrib(validator=instance_of(BallTree))
    #_geopoints_by_coordinates: Mapping[Tuple[float, float], List[_T]] = attrib()
    _geopoints = attrib(validator=deep_iterable(instance_of(GeoPoint)))

    @staticmethod
    def create_from(points: Iterable[_T]) -> "GeoPointProximity[_T]":
        geopoints = tuple(points)
        geopoint_coordinates_in_radians = [(point.latitude_radians, point.longitude_radians)
                                           for point in geopoints]

        # geopoints_by_coordinates = defaultdict(list)
        # for point in points:
        #     geopoints_by_coordinates[(point.latitude_radians, point.longitude_radians)].append(point)

        return GeoPointProximity(
            BallTree(data=tuple(geopoint_coordinates_in_radians), metric="haversine"),
            geopoints
        )

    def closest_n_points_to(self, query_point: GeoPoint, num_points: int) -> Collection[_T]:
        query_point_radians = (query_point.latitude_radians, query_point.longitude_radians)
        nearby_point_indices = self._ball_tree.query([query_point_radians], k=num_points,
                                              return_distance=False)
        return tuple(self._geopoints[idx] for idx in nearby_point_indices[0])


@attrs
class WorldGeography:
    cities: Collection[PopulatedPlace] = attrib(validator=deep_iterable(instance_of(PopulatedPlace)))
    rivers: Collection[River] =attrib(validator=deep_iterable(instance_of(River)))
    city_name_to_city: Mapping[str, PopulatedPlace] = attrib(init=False)
    city_kd_tree: GeoPointProximity[PopulatedPlace] = attrib(
        init=False,
        default = Factory(lambda self: GeoPointProximity.create_from(self.cities), takes_self=True))
    river_endpoints_kd_tree: GeoPointProximity[RiverPoint] = attrib(init=False)

    @staticmethod
    def from_directory(data_directory: Path) -> "WorldGeography":
        return WorldGeography(cities=PopulatedPlace.load_cities(data_directory / "golarion_city.kml"),
                              rivers=River.load_rivers(data_directory / "innersea_rivers.kml"))

    @city_name_to_city.default
    def _init_city_name_to_city(self) -> Mapping[str, PopulatedPlace]:
        return {
            city.name : city for city in self.cities
        }

    @river_endpoints_kd_tree.default
    def _init_river_endpoint_kd_tree(self) -> GeoPointProximity:
        return GeoPointProximity.create_from(
            [river.start for river in self.rivers] + [river.end for river in self.rivers])


def load_kml(city_kml_path: Path) -> kml.KML:
    raw_city_kml = city_kml_path.read_text(encoding="utf-8")
    city_kml = kml.KML()
    city_kml.from_string(raw_city_kml.encode(encoding="utf-8"))
    return city_kml


