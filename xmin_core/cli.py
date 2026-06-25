import logging
from pathlib import Path
from typing import Literal

import geopandas as gpd
import ohsome
from jsonargparse import auto_cli
from tqdm import tqdm

from xmin_core.quality.evaluate import evaluate_poi_quality
from xmin_core.score.scoring import score_xmin_index_one_aoi
from xmin_core.settings import RasterS3Settings, ORSSettings, OhsomeQualitySettings
from xmin_core.utils.configure import initialize_configs

logger = logging.getLogger(__name__)


def xmin_index(
    aoi_descriptor: Path,
    config_descriptor: Path,
    output_dir: Path,
    aoi_id_col: str = None,
    activated_funcs: list[Literal["accessibility", "quality"]] = ["accessibility"],
    quality_indicators: list[
        Literal["map_saturation", "attribute_completeness", "currentness"]
    ] = None,
):
    """
    Calculate x-min accessibility index for the given AOIs and save results to output_dir.
    :param aoi_descriptor: Areas of interest descriptor (*.geojson, *.gpkg, *.shp)
    :param config_descriptor: configs to specify the settings for the index calculation,
                              including POI categories, timeframes, mode speeds, etc.
    :param output_dir: Path where the output layers will be saved.
                       For each AOI, a subdirectory named 'aoi_{id}' will be created to store the results.
    :param aoi_id_col: AOI ID column's name e.g. URAU_CODE
    :param activated_funcs: what function you want to activated, accessibility (score) or (ohsome) quality
    :param quality_indicators: what indicator we want to calculate based on ohsome_quality_api
    :return:
    """
    # initialize settings
    logger.info("Initializing settings...")
    raster_s3_settings = RasterS3Settings()
    ors_settings = ORSSettings()
    ohsome_client = ohsome.OhsomeClient(
        user_agent="CA Research Xmin-city Accessibility"
    )
    ohsome_quality_settings = OhsomeQualitySettings()

    # initialize configs
    logger.info(f"Initializing configs from {config_descriptor}...")
    configs = initialize_configs(config_descriptor)
    logger.info(f"POI setting: {configs.poi_setting.__name__}")

    # run the index calculation
    logger.info("Calculating x-min accessibility index...")

    aois = gpd.read_file(aoi_descriptor).to_crs("EPSG:4326")
    logger.info(f"{len(aois)} AOIs found")

    for idx in tqdm(range(len(aois)), desc="Processing AOIs"):
        aoi = aois.iloc[[idx]]

        aoi_id = aoi[aoi_id_col].values[0] if aoi_id_col in aoi.columns else idx
        aoi_workdir = output_dir / f"{aoi_id}"
        aoi_workdir.mkdir(parents=True, exist_ok=True)

        # save aoi information to the workdir
        aoi.to_file(aoi_workdir / f"aoi_{aoi_id}.geojson", driver="GeoJSON")

        if "accessbility" in activated_funcs:
            score_xmin_index_one_aoi(
                aoi=aoi,
                configs=configs,
                raster_s3_settings=raster_s3_settings,
                ors_settings=ors_settings,
                ohsome_client=ohsome_client,
                workdir=aoi_workdir,
            )

        if "quality" in activated_funcs and quality_indicators is not None:
            # todo: buffer the aoi
            evaluate_poi_quality(
                aoi=aois.iloc[[idx]],  # geoseries
                indicators=quality_indicators,
                ohsome_quality_settings=ohsome_quality_settings,
                poi_setting=configs.poi_setting,
                workdir=aoi_workdir,
            )

    logger.info(
        f"xmin accessibility index calculation completed. Results saved to {output_dir}"
    )


if __name__ == "__main__":
    auto_cli(xmin_index, as_positional=False)
