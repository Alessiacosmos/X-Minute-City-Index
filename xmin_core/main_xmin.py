import argparse
from pathlib import Path

from xmin_core.score.scoring import score_xmin_index_one_aoi
from xmin_core.settings import RasterS3Settings, ORSSettings
from xmin_core.utils.configure import initialize_configs
from xmin_core.utils.data_process import get_city_bboxes


def parser_args():
    parser = argparse.ArgumentParser(description="XMin city composite index")
    parser.add_argument(
        "--city",
        type=str,
        required=True,
        help="City name you want to analyze.",
    )
    parser.add_argument(
        "--config-descriptor",
        type=str,
        required=True,
        help="config file path",
    )
    return parser.parse_args()


def main_xmin(
    city_name: str,
    config_descriptor: Path,
    raster_s3_settings: RasterS3Settings,
    ors_settings: ORSSettings,
):
    savedir = Path(f"./experiments/{city_name}")

    ##########
    # 1. get basic geometry and config
    ##########
    # 1.1 get buffered bounding boxes for each mode and timeframe
    city_polygon, est_utm_crs = get_city_bboxes(
        city_name
    )  # pd.DataFrame, columns: minx, miny, maxx, maxy, mode, timeframe

    # 1.2 load config
    configs = initialize_configs(config_descriptor)

    ##########
    # 2. scoring
    ##########
    score_xmin_index_one_aoi(
        aoi=city_polygon,
        configs=configs,
        raster_s3_settings=raster_s3_settings,
        ors_settings=ors_settings,
        workdir=savedir,
    )


if __name__ == "__main__":
    args = parser_args()
    city_name = args.city
    config_descriptor = Path(args.config_descriptor)
    print(f"Analyzing data for city: {city_name}")

    # initialize settings
    raster_s3_settings = RasterS3Settings()
    ors_settings = ORSSettings()

    main_xmin(city_name, config_descriptor, raster_s3_settings, ors_settings)
