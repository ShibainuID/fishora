from apps.main_api.config import MainSettings


def test_embedding_contract_and_secret_fields_are_environment_driven(monkeypatch):
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://fishora:fishora@localhost:55432/fishora")
    monkeypatch.setenv("OPENCODE_GO_API_KEY", "test-key")
    settings = MainSettings()
    assert settings.database_url == "postgresql+psycopg://fishora:fishora@localhost:55432/fishora"
    assert settings.embedding_model_name == "intfloat/multilingual-e5-base"
    assert settings.embedding_dimension == 768
    assert settings.embedding_device == "cpu"
    assert settings.opencode_go_base_url == "https://opencode.ai/zen/go/v1"
    assert settings.opencode_go_model == "gpt-5.6-luna"
    assert settings.opencode_go_api_key.get_secret_value() == "test-key"
    assert "test-key" not in repr(settings)


def test_opencode_key_not_required_for_settings_construction(monkeypatch):
    # Correction over the original brief: the API key is required only when the
    # production OpenCode client is constructed (a later task), so constructing
    # MainSettings for unrelated unit tests/imports must not fail without it.
    monkeypatch.delenv("OPENCODE_GO_API_KEY", raising=False)
    monkeypatch.setenv("FISHORA_DATABASE_URL", "postgresql+psycopg://fishora:fishora@localhost:55432/fishora")
    settings = MainSettings()
    assert settings.opencode_go_api_key.get_secret_value() == ""
