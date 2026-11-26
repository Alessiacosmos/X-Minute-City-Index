from pathlib import Path

import geopandas as gpd


def extract_subset_cities(
    cities_shapefile: Path,
    cities_of_interested_list: dict[str, list[str] | str],
    output_dir: Path,
):
    explored_city_boundaries = gpd.read_file(cities_shapefile)

    for country, city_list in cities_of_interested_list.items():
        if isinstance(city_list, str) and city_list == "all":
            subset_cities_gdf = explored_city_boundaries[
                explored_city_boundaries["CNTR_CODE"] == country
            ]
        else:
            city_list = [city_list] if isinstance(city_list, str) else city_list
            subset_cities_gdf = explored_city_boundaries[
                explored_city_boundaries["URAU_NAME"].isin(city_list)
            ]
            assert len(subset_cities_gdf) == len(city_list), (
                f"The number of extracted cities ({len(subset_cities_gdf)}) doesn't match "
                f"the number we expected ({len(city_list)}). "
                f"Please check the city names and the shapefile."
            )

        # save
        output_dir.mkdir(parents=True, exist_ok=True)
        subset_cities_gdf.to_file(output_dir / f"{country}_subset.gpkg", driver="gpkg")


if __name__ == "__main__":
    explored_cities = {
        "DE": "all",  # ["Berlin"],
        "ES": "all",  # ["Madrid"],
        "NL": "all",  # ["Amsterdam"],
    }  # capitals of three countries

    cities_shapefile = Path("resources/explored_cities_random.gpkg")
    output_dir = Path("resources/healthcare_case")

    extract_subset_cities(cities_shapefile, explored_cities, output_dir)
