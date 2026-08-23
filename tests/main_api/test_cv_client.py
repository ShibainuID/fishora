import httpx
import pytest

VALID_ENVELOPE = {
    "model_version": "test-export-1",
    "status": "confident_prediction",
    "prediction": {"label": "tuna", "confidence": 0.71},
    "top_candidates": [
        {"label": "tuna", "confidence": 0.71},
        {"label": "tenggiri", "confidence": 0.18},
        {"label": "gembolo", "confidence": 0.08},
    ],
    "threshold": 0.80,
}


def _client(handler) -> "HttpCVClient":
    from apps.main_api.services.cv_client import HttpCVClient

    # ponytail: transport injection is the standard httpx test seam; production never passes it
    return HttpCVClient("http://cv-internal:8001", timeout_seconds=5.0, transport=httpx.MockTransport(handler))


def test_predict_returns_validated_envelope_on_2xx():
    from apps.contracts import CVPredictionEnvelope

    def handler(request):
        assert request.url.path == "/predict"
        return httpx.Response(200, json=VALID_ENVELOPE)

    envelope = _client(handler).predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")
    assert isinstance(envelope, CVPredictionEnvelope)
    assert envelope.model_version == "test-export-1"
    assert [item.label for item in envelope.top_candidates] == ["tuna", "tenggiri", "gembolo"]


def test_non_2xx_response_maps_to_cv_unavailable():
    from apps.main_api.errors import CvUnavailable

    client = _client(lambda request: httpx.Response(503, text="boom"))
    with pytest.raises(CvUnavailable):
        client.predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")


def test_connection_error_maps_to_cv_unavailable():
    from apps.main_api.errors import CvUnavailable

    def handler(request):
        raise httpx.ConnectError("connection refused")

    with pytest.raises(CvUnavailable):
        _client(handler).predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")


def test_timeout_maps_to_cv_unavailable():
    from apps.main_api.errors import CvUnavailable

    def handler(request):
        raise httpx.TimeoutException("timed out")

    with pytest.raises(CvUnavailable):
        _client(handler).predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")


def test_cv_unavailable_message_never_leaks_internal_url():
    from apps.main_api.errors import CvUnavailable

    def handler(request):
        raise httpx.ConnectError("http://cv-internal:8001 Authorization secret-key")

    with pytest.raises(CvUnavailable) as excinfo:
        _client(handler).predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")
    assert "cv-internal" not in str(excinfo.value)
    assert "secret-key" not in str(excinfo.value)


@pytest.mark.parametrize("body", [b"null", b"[1, 2, 3]", b'"a string"'])
def test_non_mapping_json_body_maps_to_cv_unavailable(body):
    from apps.main_api.errors import CvUnavailable

    client = _client(lambda request: httpx.Response(200, content=body))
    with pytest.raises(CvUnavailable):
        client.predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")


def test_malformed_json_body_maps_to_cv_unavailable():
    from apps.main_api.errors import CvUnavailable

    client = _client(lambda request: httpx.Response(200, content=b"{not json"))
    with pytest.raises(CvUnavailable):
        client.predict(b"jpeg-bytes", filename="fish.jpg", content_type="image/jpeg")