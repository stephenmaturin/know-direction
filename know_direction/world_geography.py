import logging
from math import sin, cos, asin, sqrt
from math import radians
from pathlib import Path
from typing import Collection, Optional, Sequence, Mapping

from attr import attrs, attrib
from attr.validators import deep_iterable, instance_of, optional
from fastkml import kml


@attrs(kw_only=True, eq=False)
class GeoPoint:
    latitude: float = attrib(validator=instance_of(float))
    longitude: float = attrib(validator=instance_of(float))

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


@attrs
class WorldGeography:
    cities: Collection[PopulatedPlace] = attrib(validator=deep_iterable(instance_of(PopulatedPlace)))
    rivers: Collection[River] =attrib(validator=deep_iterable(instance_of(River)))
    city_name_to_city: Mapping[str, PopulatedPlace] = attrib(init=False)

    @staticmethod
    def from_directory(data_directory: Path) -> "WorldGeography":
        return WorldGeography(cities=PopulatedPlace.load_cities(data_directory / "golarion_city.kml"),
                              rivers=River.load_rivers(data_directory / "innersea_rivers.kml"))

    def _init_city_name_to_city(self) -> Mapping[str, PopulatedPlace]:
        return {
            city.name : city for city in self.cities
        }



def load_kml(city_kml_path: Path) -> kml.KML:
    raw_city_kml = city_kml_path.read_text(encoding="utf-8")
    city_kml = kml.KML()
    city_kml.from_string(raw_city_kml.encode(encoding="utf-8"))
    return city_kml


