import json
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path
from typing import Literal

import geopandas as gpd
import plotly.graph_objects as go
import requests

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
    workdir: Path,
):
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
            json.dump(result_values, jsf)


def evaluate_poi_quality_per_category(
    category_setting: POICatogories,
    aoi_geojson: dict,
    indicator: Literal["map_saturation", "attribute_completeness", "currentness"],
    indicator_url: str,
    savedir: Path,
) -> dict[str, int]:
    category_name, category_value = category_setting.name, category_setting.value

    category_filter = (
        category_value.to_tag() + " and (type:node or type:way or type:relation)"
    )

    indicator_params = get_indicator_params(
        indicator,
        topic="custom-topic",
        bpolys=aoi_geojson,
        title=category_name.capitalize(),
        filter=category_filter,
    )

    response = requests.post(
        indicator_url,
        headers={"accept": "application/json"},
        json=indicator_params,
    )

    response.raise_for_status()
    result = response.json()["result"][0]["result"]

    figure = go.Figure(result["figure"])
    figure = adjust_figure_funcs[indicator](figure)
    figure.write_json(savedir / f"{indicator}_{category_name}.json")

    return {category_name: result["value"]}
