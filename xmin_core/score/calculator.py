import logging
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
from omegaconf import DictConfig
from rasterstats import gen_zonal_stats

from xmin_core.poi_categories.base import POICatogories, Category
from xmin_core.settings import RasterS3Settings
from xmin_core.utils.data_process import get_population_from_raster_data

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
    reachable_poi_files: dict,
    mode_speeds: dict | DictConfig,
    timeframes: list[int],
    poi_setting: POICatogories,
    savedir: Path,
    is_normalize: bool = True,
):
    # modes = mode_speeds.keys()
    # category_benchmarks = poi_setting.cate_benchmarks()

    # calculate living_normalized
    hex_grids["living_weight"] = (1 / (hex_grids["living"] / 1000)).round(
        2
    )  # population weight: per thousand capita

    # get sum poi counts of each category per mode. # non-normalized poi count result
    scores_per_mode_time: dict[str, list[pd.DataFrame]] = defaultdict(list)
    for name_cate, reachable_poi_1cate_files in reachable_poi_files.items():
        cate_weights = poi_setting.obtain_weights(name_cate)
        poi_cate_setting = poi_setting[name_cate].value

        for reachable_poi_1cate_1mode_file in reachable_poi_1cate_files:
            mode_time = reachable_poi_1cate_1mode_file.parent.stem
            hex_reachable_pois_1cate_1mode = gpd.read_file(
                reachable_poi_1cate_1mode_file
            )

            # todo: process each sub category and count it
            score_cate = score_one_category_by_sub_category_pois(
                hex_reachable_pois_1cate_1mode,
                name_cate,
                poi_cate_setting,
                cate_weights,
                is_normalize,
            )

            scores_per_mode_time[mode_time].append(score_cate)

        # todo: delete below commented part, after finishing the previous func.
        # for mode, mode_poi_cnt_file in reachable_poi_file.items():
        #     # read file
        #     poi_cnt_permode_alltimes = pd.read_pickle(mode_poi_cnt_file)
        #
        #     # normalize
        #     if is_normalize:
        #         # todo: current normalize is based on top-category rather than sub-category.
        #         cate_benchmark = category_benchmarks[name_cate]
        #         if isinstance(cate_benchmark, dict):
        #             cate_benchmark = sum(
        #                 [
        #                     sub_cate_benchmark
        #                     for sub_cate_benchmark in cate_benchmark.values()
        #                 ]
        #             )
        #
        #         summed = poi_cnt_permode_alltimes.T.groupby(level=0).sum().T
        #
        #         normed_poi_cnt_permode_alltimes = normalize_score(
        #             summed, cate_benchmark
        #         )
        #
        #     # add one category_mode_time situation's pois_cnt to corresponding list
        #     normed_poi_cnts[mode][name_cate] = (
        #         normed_poi_cnt_permode_alltimes * sub_cate_weights["parent_weight"]
        #     )

    # get score results: filenum = num_modes (e.g. cycle, foot)
    hex_grids.set_index("hex_id", inplace=True)
    for mode_time, category_scores in scores_per_mode_time.items():
        # sum up all categories' poi counts for per hex, per time, and per mode.
        category_scores = pd.concat(category_scores, axis=1)
        # get total score for every hexagon
        hex_grids["total_score"] = category_scores.filter(like="weighted").sum(axis=1)

        hex_grids["total_score_lively_weighted"] = (
            hex_grids["total_score"] * hex_grids["living_weight"]
        )

        # save result
        savename = savedir / f"{mode_time}" / "score.gpkg"
        hex_grids.to_file(savename, driver="GPKG")


def score_one_category_by_sub_category_pois(
    hex_reachable_pois_1cate_1mode: gpd.GeoDataFrame,
    name_cate: str,
    poi_cate_setting: Category,
    cate_weights: dict,
    is_normalize: bool,
) -> pd.DataFrame:
    # todo: return: hex_id and total score of this category (named as name_cate)

    return pd.DataFrame().set_index("hex_id")
