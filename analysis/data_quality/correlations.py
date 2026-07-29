# correlations between per city's data quality score and accessibility score
import itertools
import json
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt

from omegaconf import DictConfig
from scipy.stats import spearmanr

from analysis.utils import (
    country_map,
    calc_correlation_data_quality,
    calc_correlation_accessibility_anal,
)
from xmin_core.utils.configure import initialize_configs


def calc_total_correlation(
    configs: DictConfig,
    total_score_descriptor: Path,
    data_quality_score_descriptor: Path,
    output_dir: Path,
):
    data_quality_scores = gpd.read_file(data_quality_score_descriptor)
    total_access_scores = gpd.read_file(total_score_descriptor)

    scores_both = data_quality_scores.merge(
        total_access_scores,
        on="URAU_CODE",
        how="left",
    )
    scores_both["country"] = scores_both["URAU_CODE"].str[:2].map(country_map)

    spearman_result = {}
    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        scores_both_mode_time = scores_both[
            ["URAU_CODE", "country", "total", f"{mode}_{time}min_weighted"]
        ]
        scores_both_mode_time = scores_both_mode_time.rename(
            columns={
                "total": "overall_quality",
                f"{mode}_{time}min_weighted": "overall_access",
            }
        )

        # spearman
        rho, pval = spearmanr(
            scores_both_mode_time["overall_quality"],
            scores_both_mode_time["overall_access"],
            nan_policy="omit",
        )
        spearman_result[f"{mode}_{time}"] = {"rho": rho, "pval": pval}

        # correlation plot
        fig, ax = plt.subplots(1, 1, figsize=(6, 6))

        calc_correlation_data_quality(
            category_name="overall",
            category_both_scores=scores_both_mode_time,
            ax=ax,
        )

        handles, labels = ax.get_legend_handles_labels()
        ax.legend(handles, labels, loc="lower right")
        fig.supxlabel("Mapping saturation score", y=0.07, fontsize=11)
        fig.supylabel("Accessibility score", fontsize=11)

        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(
            output_dir / "overall" / f"{mode}_{time}min_pop_weighted_scatter_grid.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()

    with open(output_dir / "correlations.json", "w") as jsf:
        json.dump(spearman_result, jsf, indent=4)


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

        fig, axes = plt.subplots(3, 3, figsize=(15, 15), sharex=True, sharey=True)
        axes = axes.flatten()

        for ci, category in enumerate(categories):
            calc_correlation_data_quality(
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
        fig.supxlabel("Mapping saturation score", y=0.07, fontsize=11)
        fig.supylabel("Accessibility score", fontsize=11)

        plt.tight_layout(rect=[0, 0.05, 1, 1])
        plt.savefig(
            output_dir / "categories" / f"{mode}_{time}min_scatter_grid_by_class.png",
            dpi=300,
            bbox_inches="tight",
        )
        plt.close()


def calc_correlation_pop_size(
    configs: DictConfig,
    city_population_descriptor: Path,
    data_quality_score_descriptor: Path,
    output_dir: Path,
):
    nice_ticks_real_total = [50, 100, 200, 500, 1000, 2000, 5000]

    data_quality_scores = gpd.read_file(data_quality_score_descriptor)

    city_populations = pd.read_csv(city_population_descriptor, header=0)
    city_populations["population"] = np.log10(city_populations["population"] / 1000)

    qscores_w_pop = data_quality_scores.merge(
        city_populations,
        on="URAU_CODE",
        how="left",
    )
    qscores_w_pop["country"] = qscores_w_pop["URAU_CODE"].str[:2].map(country_map)

    qscores_w_pop = qscores_w_pop[["URAU_CODE", "country", "population", "total"]]
    qscores_w_pop = qscores_w_pop.rename(
        columns={"total": "overall mapping saturation"}
    )

    fig, ax = plt.subplots(1, 1, figsize=(7, 5))

    calc_correlation_accessibility_anal(
        category_name="overall mapping saturation",
        category_both_scores=qscores_w_pop,
        ax=ax,
        nice_ticks_real=nice_ticks_real_total,
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.set_ylim(50, 100)
    ax.legend(handles, labels, loc="lower right")
    fig.supxlabel(
        "Population size (thousands of people, log scale)", y=0.07, fontsize=12
    )
    fig.supylabel("Mapping saturation", fontsize=12)

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(
        output_dir / "overall" / "pop_vs_map_saturation_logxaxis.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()


def calc_corrlation_poi_cnt(
    configs: DictConfig,
    total_poi_cnt_descriptor: Path,
    data_quality_score_descriptor: Path,
    output_dir: Path,
):
    categories = [category.name for category in configs.poi_setting]

    data_quality_scores = gpd.read_file(data_quality_score_descriptor)
    total_poi_cnts = gpd.read_file(total_poi_cnt_descriptor)
    total_poi_cnts[categories + ["total"]] = np.log10(
        total_poi_cnts[categories + ["total"]] / 100
    )

    scores_cnts = data_quality_scores.merge(
        total_poi_cnts,
        on="URAU_CODE",
        how="left",
        suffixes=("_quality", "_poi_count"),
    )
    scores_cnts["country"] = scores_cnts["URAU_CODE"].str[:2].map(country_map)
    scores_cnts = scores_cnts.rename(
        columns={
            "total_quality": "overall_quality",
            "total_poi_count": "overall_poi_count",
        }
    )

    # total correlation
    fig, ax = plt.subplots(1, 1, figsize=(8, 6))

    calc_correlation_data_quality(
        category_name="overall",
        category_both_scores=scores_cnts,
        ax=ax,
        x_suffix="poi_count",
        y_suffix="quality",
    )

    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, labels, loc="lower right")
    fig.supxlabel("POI count (hundred POIs, log scale)", y=0.07, fontsize=11)
    fig.supylabel("Mapping saturation score", fontsize=11)

    plt.tight_layout(rect=[0, 0.05, 1, 1])
    plt.savefig(
        output_dir / "overall" / "poi_count_scatter_grid_hlog.png",
        dpi=300,
        bbox_inches="tight",
    )
    plt.close()

    # # per category
    # fig, axes = plt.subplots(3, 3, figsize=(15, 15), sharex=True, sharey=True)
    # axes = axes.flatten()
    #
    # for ci, category in enumerate(categories):
    #     calc_correlation(
    #         category_name=category,
    #         category_both_scores=scores_cnts[
    #             [
    #                 "URAU_CODE",
    #                 "country",
    #                 f"{category}_quality",
    #                 f"{category}_poi_count",
    #             ]
    #         ],
    #         ax=axes[ci],
    #         x_suffix="poi_count",
    #         y_suffix="quality",
    #     )
    #
    # handles, labels = axes[0].get_legend_handles_labels()
    # fig.legend(handles, labels, loc="lower center", ncol=3, bbox_to_anchor=(0.5, 0.005))
    # fig.supxlabel("POI count", y=0.07, fontsize=11)
    # fig.supylabel("Mapping saturation score", fontsize=11)
    #
    # plt.tight_layout(rect=[0, 0.05, 1, 1])
    # plt.savefig(
    #     output_dir / "categories" / "poi_count_scatter_grid_by_class.png",
    #     dpi=300,
    #     bbox_inches="tight",
    # )
    # plt.close()


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/data_quality")

    poi_cnt_file = result_root_dir / "all_city_poi_cnts.gpkg"
    city_population_file = result_root_dir.parent / "cities_with_population.csv"

    total_access_score_file = result_root_dir / "all_city_scores.gpkg"
    category_access_score_dir = result_root_dir.parent / "aggregated_category_scores"
    data_quality_score_file = result_root_dir / "all_city_quality_scores.gpkg"

    configs = initialize_configs(config_file)

    calc_total_correlation(
        configs, total_access_score_file, data_quality_score_file, output_dir
    )
    calc_category_correlations(
        configs, category_access_score_dir, data_quality_score_file, output_dir
    )
    calc_correlation_pop_size(
        configs, city_population_file, data_quality_score_file, output_dir
    )
    # calc_corrlation_poi_cnt(configs, poi_cnt_file, data_quality_score_file, output_dir)
