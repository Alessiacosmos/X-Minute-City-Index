import geopandas as gpd

from pyproj import CRS
from rasterio.features import shapes
from shapely import MultiPolygon, MultiLineString


################
# geometry to single point
################
def multipoly2pt(multipolys: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    def multipoly2pt_onegeom(geom: MultiPolygon):
        largest_polygon = max(geom.geoms, key=lambda p: p.area)
        return largest_polygon.centroid

    return multipolys.apply(multipoly2pt_onegeom)


def multiline2pt(multilines: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    def multiline2pt_onegeom(geom: MultiLineString):
        longest_line = max(geom.geoms, key=lambda line: line.length)
        midpt = longest_line.interpolate(0.5, normalized=True)
        return midpt

    return multilines.apply(multiline2pt_onegeom)


geom2pt_operations = {
    "LineString": lambda g: g.interpolate(0.5, normalized=True),  # return Point
    "Polygon": lambda g: g.centroid,
    "MultiLineString": multiline2pt,
    "MultiPolygon": multipoly2pt,
    "GeometryCollection": lambda g: g.union_all().centroid,
}


def geometry_to_single_point(
    geom_gpd: gpd.GeoDataFrame, est_utm_crs: CRS
) -> gpd.GeoDataFrame:
    geom_gpd["geometry"] = geom_gpd["geometry"].to_crs(crs=est_utm_crs)
    for geom_type in geom_gpd.geometry.type.unique():
        if geom_type == "Point":
            continue
        # Create a boolean mask for the current geometry type
        is_type = geom_gpd.geom_type == geom_type

        # Apply the operation_func (either vectorized or targeted apply)
        # only to the subset of rows matching the mask.
        operation_func = geom2pt_operations[geom_type]
        geom_gpd.loc[is_type, "geometry"] = operation_func(
            geom_gpd.loc[is_type, "geometry"]
        )

    geom_gpd["geometry"] = geom_gpd["geometry"].to_crs(epsg=4326)
    return geom_gpd


################
# raster image to gdf
################
def raster_to_gdf(data, transform, crs) -> gpd.GeoDataFrame:
    """Convert raster array to GeoDataFrame of pixels"""
    mask = data >= 0
    geoms = [
        {"properties": {"raster_val": v}, "geometry": s}
        for i, (s, v) in enumerate(shapes(data, mask=mask, transform=transform))
    ]

    # 3. & 4. Convert to GeoDataFrame
    return gpd.GeoDataFrame.from_features(geoms, crs=crs)


################
# get hexogon within city boundary
################
def area_ratio_within_city(hexagon, city_union) -> float:
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
def normalize_score(value, benchmark) -> float:
    """
    normalize the value to a score between 0 and 100 based on the benchmark.
    :param value: the value to be normalized
    :param benchmark: the benchmark value for normalization (e.g., 5 for commerce category)
    """
    if benchmark == 0:
        return 0

    # another way with growth_rate - making it grow fast at start and then slow.
    # np.minimum((1 - np.exp(-growth_rate/benchmark * value)) * 100, 100) # log_benchmark(value) * 100, capped at 100
    return min(100, value / benchmark * 100)
