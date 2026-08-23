import json


def test_loader_imports_generated_wrapper(tmp_path):
    (tmp_path / "inference_config.json").write_text(json.dumps({"model_name": "test", "classes": ["tuna"]}), encoding="utf-8")
    (tmp_path / "model_state_dict.pt").write_bytes(b"test-state")
    (tmp_path / "inference.py").write_text(
        "class FishoraClassifier:\n"
        "    instances = 0\n"
        "    def __init__(self, export_dir, device=None):\n"
        "        type(self).instances += 1\n"
        "        self.export_dir = export_dir\n",
        encoding="utf-8",
    )
    from apps.cv_service.runtime import load_classifier

    loaded = load_classifier(tmp_path, "cpu")
    assert loaded.export_dir == tmp_path


def test_loader_requires_generated_files_and_wrapper_symbol(tmp_path):
    from apps.cv_service.runtime import load_classifier

    (tmp_path / "inference_config.json").write_text(json.dumps({"model_name": "test"}), encoding="utf-8")
    (tmp_path / "model_state_dict.pt").write_bytes(b"test-state")
    (tmp_path / "inference.py").write_text("NOT_A_CLASSIFIER = 1\n", encoding="utf-8")

    import pytest

    with pytest.raises(Exception):
        load_classifier(tmp_path, "cpu")


def test_app_startup_loads_the_classifier_once(monkeypatch, tmp_path):
    from apps.cv_service.main import create_cv_app

    calls = []
    monkeypatch.setattr("apps.cv_service.main.load_classifier", lambda export_dir, device: calls.append((export_dir, device)) or object())
    from apps.cv_service.config import CVSettings
    from fastapi.testclient import TestClient

    settings = CVSettings(export_dir=tmp_path, device="cpu", model_version="test-export-1")
    with TestClient(create_cv_app(settings=settings)) as client:
        assert client.get("/health").status_code == 200
        assert client.get("/health").status_code == 200
    assert len(calls) == 1