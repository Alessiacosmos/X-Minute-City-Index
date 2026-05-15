import logging
from pathlib import Path

import geopandas as gpd
import pandas as pd
from omegaconf import DictConfig
from rasterstats import gen_zonal_stats

from xmin_core.poi_categories.base import POICatogories
from xmin_core.settings import RasterS3Settings
from xmin_core.utils.data_process import get_population_from_raster_data
from xmin_core.utils.utils import (
    normalize_score,
)

log = logging.getLogger(__name__)


def get_population_info_hex_grids(
    raster_s3_settings: RasterS3Settings,
    hexagons: gpd.GeoDataFrame,
    city_polygon: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    ##################
    # 1. get population raster clipped to city bbox
    ##################
    pops_city_raster = get_population_from_raster_data(
        raster_s3_settings, city_polygon, city_polygon.crs.to_epsg()
    )

    ##################
    # 2. aggregate population to hex grids
    # note: weighted_population is not necessary as population's resolution is better than hexagon size.
    ##################
    hexagons_crs = hexagons.crs
    stats = gen_zonal_stats(
        hexagons.to_crs(pops_city_raster["src_crs"]),
        pops_city_raster["clipped_raster"],
        affine=pops_city_raster["transform"],
        stats=["sum"],
        all_touched=True,
    )
    hexagons["living"] = [s["sum"] for s in stats]

    return hexagons.to_crs(hexagons_crs)


def get_xmin_index_score(
    hex_grids: gpd.GeoDataFrame,
    pois_cnt_cates_files: dict,
    mode_speeds: dict | DictConfig,
    poi_setting: POICatogories,
    savedir: Path,
    is_normalize: bool = True,
):
    modes = mode_speeds.keys()
    category_benchmarks = poi_setting.cate_benchmarks()

    savedir = savedir / "index_score"
    savedir.mkdir(exist_ok=True)

    # calculate living_normalized
    hex_grids["living_weight"] = (1 / (hex_grids["living"] / 1000)).round(
        2
    )  # population weight: per thousand capita

    # get sum poi counts of each category per mode. # non-normalized poi count result
    normed_poi_cnts = {mode: dict() for mode in modes}  # normalized
    for name_cate, cate_poi_cnt_files in pois_cnt_cates_files.items():
        sub_cate_weights = poi_setting.obtain_weights(name_cate)
        for mode, mode_poi_cnt_file in cate_poi_cnt_files.items():
            # read file
            poi_cnt_permode_alltimes = pd.read_pickle(mode_poi_cnt_file)

            # normalize
            if is_normalize:
                # todo: current normalize is based on top-category rather than sub-category.
                cate_benchmark = category_benchmarks[name_cate]
                if isinstance(cate_benchmark, dict):
                    cate_benchmark = sum(
                        [
                            sub_cate_benchmark
                            for sub_cate_benchmark in cate_benchmark.values()
                        ]
                    )

                summed = poi_cnt_permode_alltimes.T.groupby(level=0).sum().T

                normed_poi_cnt_permode_alltimes = normalize_score(
                    summed, cate_benchmark
                )

            # add one category_mode_time situation's pois_cnt to corresponding list
            normed_poi_cnts[mode][name_cate] = (
                normed_poi_cnt_permode_alltimes * sub_cate_weights["parent_weight"]
            )

    # get score results: filenum = num_modes (e.g. cycle, foot)
    for mode, normed_poi_cnt_permode in normed_poi_cnts.items():
        # sum up all categories' poi counts for per time, per hex, and per mode.
        normed_poi_cnt_permode: pd.DataFrame = (
            sum(normed_poi_cnt_permode.values()) / len(normed_poi_cnt_permode)
        ).multiply(
            hex_grids["living_weight"], axis=0
        )  # TODO: check why it's .mean in original code.
        hex_scores_permode = hex_grids.merge(
            normed_poi_cnt_permode, on="hex_id", how="left"
        )

        # save result
        savename = savedir / f"{mode}_score.gpkg"
        hex_scores_permode.to_file(savename, driver="GPKG")
