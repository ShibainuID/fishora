from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class MainSettings(BaseSettings):
    """Application settings.

    Secrets are typed as SecretStr and only exposed via get_secret_value(),
    so repr()/serialization never leaks them. The OpenCode API key is blank by
    default; it is required only when the production OpenCode client is
    constructed (a later task), not for settings construction or unit tests.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field(validation_alias=AliasChoices("FISHORA_DATABASE_URL", "database_url"))
    cv_service_url: str = Field(default="http://localhost:8001", validation_alias=AliasChoices("FISHORA_CV_SERVICE_URL", "cv_service_url"))
    cv_timeout_seconds: float = Field(default=30.0, validation_alias=AliasChoices("FISHORA_CV_TIMEOUT_SECONDS", "cv_timeout_seconds"))
    cv_max_image_bytes: int = Field(default=10 * 1024 * 1024, validation_alias=AliasChoices("FISHORA_CV_MAX_IMAGE_BYTES", "cv_max_image_bytes"))
    image_storage_dir: Path = Field(default=Path("data/images"), validation_alias=AliasChoices("FISHORA_IMAGE_STORAGE_DIR", "image_storage_dir"))
    embedding_model_name: str = Field(default="intfloat/multilingual-e5-base", validation_alias=AliasChoices("FISHORA_EMBEDDING_MODEL_NAME", "embedding_model_name"))
    embedding_dimension: int = Field(default=768, validation_alias=AliasChoices("FISHORA_EMBEDDING_DIMENSION", "embedding_dimension"))
    opencode_go_base_url: str = Field(default="https://opencode.ai/zen/go/v1", validation_alias=AliasChoices("FISHORA_OPENCODE_GO_BASE_URL", "opencode_go_base_url"))
    # ponytail: blank key allowed here; the production OpenCode client constructor enforces it.
    opencode_go_api_key: SecretStr = Field(default=SecretStr(""), validation_alias=AliasChoices("OPENCODE_GO_API_KEY", "opencode_go_api_key"))
    opencode_go_model: str = Field(default="gpt-5.6-luna", validation_alias=AliasChoices("FISHORA_OPENCODE_GO_MODEL", "opencode_go_model"))
    opencode_go_timeout_seconds: float = Field(default=60.0, validation_alias=AliasChoices("FISHORA_OPENCODE_GO_TIMEOUT_SECONDS", "opencode_go_timeout_seconds"))