# X-Minute-City Composite Index

Create your own accessibility analysis for your city and needs!
Forked and improved based on https://github.com/MilenaLang/X-Minute-City-Index.

This repository is used to calculate an accessibility index for x-minute city analysis.


## Relevance
The 15-minute city concept envisions access to all essential services within a 15-minute walk or bike ride.

As accessibility is not equal throughout a city or across cities, a tool to measure pedestrian accessibility is necessary for urban planners and stakeholders to implement the concept.
Existing indices often lack timeframe-adaptability and sufficiency by assuming uniform service needs and POI categories.
Thus, this composite index includes the adaptable timeframe of the x-minute city & support editable POI category settings.

## Methodology
The script uses open-source OpenStreetmap (OSM) Points of Interest (POIs) for amenities and GHSL population data for population density.
POIs for multi categories are fetched via [ohsome API](https://github.com/giscience/ohsome-api) and cleaned for routing.
Small neighborhood units are represented as [h3](https://h3geo.org) hexagonal grid cells of approximately 1km x 1km and filtered to habited areas.
Walking time matrices are generated using [openrouteservice (ORS)](https://openrouteservice.org/) with manual speed adjustments for different mobility mode.

The time matrices are calculated by isochrones of hexagons.
The final index score is the population-weighted sum of normalized scores across categories.


## Usage
The repository now is managed by uv.

1. Fork and clone the repository
2. Init your uv, activate venv and do sync.
2. Set `.env` file (please copy `.env_template` and rename it as `.env`) to access to HeiGIT population data bucket and ORS service.
3. Run the following command:
```shell
# Option 1: you have a vector layer including a series of AOIs you want to analyse
#$ uv run xmin_core/cli.py --aoi_descriptor test/test_data/test_aoi_xmin.geojson  --config_descriptor configs/default.yaml --output_dir experiments/test_aoi/
$ uv run xmin_core/cli.py --aoi_descriptor resources/explored_cities.gpkg --aoi_id_col URAU_CODE --config_descriptor configs/default.yaml --output_dir experiments/test_aoi/

# Option 2: you want to do analysis for a city with given city name
$ uv run python xmin_core/main_xmin.py --city Heidelberg --config configs/default.yaml

# Option 3 if you want to do analysis following ghsl settlement data, I prepared a spefical script for you
$ uv run xmin_core/main_xmin_urcls.py --config configs/default.yaml --output_dir experiments/urcls/
```

## Useful Tools
Under `tools/` folder, you can find some useful tools to prepare your data for the analysis, such as:
```shell
# 1. `extract_cities_of_interest.py`: extract city boundaries from given data for a list of cities.
uv run tools/extract_cities_of_interest.py --cities_shapefile <your_cities_shapefile> --cities_of_interest_file <your_coi_list> --save_dir <your_output_dir>
```

## Acknowledgement
This code is evolved from the original work of Milena Bremer [X-Minute-City-Index](https://github.com/MilenaLang/X-Minute-City-Index)

## Author
[HeiGIT](https://heigit.org/)
[Milena Bremer](https://github.com/MilenaLang/X-Minute-City-Index)

