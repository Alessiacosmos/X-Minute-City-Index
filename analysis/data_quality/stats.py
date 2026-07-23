# statistic analysis by country and category
from pathlib import Path

import geopandas as gpd
import pandas as pd
import seaborn as sns
from matplotlib import pyplot as plt
from matplotlib.colors import LinearSegmentedColormap
from matplotlib.patches import Patch
from omegaconf import DictConfig

from analysis.utils import country_map, style_map
from xmin_core.utils.configure import initialize_configs


def stat_by_country(
    configs: DictConfig,
    data_quality_score_descriptor: Path,
    output_dir: Path,
):
    data_quality_scores = gpd.read_file(data_quality_score_descriptor)
    data_quality_scores["Country"] = (
        data_quality_scores["URAU_CODE"].str[:2].map(country_map)
    )

    categories = [category.name for category in configs.poi_setting] + ["total"]

    country_cat_matrix = data_quality_scores.groupby("Country")[categories].mean()

    # basic stats
    calc_summary_table(qscores=data_quality_scores, categories=categories)
    draw_boxplots_per_category_per_country(
        qscores=data_quality_scores, categories=categories, output_dir=output_dir
    )
    draw_hist_total_score_per_country(
        qscores=data_quality_scores, output_dir=output_dir
    )

    # ranking
    draw_score_ranking(
        qscores=data_quality_scores,
        categories=categories,
        output_dir=output_dir,
        rank_num=5,
    )

    # heatmap
    draw_heatmap_category_country(
        country_cat_matrix=country_cat_matrix, output_dir=output_dir
    )


def calc_summary_table(qscores: gpd.GeoDataFrame, categories: list[str]):
    summary = qscores.groupby("Country")[categories].agg(
        ["mean", "median", "std", "min", "max", "sum"]
    )

    summary.T.to_csv(output_dir / "stats_summary.csv", index=True)


def draw_boxplots_per_category_per_country(
    qscores: gpd.GeoDataFrame, categories: list[str], output_dir: Path
):
    melted = qscores.melt(
        id_vars="Country",
        value_vars=categories,
        var_name="Category",
        value_name="Mapping saturation score",
    )

    g = sns.catplot(
        data=melted[melted["Category"] != "total"],
        x="Country",
        y="Mapping saturation score",
        col="Category",
        kind="box",
        col_wrap=3,
        height=3.5,
        sharey=False,
        hue="Country",
        palette={country: styles["color"] for country, styles in style_map.items()},
    )
    g.fig.suptitle("Score distribution by country per category", y=1.02)
    g.set(ylim=(0, 100))
    g.savefig(output_dir / "boxplots_category_country.png", dpi=300)
    plt.close()

    sns.boxplot(
        data=melted[melted["Category"] == "total"],
        x="Country",
        y="Mapping saturation score",
        hue="Country",
        palette={country: styles["color"] for country, styles in style_map.items()},
        legend=False,
    )
    plt.xlabel("Country")
    plt.ylabel("Mapping Saturation score")
    plt.tight_layout()
    plt.ylim(50, 100)
    plt.savefig(output_dir / "boxplots_total_country.png", dpi=300)
    plt.close()


def draw_hist_total_score_per_country(qscores: gpd.GeoDataFrame, output_dir: Path):
    plt.figure(figsize=(8, 5))
    sns.histplot(
        data=qscores,
        x="total",
        hue="Country",
        kde=True,
        element="step",
        stat="density",
        common_norm=False,
        palette={country: styles["color"] for country, styles in style_map.items()},
    )
    plt.title("Overall mapping saturation score distribution by country")
    plt.tight_layout()
    plt.savefig(output_dir / "histogram_total_country.png", dpi=300)
    plt.close()


def draw_score_ranking(
    qscores: gpd.GeoDataFrame,
    categories: list[str],
    output_dir: Path,
    rank_num: int = 5,
):
    # by overall score
    topN = qscores.nlargest(rank_num, "total")
    bottomN = qscores.nsmallest(rank_num, "total").sort_values(
        by=["total"], ascending=False
    )

    top_bottom = pd.concat(
        [topN.assign(Group="Top 5"), bottomN.assign(Group="Bottom 5")]
    )

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = top_bottom["Group"].map(
        {f"Top {rank_num}": "#2a9d8f", f"Bottom {rank_num}": "#e76f51"}
    )
    bars = ax.barh(
        top_bottom["URAU_NAME"] + ", " + top_bottom["CNTR_CODE"],
        top_bottom["total"],
        color=colors,
    )
    ax.invert_yaxis()  # highest score at top
    ax.set_xlabel("Total mapping saturation score")
    ax.set_title(
        f"Top {rank_num} and Bottom {rank_num} cities by total mapping saturation score"
    )
    ax.bar_label(bars, fmt="%.1f", padding=3)

    ax.legend(
        handles=[
            Patch(color="#2a9d8f", label=f"Top {rank_num}"),
            Patch(color="#e76f51", label=f"Bottom {rank_num}"),
        ]
    )
    plt.tight_layout()
    plt.savefig(output_dir / "ranking_total_score.png", dpi=300)
    plt.close()

    # # by per category
    # best_per_country_per_category = dict()
    # for category in categories:
    #     best_per_country_per_category[category] = qscores.loc[
    #         qscores.groupby("Country")[category].idxmax(), ["URAU_CODE", "Country", category]
    #     ]


def draw_heatmap_category_country(country_cat_matrix: pd.DataFrame, output_dir: Path):
    colors_list = ["#e76f51", "#fdfbf7", "#2a9d8f"]
    custom_cmap = LinearSegmentedColormap.from_list("TealCoral", colors_list)

    plt.figure(figsize=(10, 4))
    sns.heatmap(
        country_cat_matrix,
        annot=True,
        fmt=".1f",
        cmap=custom_cmap,
        cbar_kws={"label": "Avg score"},
    )
    plt.xticks(rotation=30, ha="right")  # Rotates category names 45 degrees
    plt.yticks(rotation=0)
    plt.title("Average mapping saturation score by country and category")
    plt.xlabel("Category")
    plt.ylabel("Country")
    plt.tight_layout()
    plt.savefig(output_dir / "heatmap_category_country.png", dpi=300)
    plt.close()


def draw_bar_plot_per_category_per_country(
    country_cat_matrix: pd.DataFrame, output_dir: Path
):
    # NOTE: duplicated of the heatmap, so won't draw it.
    # Grouped bar chart: average score per category, grouped by country
    plot_df = country_cat_matrix.reset_index().melt(
        id_vars="Country", var_name="Category", value_name="Mapping saturation score"
    )
    plt.figure(figsize=(10, 5))
    sns.barplot(data=plot_df, x="Category", y="Mapping saturation score", hue="Country")
    plt.title("Average Data Quality Score per Category by Country")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(output_dir / "bar_grouped_category_avg_country.png", dpi=300)
    plt.close()

    # Per-category bar chart: one subplot per category, bars = countries
    g_bar = sns.catplot(
        data=plot_df,
        x="Country",
        y="Mapping saturation score",
        col="Category",
        kind="bar",
        col_wrap=3,
        height=3.5,
        sharey=False,
        palette="Set2",
    )
    g_bar.fig.suptitle(
        "Average mapping saturation score by country per category", y=1.02
    )
    g_bar.set_titles("{col_name}")
    for ax in g_bar.axes.flat:
        for container in ax.containers:
            ax.bar_label(container, fmt="%.1f", padding=2)
    g_bar.savefig(output_dir / "bar_per_category.png", dpi=300)
    plt.close()


if __name__ == "__main__":
    config_file = "configs/default.yaml"
    result_root_dir = Path(
        "/media/kta/heigit/01_Allgemein/Climate Action/x_min_city/Helix_results/accessibility_scores"
    )
    output_dir = Path("experiments/result_analysis/data_quality/stats")

    data_quality_score_file = result_root_dir / "all_city_quality_scores.gpkg"

    configs = initialize_configs(config_file)

    stat_by_country(
        configs=configs,
        data_quality_score_descriptor=data_quality_score_file,
        output_dir=output_dir,
    )
