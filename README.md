# X-Minute-City Composite Index

Reproductive accessibility scoring tool for your area of interest (AOI).
Forked and improved based on https://github.com/MilenaLang/X-Minute-City-Index.


## Relevance
The 15-minute city concept envisions access to all essential services within a 15-minute walk or bike ride.

As accessibility is not equal throughout a city or across cities,
a tool to measure active accessibility (active means active mobility) is necessary for urban planners and stakeholders to implement the concept.
Existing indices often lack time threshold-adaptability and sufficiency by assuming uniform service needs and POI categories.
Thus, this composite index includes the adaptable travel mode and time threshold of the x-minute city & support editable POI category settings.

## Methodology
The tool follows hexagon-based accessibility scoring method. In detail,
an AOI is firstly gridded as hexagons ([h3](https://h3geo.org)) of approximately 1km x 1km;
then, its Point of Interests (POIs) for multi categories are fetched through [ohsome API](https://github.com/giscience/ohsome-api).
Subsequently, the accessibility score of each hexagon is calculated based on the aggregated POI features (count/area ratio with weights) in its corresponding isochrones ([openrouteservice (ORS)](https://openrouteservice.org/)),
where the isochrone is calculated based on specified travel mode and time threshold.
City-level score is calculated based on accessibility scores across hexagons and weighted by population.

### Data sources
1. POI data: [OpenStreetMap](https://www.openstreetmap.org/)
2. Population data: [GHS-POP dataset](https://data.jrc.ec.europa.eu/dataset/2ff68a52-5b5b-4a22-8f40-c41da8332cfe)

## Usage
The repository is managed by uv.

1. Fork and clone the repository, and install uv following https://docs.astral.sh/uv/getting-started/installation/
2. Install it by running the following command
```shell
$ uv sync # --extra dev
```
3. Set `.env` file (please copy `.env_template` and rename it as `.env`) to access to HeiGIT population data bucket and ORS service.
4. Run the following command:
```shell
# You have a vector layer including a series of AOIs you want to analyse accessibility
$ uv run xmin_core/cli.py --aoi_descriptor resources/explored_cities.gpkg --aoi_id_col URAU_CODE --config_descriptor configs/default.yaml --output_dir experiments/test_aoi/

# Scoring accessibility plus data quality by mapping saturation
$ uv run xmin_core/cli.py --aoi_descriptor resources/explored_cities.gpkg --aoi_id_col URAU_CODE --config_descriptor configs/default.yaml --output_dir experiments/test_aoi/ --activated_funcs=['accessibility', 'quality'] --quality_indicators=['map_saturation']
```

### Configuration based on your needs
The following parameters are configurable:
1. travel modes
2. travel time thresholds
3. analysis resolution
4. all POI settings (categories, weights, and benchmarks)

***How to***

To cutomize these configs, create your own `config.yaml` file under `configs` folder (e.g. *default.yaml*)
Parameters 1-3 can easily and directly configure at the yaml file, while the 4 (POI settings) are a little bit more complex.

***How to configure your own POI settings***

1. create a POI setting file at `xmin_core/poi_categories` (e.g. naming it as `<your_POI_config_file>.py`)
2. customize your settings as a class (e.g. `class <your_POI_config_class>`), including categories, and category weights and benchmarks. (reference: *two_levels.py* v.s. *sp_healthcare.py*)
3. register the new class at `xmin_core/poi_categories/__init__.py`
```python
# example
from xmin_core.poi_categories.<your_POI_config_file> import <your_POI_config_class>

category_settings = {
    "simple": SimpleFacilitiesCategories,
    "two_level": TwoLvlFacilitiesCategories,
    "healthcare_de": DEHealthCareCategories,
    "healthcare_nl": NLHealthCareCategories,
    "healthcare_es": ESHealthCareCategories,
    ###### --- your new setting ----------------------
    "<your_POI_setting_register_name>": <your_POI_config_class>
    ###### --- your new setting ----------------------

}
```
4. use the registered new POI settings at `config.yaml` (`<your_POI_setting_register_name>`)


## Useful Tools
Under `tools/` folder, you can find some useful tools to prepare your data for the analysis, such as:
```shell
# 1. `extract_cities_of_interest.py`: extract city boundaries from given data for a list of cities.
uv run tools/extract_cities_of_interest.py --cities_shapefile <your_cities_shapefile> --cities_of_interest_file <your_coi_list> --save_dir <your_output_dir>
```

## Dev Tips
1. Currently, please do everything at `refactor` branch. Once the code is stable, we will merge it to `main` branch.

## Take care!
Here an known issue for batched isochrone calculation -
if your AOI covers region unreachable (e.g. sea, deep forest, etc.), the isochrone cannot be calculated correctly and will trigger an error (3099, cannot calculate isochrone) for entire batch.
E.g., you're calculating 10 hexagons' isochrones in one batch, and one of them is unreachable, the entire batch will fail.
In such case, these hexagons will be skipped and the failed hexagon id will be saved, and you can re-run the isochrone calculation for the failed hexagons only one by one later.

## Acknowledgement
This code is evolved from the original work of Milena Bremer [X-Minute-City-Index](https://github.com/MilenaLang/X-Minute-City-Index)

## License
[GNU v3](LICENSE)

## Author
[HeiGIT](https://heigit.org/)
[Milena Bremer](https://github.com/MilenaLang/X-Minute-City-Index)

