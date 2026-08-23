import importlib.util
from pathlib import Path
from typing import Protocol

from PIL import Image

REQUIRED_EXPORT_FILES = ("inference.py", "inference_config.json", "model_state_dict.pt")


class ClassifierProtocol(Protocol):
    def predict(self, image: Image.Image | str | Path, top_k: int = 3) -> dict[str, object]: ...


def load_classifier(export_dir: Path, device: str | None = None) -> ClassifierProtocol:
    """Import the notebook-generated inference.py and instantiate its wrapper as-is.

    The wrapper owns all preprocessing; this loader duplicates nothing.
    """
    export_dir = Path(export_dir)
    missing = [name for name in REQUIRED_EXPORT_FILES if not (export_dir / name).exists()]
    if missing:
        raise FileNotFoundError(f"export {export_dir} is missing required files: {', '.join(missing)}")
    spec = importlib.util.spec_from_file_location("fishora_export_inference", export_dir / "inference.py")
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {export_dir / 'inference.py'}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    classifier_cls = getattr(module, "FishoraClassifier")
    return classifier_cls(export_dir, device=device)