import argparse
from pathlib import Path

import geopandas as gpd

from xmin_core.settings import RasterS3Settings, ORSSettings
from xmin_core.utils.data_process import get_city_bboxes, get_hex_grids
from xmin_core.utils.reachable_pois import get_reachable_poi_cnt_categories
from xmin_core.utils.utils import MAX_BUFFER_DISTANCE
from xmin_core.utils.xmin_calc import (
    get_city_pois_categories,
    get_population_info_hex_grids,
    get_xmin_index_score,
)


def parser_args():
    parser = argparse.ArgumentParser(description="XMin city composite index")
    parser.add_argument(
        "--city",
        type=str,
        required=True,
        help="City name you want to analyze.",
    )
    return parser.parse_args()


def main_xmin(city_name: str, raster_s3_settings: RasterS3Settings, ors_settings: ORSSettings):
    savedir = Path('./experiments')
    ##########
    # 1. get basic geometry data: bboxes for each mode and timeframe; hex_grids
    ##########
    # 1.1 get buffered bounding boxes for each mode and timeframe
    city_polygon, est_utm_crs = get_city_bboxes(city_name) # pd.DataFrame, columns: minx, miny, maxx, maxy, mode, timeframe

    # 1.2 generate hex grids for each mode and timeframe
    hex_grids = get_hex_grids(city_polygon)
    if hex_grids is None:
        return

    ##########
    # 2. map population and poi information to hex grids
    ##########
    # 2.1 get pois for different categories within each mode and timeframe bbox
    buffered_city_polygon = (
        gpd.GeoSeries(city_polygon.union_all(), crs=city_polygon.crs)
        .to_crs(est_utm_crs)
        .buffer(MAX_BUFFER_DISTANCE)
        .to_crs(4326)
        .geometry.iloc[0]
    )
    pois_dir = savedir / 'pois'
    pois_dir.mkdir(parents=True, exist_ok=True)
    city_pois_cates_files = get_city_pois_categories(buffered_city_polygon, est_utm_crs, pois_dir)

    # 2.2 assign population to hex grid. attr: Living
    hex_grids = get_population_info_hex_grids(raster_s3_settings, hex_grids, city_polygon)

    # 2.3 get reachable poi counts for each categories, mode, and timeframe.
    pois_cnt_cates_files = get_reachable_poi_cnt_categories(
        ors_settings, hex_grids, city_pois_cates_files, est_utm_crs, savedir
    )

    # 2.4 get score
    get_xmin_index_score(hex_grids, pois_cnt_cates_files, savedir, is_normalize=True)



if __name__ == "__main__":
    args = parser_args()
    city_name = args.city
    print(f"Analyzing data for city: {city_name}")

    # initialize settings
    raster_s3_settings = RasterS3Settings()
    ors_settings = ORSSettings()

    main_xmin(city_name, raster_s3_settings, ors_settings)

