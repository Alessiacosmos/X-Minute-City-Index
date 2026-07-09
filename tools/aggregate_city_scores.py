import itertools
from pathlib import Path

import geopandas as gpd
import pandas as pd
from jsonargparse import auto_cli
from omegaconf import OmegaConf


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
    configs = OmegaConf.load(config_descriptor)

    # Initialize an empty DataFrame to hold aggregated scores
    aggregated_scores = []

    for idx in range(len(aois)):
        aoi = aois.iloc[[idx]]

        aoi_id = aoi[aoi_id_col].values[0] if aoi_id_col in aoi.columns else idx

        aoi_score_dir = score_root_dir / aoi_id / "scores"

        if not aoi_score_dir.exists():
            print(f"Score directory for AOI {aoi_id} does not exist. Skipping.")
            continue

        score_city = extract_score_one_aoi(
            aoi_id=aoi_id,
            aoi_score_dir=aoi_score_dir,
            travel_modes=list(configs.mode_speeds.keys()),
            travel_times=configs.xmin_timeframes,
        )
        aggregated_scores.append(score_city)

    aggregated_scores = pd.DataFrame(aggregated_scores).rename(
        columns={"aoi_id": aoi_id_col}
    )
    aoi_scores = aois.merge(aggregated_scores, on=aoi_id_col, how="left")

    # Save the aggregated scores to a CSV file
    aoi_scores.to_file(score_root_dir / "all_city_scores.gpkg")
    print(f"Aggregated scores saved to {score_root_dir / 'all_city_scores.gpkg'}")


def extract_score_one_aoi(
    aoi_id: str,
    aoi_score_dir: Path,
    travel_modes: list[str],
    travel_times: list[int],
):
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


if __name__ == "__main__":
    auto_cli(aggregate_city_scores, as_positional=False)
