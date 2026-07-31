import itertools
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from omegaconf import DictConfig

from analysis.utils import city_name_fixes_map, country_map, style_map
from xmin_core.utils.configure import initialize_configs


def calc_param_sensitivity_analysis(
    configs: DictConfig,
    total_score_descriptor: Path,
    category_access_score_dir_descriptor: Path,
    output_dir: Path,
    n_draws: int = 2000,
):
    category_weights = {
        category.name: category.value.weight for category in configs.poi_setting
    }

    total_access_scores = gpd.read_file(total_score_descriptor)

    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        category_access_score_mode_time = gpd.read_file(
            category_access_score_dir_descriptor
            / f"{mode}_{time}min_category_scores.gpkg"
        )

        category_access_score_mode_time = category_access_score_mode_time.merge(
            total_access_scores[["URAU_CODE", "URAU_NAME"]],
            on="URAU_CODE",
            how="left",
        )

        category_access_score_mode_time["URAU_NAME"] = category_access_score_mode_time[
            "URAU_NAME"
        ].replace(city_name_fixes_map)
        sensitivity_simulated_scores = run_sensitivity_analysis(
            category_weights=category_weights,
            category_access_scores=category_access_score_mode_time,
            n_draws=n_draws,
        )

        draw_sensitivity_analysis_result(
            sensitivity_simulated_scores, mode, time, output_dir
        )


def run_sensitivity_analysis(
    category_weights: dict,
    category_access_scores: gpd.GeoDataFrame,
    n_draws: int,
) -> pd.DataFrame:
    # Monte-Carlo simulation
    ## prepare random flags
    rng = np.random.default_rng(52)
    n_draws = (n_draws // 2) * 2  # make it always even
    geometric_flags = np.zeros(n_draws, dtype=bool)
    geometric_flags[: n_draws // 2] = True
    rng.shuffle(geometric_flags)

    n_cities = len(category_access_scores)
    sensitivity_results = np.empty((n_cities, n_draws))

    categories = list(category_weights.keys())
    category_base_weights = np.asarray(list(category_weights.values()))
    score_matrix = category_access_scores[categories].to_numpy(
        dtype=float
    )  # (n_cities, category)

    for i in range(n_draws):
        weights_i = category_base_weights * rng.uniform(
            0.75, 1.25, size=len(category_weights)
        )
        weights_i = weights_i / weights_i.sum()

        if geometric_flags[i]:
            sensitivity_results[:, i] = weighted_geo_mean(score_matrix, weights_i)
        else:
            sensitivity_results[:, i] = (
                score_matrix @ weights_i
            )  # weighted arith. mean, sum(x*w)

    sensitivity_results = pd.DataFrame(
        {
            "URAU_CODE": category_access_scores["URAU_CODE"],
            "URAU_NAME": category_access_scores["URAU_NAME"],
            "score_median": np.nanmedian(sensitivity_results, axis=1),
            "score_lowerci": np.nanquantile(sensitivity_results, 0.025, axis=1),
            "score_upperci": np.nanquantile(sensitivity_results, 0.975, axis=1),
        },
    )

    return sensitivity_results


def weighted_geo_mean(x: np.ndarray, w: np.ndarray) -> np.ndarray:
    assert x.shape[1] == len(w), (
        f"x's column ({x.shape}) and w's length ({len(w)}) must be the same"
    )

    return np.exp(np.log(x) @ w)


def draw_sensitivity_analysis_result(
    simulated_scores: pd.DataFrame,
    mode: str,
    time: int,
    output_dir: Path,
):
    simulated_scores["Country"] = simulated_scores["URAU_CODE"].str[:2].map(country_map)
    simulated_scores = simulated_scores.sort_values("score_median").reset_index(
        drop=True
    )

    fig, ax = plt.subplots(1, 1, figsize=(6, 10))
    y_pos = np.arange(len(simulated_scores))

    # 95% CI horizontal error bars (drawn once, neutral colour, no legend).
    xerr = np.vstack(
        [
            simulated_scores["score_median"] - simulated_scores["score_lowerci"],
            simulated_scores["score_upperci"] - simulated_scores["score_median"],
        ]
    )
    ax.errorbar(
        simulated_scores["score_median"],
        y_pos,
        xerr=xerr,
        fmt="none",
        ecolor="black",
        elinewidth=0.8,
        capsize=3,
        zorder=1,
    )

    # Median dots, filled by country colour / shaped by country marker.
    for country, style in style_map.items():
        mask = (simulated_scores["Country"] == country).to_numpy()
        ax.scatter(
            simulated_scores.loc[mask, "score_median"],
            y_pos[mask],
            color=style["color"],
            marker=style["marker"],
            edgecolor="black",
            linewidth=0.5,
            s=25,
            label=country,
            zorder=2,
        )

    ax.set_xlim(0, 100)
    ax.set_ylim(min(y_pos) - 1, max(y_pos) + 1)
    ax.set_yticks(y_pos)
    ax.set_yticklabels(simulated_scores["URAU_NAME"], fontsize=9)

    ax.set_xlabel("Accessibility score", fontsize=11)
    ax.set_title("Sensitivity Analysis", fontsize=12)

    ax.grid(axis="both", which="major", alpha=0.3)
    ax.legend(loc="upper left")  # , bbox_to_anchor=(0.5, 0.02), ncol=3, frameon=False)

    plt.tight_layout()
    plt.savefig(
        output_dir / "sensitivity" / f"{mode}_{time}_sensitivity_analysis.png", dpi=300
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

    # do sensitivity analysis just for 15-walk
    configs.mode_speeds = ["foot-walking"]
    configs.xmin_timeframes = [15]

    calc_param_sensitivity_analysis(
        configs, total_access_score_file, category_access_score_dir, output_dir
    )
