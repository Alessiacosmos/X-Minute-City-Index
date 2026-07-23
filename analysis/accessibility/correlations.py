import itertools
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from matplotlib.ticker import FixedLocator, FixedFormatter
from omegaconf import DictConfig
from scipy import stats

from analysis.utils import country_map, style_map
from xmin_core.utils.configure import initialize_configs


def calc_total_correlation_pop_vs_access(
    configs: DictConfig,
    total_score_descriptor: Path,
    city_population_descriptor: Path,
    output_dir: Path,
):
    nice_ticks_real_total = [50, 100, 200, 500, 1000, 2000, 5000]

    total_access_scores = gpd.read_file(total_score_descriptor)
    city_populations = load_city_population_data(city_population_descriptor)

    scores_w_pop = total_access_scores.merge(
        city_populations,
        on="URAU_CODE",
        how="left",
    )
    scores_w_pop["country"] = scores_w_pop["URAU_CODE"].str[:2].map(country_map)

    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        scores_w_pop_mode_time = scores_w_pop[
            ["URAU_CODE", "country", "population", f"{mode}_{time}min_weighted"]
        ]
        scores_w_pop_mode_time = scores_w_pop_mode_time.rename(
            columns={f"{mode}_{time}min_weighted": "overall accessibility"}
        )

        fig, ax = plt.subplots(1, 1, figsize=(9, 7))

        calc_correlation_accessibility_anal(
            category_name="overall accessibility",
            category_both_scores=scores_w_pop_mode_time,
            ax=ax,
            nice_ticks_real=nice_ticks_real_total,
        )

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc="lower right")
        fig.supxlabel(
            "Population size (thousands of people, log scale)", y=0.07, fontsize=11
        )
        fig.supylabel("Accessibility score", fontsize=11)

        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(
            output_dir
            / "overall"
            / f"{mode}_{time}min_pop_weighted_pop_vs_access_logxaxis.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


def calc_category_correlation_pop_vs_access(
    configs: DictConfig,
    category_access_score_dir_descriptor: Path,
    city_population_descriptor: Path,
    output_dir: Path,
):
    nice_ticks_real_category = [50, 250, 1000, 4000]

    categories = [category.name for category in configs.poi_setting]

    city_populations = load_city_population_data(city_population_descriptor)

    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        category_access_score_mode_time = gpd.read_file(
            category_access_score_dir_descriptor
            / f"{mode}_{time}min_category_scores.gpkg"
        )

        scores_w_pop_mode_time = category_access_score_mode_time.merge(
            city_populations,
            on="URAU_CODE",
            how="left",
        )
        scores_w_pop_mode_time["country"] = (
            scores_w_pop_mode_time["URAU_CODE"].str[:2].map(country_map)
        )

        fig, axes = plt.subplots(3, 3, figsize=(14, 10), sharex=True, sharey=True)
        axes = axes.flatten()

        for ci, category in enumerate(categories):
            calc_correlation_accessibility_anal(
                category_name=category,
                category_both_scores=scores_w_pop_mode_time[
                    [
                        "URAU_CODE",
                        "country",
                        "population",
                        f"{category}",
                    ]
                ],
                ax=axes[ci],
                nice_ticks_real=nice_ticks_real_category,
            )

        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(
            handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.02)
        )
        fig.supxlabel(
            "Population size (thousands of people, log scale)", y=0.07, fontsize=12
        )
        fig.supylabel("Accessibility score", fontsize=12)

        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(
            output_dir
            / "categories"
            / f"{mode}_{time}min_pop_vs_access_by_class_logxaxis.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


def load_city_population_data(city_population_descriptor: Path):
    city_populations = pd.read_csv(city_population_descriptor, header=0)
    city_populations["population"] = np.log10(city_populations["population"] / 1000)

    return city_populations


def calc_correlation_accessibility_anal(
    category_name: str,
    category_both_scores: pd.DataFrame,
    ax: plt.Axes,
    nice_ticks_real: list[int],
):
    x = category_both_scores["population"]

    # regression
    x_range = x.max() - x.min()
    x_min, x_max = x.min() - x_range * 0.05, x.max() + x_range * 0.05

    line_x = np.linspace(x_min, x_max, 100)

    # 3. Plot
    # scatter points, colored/shaped by country
    for country, style in style_map.items():
        pts = category_both_scores[category_both_scores["country"] == country]
        country_x, country_y = pts["population"], pts[f"{category_name}"]
        ax.scatter(
            country_x,
            country_y,
            color=style["color"],
            marker=style["marker"],
            edgecolor="black",
            linewidth=0.3,
            alpha=0.8,
            s=50,
            label=country,
        )

        # regression line
        country_valid = ~np.isnan(country_x) & ~np.isnan(country_y)
        country_x_valid, country_y_valid = (
            country_x[country_valid],
            country_y[country_valid],
        )
        slope, intercept, r_value, p_value, std_err = stats.linregress(
            country_x_valid, country_y_valid
        )
        line_y = slope * line_x + intercept

        if not np.isnan(slope):
            linestyle = "-" if p_value < 0.05 else "--"
            ax.plot(
                line_x, line_y, color=style["color"], linestyle=linestyle, linewidth=1.5
            )

    ax.set_title(f"{category_name}", fontsize=12)

    ax.set_xlim(x_min, x_max)

    # keep only ticks within the actual data range, to avoid clutter/out-of-range labels
    nice_ticks_real = [v for v in nice_ticks_real if x_min <= np.log10(v) <= x_max]

    # convert to log10(thousands) coordinate space to match your transformed x
    tick_positions = [np.log10(v) for v in nice_ticks_real]
    tick_labels = [f"{v:,.0f}" for v in nice_ticks_real]

    ax.xaxis.set_major_locator(FixedLocator(tick_positions))
    ax.xaxis.set_major_formatter(FixedFormatter(tick_labels))

    ax.set_ylim(0, 100)


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/accessibility")

    total_access_score_file = result_root_dir / "all_city_scores.gpkg"
    category_access_score_dir = result_root_dir.parent / "aggregated_category_scores"
    city_population_file = result_root_dir.parent / "cities_with_population.csv"

    configs = initialize_configs(config_file)

    calc_total_correlation_pop_vs_access(
        configs, total_access_score_file, city_population_file, output_dir
    )
    calc_category_correlation_pop_vs_access(
        configs, category_access_score_dir, city_population_file, output_dir
    )
