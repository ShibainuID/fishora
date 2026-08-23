from apps.main_api.contracts import PredictionRecord, SpeciesRecord


class FakeCVClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.calls = 0

    def predict(self, image_bytes, *, filename, content_type):
        self.calls += 1
        if self.error is not None:
            raise self.error
        return self.result


class FakeSpeciesRepository:
    def __init__(self, species: list[SpeciesRecord]):
        self._by_label = {s.normalized_label: s for s in species}
        self._by_id = {s.id: s for s in species}

    def get_by_normalized_label(self, label):
        return self._by_label.get(label)

    def get_by_id(self, species_id):
        return self._by_id.get(species_id)


class FakePredictionRepository:
    def __init__(self, records: dict[str, PredictionRecord] | None = None):
        self._records = dict(records or {})

    def create(self, prediction_id, image_reference, predicted_species_id, confidence, top_candidates, model_version):
        record = PredictionRecord(
            id=prediction_id,
            image_reference=image_reference,
            predicted_species_id=predicted_species_id,
            confidence=confidence,
            top_candidates=top_candidates,
            model_version=model_version,
            verification_status="pending",
        )
        self._records[prediction_id] = record
        return record

    def get(self, prediction_id):
        return self._records.get(prediction_id)

    def verify(self, prediction_id, verified_species_id, verification_status):
        record = self._records[prediction_id]  # service checks existence first
        record.verified_species_id = verified_species_id
        record.verification_status = verification_status
        return record

    def all(self):
        return list(self._records.values())


class FakeImageStore:
    def __init__(self):
        self.saved = []

    def save(self, prediction_id, image_bytes, content_type):
        self.saved.append((prediction_id, image_bytes, content_type))
        return f"images/{prediction_id}.jpg"