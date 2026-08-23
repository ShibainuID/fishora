from io import BytesIO

from PIL import Image
from fastapi.testclient import TestClient


def jpeg_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (32, 16), "white").save(buffer, format="JPEG")
    return buffer.getvalue()


def png_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (16, 32), "blue").save(buffer, format="PNG")
    return buffer.getvalue()


class FakeClassifier:
    def __init__(self, low_confidence: bool = False):
        self.calls = 0
        self.low_confidence = low_confidence

    def predict(self, image, top_k=3):
        self.calls += 1
        confidence = 0.41 if self.low_confidence else 0.71
        return {
            "status": "low_confidence_human_verification_required" if self.low_confidence else "confident_prediction",
            "prediction": {"label": "tuna", "confidence": confidence},
            "top_candidates": [
                {"label": "tuna", "confidence": confidence},
                {"label": "tenggiri", "confidence": 0.18},
                {"label": "gembolo", "confidence": 0.08},
            ],
            "threshold": 0.80,
        }


def _client(classifier: FakeClassifier, max_image_bytes: int = 10485760) -> TestClient:
    from apps.cv_service.config import CVSettings
    from apps.cv_service.main import create_cv_app

    settings = CVSettings(export_dir="/opt/fishora/model/export", model_version="test-export-1", max_image_bytes=max_image_bytes)
    return TestClient(create_cv_app(settings=settings, classifier=classifier))


def test_predict_returns_model_version_ordered_top_three_and_abstention_status():
    classifier = FakeClassifier(low_confidence=True)
    response = _client(classifier).post(
        "/predict", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model_version"] == "test-export-1"
    assert body["status"] == "low_confidence_human_verification_required"
    assert [item["label"] for item in body["top_candidates"]] == ["tuna", "tenggiri", "gembolo"]
    assert len(body["top_candidates"]) == 3
    assert body["threshold"] == 0.80
    assert classifier.calls == 1


def test_invalid_image_is_rejected_before_classifier():
    classifier = FakeClassifier()
    response = _client(classifier).post(
        "/predict", files={"file": ("fish.jpg", b"not-an-image", "image/jpeg")}
    )
    assert response.status_code == 400
    assert classifier.calls == 0


def test_predict_accepts_png_and_preserves_ordering():
    classifier = FakeClassifier()
    response = _client(classifier).post(
        "/predict", files={"file": ("fish.png", png_bytes(), "image/png")}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "confident_prediction"
    assert [item["label"] for item in body["top_candidates"]] == ["tuna", "tenggiri", "gembolo"]
    assert all(0.0 <= item["confidence"] <= 1.0 for item in body["top_candidates"])
    assert classifier.calls == 1


def test_rejects_unsupported_content_type_before_classifier():
    classifier = FakeClassifier()
    response = _client(classifier).post(
        "/predict", files={"file": ("fish.gif", jpeg_bytes(), "image/gif")}
    )
    assert response.status_code == 415
    assert classifier.calls == 0


def test_rejects_oversized_image_before_classifier():
    classifier = FakeClassifier()
    response = _client(classifier, max_image_bytes=100).post(
        "/predict", files={"file": ("fish.jpg", jpeg_bytes(), "image/jpeg")}
    )
    assert response.status_code == 413
    assert classifier.calls == 0


def test_health_reports_ok_and_model_version():
    classifier = FakeClassifier()
    response = _client(classifier).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "model_version": "test-export-1"}
    assert classifier.calls == 0