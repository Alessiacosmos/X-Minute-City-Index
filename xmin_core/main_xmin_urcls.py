import argparse
import os
from pathlib import Path

import geopandas as gpd
from pyproj import CRS
from shapely import Polygon, MultiPolygon

from xmin_core.settings import RasterS3Settings, ORSSettings
from xmin_core.utils.data_process import get_city_bboxes, get_hex_grids
from xmin_core.utils.reachable_pois import get_reachable_poi_cnt_categories
from xmin_core.utils.utils import MAX_BUFFER_DISTANCE
from xmin_core.utils.xmin_calc import (
    get_city_pois_categories,
    get_population_info_hex_grids,
    get_xmin_index_score,
)


def main_xmin_one_aoi(
    aoi: gpd.GeoSeries | Polygon | MultiPolygon,
    org_crs: CRS,
    raster_s3_settings: RasterS3Settings,
    ors_settings: ORSSettings,
    workdir:Path
):
    ##########
    # 1. get basic geometry data: polygon + crs; hex_grids
    ##########
    # 1.1 get polygon's aoi
    aoi = gpd.GeoDataFrame(aoi.to_frame().T, geometry='geometry', crs=org_crs)

    est_utm_crs = aoi.estimate_utm_crs()

    # 1.2 generate hex grids for each mode and timeframe
    hex_grids = get_hex_grids(aoi)
    if hex_grids is None:
        return

    ##########
    # 2. map population and poi information to hex grids
    ##########
    # 2.1 get pois for different categories within each mode and timeframe bbox
    buffered_aoi = (
        gpd.GeoSeries(aoi.union_all(), crs=aoi.crs)
        .to_crs(est_utm_crs)
        .buffer(MAX_BUFFER_DISTANCE)
        .to_crs(4326)
        .geometry.iloc[0]
    )
    pois_dir = workdir / 'pois'
    pois_dir.mkdir(parents=True, exist_ok=True)
    city_pois_cates_files = get_city_pois_categories(buffered_aoi, est_utm_crs, pois_dir)

    # 2.2 assign population to hex grid. attr: Living
    hex_grids = get_population_info_hex_grids(raster_s3_settings, hex_grids, aoi)

    # 2.3 get reachable poi counts for each categories, mode, and timeframe.
    pois_cnt_cates_files = get_reachable_poi_cnt_categories(
        ors_settings, hex_grids, city_pois_cates_files, est_utm_crs, workdir
    )

    # 2.4 get score
    get_xmin_index_score(hex_grids, pois_cnt_cates_files, workdir, is_normalize=True)


def main_xmin_urcls(raster_s3_settings: RasterS3Settings, ors_settings: ORSSettings, workdir: Path):

    ##########
    # 1. get basic geometry data: aois in urcls data & create buffer for max distance based on mode and timeframe
    ##########
    # 1.1 get aois
    urcls_path = os.path.join(workdir, 'urcls_4229_int_poly', 'urcls_4229_int_poly.shp')
    urcls_aois = gpd.read_file(urcls_path)
    urcls_aois = urcls_aois.to_crs(4326)
    org_crs = urcls_aois.crs

    ##########
    # 2. execute accessibility calculation for every aoi
    ##########
    for idx, aoi in urcls_aois.iterrows():
        main_xmin_one_aoi(aoi, org_crs, raster_s3_settings, ors_settings, workdir)

def parser_args():
    parser = argparse.ArgumentParser(description="XMin city composite index")
    parser.add_argument(
        "--workdir",
        type=str,
        default='./experiments',
        help="work directory which saves GHSL settlement AOIs and will save all results.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parser_args()

    raster_s3_settings = RasterS3Settings()
    ors_settings = ORSSettings()
    main_xmin_urcls(raster_s3_settings, ors_settings, Path(args.workdir))

