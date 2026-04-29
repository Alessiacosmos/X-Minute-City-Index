import argparse
import os
from pathlib import Path

import geopandas as gpd
from pyproj import CRS
from shapely import Polygon, MultiPolygon

from xmin_core.cli import xmin_index
from xmin_core.settings import RasterS3Settings, ORSSettings
from xmin_core.utils.data_process import get_hex_grids
from xmin_core.pois.reachable_pois import get_reachable_poi_cnt_categories
from xmin_core.utils.utils import MAX_BUFFER_DISTANCE
from xmin_core.score.calculator import (
    get_city_pois_categories,
    get_population_info_hex_grids,
    get_xmin_index_score,
)



def main_xmin_urcls(
    config_descriptor: Path,
    workdir: Path
):

    ##########
    # 1. get basic geometry data: aois in urcls data & create buffer for max distance based on mode and timeframe
    ##########
    # 1.1 get aois
    urcls_path = workdir / 'urcls_4229_int_poly' / 'urcls_4229_int_poly.shp'

    xmin_index(
        aoi_descriptor=urcls_path,
        config_descriptor=config_descriptor,
        output_dir=workdir,
    )


def parser_args():
    parser = argparse.ArgumentParser(description="XMin city composite index")
    parser.add_argument(
        "--config-descriptor",
        type=str,
        default='./configs/default.yaml',
        help="config file path",
    )
    parser.add_argument(
        "--workdir",
        type=str,
        default='./experiments/urcls',
        help="work directory which saves GHSL settlement AOIs and will save all results.",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parser_args()

    main_xmin_urcls(Path(args.config_descriptor), Path(args.workdir))

