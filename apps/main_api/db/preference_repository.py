from typing import Callable

from sqlalchemy.orm import Session

from apps.main_api.contracts import BuyerPreferenceRecord
from apps.main_api.db.models import BuyerPreference


class SqlPreferenceRepository:
    def __init__(self, session_factory: Callable[[], Session]):
        self._session_factory = session_factory

    def get(self, buyer_id: str) -> BuyerPreferenceRecord | None:
        with self._session_factory() as session:
            row = session.get(BuyerPreference, buyer_id)
            return None if row is None else self._to_record(row)

    def upsert(self, record: BuyerPreferenceRecord) -> BuyerPreferenceRecord:
        with self._session_factory() as session:
            row = session.get(BuyerPreference, record.buyer_id)
            if row is None:
                row = BuyerPreference(buyer_id=record.buyer_id)
                session.add(row)
            row.business_type = record.business_type
            row.intended_uses = record.intended_uses
            row.characteristics = record.characteristics
            row.max_price_per_kg = record.max_price_per_kg
            row.min_quantity_kg = record.min_quantity_kg
            row.latitude = record.latitude
            row.longitude = record.longitude
            session.commit()
        return record

    @staticmethod
    def _to_record(row: BuyerPreference) -> BuyerPreferenceRecord:
        return BuyerPreferenceRecord(
            buyer_id=row.buyer_id,
            business_type=row.business_type,
            intended_uses=list(row.intended_uses or []),
            characteristics=list(row.characteristics or []),
            max_price_per_kg=row.max_price_per_kg,
            min_quantity_kg=row.min_quantity_kg,
            latitude=row.latitude,
            longitude=row.longitude,
        )
