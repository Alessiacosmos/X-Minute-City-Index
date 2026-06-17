import logging
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import pandas as pd
from omegaconf import DictConfig
from pyproj import CRS
from rasterstats import gen_zonal_stats

from xmin_core.poi_categories.base import POICatogories
from xmin_core.settings import RasterS3Settings
from xmin_core.utils.data_process import get_population_from_raster_data
from xmin_core.utils.utils import normalize_score

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
):
    # modes = mode_speeds.keys()
    # category_benchmarks = poi_setting.cate_benchmarks()
    est_utm_crs = hex_grids.estimate_utm_crs()

    # calculate living_normalized
    hex_grids["living_weight"] = (1 / (hex_grids["living"] / 1000)).round(
        2
    )  # population weight: per thousand capita

    # get sum poi counts of each category per mode. # non-normalized poi count result
    scores_per_mode_time: dict[str, list[pd.DataFrame]] = defaultdict(list)
    for name_cate, reachable_poi_1cate_files in reachable_poi_files.items():
        cate_weights_benchmarks = poi_setting.obtain_weights_and_benchmarks(name_cate)
        # poi_cate_setting = poi_setting[name_cate].value

        for reachable_poi_1cate_1mode_file in reachable_poi_1cate_files:
            mode_time = reachable_poi_1cate_1mode_file.parent.stem
            hex_reachable_pois_1cate_1mode = gpd.read_file(
                reachable_poi_1cate_1mode_file
            )

            score_cate = score_hexagons_one_category(
                hex_reachable_pois_1cate_1mode=hex_reachable_pois_1cate_1mode,
                name_cate=name_cate,
                cate_weights_benchmarks=cate_weights_benchmarks,
                est_utm_crs=est_utm_crs,
                poi_filepath=savedir / "pois" / f"pois_pts_{name_cate}.gpkg",
            )

            scores_per_mode_time[mode_time].append(score_cate)

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
        savename = savedir / "scores" / f"{mode_time}" / "score.gpkg"
        hex_grids.to_file(savename, driver="GPKG")


def score_hexagons_one_category(
    hex_reachable_pois_1cate_1mode: gpd.GeoDataFrame,
    name_cate: str,
    cate_weights_benchmarks: dict,
    est_utm_crs: CRS,
    poi_filepath: Path,
) -> pd.DataFrame:
    parent_weight, sub_weights_benchmarks = (
        cate_weights_benchmarks["parent_weight"],
        cate_weights_benchmarks["sub_weights_benchmarks"],
    )

    hex_scores = []
    for hex_id, hex_group in hex_reachable_pois_1cate_1mode.groupby("hex_id"):
        hex_score = dict()
        hex_score["hex_id"] = hex_id

        # todo: using a totally different logic when name_cate is nature_space
        if name_cate == "nature_space":
            hex_score[name_cate] = score_one_hex_nature_space_by_area(
                hex_group,
                sub_weights_benchmarks,
                est_utm_crs=est_utm_crs,
                poi_filepath=poi_filepath,
            )
        else:
            hex_score[name_cate] = score_one_hex_one_category_by_sub_category_pois(
                hex_group, sub_weights_benchmarks
            )
            hex_score[f"{name_cate}_weighted"] = hex_score[name_cate] * parent_weight
        hex_scores.append(hex_score)

    hex_scores = pd.DataFrame(hex_scores)

    return hex_scores.set_index("hex_id")


def score_one_hex_one_category_by_sub_category_pois(
    one_hex_reachable_pois: gpd.GeoDataFrame,
    sub_weights_benchmarks: dict,
) -> float:
    cate_score = 0
    for sub_cate, sub_weight_benchmark in sub_weights_benchmarks.items():
        sub_pois = one_hex_reachable_pois[
            one_hex_reachable_pois["sub_category"] == sub_cate
        ]
        sub_poi_num = len(sub_pois)
        if "benchmark" in sub_weight_benchmark:
            sub_score = (
                normalize_score(
                    value=sub_poi_num, benchmark=sub_weight_benchmark["benchmark"]
                )
                * sub_weight_benchmark["weight"]
            )
        elif "group" in sub_weight_benchmark:
            group_sub_score = 0
            for (
                group_sub_cate,
                group_sub_weight_benchmark,
            ) in sub_weights_benchmarks.items():
                group_sub_score += (
                    normalize_score(
                        value=sub_poi_num, benchmark=sub_weight_benchmark["benchmark"]
                    )
                    * group_sub_weight_benchmark["weight"]
                )
            sub_score = min(100, group_sub_score)
        else:
            raise NotImplementedError(
                f"sub category {sub_cate} with {sub_weights_benchmarks} not implemented."
            )

        cate_score += sub_score

    return cate_score


def score_one_hex_nature_space_by_area(
    one_hex_reachable_pois: gpd.GeoDataFrame,
    sub_weights_benchmarks: dict,
    est_utm_crs: CRS,
    poi_filepath: Path,
) -> float:
    default_nature_space_area = 40

    # pre-process hex isochrone and pois
    isochrone = (
        one_hex_reachable_pois.iloc[[0]].to_crs(crs=est_utm_crs).iloc[0].geometry
    )

    pois = gpd.read_file(poi_filepath)
    pois_in_iso = pois.loc[one_hex_reachable_pois["index_right"].values]

    pois_in_iso["area"] = default_nature_space_area
    for geom_type in pois_in_iso.geometry.type.unique():
        match geom_type:
            case "MultiPolygon" | "Polygon" | "GeometryCollection":
                pois_in_iso = pois_in_iso.clip(isochrone)

                is_type = pois_in_iso.geom_type == geom_type
                pois_in_iso.loc[is_type, "area"] = pois_in_iso[is_type].area

                too_small_geom = (
                    pois_in_iso.loc[is_type, "area"] < default_nature_space_area
                )
                pois_in_iso.loc[too_small_geom, "area"] = 0
            case _:
                continue

    pois_area_in_iso_ratio = pois_in_iso["area"].sum() / isochrone.area

    return normalize_score(
        value=pois_area_in_iso_ratio,
        benchmark=sub_weights_benchmarks["all"]["benchmark"],
    )
