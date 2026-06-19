from pathlib import Path

import logging
import geopandas as gpd
import pandas as pd
from ohsome import OhsomeClient, OhsomeException

from pyproj import CRS
from shapely import Polygon
from tqdm import tqdm

from xmin_core.poi_categories.base import POICatogories, SubCategory, Category

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
        cate_pois = []
        for subcategory in category.value.subcategories:
            log.info(f"Getting pois for {subcategory}")
            if isinstance(subcategory, Category):
                subcategory = subcategory.subcategories
            else:
                subcategory = [subcategory]
            subcate_pois = get_pois_sub_categories(
                subcategories=subcategory,
                ohsome_client=ohsome_client,
                buffered_polygon=buffered_polygon,
            )
            cate_pois.extend(subcate_pois)

        cate_pois = pd.concat(cate_pois, ignore_index=True)
        cate_pois.drop_duplicates(
            subset=["@osmId", "geometry", "sub_category"], inplace=True
        )

        savename = savedir / f"pois_pts_{category.name}.gpkg"
        cate_pois.to_file(savename, driver="GPKG")
        pois_cate_filenames[category.name] = savename

    return pois_cate_filenames


def get_pois_sub_categories(
    subcategories: list[SubCategory],
    ohsome_client: OhsomeClient,
    buffered_polygon: Polygon,
) -> list[gpd.GeoDataFrame]:
    parent_cate_pois = []
    for leaf_cateogry in subcategories:
        leaf_cate_pois = fetch_osm_data(
            ohsome=ohsome_client, aoi=buffered_polygon, osm_filter=leaf_cateogry.tag
        )
        leaf_cate_pois["sub_category"] = leaf_cateogry.name
        parent_cate_pois.append(leaf_cate_pois)

    return parent_cate_pois


def fetch_osm_data(
    ohsome: OhsomeClient, aoi: Polygon, osm_filter: str
) -> gpd.GeoDataFrame:
    try:
        elements = ohsome.elements.geometry.post(
            bpolys=aoi, clipGeometry=True, properties="tags", filter=osm_filter
        ).as_dataframe()
    except OhsomeException as e:
        raise e

    elements = elements.reset_index(drop=False)
    print(elements)
    return elements[["@osmId", "geometry", "@other_tags"]]
