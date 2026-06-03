import os
import logging
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from omegaconf import DictConfig, ListConfig
from rasterstats import gen_zonal_stats

from xmin_core.settings import RasterS3Settings
from xmin_core.utils.data_process import get_population_from_raster_data
from xmin_core.utils.utils import (
    normalize_score,
)

log = logging.getLogger(__name__)


def get_population_info_hex_grids(
    raster_s3_settings: RasterS3Settings,
    hexagons: gpd.GeoDataFrame,
    city_polygon: gpd.GeoDataFrame,
) -> gpd.GeoDataFrame:
    ##################
    # 1. get population raster clipped to city bbox
    ##################
    pops_city_raster = get_population_from_raster_data(
        raster_s3_settings, city_polygon, city_polygon.crs.to_epsg()
    )

    ##################
    # 2. aggregate population to hex grids
    # note: weighted_population is not necessary as population's resolution is better than hexagon size.
    ##################
    hexagons_crs = hexagons.crs
    stats = gen_zonal_stats(
        hexagons.to_crs(pops_city_raster["src_crs"]),
        pops_city_raster["clipped_raster"],
        affine=pops_city_raster["transform"],
        stats=["sum"],
        all_touched=True,
    )
    hexagons["living"] = [s["sum"] for s in stats]

    return hexagons.to_crs(hexagons_crs)


def get_xmin_index_score(
    hex_grids: gpd.GeoDataFrame,
    pois_cnt_cates_files: dict,
    mode_speeds: dict | DictConfig,
    timeframes: list | ListConfig,
    category_benchmarks: dict,
    savedir: Path,
    is_normalize: bool = True,
):
    modes = mode_speeds.keys()

    savedir = savedir / "index_score"
    savedir.mkdir(exist_ok=True)

    # calculate living_normalized
    hex_grids["living_normalized"] = np.minimum(
        hex_grids["living"].values / category_benchmarks["living"] * 100, 100
    )

    # re-organize pois_cnt based on their modes and times.
    pois_cnt_modes_times = {f"{m[:4]}_{t}": [] for m in modes for t in timeframes}
    for name_cate, pois_cnt_cate_files in pois_cnt_cates_files.items():
        for pois_cnt_cate_mode_time_file in pois_cnt_cate_files:
            # get current category's mode and timeframe key.
            pois_cnt_c_m_t_file_sp = os.path.basename(pois_cnt_cate_mode_time_file)[
                :-4
            ].split("_")
            xmin_mode, xmin_time = pois_cnt_c_m_t_file_sp[0], pois_cnt_c_m_t_file_sp[-1]
            key_mode_time = f"{xmin_mode[:4]}_{xmin_time}"

            # read file
            pois_cnt_cate_mode_time = pd.read_csv(pois_cnt_cate_mode_time_file)
            # normalize
            if is_normalize:
                pois_cnt_cate_mode_time[f"{name_cate}_normalized"] = normalize_score(
                    pois_cnt_cate_mode_time[name_cate].values,
                    category_benchmarks[name_cate],
                )

            # add one category_mode_time situation's pois_cnt to corresponding list
            pois_cnt_cate_mode_time.set_index("hex_id", inplace=True)
            pois_cnt_modes_times[key_mode_time].append(pois_cnt_cate_mode_time)

    # get score results: filenum = num_modes (e.g. cycle, foot) * num_timeframes (e.g. 15,20,25)
    normalized_columns = [
        f"{category}_normalized" for category in pois_cnt_cates_files.keys()
    ]
    for key_mode_time, pois_cnt_mode_time in pois_cnt_modes_times.items():
        pois_cnt_mode_time = pd.concat(pois_cnt_mode_time, axis=1)
        hex_grids_w_pois = hex_grids.merge(pois_cnt_mode_time, on="hex_id", how="left")

        # get total score
        hex_grids_w_pois["score"] = hex_grids_w_pois[normalized_columns].sum(
            axis=1
        ) / len(category_benchmarks)  # TODO: check why it's .mean in original code.

        # save result
        savename = savedir / f"{key_mode_time}.gpkg"
        hex_grids_w_pois.to_file(savename, driver="GPKG")
