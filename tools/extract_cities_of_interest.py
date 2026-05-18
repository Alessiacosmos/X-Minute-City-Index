from pathlib import Path

from jsonargparse import auto_cli

import geopandas as gpd
from omegaconf import OmegaConf


def main(
    cities_shapefile: Path,
    cities_of_interest_file: Path,
    save_dir: Path,
) -> None:
    """
    Extract polygons of 'cities of interest' from Urban Audit 2024 and save the results to save_dir.
    Reference(s):
        Urban Audit 2024: https://gisco-services.ec.europa.eu/distribution/v2/urau/urau-2024-metadata.pdf
            (This includes polygons for 739 cities from the European Union, plus Iceland, Norway, and Switzerland.)
    :param cities_shapefile: Path to the shapefile containing city boundaries in Europe.
                             Downlaod from:
                             https://gisco-services.ec.europa.eu/distribution/v2/urau/gpkg/URAU_RG_100K_2024_3035_CITIES.gpkg
                             file example: resources/URAU_RG_100K_2024_3035_CITIES.gpkg
    :param cities_of_interest_file: Path to the city name the user wants to extract.
                                    The file should be .yaml file. Pattern example:
                                    <name_of_country>:
                                         large: [list of large cities in the country]
                                         small: [list of small cities in the country]
                                    file example: configs/explored_cities.yaml
    :param save_dir: Path to the directory saving the extracted city polygons in one.geojson file.
                     e.g. resources/
    :return:
    """

    eu_city_boundaries = gpd.read_file(cities_shapefile)

    cities_of_interest = OmegaConf.load(cities_of_interest_file)
    flatlist_cities_of_interest = []
    for country, city_size_dict in cities_of_interest.items():
        for city_size, city_list in city_size_dict.items():
            flatlist_cities_of_interest.extend(city_list)

    # extract cities of interest
    cities_of_interest_gdf = eu_city_boundaries[
        eu_city_boundaries["URAU_NAME"].isin(flatlist_cities_of_interest)
    ]
    assert len(cities_of_interest_gdf) == len(flatlist_cities_of_interest), (
        f"The number of extracted cities of interest ({len(cities_of_interest_gdf)}) doesn't match "
        f"the number we expected ({len(flatlist_cities_of_interest)}). "
        f"Please check the city names and the shapefile."
    )

    # save
    cities_of_interest_gdf.to_file(
        save_dir / f"{cities_of_interest_file.stem}.gpkg", driver="gpkg"
    )


if __name__ == "__main__":
    auto_cli(main, as_positional=False)
