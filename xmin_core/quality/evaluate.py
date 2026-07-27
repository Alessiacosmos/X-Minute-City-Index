import json
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Literal, Any

import geopandas as gpd
import plotly.graph_objects as go
import requests

from omegaconf import DictConfig

from xmin_core.poi_categories.base import POICatogories
from xmin_core.quality.figure import adjust_figure_funcs
from xmin_core.quality.indicator_params import get_indicator_params
from xmin_core.settings import OhsomeQualitySettings


def evaluate_poi_quality(
    aoi: gpd.GeoDataFrame,
    indicators: list[
        Literal["map_saturation", "attribute_completeness", "currentness"]
    ],
    ohsome_quality_settings: OhsomeQualitySettings,
    poi_setting: POICatogories,
    attribute_completeness_settings: DictConfig | None,
    workdir: Path,
):
    if "attribute_completeness" in indicators:
        assert attribute_completeness_settings is not None, (
            "As you query 'attribute_completeness' quality indicator, please specify 'attribute_completeness_setting'."
        )

    aoi_geojson = aoi.__geo_interface__  # featurecollection geojson

    save_dir = workdir / "quality"
    save_dir.mkdir(exist_ok=True)

    for indicator in indicators:
        _evaluate_poi_quality_per_category = partial(
            evaluate_poi_quality_per_category,
            aoi_geojson=aoi_geojson,
            indicator=indicator,
            indicator_url=ohsome_quality_settings.indicator_url(indicator),
            savedir=save_dir,
            attribute_completeness_filters=attribute_completeness_settings,
        )

        with ThreadPool(10) as threadpool:
            result_values = threadpool.map(
                _evaluate_poi_quality_per_category, poi_setting
            )

        result_values = {
            k: v
            for category_result in result_values
            for k, v in category_result.items()
        }

        result_savename = save_dir / f"{indicator}_all.json"
        with open(result_savename, "w") as jsf:
            json.dump(result_values, jsf, indent=4)


def evaluate_poi_quality_per_category(
    category_setting: POICatogories,
    aoi_geojson: dict,
    indicator: Literal["map_saturation", "attribute_completeness", "currentness"],
    indicator_url: str,
    savedir: Path,
    attribute_completeness_filters: DictConfig,
) -> dict[str, dict[str, Any]]:
    category_name, category_value = category_setting.name, category_setting.value

    general_configs = dict(
        category_name=category_name,
        aoi_geojson=aoi_geojson,
        indicator=indicator,
        indicator_url=indicator_url,
        savedir=savedir,
    )

    if indicator == "attribute_completeness":
        quality_result = evaluate_attribute_completeness(
            general_configs,
            attribute_completeness_filters=attribute_completeness_filters,
        )
    else:
        quality_result = call_ohsome_quality_api(
            **general_configs,
            topic_filter=complete_topic_filter(category_value.to_tag()),
        )

    return {category_name: quality_result}


def evaluate_attribute_completeness(
    general_configs: dict,
    attribute_completeness_filters: DictConfig,
) -> dict[str, dict[str, Any]]:
    cate_attr_completeness_filter: DictConfig = attribute_completeness_filters.get(
        general_configs["category_name"], None
    )
    # when the category is considered in poi settings, but we don't want to consider its attribute completeness
    if cate_attr_completeness_filter is None:
        return {}

    assert (
        "topic_filter" in cate_attr_completeness_filter.keys()
        and "attribute_filter" in cate_attr_completeness_filter.keys()
    ), (
        "to calculate attribute_completeness, specific topic_filter and attribute_filter should be defined"
    )
    assert isinstance(cate_attr_completeness_filter["attribute_filter"], DictConfig), (
        "to calculate attribute_completeness, "
        "attribute_filter should be organized as a series of {<attr_filter_title>: <attr_filter_tags>}"
    )

    attr_topic_filter = complete_topic_filter(
        cate_attr_completeness_filter["topic_filter"]
    )
    quality_result = dict()
    for sub_attr_topic, sub_attr_filter in cate_attr_completeness_filter[
        "attribute_filter"
    ].items():
        attr_kwargs = dict(
            attribute_title=f"attr_{sub_attr_topic}", attribute_filter=sub_attr_filter
        )
        sub_attr_quality_result = call_ohsome_quality_api(
            **general_configs,
            topic_filter=attr_topic_filter,
            **attr_kwargs,
        )
        quality_result.update(sub_attr_quality_result)

    return quality_result


def complete_topic_filter(
    basic_filter: str,
) -> str:
    return basic_filter + " and (type:node or type:way or type:relation)"


def call_ohsome_quality_api(
    category_name: str,
    aoi_geojson: dict,
    indicator: Literal["map_saturation", "attribute_completeness", "currentness"],
    indicator_url: str,
    savedir: Path,
    topic_filter: str,
    **kwargs,
) -> dict[str, dict[str, Any]]:
    indicator_params = get_indicator_params(
        indicator,
        topic="custom-topic",
        bpolys=aoi_geojson,
        title=category_name.capitalize(),
        filter=topic_filter,
        **kwargs,
    )

    response = requests.post(
        indicator_url,
        headers={"accept": "application/json"},
        json=indicator_params,
    )

    response.raise_for_status()
    result = response.json()["result"][0]["result"]

    if indicator != "attribute_completeness":
        figure = go.Figure(result["figure"])
        figure = adjust_figure_funcs[indicator](figure)
        figure.write_json(savedir / f"{indicator}_{category_name}.json")

    result.pop("figure")

    return result
