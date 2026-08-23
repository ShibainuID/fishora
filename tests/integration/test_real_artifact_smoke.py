import json
import os
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DATASET_DIR = REPO_ROOT / "artifacts" / "Dataset" / "fishora_dataset"
EXPECTED_LABELS = [
    "bandeng",
    "gelama_bunga",
    "gembolo",
    "gulamah",
    "kembung",
    "kuniran",
    "mujair",
    "nila",
    "senangin",
    "tenggiri",
    "tuna",
]

pytestmark = pytest.mark.real_artifact


def _export_dir() -> Path:
    export = os.environ.get("FISHORA_CV_EXPORT_DIR")
    if not export:
        pytest.skip("FISHORA_CV_EXPORT_DIR is not set")
    path = Path(export)
    if not path.is_dir():
        pytest.skip(f"FISHORA_CV_EXPORT_DIR={path} does not exist")
    return path


def _config():
    export = _export_dir()
    cfg_path = export / "inference_config.json"
    if not cfg_path.exists():
        pytest.skip(f"export is missing inference_config.json: {cfg_path}")
    return json.loads(cfg_path.read_text(encoding="utf-8"))


def _first_clean_path() -> Path:
    csv = DATASET_DIR / "splits" / "test.csv"
    if not csv.exists():
        pytest.skip(f"dataset split missing: {csv}")
    # header: image_id,path,clean_path,normalized_label,specimen_group
    first = csv.read_text(encoding="utf-8").splitlines()[1].split(",")[2]
    return DATASET_DIR / first


def test_export_config_contract():
    """The real export's config must match what the service contract assumes."""
    cfg = _config()
    assert cfg["classes"] == EXPECTED_LABELS
    assert cfg["img_size"] == 256
    for key in ("mean", "std", "fill_rgb", "temperature", "abstain_threshold"):
        assert key in cfg, f"inference_config.json is missing {key!r}"
    assert len(cfg["mean"]) == len(cfg["std"]) == len(cfg["fill_rgb"]) == 3


def test_dataset_test_split_resolves_against_export_classes():
    """The first test.csv clean_path must resolve inside the dataset and its label must be in the export."""
    cfg = _config()
    path = _first_clean_path()
    if not path.exists():
        pytest.skip(f"first test.csv clean_path is not a readable file (broken symlink?): {path}")
    assert path.parts[-2] in cfg["classes"]


def test_wrapper_transform_matches_export_preprocessing():
    """Genuine environment skip (not a passing fake) when torch/timm are unavailable."""
    cfg = _config()
    pytest.importorskip("torch", reason="torch not installed: cannot load the generated DINOv3 wrapper")
    pytest.importorskip("timm", reason="timm not installed: cannot load the generated DINOv3 wrapper")

    from PIL import Image

    from apps.cv_service.runtime import load_classifier

    model = load_classifier(_export_dir(), "cpu")

    probe = Image.new("RGB", (40, 20), "white")
    probe.getexif()[274] = 6
    tensor = model.transform(probe)
    assert tuple(tensor.shape) == (3, 256, 256)


def test_wrapper_prediction_on_real_sample():
    """One real prediction through the generated wrapper; skips when no usable sample exists."""
    cfg = _config()
    pytest.importorskip("torch", reason="torch not installed: cannot load the generated DINOv3 wrapper")
    pytest.importorskip("timm", reason="timm not installed: cannot load the generated DINOv3 wrapper")

    sample = _first_clean_path()
    if not sample.exists():
        pytest.skip(f"first test.csv clean_path is not a readable file (broken symlink?): {sample}")

    from apps.cv_service.runtime import load_classifier

    model = load_classifier(_export_dir(), "cpu")
    result = model.predict(sample, top_k=3)
    candidates = result["top_candidates"]
    assert len(candidates) == 3
    assert all(candidates[i]["confidence"] >= candidates[i + 1]["confidence"] for i in range(2))
    assert all(0.0 <= c["confidence"] <= 1.0 for c in candidates)
    threshold = float(cfg["abstain_threshold"])
    expected_status = (
        "confident_prediction"
        if candidates[0]["confidence"] >= threshold
        else "low_confidence_human_verification_required"
    )
    assert result["status"] == expected_status
    assert result["prediction"] == candidates[0]