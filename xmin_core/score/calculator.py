import ast
import logging
from collections import defaultdict
from functools import partial
from multiprocessing import Pool
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS
from rasterstats import gen_zonal_stats
from shapely import Polygon
from tqdm import tqdm

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
    hexagons["population"] = [s["sum"] for s in stats]

    return hexagons.to_crs(hexagons_crs)


def get_xmin_index_score(
    hex_grids: gpd.GeoDataFrame,
    reachable_poi_files: dict,
    poi_setting: POICatogories,
    savedir: Path,
):
    est_utm_crs = hex_grids.estimate_utm_crs()

    # get sum poi counts of each category per mode. # non-normalized poi count result
    scores_per_mode_time: dict[str, list[pd.DataFrame]] = defaultdict(list)
    for name_cate, reachable_poi_1cate_files in tqdm(
        reachable_poi_files.items(),
        total=len(reachable_poi_files),
        desc="Scoring each category...",
    ):
        cate_weights_benchmarks = poi_setting.obtain_weights_and_benchmarks(name_cate)
        # poi_cate_setting = poi_setting[name_cate].value

        for reachable_poi_1cate_file in reachable_poi_1cate_files:
            mode_time = reachable_poi_1cate_file.parent.stem

            # if (savedir / "scores" / mode_time / "score_categories.csv").exists():
            #     continue

            hex_iso_reachable_pois_1cate = gpd.read_file(reachable_poi_1cate_file)
            hex_iso_reachable_pois_1cate["poi_ids"] = hex_iso_reachable_pois_1cate[
                "poi_ids"
            ].apply(ast.literal_eval)

            score_cate = score_hexagons_one_category(
                hex_iso_reachable_pois_1cate=hex_iso_reachable_pois_1cate,
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

        # get city-level analysis
        city_score = score_city_level(hex_grids)

        # save result
        hex_grids.to_file(savedir / "scores" / mode_time / "score.gpkg", driver="GPKG")
        city_score.to_csv(savedir / "scores" / mode_time / "score_city.csv", index=True)
        category_scores.to_csv(
            savedir / "scores" / mode_time / "score_categories.csv", index=True
        )


def score_hexagons_one_category(
    hex_iso_reachable_pois_1cate: gpd.GeoDataFrame,
    name_cate: str,
    cate_weights_benchmarks: dict,
    est_utm_crs: CRS,
    poi_filepath: Path,
) -> pd.DataFrame:
    parent_weight, sub_weights_benchmarks = (
        cate_weights_benchmarks["parent_weight"],
        cate_weights_benchmarks["sub_weights_benchmarks"],
    )

    hex_iso_reachable_pois_1cate = hex_iso_reachable_pois_1cate.to_crs(est_utm_crs)

    pois = gpd.read_file(poi_filepath)
    pois = pois.set_index("@osmId")

    _score_one_hex = partial(
        score_one_hex,
        name_cate=name_cate,
        pois=pois,
        parent_weight=parent_weight,
        sub_weights_benchmarks=sub_weights_benchmarks,
        est_utm_crs=est_utm_crs,
    )

    with Pool(processes=5) as pool:
        hex_scores = pool.map(_score_one_hex, hex_iso_reachable_pois_1cate.iterrows())

    hex_scores = pd.DataFrame(hex_scores)

    return hex_scores.set_index("hex_id")


def score_one_hex(
    one_hex_row: tuple[int, gpd.GeoSeries],
    name_cate: str,
    pois: gpd.GeoDataFrame,
    parent_weight: float,
    sub_weights_benchmarks: dict,
    est_utm_crs: CRS,
):
    _, one_hex_poi_ids = one_hex_row

    hex_score = dict()
    hex_score["hex_id"] = one_hex_poi_ids["hex_id"]

    if len(one_hex_poi_ids["poi_ids"]) == 0:
        hex_score[name_cate] = 0

    one_hex_pois = pois.loc[one_hex_poi_ids["poi_ids"]]

    if name_cate == "nature_space":
        hex_score[name_cate] = score_one_hex_nature_space_by_area(
            one_hex_reachable_pois=one_hex_pois,
            isochrone=one_hex_poi_ids.geometry,
            sub_weights_benchmarks=sub_weights_benchmarks,
            est_utm_crs=est_utm_crs,
        )
    else:
        hex_score[name_cate] = score_one_hex_one_category_by_sub_category_pois(
            one_hex_pois, sub_weights_benchmarks
        )
    hex_score[f"{name_cate}_weighted"] = hex_score[name_cate] * parent_weight

    return hex_score


def score_one_hex_one_category_by_sub_category_pois(
    one_hex_reachable_pois: gpd.GeoDataFrame,
    sub_weights_benchmarks: dict,
) -> float:
    cate_score = 0
    for sub_cate, sub_w_bmk in sub_weights_benchmarks.items():
        if "benchmark" in sub_w_bmk:
            sub_score = score_sub_cate(
                pois=one_hex_reachable_pois,
                sub_cate=sub_cate,
                weight_benchmark=sub_w_bmk,
            )
        elif "group" in sub_w_bmk:
            group_sub_score = 0
            for group_sub_cate, group_sub_w_bmk in sub_w_bmk["group"].items():
                group_sub_score += score_sub_cate(
                    pois=one_hex_reachable_pois,
                    sub_cate=group_sub_cate,
                    weight_benchmark=group_sub_w_bmk,
                )
            sub_score = min(100, group_sub_score) * sub_w_bmk["weight"]
        else:
            raise NotImplementedError(
                f"sub category {sub_cate} with {sub_weights_benchmarks} not implemented."
            )

        cate_score += sub_score

    return cate_score


def score_one_hex_nature_space_by_area(
    one_hex_reachable_pois: gpd.GeoDataFrame,
    isochrone: Polygon,
    sub_weights_benchmarks: dict,
    est_utm_crs: CRS,
) -> float:
    default_nature_space_area = 100  # m^2
    default_nature_space_radius = np.sqrt(default_nature_space_area / np.pi)
    smallest_nature_space_area = 25

    isochrone = isochrone if isochrone.is_valid else isochrone.buffer(0)

    pois_in_iso = one_hex_reachable_pois.to_crs(est_utm_crs)
    pois_in_iso["geometry"] = pois_in_iso.make_valid()

    for geom_type in pois_in_iso.geometry.type.unique():
        mask = pois_in_iso.geom_type == geom_type
        match geom_type:
            case "MultiPolygon" | "Polygon" | "GeometryCollection":
                pass
            case "LineString" | "MultiLineString":
                pois_in_iso.loc[mask, "geometry"] = pois_in_iso.loc[
                    mask
                ].geometry.centroid.buffer(
                    default_nature_space_radius
                )  # use centroid to simulate it as a point
            case _:
                pois_in_iso.loc[mask, "geometry"] = pois_in_iso.loc[
                    mask
                ].geometry.buffer(default_nature_space_radius)

    pois_in_iso["area"] = pois_in_iso.area
    pois_in_iso_solid: gpd.GeoDataFrame = pois_in_iso[
        pois_in_iso["area"] >= smallest_nature_space_area
    ]
    if pois_in_iso_solid.empty:
        pois_area_absolute = 0
    else:
        pois_area_absolute = pois_in_iso_solid.union_all().intersection(isochrone).area

    return normalize_score(
        value=pois_area_absolute,
        benchmark=sub_weights_benchmarks["all"]["benchmark"],
    )


def score_sub_cate(
    pois: gpd.GeoDataFrame, sub_cate: str, weight_benchmark: str
) -> float:
    sub_pois = pois[pois["sub_category"] == sub_cate]
    sub_poi_num = len(sub_pois)
    return (
        normalize_score(value=sub_poi_num, benchmark=weight_benchmark["benchmark"])
        * weight_benchmark["weight"]
    )


def score_city_level(
    hex_scores: gpd.GeoDataFrame,
) -> pd.DataFrame:
    hex_scores["total_score_pop_weighted"] = (
        hex_scores["population"]
        * hex_scores["total_score"]
        / hex_scores["population"].sum()
    )

    base_stats = hex_scores.describe()  # mean, std, min, 25, 50, 75, max
    sum_stat = pd.DataFrame(hex_scores.drop(["geometry"], axis=1).sum(axis=0)).T.rename(
        index={0: "sum"}
    )

    return pd.concat([base_stats, sum_stat])
