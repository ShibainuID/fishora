class CvUnavailable(Exception):
    """Upstream CV failure: connection error, timeout, non-2xx, or unparsable body.

    Maps to HTTP 503. The message must never contain the internal CV URL,
    credentials, or request headers; the API layer emits a fixed generic detail.
    """


class PredictionNotFound(Exception):
    """No stored prediction for the given id. Maps to HTTP 404."""

    def __init__(self, prediction_id: str):
        super().__init__(f"prediction {prediction_id!r} not found")
        self.prediction_id = prediction_id


class UnsupportedSpecies(Exception):
    """The verified species id is not one of the seeded supported rows. Maps to HTTP 422."""

    def __init__(self, species_id: str):
        super().__init__(f"species {species_id!r} is not supported")
        self.species_id = species_id


class UnsupportedCvLabel(Exception):
    """The CV service returned a label outside the seeded taxonomy (upstream contract error).

    Maps to HTTP 502 and must never persist a prediction or image file.
    """

    def __init__(self, label: str):
        super().__init__(f"cv returned unsupported label {label!r}")
        self.label = label