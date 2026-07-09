import logging
import time
from functools import partial
from multiprocessing.pool import ThreadPool
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
from openrouteservice.exceptions import ApiError
from pyproj import CRS
from tqdm import tqdm

from xmin_core.settings import ORSSettings

log = logging.getLogger(__name__)


def get_each_hexagon_reachable_pois(
    ors_settings: ORSSettings,
    hex_grids: gpd.GeoDataFrame,
    city_pois_cates_files: dict,
    est_utm_crs: CRS,
    speed_modes: dict,
    timeframes: list,
    savedir: Path,
) -> dict[str, list]:
    hex_grids_crs = hex_grids.crs
    hex_centroids = hex_grids.to_crs(est_utm_crs).centroid.to_crs(hex_grids_crs)
    hex_centroids.name = "geometry"
    hex_centroids = gpd.GeoDataFrame(
        pd.concat([hex_grids["hex_id"], hex_centroids], axis=1), crs=hex_grids_crs
    )
    # hex_grids_centroid = list(zip(hex_grids_centroid.x, hex_grids_centroid.y))

    # create isochrones, which is defined by hexagon centers, and speed mode and timeframes.
    isochrone_dir = savedir / "isochrones"
    isochrone_dir.mkdir(parents=True, exist_ok=True)
    isochrone_savenames = create_isochrones(
        ors_settings, hex_centroids, speed_modes, timeframes, isochrone_dir
    )

    # for every category, calculate the durations from each hex grid to each poi
    # and get their accessibility at different timeframes
    reachable_pois_cates_files = {}
    for name_cate, pois_cate_file in city_pois_cates_files.items():
        log.info(f"Processing {name_cate}...")
        # get category's data, and convert it to list
        pois_cate = gpd.read_file(pois_cate_file)

        # do intersection with isochrones to get the reachable pois for each hexagon at different mode and timeframe, and save them
        for isochrone_file in tqdm(
            isochrone_savenames,
            total=len(isochrone_savenames),
            desc="Calculating reachable pois in isochrones",
        ):
            isochrone = gpd.read_file(isochrone_file)
            mode_time_str = isochrone_file.stem

            savename = (
                savedir
                / "scores"
                / f"{mode_time_str}"
                / f"{name_cate}_reachable_pois.gpkg"
            )
            # if savename.exists():
            #     if name_cate not in reachable_pois_cates_files:
            #         reachable_pois_cates_files[name_cate] = []
            #     reachable_pois_cates_files[name_cate].append(savename)
            #     continue

            # spatial join to get the reachable pois for each hexagon at this mode and timeframe
            # join_result will have columns: hex_id, geometry (isochrone), and poi info (from pois_cate) incl. tags
            join_result = gpd.sjoin(
                isochrone, pois_cate, predicate="intersects", how="left"
            )

            # re-organize it.
            reachable_poi_id_map = (
                join_result.groupby("hex_id")["@osmId"]
                .apply(lambda s: s.dropna().tolist())
                .to_dict()
            )

            isochrone["poi_ids"] = (
                isochrone["hex_id"]
                .map(reachable_poi_id_map)
                .apply(lambda x: x if isinstance(x, list) else [])
            )

            savename.parent.mkdir(parents=True, exist_ok=True)
            isochrone.to_file(savename)

            if name_cate not in reachable_pois_cates_files:
                reachable_pois_cates_files[name_cate] = []
            reachable_pois_cates_files[name_cate].append(savename)

    return reachable_pois_cates_files


def create_isochrones(
    ors_settings: ORSSettings,
    centroids: gpd.GeoDataFrame,
    speed_modes: dict,
    timeframes: list,
    savedir: Path,
) -> list[Path]:
    batched_centroids = batch_hexes(centroids, ors_settings.ors_isochrone_batch_size)

    isochrone_savenames = []
    for mode in speed_modes:
        for time_range in timeframes:
            savename = savedir / f"{mode}_{time_range}min.gpkg"
            savename_abnormal_hex_ids = (
                savename.parent / f"{savename.stem}_abnormal_hex_ids.txt"
            )
            if savename.exists():
                # pre-processing to check the abnormal hexagons that cannot create isochrones, and save them to a txt file
                if savename_abnormal_hex_ids.exists():
                    abnormal_hex_ids = np.loadtxt(savename_abnormal_hex_ids, dtype=str)
                    abnormal_centroids = centroids[
                        centroids["hex_id"].isin(abnormal_hex_ids)
                    ]
                    batched_centroids = batch_hexes(abnormal_centroids, 1)
                else:
                    isochrone_savenames.append(savename)
                    continue

            _get_isochrone_batch_partial = partial(
                create_isochrone_batch,
                mode=mode,
                time_range=time_range * 60,
                ors_settings=ors_settings,
            )

            with ThreadPool(ors_settings.ors_isochrone_pool_number) as pool:
                iso_1mode_1time_with_abnormal_info = list(
                    tqdm(
                        pool.map(_get_isochrone_batch_partial, batched_centroids),
                        total=len(batched_centroids),
                        desc=f"Isochrones for hexagons ({mode})",
                    )
                )

            iso_results, abnormal_hex_ids = zip(*iso_1mode_1time_with_abnormal_info)

            # append the new isochrones calculated from abnormal hexagons to the existing isochrones
            if savename.exists():
                # all abnormal hexagons cannot create isochrones, so we don't need to append anything
                if all(x is None for x in iso_results):
                    continue
                iso_1mode_1time = gpd.read_file(savename)
                iso_1mode_1time = gpd.GeoDataFrame(
                    pd.concat(
                        [iso_1mode_1time, pd.concat(iso_results)], ignore_index=True
                    ),
                    crs=centroids.crs,
                )
            else:
                iso_1mode_1time = gpd.GeoDataFrame(
                    pd.concat(iso_results), crs=centroids.crs
                )
            abnormal_hex_ids = np.unique(np.hstack(abnormal_hex_ids))

            assert (len(iso_1mode_1time) + len(abnormal_hex_ids)) == len(centroids), (
                f"calculate {len(iso_1mode_1time)} hexagon's isochrones but should get {len(centroids)}."
            )

            iso_1mode_1time.to_file(savename)
            isochrone_savenames.append(savename)

            if len(abnormal_hex_ids) > 0:
                np.savetxt(
                    savename_abnormal_hex_ids,
                    abnormal_hex_ids,
                    fmt="%s",
                )

    return isochrone_savenames


def batch_hexes(centroids: gpd.GeoDataFrame, batch_size: int) -> list[gpd.GeoDataFrame]:
    batched_centroids = []
    for i in range(0, len(centroids), batch_size):
        batched_centroids.append(centroids.iloc[i : i + batch_size].reset_index())

    return batched_centroids


def create_isochrone_batch(
    centroid_batch: gpd.GeoDataFrame,
    mode: str,
    time_range: int,
    ors_settings: ORSSettings,
) -> tuple[gpd.GeoDataFrame, list[str]]:
    """
    Processes a batch of POIs to calculate travel time matrices
    :param center_coords: List of coordinates for center points
    :param mode: foot-walking or cycling-regular
    :param time_range: timeframe, e.g 5*60 seconds
    :returns: Relevant travel durations and indices of reachable POIs within the time limit
    """
    log.debug(
        f"Calculate isochrone for mode {mode} and timeframes {time_range // 60} minutes"
    )

    # Send the POST request to the ORS API with the dynamic URL
    iso, abnormal_hex_ids = None, []
    try:
        isochrones = ors_settings.client.isochrones(
            locations=list(zip(centroid_batch.geometry.x, centroid_batch.geometry.y)),
            profile=mode,
            range=[time_range],
            location_type="start",
            range_type="time",
        )
        iso = gpd.GeoDataFrame.from_features(
            isochrones, crs=centroid_batch.crs
        )  # [index, geometry, properties]
        # sleep a while to avoid over quota limitation
        time.sleep(60 / ors_settings.ors_duration_rate_limit)
        iso["hex_id"] = centroid_batch["hex_id"].values
    except Exception as e:
        print("[isochrone calculation error] - ")
        if (
            isinstance(e, ApiError)
            and e.args[0] == 500
            and e.message.get("error", {}).get("code") == 3099
        ):
            # cannot create isochrone (because the region is too far away from the road (may be at the sea)
            abnormal_hex_ids.append(centroid_batch["hex_id"].values)
        else:
            raise e

    if len(abnormal_hex_ids) > 0:
        abnormal_hex_ids = np.hstack(abnormal_hex_ids).tolist()

    return iso, abnormal_hex_ids
