import itertools
from pathlib import Path

import geopandas as gpd
import pandas as pd
from matplotlib import pyplot as plt
from omegaconf import DictConfig

from analysis.utils import country_map, style_map, travel_mode_map
from xmin_core.utils.configure import initialize_configs


def present_scores_at_different_travel_settings(
    config: DictConfig, total_score_descriptor: Path, output_dir: Path
):
    total_access_scores = gpd.read_file(total_score_descriptor)
    total_access_scores["country"] = (
        total_access_scores["URAU_CODE"].str[:2].map(country_map)
    )

    average_scores = []
    for mode, time in list(
        itertools.product(config.mode_speeds, config.xmin_timeframes)
    ):
        col = f"{mode}_{time}min_weighted"

        avg_score_per_country = (
            total_access_scores.groupby("country")[col].mean().rename("score")
        )
        avg_score_per_country["mode"] = travel_mode_map[mode]
        avg_score_per_country["time"] = time
        average_scores.append(avg_score_per_country)

    average_scores = pd.concat(
        average_scores, axis=1, ignore_index=True
    )  # index = Germany, Netherlands, Spain, mode, time

    fig, ax = plt.subplots(figsize=(7, 5))
    x_positions = {
        (average_scores.loc["mode", acol], average_scores.loc["time", acol]): acol + 1
        for acol in average_scores.columns
    }

    for country, style in style_map.items():
        scores_per_country = average_scores.loc[country]

        ax.plot(
            list(x_positions.values()),
            scores_per_country.values,
            color=style["color"],
            marker=style["marker"],
            markersize=7,
            markerfacecolor=style["color"],
            markeredgecolor="black",
            linewidth=1.5,
        )
        ax.text(
            list(x_positions.values())[-1] + 0.1,
            scores_per_country.values[-1],
            country,
            color=style["color"],
            fontsize=9,
            fontweight="bold",
            va="center",
        )

    ax.set_xlim(0.7, len(x_positions) + 1)
    ax.set_xticks(list(x_positions.values()))
    ax.set_xticklabels([f"{t}-min" for t in average_scores.loc["time"]])
    ax.set_ylim(49, 101)
    ax.set_ylabel("Accessibility score", fontsize=11)
    ax.tick_params(axis="y")  # , labelsize=14)

    # group labels (mode names) centered under each mode's ticks
    for mode in travel_mode_map.values():
        xs_for_mode = []
        for x_item_k, x_item_v in x_positions.items():  # (mode, t): value
            if mode in x_item_k:
                xs_for_mode.append(x_item_v)
        center = sum(xs_for_mode) / len(xs_for_mode)
        ax.annotate(
            mode.capitalize(),
            xy=(center, 0),
            xycoords=("data", "axes fraction"),
            xytext=(0, -35),
            textcoords="offset points",
            ha="center",
            fontsize=11,
        )

    ax.set_title(
        "Average accessibility scores across travel modes and time thresholds",
        fontsize=11,
    )
    plt.tight_layout()

    plt.savefig(
        output_dir / "scores_across_mode_time.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/accessibility")

    total_access_score_file = result_root_dir / "all_city_scores.gpkg"
    category_access_score_dir = result_root_dir.parent / "aggregated_category_scores"

    configs = initialize_configs(config_file)

    present_scores_at_different_travel_settings(
        configs, total_access_score_file, output_dir
    )
