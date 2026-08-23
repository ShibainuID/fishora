import httpx

from apps.contracts import CVPredictionEnvelope
from apps.main_api.errors import CvUnavailable


class HttpCVClient:
    """Production CVClient: posts the raw bytes to the CV service /predict.

    Connection errors, timeouts, non-2xx responses, and unparsable envelopes
    all become CvUnavailable with a generic message; the internal URL,
    credentials, and request headers are never included in the error.
    """

    def __init__(self, base_url: str, timeout_seconds: float, transport: httpx.BaseTransport | None = None):
        self._base_url = base_url
        self._timeout = timeout_seconds
        # ponytail: transport is the standard httpx test seam (MockTransport); production omits it
        self._transport = transport

    def predict(self, image_bytes: bytes, *, filename: str, content_type: str) -> CVPredictionEnvelope:
        try:
            with httpx.Client(base_url=self._base_url, timeout=self._timeout, transport=self._transport) as client:
                response = client.post("/predict", files={"file": (filename, image_bytes, content_type)})
                response.raise_for_status()
                return CVPredictionEnvelope(**response.json())
        except (httpx.HTTPError, ValueError) as exc:
            # ValueError covers JSON decode and pydantic envelope validation failures.
            raise CvUnavailable("cv service unavailable") from exc