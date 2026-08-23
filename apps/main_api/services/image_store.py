from pathlib import Path


class FilesystemImageStore:
    """Saves accepted images under an opaque prediction-reference filename."""

    EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png"}

    def __init__(self, storage_dir: Path):
        self._storage_dir = Path(storage_dir)

    def save(self, prediction_id: str, image_bytes: bytes, content_type: str) -> str:
        filename = f"{prediction_id}.{self.EXTENSIONS[content_type]}"
        self._storage_dir.mkdir(parents=True, exist_ok=True)
        (self._storage_dir / filename).write_bytes(image_bytes)
        return f"images/{filename}"

    def delete(self, image_reference: str) -> None:
        # reference is "images/{filename}"; strip the opaque prefix to stay inside storage_dir
        (self._storage_dir / Path(image_reference).name).unlink(missing_ok=True)