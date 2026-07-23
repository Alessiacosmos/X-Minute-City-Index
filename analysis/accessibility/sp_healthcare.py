from pathlib import Path

import geopandas as gpd
import pandas as pd
from matplotlib import pyplot as plt

from analysis.utils import style_map, country_map


def present_healthcare_score_transfer(
    uni_health_score_descriptor: Path,
    sp_health_score_dir_descriptor: Path,
):
    uni_health_score = gpd.read_file(uni_health_score_descriptor)
    uni_health_score["country"] = uni_health_score["URAU_CODE"].str[:2].map(country_map)

    fig, ax = plt.subplots(figsize=(4, 5.5))

    x_positions = [1, 2]
    for city_code, city_attrs in SPECIAL_CASE_CITIES.items():
        city_uni_score = uni_health_score.loc[
            uni_health_score["URAU_CODE"] == city_code, ["country", CATEGORY]
        ]

        city_sp_score = pd.read_csv(
            sp_health_score_dir_descriptor
            / city_code
            / "scores"
            / f"{MODE}_{TIME}min"
            / "score_city.csv",
            index_col=0,
            header=0,
        )
        city_sp_score = (
            city_sp_score.loc["sum", "total_score_pop_weighted"]
            / city_attrs["category_weight"]
        )

        scores_uni_vs_sp = [city_uni_score[CATEGORY].values[0], city_sp_score]

        city_style = style_map[city_uni_score["country"].values[0]]
        ax.plot(
            x_positions,
            scores_uni_vs_sp,
            color=city_style["color"],
            marker=city_style["marker"],
            markersize=7,
            markerfacecolor=city_style["color"],
            markeredgecolor="black",
            linewidth=1.5,
        )
        ax.text(
            x_positions[-1] + 0.1,
            scores_uni_vs_sp[-1],
            city_attrs["name"],
            color=city_style["color"],
            fontsize=9,
            fontweight="bold",
            va="center",
        )

    ax.set_xlim(0.7, len(x_positions) + 0.7)
    ax.set_xticks(x_positions)
    ax.set_xticklabels(["Universal\nparameters", "Country-specific\nparameters"])
    ax.set_ylim(54, 91)
    ax.set_ylabel("Accessibility score")
    ax.tick_params(axis="y")

    ax.set_title(
        "Accessibility score comparison",
        fontsize=10,
    )
    plt.tight_layout()

    plt.savefig(
        output_dir / "sp_score_change_uni_vs_country-spec.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


if __name__ == "__main__":
    SPECIAL_CASE_CITIES = {
        "DE001C": {
            "name": "Berlin",
            "category_weight": 0.1,
        },  # category_weight is from the poi_categories setting
        "NL001C": {"name": "Amsterdam", "category_weight": 0.1},
        "ES001C": {"name": "Madrid", "category_weight": 0.1},
    }

    MODE, TIME, CATEGORY = "foot-walking", 15, "healthcare"

    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/accessibility")

    uni_health_access_score_file = (
        result_root_dir.parent
        / "aggregated_category_scores"
        / f"{MODE}_{TIME}min_category_scores.gpkg"
    )
    sp_health_access_score_dir = result_root_dir / "AHealthSpec"

    present_healthcare_score_transfer(
        uni_health_access_score_file, sp_health_access_score_dir
    )
