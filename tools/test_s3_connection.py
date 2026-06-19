import rasterio

from xmin_core.settings import RasterS3Settings


def check_s3_connection() -> bool:
    """
    Validates that the s3_endpoint is reachable and the s3_bucket exists
    using the configured rasterio AWSSession.
    """
    s3_settings = RasterS3Settings()

    try:
        # Inject the AWSSession into the GDAL context loop
        with rasterio.Env(s3_settings.s3_client, AWS_VIRTUAL_HOSTING=False):
            with rasterio.open(s3_settings.pop_raster_url) as src:
                print(src.meta)
            return True

    except Exception as e:
        # Catch GDAL execution errors or bad credential exceptions
        print(
            f"S3 Connection Failed for bucket '{s3_settings.s3_bucket}' at endpoint '{s3_settings.s3_endpoint}'"
        )
        raise e


if __name__ == "__main__":
    check_s3_connection()
