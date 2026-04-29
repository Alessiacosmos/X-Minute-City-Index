from pathlib import Path

import logging
import osmnx as ox

from pyproj import CRS
from shapely import Polygon
from tqdm import tqdm

from xmin_core.poi_categories.base import POICatogories
from xmin_core.utils.utils import geometry_to_single_point

log = logging.getLogger(__name__)


def get_city_pois_categories(
    buffered_polygon: Polygon,
    poi_categories: POICatogories,
    est_utm_crs: CRS,
    savedir: Path,
) -> dict[str, Path]:
    # get pois for each category,
    pois_cate_filenames = {}
    for category in tqdm(
        poi_categories, total=len(poi_categories), desc="Getting POIs per category"
    ):
        log.info(f"Getting pois modes for {category.name}")
        most_pois_cate = ox.features.features_from_polygon(
            buffered_polygon, tags=category.value
        )

        # convert multiple geometries to single point
        most_pois_cate = geometry_to_single_point(most_pois_cate, est_utm_crs)

        savename = savedir / f"pois_pts_{category.name}.gpkg"
        most_pois_cate.to_file(savename, driver="GPKG")
        pois_cate_filenames[category.name] = savename

    return pois_cate_filenames
