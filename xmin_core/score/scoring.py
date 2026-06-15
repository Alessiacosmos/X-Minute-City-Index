from pathlib import Path

import geopandas as gpd
from ohsome import OhsomeClient
from omegaconf import DictConfig

from xmin_core.pois.collect import get_city_pois_categories
from xmin_core.pois.reachable_pois import get_each_hexagon_reachable_pois
from xmin_core.score.calculator import (
    get_population_info_hex_grids,
    get_xmin_index_score,
)
from xmin_core.settings import RasterS3Settings, ORSSettings
from xmin_core.utils.data_process import get_hex_grids


def score_xmin_index_one_aoi(
    aoi: gpd.GeoDataFrame,
    configs: DictConfig,
    raster_s3_settings: RasterS3Settings,
    ors_settings: ORSSettings,
    ohsome_client: OhsomeClient,
    workdir: Path,
):
    poi_setting = configs.poi_setting

    ##########
    # 1. get basic geometry data: polygon + crs; hex_grids
    ##########
    # 1.1 get polygon's aoi
    # aoi = gpd.GeoDataFrame(aoi.to_frame().T, geometry='geometry', crs=org_crs)
    est_utm_crs = aoi.estimate_utm_crs()

    # 1.2 generate hex grids for each mode and timeframe
    hex_grids = get_hex_grids(aoi, hex_resolution=configs.hex_resolution)
    if hex_grids is None:
        return

    ##########
    # 2. map population and poi information to hex grids
    ##########
    # 2.1 get pois for different categories within each mode and timeframe bbox
    buffered_aoi = (
        gpd.GeoSeries(aoi.union_all(), crs=aoi.crs)
        .to_crs(est_utm_crs)
        .buffer(configs.max_buffer_distance)
        .to_crs(4326)
        .geometry.iloc[0]
    )
    pois_dir = workdir / "pois"
    pois_dir.mkdir(parents=True, exist_ok=True)
    city_pois_cates_files = get_city_pois_categories(
        ohsome_client, buffered_aoi, poi_setting, est_utm_crs, pois_dir
    )

    # 2.2 assign population to hex grid. attr: Living
    hex_grids = get_population_info_hex_grids(raster_s3_settings, hex_grids, aoi)

    # 2.3 get reachable poi counts for each category, mode, and timeframe.
    reachable_poi_files = get_each_hexagon_reachable_pois(
        ors_settings=ors_settings,
        hex_grids=hex_grids,
        city_pois_cates_files=city_pois_cates_files,
        est_utm_crs=est_utm_crs,
        speed_modes=configs.mode_speeds,
        timeframes=configs.xmin_timeframes,
        savedir=workdir,
    )

    # 3 get score
    # todo: update scoring as currently our reachable poi is saved as index lists.
    get_xmin_index_score(
        hex_grids=hex_grids,
        pois_cnt_cates_files=reachable_poi_files,
        mode_speeds=configs.mode_speeds,
        timeframes=configs.xmin_timeframes,
        category_benchmarks=poi_setting.cate_benchmarks(),
        savedir=workdir,
        is_normalize=True,
    )
