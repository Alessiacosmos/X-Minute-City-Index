import atexit
import os
import tempfile
from functools import cached_property

import openrouteservice
import requests
from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from pyrate_limiter import SQLiteBucket
from rasterio.session import AWSSession
from requests import Session
from requests.adapters import HTTPAdapter
from requests_ratelimiter import LimiterSession
from urllib3 import Retry


class RasterS3Settings(BaseSettings):
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: SecretStr
    s3_bucket: str
    s3_pop_filename: str

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    @cached_property
    def s3_client(self) -> AWSSession:
        session = AWSSession(
            endpoint_url=self.s3_endpoint,
            aws_access_key_id=self.s3_access_key,
            aws_secret_access_key=self.s3_secret_key.get_secret_value(),
        )

        return session

    @cached_property
    def pop_raster_url(self) -> str:
        return f's3://{self.s3_bucket}/{self.s3_pop_filename}'


class ORSSettings(BaseSettings):
    ors_base_url: str | None = None
    ors_api_key: str | None = None

    ors_duration_batch_size: int = 50
    ors_duration_pool_number: int = 20
    ors_duration_rate_limit: int = 100

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')  # dead: disable

    @cached_property
    def client(self) -> openrouteservice.Client:
        # For future reference maybe check this suggestion: https://gitlab.heigit.org/climate-action/plugins/walkability/-/merge_requests/82#note_61406
        if self.ors_base_url is None:
            client = openrouteservice.Client(key=self.ors_api_key)
        else:
            client = openrouteservice.Client(base_url=self.ors_base_url, key=self.ors_api_key)

        openrouteservice.client._RETRIABLE_STATUSES = {502, 503}

        return client

    @cached_property
    def client_headers(self) -> dict:
        return {
            'Accept': 'application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8',
            'Authorization': self.client._key,
            'Content-Type': 'application/json; charset=utf-8'
        }

    @cached_property
    def _session_db_path(self) -> str:
        """Creates a temp file path and registers it for deletion on exit."""
        # Create a temp file but close it immediately so the path is free
        fd, path = tempfile.mkstemp(suffix=".sqlite", prefix='ors_session_')
        os.close(fd)

        # Register the cleanup function to run when the script ends
        atexit.register(self._cleanup_temp_db, path)
        return path

    @cached_property
    def client_request_session(self) -> Session:
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods={'POST'},
        )

        request_session = LimiterSession(per_minute=self.ors_duration_rate_limit, bucket_class=SQLiteBucket, bucket_kwargs={'path': self._session_db_path})
        request_session.mount('https://', HTTPAdapter(max_retries=retries))
        request_session.mount('http://', HTTPAdapter(max_retries=retries))

        return request_session

    def _cleanup_temp_db(self, path: str):
        """Helper to delete the file when the program closes."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass