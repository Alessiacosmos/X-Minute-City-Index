import logging
import time
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from pyproj import CRS
from tqdm import tqdm

from xmin_core.settings import ORSSettings

log = logging.getLogger(__name__)


def get_reachable_poi_cnt_categories(
    ors_settings: ORSSettings,
    hex_grids: gpd.GeoDataFrame,
    city_pois_cates_files: dict,
    est_utm_crs: CRS,
    speed_modes: dict,
    timeframes: list,
    savedir: Path,
) -> dict[str, list]:
    hex_grids_crs = hex_grids.crs
    hex_grids_centroid = hex_grids.to_crs(est_utm_crs).centroid.to_crs(hex_grids_crs)
    hex_grids_centroid = list(zip(hex_grids_centroid.x, hex_grids_centroid.y))

    # for every category, calculate the durations from each hex grid to each poi
    # and get their accessibility at different timeframes
    pois_cnt_cates_files = {}
    for name_cate, pois_cate_file in city_pois_cates_files.items():
        log.info(f"Processing {name_cate}...")
        # get category's data, and convert it to list
        pois_cate = gpd.read_file(pois_cate_file)
        # pois_cate = pois_cate.reset_index()
        pois_cate_list = list(zip(pois_cate.geometry.x, pois_cate.geometry.y))

        # get one category's duration info. for different modes
        pois_cate_modes_durations = get_duration_modes_1cate(
            hex_grids_centroid=hex_grids_centroid,
            pois_cate_list=pois_cate_list,
            name_cate=name_cate,
            speed_modes=speed_modes,
            ors_settings=ors_settings,
        )

        # get the count of reachable points at different mode and timeframe, and save them
        # save to path: <savedir>/<name_cate>/<mode>__pois_cnt_<timeframe>.csv
        # includes hex_id and poi_cnt info.
        pois_cnt_cate_files = get_reachable_pois_mode_time(
            pois_cate_modes_durations=pois_cate_modes_durations,
            hex_ids=hex_grids["hex_id"].values,
            name_cate=name_cate,
            speed_modes=speed_modes,
            timeframes=timeframes,
            savedir=savedir,
        )

        pois_cnt_cates_files[name_cate] = pois_cnt_cate_files

    return pois_cnt_cates_files


def get_reachable_pois_mode_time(
    pois_cate_modes_durations: dict[str, np.ndarray[float]],
    hex_ids: np.ndarray,
    name_cate: str,
    speed_modes: dict,
    timeframes: list,
    savedir: Path,
) -> list[Path]:
    modes = speed_modes.keys()
    timeframes_second = np.asarray(timeframes) * 60

    savedir = savedir / name_cate
    savedir.mkdir(parents=True, exist_ok=True)

    # calculate the poi cnt at each mode and each timeframe, then save it to local files.
    savenames = []
    for mode in modes:
        for timeframe_s in timeframes_second:
            # todo: update here to adapt to sub categories
            hex_grids_reachable_poi_cnt_mode = np.sum(
                pois_cate_modes_durations[mode] <= timeframe_s, axis=1
            )
            hex_grids_reachable_poi_cnt_mode = pd.DataFrame(
                np.column_stack([hex_ids, hex_grids_reachable_poi_cnt_mode]),
                columns=["hex_id", name_cate],
            )
            savename = savedir / f"{mode}_pois_cnt_{timeframe_s // 60}.csv"
            hex_grids_reachable_poi_cnt_mode.to_csv(savename, index=False)

            savenames.append(savename)

    return savenames


def get_duration_modes_1cate(
    hex_grids_centroid: list,
    pois_cate_list: list,
    name_cate: str,
    speed_modes: dict,
    ors_settings: ORSSettings,
) -> dict[str, np.ndarray[float]]:
    # for different mode we will get different times
    pois_cate_modes_durations = {}
    for mode in speed_modes:
        # calculate durations between every hex grid center to every pois in one category
        pois_cate_mode_durations = get_duration_1mode_1cate(
            hex_grids_centroid,
            pois_cate_list,
            name_cate,
            mode,
            ors_settings,
        )

        pois_cate_modes_durations[mode] = pois_cate_mode_durations

    return pois_cate_modes_durations


def get_duration_1mode_1cate(
    hex_grids_centroid: list,
    pois_cate_list: list,
    name_cate: str,
    mode: str,
    ors_settings: ORSSettings,
) -> np.ndarray[float]:
    poi_batch_size = ors_settings.ors_duration_batch_size

    num_pois_cate = len(pois_cate_list)
    num_pois_batch = int(np.ceil(num_pois_cate / poi_batch_size))

    tasks = []
    for batch_idx in range(num_pois_batch):
        start_idx = batch_idx * poi_batch_size
        end_idx = min(start_idx + poi_batch_size, num_pois_cate)
        tasks.append((batch_idx, start_idx, end_idx))

    _get_duration_batch_partial = partial(
        get_duration_batch,
        center_coords=hex_grids_centroid,
        category_coords=pois_cate_list,
        mode=mode,
        ors_settings=ors_settings,
    )
    with ThreadPool(ors_settings.ors_duration_pool_number) as pool:
        results = list(
            tqdm(
                pool.starmap(_get_duration_batch_partial, tasks),
                total=num_pois_batch,
                desc=f"Durations for pois of {name_cate} ({mode})",
            )
        )

    results.sort(key=lambda x: x[0])
    ordered_batches = [batch for _, batch in results]

    pois_cate_mode_durations = np.hstack(ordered_batches)

    assert pois_cate_mode_durations.shape[1] == num_pois_cate, (
        f"calculate {pois_cate_mode_durations.shape} pois durations but should get {num_pois_cate}."
    )

    return pois_cate_mode_durations


def get_duration_batch(
    batch_idx: int,
    start_idx: int,
    end_idx: int,
    center_coords: list,
    category_coords: list,
    mode: str,
    ors_settings: ORSSettings,
) -> tuple[int, np.ndarray]:
    """
    Processes a batch of POIs to calculate travel time matrices
    :param center_coords: List of coordinates for center points
    :param category_coords: List of coordinates for the category points
    :param start_idx: Starting index of the batch
    :param end_idx: Ending index of the batch
    :param mode: foot-walking or cycling-regular
    :returns: Relevant travel durations and indices of reachable POIs within the time limit
    """
    log.debug(
        f"[batch {batch_idx}] Calculate duration time with POIs from index {start_idx} to {end_idx} for mode {mode}"
    )

    # Select the batch of category points
    batch_coords = category_coords[start_idx:end_idx]
    all_coordinates = np.vstack([batch_coords, center_coords]).tolist()
    num_batch_coords = end_idx - start_idx
    # Define the request body
    body = {
        "locations": all_coordinates,
        "sources": np.arange(num_batch_coords, len(all_coordinates), 1)
        .astype("int")
        .tolist(),
        "destinations": np.arange(0, num_batch_coords, 1).astype("int").tolist(),
        "metrics": ["duration"],
    }

    # Send the POST request to the ORS API with the dynamic URL
    response = ors_settings.client_request_session.post(
        f"{ors_settings.client._base_url}/v2/matrix/{mode}",
        json=body,
        headers=ors_settings.client_headers,
    )
    response.raise_for_status()
    data = response.json()
    # print(data)

    # Extract the duration matrix
    durations = data.get("durations", [])

    # Extract relevant part of the duration matrix (centers to batch points)
    durations = np.asarray(
        durations
    )  # [num_batch_coords:, :] # shape = [len(center_coords), len(batch_coords)]

    # sleep a while to avoid over quota limitation
    time.sleep(60 / ors_settings.ors_duration_rate_limit)

    return batch_idx, durations
