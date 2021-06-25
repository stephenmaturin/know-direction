from enum import Enum, auto

from attr import attrs, attrib
from attr.validators import instance_of


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
upstream_speed_in_miles_per_day = 15.0,
downstream_speed_in_miles_per_day=40.0
)


NORMAL_SEA = SeaSpeedInfo(
seas_speed_in_miles_per_day = 100.0
)

DEFAULT_SPEED_INFO = SpeedInfo(
    overland_speeds = ON_FOOT,
    river_speeds=NORMAL_RIVER,
    sea_speeds=NORMAL_SEA
)
