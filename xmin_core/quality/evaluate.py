from functools import partial
from multiprocessing.pool import ThreadPool
from typing import Optional

import geopandas as gpd
import plotly.graph_objects as go
import requests

from xmin_core.poi_categories.base import POICatogories
from xmin_core.quality.indicator_params import get_indicator_params
from xmin_core.settings import OhsomeQualitySettings


def evaluate_poi_quality(
    aoi: gpd.GeoSeries,
    indicator: Optional["map_saturation", "attribute_completeness", "currentness"],
    ohsome_quality_api_settings: OhsomeQualitySettings,
    poi_setting: POICatogories,
    savedir: str,
):
    aoi_geojson = aoi.__geo_interface__  # featurecollection geojson

    _evaluate_poi_quality_per_category = partial(
        aoi="",
        indicator=indicator,
        indicator_url=ohsome_quality_api_settings.indicator_url(indicator),
        poi_setting=poi_setting,
        savedir=savedir,
    )

    with ThreadPool(10) as threadpool:
        result_values = threadpool.map(
            _evaluate_poi_quality_per_category, name_categories
        )


def evaluate_poi_quality_per_category(
    name_cate: str,
    aoi: gpd.GeoSeries,
    indicator: Optional["map_saturation", "attribute_completeness", "currentness"],
    ohsome_quality_api_settings: OhsomeQualitySettings,
    poi_setting: POICatogories,
    savedir: str,
) -> dict[str, int]:
    # todo: get topic, title, and filter from poi_setting based on name_cate
    # topic, title, filter =

    indicator_params = get_indicator_params(
        indicator, topic="", bpolys=aoi_geojson, title="", filter=""
    )

    response = requests.post(
        ohsome_quality_api_settings.indicator_url(indicator),
        headers={"accept": "application/json"},
        json=indicator_params,
    )

    response.raise_for_status()
    result = response.json()["result"][0]["result"]

    figure = go.Figure(result["figure"])
    figure.write_json(savedir / f"{aoi_name}.json")  # todo: give aoi name

    return dict(name_cate=result["value"])
