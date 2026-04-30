from pathlib import Path

import logging
import geopandas as gpd
import osmnx as ox
from ohsome import OhsomeClient, OhsomeException

from pyproj import CRS
from shapely import Polygon
from tqdm import tqdm

from xmin_core.poi_categories.base import POICatogories
from xmin_core.utils.utils import geometry_to_single_point

log = logging.getLogger(__name__)


def get_city_pois_categories(
    ohsome_client: OhsomeClient,
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
        most_pois_cate = fetch_osm_data(
            ohsome=ohsome_client, aoi=buffered_polygon, osm_filter=category.value
        )

        # convert multiple geometries to single point
        most_pois_cate = geometry_to_single_point(most_pois_cate, est_utm_crs)

        savename = savedir / f"pois_pts_{category.name}.gpkg"
        most_pois_cate.to_file(savename, driver="GPKG")
        pois_cate_filenames[category.name] = savename

    return pois_cate_filenames


def fetch_osm_data(ohsome: OhsomeClient, aoi: Polygon, osm_filter: str) -> gpd.GeoDataFrame:
    try:
        elements = ohsome.elements.geometry.post(
            bpolys=aoi, clipGeometry=True, properties='tags', filter=osm_filter
        ).as_dataframe()
    except OhsomeException as e:
            raise e

    elements = elements.reset_index(drop=False)
    return elements[['@osmId', 'geometry', '@other_tags']]