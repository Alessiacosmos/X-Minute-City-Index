import geopandas as gpd

from enum import Enum

import numpy as np
from pyproj import CRS
from rasterio.features import shapes
from shapely import MultiPolygon, MultiLineString

#############################################################################################
# basic setting
#############################################################################################
XMIN_Timeframse = [15, 20, 25, 30]

MODE_SPEEDS = {
    'foot-walking': 1.3889,       # m/s (5 km/h)
    'cycling-regular': 4.1667     # m/s (15 km/h)
}

BUFFER_DISTANCES = {
    mode: {t: speed * t * 60 for t in XMIN_Timeframse} for mode, speed in MODE_SPEEDS.items() # m
}

MAX_BUFFER_DISTANCE = max(MODE_SPEEDS.values()) * max(XMIN_Timeframse) * 60

# Set the  H3 resolution (higher numbers means smaller hexagons)
HEX_RESOLUTION = 8

CATEGORY_BENCHMARKS = {
    'commerce': 5,
    'healthcare': 5,
    'education': 5,
    'entertainment': 20,
    'living': 2000
}


class FacilitiesCategories(Enum):
    commerce = {
        'shop': ['supermarket', 'convenience', 'bakery', 'grocery'],
        'amenity': ['marketplace', 'bank', 'post_box', 'atm', 'post_office']
    }

    healthcare = {
        'amenity': ['pharmacy', 'doctors', 'dentist', 'hospital', 'clinic'],
        'leisure': ['park', 'garden', 'fitness_centre', 'fitness_station', 'playground', 'sports_centre'],
        'landuse': ['recreation_ground', 'forest'],
        'club': ['sport'],
    }

    education = {
        'amenity': ['kindergarten', 'childcare', 'school']
    }

    entertainment = {
        'amenity': ['restaurant', 'fast_food', 'café', 'bar', 'pub', 'ice_cream', 'night_club', 'biergarten', 'library',
                    'theatre', 'museum', 'cinema', 'arts_centre', 'community_centre', 'events_venue'],
        'sport': ['swimming']
    }



################
# geometry to single point
################
def multipoly2pt(multipolys: gpd.GeoDataFrame):
    def multipoly2pt_onegeom(geom: MultiPolygon):
        largest_polygon = max(geom.geoms, key=lambda p: p.area)
        return largest_polygon.centroid
    return multipolys.apply(multipoly2pt_onegeom)


def multiline2pt(multilines: gpd.GeoDataFrame):
    def multiline2pt_onegeom(geom: MultiLineString):
        longest_line = max(geom.geoms, key=lambda l: l.length)
        midpt = longest_line.interpolate(0.5, normalized=True)
        return midpt
    return multilines.apply(multiline2pt_onegeom)

geom2pt_operations = {
    'LineString': lambda g: g.interpolate(0.5, normalized=True), # return Point
    'Polygon': lambda g: g.centroid,
    'MultiPolygon': multipoly2pt,
    'MultiLineString': multiline2pt,
}
def geometry_to_single_point(geom_gpd: gpd.GeoDataFrame, est_utm_crs: CRS):
    geom_gpd['geometry'] = geom_gpd['geometry'].to_crs(crs=est_utm_crs)
    for geom_type in geom_gpd.geometry.type.unique():
        if geom_type == 'Point': continue
        # Create a boolean mask for the current geometry type
        is_type = geom_gpd.geom_type == geom_type

        # Apply the operation_func (either vectorized or targeted apply)
        # only to the subset of rows matching the mask.
        operation_func = geom2pt_operations[geom_type]
        geom_gpd.loc[is_type, 'geometry'] = operation_func(geom_gpd.loc[is_type, 'geometry'])

    geom_gpd['geometry'] = geom_gpd['geometry'].to_crs(epsg=4326)
    return geom_gpd


################
# raster image to gdf
################
def raster_to_gdf(data, transform, crs):
    """Convert raster array to GeoDataFrame of pixels"""
    mask = data >= 0
    geoms = [
        {'properties': {'raster_val': v}, 'geometry': s}
        for i, (s, v) in enumerate(shapes(data, mask=mask, transform=transform))
    ]

    # 3. & 4. Convert to GeoDataFrame
    return gpd.GeoDataFrame.from_features(geoms, crs=crs)


################
# get hexogon within city boundary
################
def area_ratio_within_city(hexagon, city_union):
    """
    calculates the intersection area ratio of each hexagon within the city boundariy
    :param hexagon: hexagon GeoDataframe
    :param city_union: unary union of the city boundary geometries
    :return: intersection area in %
    """
    # Calculate the intersection of the hexagon with the city boundary
    intersection = hexagon.intersection(city_union)
    # Calculate the area ratio (intersection area / hexagon area)
    return intersection.area / hexagon.area if hexagon.area > 0 else 0


################
# normalize each categories' counts
################
def normalize_score(value, benchmark, growth_rate=10):
    """
    normalize the value to a score between 0 and 100 based on the benchmark and growth rate.
    :param value: the value to be normalized
    :param benchmark: the benchmark value for normalization (e.g., 5 for commerce category)
    :param growth_rate: the growth rate for the exponential function (default: 10). Bigger rate means faster growth.
    """
    if benchmark == 0:
        return 0
    return np.minimum((1 - np.exp(-growth_rate/benchmark * value)) * 100, 100) # log_benchmark(value) * 100, capped at 100