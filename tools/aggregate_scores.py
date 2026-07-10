import itertools
import json
from pathlib import Path

import geopandas as gpd
import pandas as pd
from jsonargparse import auto_cli
from tqdm import tqdm

from xmin_core.utils.configure import initialize_configs


def aggregate_city_scores(
    aoi_descriptor: Path,
    config_descriptor: Path,
    score_root_dir: Path,
    aoi_id_col: str = None,
):
    """
    Aggregate the scores of all AOIs in a city and save the results to score_root_dir.
    :param aoi_descriptor: Areas of interest descriptor (*.geojson, *.gpkg, *.shp)
    :param config_descriptor: configs used to specify the settings for the index calculation,
                              including POI categories, timeframes, mode speeds, etc.
    :param score_root_dir: Path where the output layers will be saved.
                           For each AOI, a subdirectory named '{aoi_id}' is there which stores the results.
    :param aoi_id_col: AOI ID column's name e.g. URAU_CODE
    :return:
    """
    aois = gpd.read_file(aoi_descriptor).to_crs("EPSG:4326")
    print(f"{len(aois)} AOIs found")

    # Initialize configures
    configs = initialize_configs(config_descriptor)
    categories = {
        category.name: configs.poi_setting.obtain_weights_and_benchmarks(category.name)[
            "parent_weight"
        ]
        for category in configs.poi_setting
    }

    # Initialize an empty DataFrame to hold aggregated scores
    aggregated_accessibility_scores = []
    aggregated_quality_scores = []
    category_scores = []

    for idx in tqdm(range(len(aois)), desc="Aggregate scores of AOIs"):
        aoi = aois.iloc[[idx]]

        aoi_id = aoi[aoi_id_col].values[0] if aoi_id_col in aoi.columns else idx

        score_city = extract_accessibility_score_one_aoi(
            aoi_id=aoi_id,
            aoi_score_dir=score_root_dir / aoi_id / "scores",
            travel_modes=list(configs.mode_speeds.keys()),
            travel_times=configs.xmin_timeframes,
        )
        qscore_city = extract_quality_score_one_aoi(
            aoi_id=aoi_id,
            category_weights=categories,
            aoi_quality_dir=score_root_dir / aoi_id / "quality",
        )
        category_scores_city = calc_category_score_one_aoi(
            aoi_id=aoi_id,
            aoi_score_dir=score_root_dir / aoi_id / "scores",
            travel_modes=configs.mode_speeds,
            travel_times=configs.xmin_timeframes,
            categories=list(categories.keys()),
        )
        aggregated_accessibility_scores.append(score_city)
        aggregated_quality_scores.append(qscore_city)
        category_scores.extend(category_scores_city)

    # save accessibility and quality scores
    aoi_accessibility_scores = merge_scores_to_geom(
        aggregated_accessibility_scores, aois, aoi_id_col
    )
    aoi_quality_scores = merge_scores_to_geom(
        aggregated_quality_scores, aois, aoi_id_col
    )

    aoi_accessibility_scores.to_file(score_root_dir / "all_city_scores.gpkg")
    aoi_quality_scores.to_file(score_root_dir / "all_city_quality_scores.gpkg")
    print(f"Aggregated scores saved to {score_root_dir}")

    # save category scores
    aoi_category_scores = pd.concat(category_scores, axis=1).T.rename(
        columns={"aoi_id": aoi_id_col}
    )
    aoi_category_scores[list(categories.keys())] = aoi_category_scores[
        list(categories.keys())
    ].astype("float")
    save_category_scores_by_mode_time(
        category_scores=aoi_category_scores,
        aoi_geoms=aois[[aoi_id_col, "geometry"]],
        aoi_id_col=aoi_id_col,
        output_dir=score_root_dir.parent / "aggregated_category_scores",
    )


def extract_accessibility_score_one_aoi(
    aoi_id: str,
    aoi_score_dir: Path,
    travel_modes: list[str],
    travel_times: list[int],
) -> dict[str, float]:
    score_city = dict(aoi_id=aoi_id)
    for mode, time in itertools.product(travel_modes, travel_times):
        score_mode_time_dir = aoi_score_dir / f"{mode}_{time}min"

        score_city_mode_time = pd.read_csv(
            score_mode_time_dir / "score_city.csv", index_col=0, header=0
        )
        score_city[f"{mode}_{time}min"] = score_city_mode_time.loc[
            "mean", "total_score"
        ]
        score_city[f"{mode}_{time}min_weighted"] = score_city_mode_time.loc[
            "sum", "total_score_pop_weighted"
        ]

    return score_city


def extract_quality_score_one_aoi(
    aoi_id: str,
    category_weights: dict[str, float],
    aoi_quality_dir: Path,
) -> dict[str, float]:
    qscore_city = dict(aoi_id=aoi_id)

    with open(aoi_quality_dir / "map_saturation_all.json", "r") as qf:
        qscore_per_category = json.load(qf)

    weighted_total_qscore = 0.0
    for category, qscore in qscore_per_category.items():
        if qscore["value"] is not None:
            qscore_city[category] = qscore["value"] * 100  # convert to percentage
            weighted_total_qscore += qscore_city[category] * category_weights[category]
        else:  # some saturation curve cannot calculate, e.g. NL016C - education, we need pass them
            qscore_city[category] = qscore["value"]

    qscore_city["total"] = weighted_total_qscore

    return qscore_city


def calc_category_score_one_aoi(
    aoi_id: str,
    aoi_score_dir: Path,
    travel_modes: list[str],
    travel_times: list[int],
    categories: list[str],
) -> list[pd.Series]:
    score_hex_categories = []
    for mode, time in itertools.product(travel_modes, travel_times):
        score_mode_time_dir = aoi_score_dir / f"{mode}_{time}min"

        hex_scores = gpd.read_file(score_mode_time_dir / "score.gpkg").set_index(
            "hex_id"
        )
        score_hex_categories_mode_time = pd.read_csv(
            score_mode_time_dir / "score_categories.csv", index_col=0, header=0
        )

        score_hex_categories_mode_time = score_hex_categories_mode_time[categories]

        score_hex_categories_mode_time = (
            score_hex_categories_mode_time.mul(hex_scores["population"], axis=0)
            / hex_scores["population"].sum()
        )
        score_hex_categories_mode_time = score_hex_categories_mode_time.sum(axis=0)
        score_hex_categories_mode_time["aoi_id"] = aoi_id
        score_hex_categories_mode_time["mode_time"] = f"{mode}_{time}min"

        score_hex_categories.append(score_hex_categories_mode_time)

    return score_hex_categories


def merge_scores_to_geom(
    aggregated_scores: list[dict],
    aois: gpd.GeoDataFrame,
    aoi_id_col: str,
) -> gpd.GeoDataFrame:
    aggregated_scores = pd.DataFrame(aggregated_scores).rename(
        columns={"aoi_id": aoi_id_col}
    )
    return aois.merge(aggregated_scores, on=aoi_id_col, how="left")


def save_category_scores_by_mode_time(
    category_scores: pd.DataFrame,
    aoi_geoms: gpd.GeoDataFrame,
    aoi_id_col: str,
    output_dir: Path,
):
    for mode_time, category_scores_mode_time in category_scores.groupby("mode_time"):
        category_scores_mode_time = gpd.GeoDataFrame(
            category_scores_mode_time.merge(aoi_geoms, on=aoi_id_col),
            crs=aoi_geoms.crs,
        )
        category_scores_mode_time.to_file(
            output_dir / f"{mode_time}_category_scores.gpkg", driver="GPKG"
        )


if __name__ == "__main__":
    auto_cli(aggregate_city_scores, as_positional=False)
