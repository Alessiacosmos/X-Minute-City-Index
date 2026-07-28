import atexit
import os
from contextlib import contextmanager
from functools import cached_property
from typing import Optional

import openrouteservice
import rasterio
from pydantic import SecretStr, field_validator
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

    # optional override — if set, local file is used instead of S3
    local_pop_path: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @field_validator("local_pop_path", mode="before")
    @classmethod
    def blank_to_none(cls, v):
        if v is None:
            return None
        if isinstance(v, str) and v.strip() == "":
            return None
        return v

    @property
    def use_local(self) -> bool:
        return self.local_pop_path is not None

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
        if self.use_local:
            return self.local_pop_path

        return f"s3://{self.s3_bucket}/{self.s3_pop_filename}"

    @contextmanager
    def raster_env(self):
        if self.s3_client:
            with rasterio.Env(session=self.s3_client, AWS_VIRTUAL_HOSTING=False):
                yield
        else:
            yield


class ORSSettings(BaseSettings):
    ors_base_url: str = "https://api.heigit.org/openrouteservice"
    ors_api_key: str | None = None

    ors_duration_batch_size: int = 500
    ors_duration_pool_number: int = 5
    ors_duration_rate_limit: int = 40

    ors_isochrone_batch_size: int = 5
    ors_isochrone_pool_number: int = 1  # 4
    ors_isochrone_rate_limit: int = 40

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")  # dead: disable

    @cached_property
    def client(self) -> openrouteservice.Client:
        # For future reference maybe check this suggestion: https://gitlab.heigit.org/climate-action/plugins/walkability/-/merge_requests/82#note_61406
        if self.ors_base_url is None:
            client = openrouteservice.Client(
                key=self.ors_api_key, retry_over_query_limit=True
            )
        else:
            client = openrouteservice.Client(
                base_url=self.ors_base_url,
                key=self.ors_api_key,
                retry_over_query_limit=True,
            )

        openrouteservice.client._RETRIABLE_STATUSES = {502, 503}

        return client

    @cached_property
    def client_headers(self) -> dict:
        return {
            "Accept": "application/json, application/geo+json, application/gpx+xml, img/png; charset=utf-8",
            "Authorization": self.client._key,
            "Content-Type": "application/json; charset=utf-8",
        }

    @cached_property
    def _session_db_path(self) -> str:
        """Creates a temp file path and registers it for deletion on exit."""
        path = "./resources/ors_rate_limit_shared.sqlite"

        # Register the cleanup function to run when the script ends
        atexit.register(self._cleanup_temp_db, path)
        return path

    @cached_property
    def client_request_session(self) -> Session:
        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
            allowed_methods={"POST"},
        )

        request_session = LimiterSession(
            per_minute=self.ors_duration_rate_limit,
            bucket_class=SQLiteBucket,
            bucket_kwargs={"path": self._session_db_path},
        )
        request_session.mount("https://", HTTPAdapter(max_retries=retries))
        request_session.mount("http://", HTTPAdapter(max_retries=retries))

        return request_session

    def _cleanup_temp_db(self, path: str):
        """Helper to delete the file when the program closes."""
        try:
            if os.path.exists(path):
                os.remove(path)
        except OSError:
            pass


class OhsomeQualitySettings(BaseSettings):
    ohsome_quality_base_url: str = "https://api.quality.ohsome.org/v1-test"
    ohsome_quality_endpoint: str = "/indicators"

    indicator_map_saturation: str = "/mapping-saturation"
    indicator_attribute_completeness: str = "/attribute-completeness"
    indicator_currentness: str = "currentness"

    ohsome_quality_headers: dict[str, str] = {"accept": "application/json"}

    # ref: https://github.com/GIScience/ohsome-quality-api-examples/blob/main/OQAPI_grid_request.py
    @cached_property
    def base_indicator_url(self) -> str:
        return self.ohsome_quality_base_url + self.ohsome_quality_endpoint

    def indicator_url(self, indicator: str) -> str:
        """Query URL for a given indicator name, e.g. 'mapping_saturation'."""
        key = f"indicator_{indicator}"
        path = getattr(self, key, None)
        if path is None:
            raise ValueError(
                f"Unknown indicator: '{indicator}'. No setting '{key}' found."
            )
        return self.base_indicator_url + path
