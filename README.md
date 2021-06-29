## Purpose

To compute travel routes and times for RPG settings.
Currently, this is hard-coded for the Golarion setting for Pathfinder,
but it is easy to extend.

## Usage (Pathfinder)

1. From the [Dungeonetics Golarion Geography site](https://dungeonetics.com/golarion-geography/datalayers.html) download the KML files for:
  * Golarion Cities
  * Golarion Continents
  * Golarion Points of Interest
  * Inner Sea Rivers
  * Inner Sea Water Bodies
2. Put these all in a directory.
3. Install [Poetry](https://python-poetry.org/docs/)
4. `poetry run python -m know_direction.find_directions <directory_where_you_downloaded_kml_files`

It will ask you for the name of your starting and destination cities
and will give you the route between them with travel times.

## Limitations

* The software currently supports configurable travel speeds
but does not expose this configuration to the user.
* The software is completely oblivious of the sea: it neither stops you from traveling overland across the sea nor support more rapid sea travel.

## Contact

`maturinydomonova@gmail.com`
