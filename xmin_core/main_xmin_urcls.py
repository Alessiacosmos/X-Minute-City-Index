import argparse
from pathlib import Path


from xmin_core.cli import xmin_index


def main_xmin_urcls(config_descriptor: Path, workdir: Path):
    ##########
    # 1. get basic geometry data: aois in urcls data & create buffer for max distance based on mode and timeframe
    ##########
    # 1.1 get aois
    urcls_path = workdir / "urcls_4229_int_poly" / "urcls_4229_int_poly.shp"

    xmin_index(
        aoi_descriptor=urcls_path,
        config_descriptor=config_descriptor,
        output_dir=workdir,
    )


def parser_args():
    parser = argparse.ArgumentParser(description="XMin city composite index")
    parser.add_argument(
        "--config",
        type=str,
        default="./configs/default.yaml",
        help="config file path",
    )
    parser.add_argument(
        "--output_dir",
        type=str,
        default="./experiments/urcls",
        help="work directory which saves GHSL settlement AOIs and will save all results.",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parser_args()

    main_xmin_urcls(Path(args.config), Path(args.output_dir))
