# correlations between per city's data quality score and accessibility score
import itertools
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from omegaconf import DictConfig
from scipy import stats

from analysis.data_quality.utils import country_map, style_map
from xmin_core.utils.configure import initialize_configs


def calc_category_correlations(
    configs: DictConfig,
    category_access_score_dir_descriptor: Path,
    data_quality_score_descriptor: Path,
    output_dir: Path,
):
    categories = [category.name for category in configs.poi_setting]

    data_quality_scores = gpd.read_file(data_quality_score_descriptor)

    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        category_access_score_mode_time = gpd.read_file(
            category_access_score_dir_descriptor
            / f"{mode}_{time}min_category_scores.gpkg"
        )

        scores_both = data_quality_scores.merge(
            category_access_score_mode_time,
            on="URAU_CODE",
            how="left",
            suffixes=("_quality", "_access"),
        )
        scores_both["country"] = scores_both["URAU_CODE"].str[:2].map(country_map)

        fig, axes = plt.subplots(3, 3, figsize=(15, 15))
        axes = axes.flatten()

        for ci, category in enumerate(categories):
            calc_correlation(
                category_name=category,
                category_both_scores=scores_both[
                    [
                        "URAU_CODE",
                        "country",
                        f"{category}_quality",
                        f"{category}_access",
                    ]
                ],
                ax=axes[ci],
            )

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.005)
        )

        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(
            output_dir / f"{mode}_{time}min_scatter_grid_by_class.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


def calc_correlation(
    category_name: str,
    category_both_scores: pd.DataFrame,
    ax: plt.Axes,
):
    x, y = (
        category_both_scores[f"{category_name}_quality"],
        category_both_scores[f"{category_name}_access"],
    )

    # regression
    valid = ~np.isnan(x) & ~np.isnan(y)
    x_valid, y_valid = x[valid], y[valid]
    slope, intercept, r_value, p_value, std_err = stats.linregress(x_valid, y_valid)
    line_x = np.linspace(x.min(), x.max(), 100)
    line_y = slope * line_x + intercept

    # 3. Plot
    # scatter points, colored/shaped by country
    for country, style in style_map.items():
        pts = category_both_scores[category_both_scores["country"] == country]
        ax.scatter(
            pts[f"{category_name}_quality"],
            pts[f"{category_name}_access"],
            color=style["color"],
            marker=style["marker"],
            edgecolor="black",
            linewidth=0.3,
            alpha=0.8,
            s=50,
            label=country,
        )

    # regression line
    if not np.isnan(slope):
        ax.plot(line_x, line_y, color="black", linewidth=2)
        reg_label = f"y={slope:.2f}x+{intercept:.2f}, $R^2$={r_value**2:.2f}"
    else:
        reg_label = "Regression: n/a"

    ax.set_title(f"{category_name} ({reg_label})", fontsize=9)
    ax.set_xlabel("Map saturation score")
    ax.set_ylabel("Accessibility score")

    # plt.legend()
    # plt.tight_layout()
    # plt.show()
    #
    # print("done.")


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis")

    category_access_score_dir = result_root_dir.parent / "aggregated_category_scores"
    data_quality_score_file = result_root_dir / "all_city_quality_scores.gpkg"

    configs = initialize_configs(config_file)

    calc_category_correlations(
        configs, category_access_score_dir, data_quality_score_file, output_dir
    )
