# entrance of starting the special case, instead of call cli at command line many times
from pathlib import Path

from xmin_core.cli import xmin_index


def compute_healthcare_case(
    aoi_descriptor_dir: Path,
    config_descriptor_dir: Path,
    output_dir: Path,
):
    # todo: prepare output_dir
    #  manually copy-paste each interested city's isochrones foot-walking result to the output_dir. (to speed up)
    #  e.g. in the output_dir, we will have <output_dir>/<URAU_CODE>/isochrones/foot-walking_15min.gpkg

    for config_descriptor in config_descriptor_dir.glob("*.yaml"):
        country_code = config_descriptor.stem.split("_")[1].upper()  # e.g. DE
        xmin_index(
            aoi_descriptor=aoi_descriptor_dir / f"{country_code}_subset.gpkg",
            config_descriptor=config_descriptor,
            output_dir=output_dir,
            aoi_id_col="URAU_CODE",
            activated_funcs=[
                "accessibility"
            ],  # accessibility only, as in this special case the quality won't change
        )
