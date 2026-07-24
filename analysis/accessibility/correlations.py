import itertools
import json
from collections import defaultdict
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from matplotlib import pyplot as plt
from omegaconf import DictConfig, OmegaConf
from scipy.stats import spearmanr

from analysis.utils import country_map, style_map, calc_correlation_accessibility_anal
from xmin_core.utils.configure import initialize_configs


def calc_total_correlation_pop_vs_access(
    configs: DictConfig,
    total_score_descriptor: Path,
    city_population_descriptor: Path,
    city_of_interest_descriptor: Path,
    output_dir: Path,
):
    nice_ticks_real_total = [50, 100, 200, 500, 1000, 2000, 5000]

    total_access_scores = gpd.read_file(total_score_descriptor)
    city_populations = load_city_population_data(city_population_descriptor)
    cities_of_interest = OmegaConf.load(city_of_interest_descriptor)

    scores_w_pop = total_access_scores.merge(
        city_populations,
        on="URAU_CODE",
        how="left",
    )
    scores_w_pop["country"] = scores_w_pop["URAU_CODE"].str[:2].map(country_map)

    for mode, time in itertools.product(configs.mode_speeds, configs.xmin_timeframes):
        scores_w_pop_mode_time = scores_w_pop[
            [
                "URAU_CODE",
                "URAU_NAME",
                "country",
                "population",
                f"{mode}_{time}min_weighted",
            ]
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

        # spearman
        spearman_result = calc_spearman_accessibility_anal(
            category_name="overall accessibility",
            category_both_scores=scores_w_pop_mode_time,
            cities_of_interest=cities_of_interest,
        )
        with open(
            output_dir / "overall" / "correlations" / f"{mode}_{time}min_spearman.json",
            "w",
        ) as jsf:
            json.dump(spearman_result, jsf, indent=4)


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


def calc_spearman_accessibility_anal(
    category_name: str,
    category_both_scores: pd.DataFrame,
    cities_of_interest: DictConfig,
):
    spearman_result = dict()

    # based on countries
    for country, style in style_map.items():
        pts = category_both_scores[category_both_scores["country"] == country]
        country_x, country_y = pts["population"], pts[f"{category_name}"]

        # spearman
        ## overall
        rho, pval = spearmanr(
            country_x,
            country_y,
            nan_policy="omit",
        )
        spearman_result[country] = {"rho": rho, "pval": pval}

        ## small and large cities
        for city_size_type, city_list in cities_of_interest[country].items():
            pts_size_cty = pts[pts["URAU_NAME"].isin(city_list)]
            x_size_cty, y_size_cty = (
                pts_size_cty["population"],
                pts_size_cty[f"{category_name}"],
            )
            rho_size_cty, pval_size_cty = spearmanr(
                x_size_cty,
                y_size_cty,
                nan_policy="omit",
            )
            spearman_result[country].update(
                {city_size_type: {"rho": rho_size_cty, "pval": pval_size_cty}}
            )

    # based on small and large cities only
    spearman_result["overall"] = {}
    different_size_city_list = defaultdict(list)
    for country, city_size_dict in cities_of_interest.items():
        for city_size, city_list in city_size_dict.items():
            different_size_city_list[city_size].extend(city_list)

    for city_size, city_list in different_size_city_list.items():
        pts_size_all = category_both_scores[
            category_both_scores["URAU_NAME"].isin(city_list)
        ]
        x_size_all, y_size_all = (
            pts_size_all["population"],
            pts_size_all[f"{category_name}"],
        )
        rho_size_all, pval_size_all = spearmanr(
            x_size_all,
            y_size_all,
            nan_policy="omit",
        )
        spearman_result["overall"].update(
            {f"{city_size}_city": {"rho": rho_size_all, "pval": pval_size_all}}
        )

    # overall
    rho_all, pval_all = spearmanr(
        category_both_scores["population"],
        category_both_scores[f"{category_name}"],
        nan_policy="omit",
    )
    spearman_result["overall"].update({"allinall": {"rho": rho_all, "pval": pval_all}})

    return spearman_result


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/accessibility")

    total_access_score_file = result_root_dir / "all_city_scores.gpkg"
    category_access_score_dir = result_root_dir.parent / "aggregated_category_scores"
    city_population_file = result_root_dir.parent / "cities_with_population.csv"
    cities_of_interest_file = "configs/explored_cities.yaml"

    configs = initialize_configs(config_file)

    calc_total_correlation_pop_vs_access(
        configs,
        total_access_score_file,
        city_population_file,
        cities_of_interest_file,
        output_dir,
    )
    calc_category_correlation_pop_vs_access(
        configs, category_access_score_dir, city_population_file, output_dir
    )
