from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class CVSettings(BaseSettings):
    """Runtime values for the CV inference service.

    Env vars use the FISHORA_CV_* family (consistent with FISHORA_CV_EXPORT_DIR).
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    export_dir: Path = Field(validation_alias=AliasChoices("FISHORA_CV_EXPORT_DIR", "export_dir"))
    model_version: str = Field(validation_alias=AliasChoices("FISHORA_CV_MODEL_VERSION", "model_version"))
    device: str | None = Field(default=None, validation_alias=AliasChoices("FISHORA_CV_DEVICE", "device"))
    max_image_bytes: int = Field(default=10 * 1024 * 1024, validation_alias=AliasChoices("FISHORA_CV_MAX_IMAGE_BYTES", "max_image_bytes"))