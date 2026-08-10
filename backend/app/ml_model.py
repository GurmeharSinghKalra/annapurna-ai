"""Loader for the optional trained crop classifier.

The model is advisory: it nudges the deterministic ranking and never replaces it.
How much it may nudge is tied to its measured cross-validated accuracy, so a model
trained on a thin dataset cannot outvote the agronomic rules.
"""

import json
import logging
import threading
from pathlib import Path
from typing import Any

import joblib

from .config import get_settings
from .schemas import FarmProfile

logger = logging.getLogger(__name__)

MODEL_FILENAME = "crop_recommender.joblib"
METRICS_FILENAME = "crop_recommender.metrics.json"

# Below this cross-validated accuracy the classifier is loaded and reported but
# not allowed to influence the ranking at all.
MIN_TRUSTED_ACCURACY = 0.60

_lock = threading.Lock()
_cache: dict[str, Any] = {"model": None, "metrics": None, "signature": None}


def model_path() -> Path:
    return get_settings().model_dir / MODEL_FILENAME


def metrics_path() -> Path:
    return get_settings().model_dir / METRICS_FILENAME


def model_available() -> bool:
    return model_path().exists()


def _signature(path: Path) -> tuple[float, int]:
    stat = path.stat()
    return (stat.st_mtime, stat.st_size)


def load_metrics() -> dict:
    path = metrics_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read model metrics: %s", exc)
        return {}


def _load() -> tuple[Any, dict]:
    """Return the cached model, reloading only when the artifact changes on disk."""
    path = model_path()
    if not path.exists():
        return None, {}

    signature = _signature(path)
    with _lock:
        # The signature alone decides when to reload. A failed load is cached as
        # None against that signature, so a corrupt artifact is reported once
        # rather than re-read on every request.
        if _cache["signature"] != signature:
            logger.info("Loading crop classifier from %s", path)
            try:
                _cache["model"] = joblib.load(path)
                _cache["metrics"] = load_metrics()
            except Exception as exc:
                # A truncated or incompatible artifact must not take down ranking.
                logger.error("Could not load crop classifier from %s: %s", path, exc)
                _cache["model"] = None
                _cache["metrics"] = {}
            _cache["signature"] = signature
        return _cache["model"], _cache["metrics"] or {}


def reset_cache() -> None:
    with _lock:
        _cache.update({"model": None, "metrics": None, "signature": None})


def model_accuracy() -> float | None:
    _, metrics = _load()
    value = metrics.get("cv_accuracy")
    return float(value) if isinstance(value, (int, float)) else None


def model_status() -> dict:
    """Human-readable state for /health and /admin/summary."""
    if not model_available():
        return {"state": "not_trained", "trusted": False}

    _, metrics = _load()
    accuracy = metrics.get("cv_accuracy")
    trusted = isinstance(accuracy, (int, float)) and accuracy >= MIN_TRUSTED_ACCURACY
    return {
        "state": "available",
        "trusted": trusted,
        "cv_accuracy": accuracy,
        "samples": metrics.get("samples"),
        "trained_at": metrics.get("trained_at"),
        "note": (
            "Influences ranking, scaled by measured accuracy."
            if trusted
            else "Loaded but excluded from ranking: accuracy is unmeasured or below threshold."
        ),
    }


def predict_crop(farm: FarmProfile) -> tuple[str | None, float]:
    """Return (crop, trust-weighted confidence). Confidence is 0 when untrusted."""
    model, metrics = _load()
    if model is None:
        return None, 0.0

    accuracy = metrics.get("cv_accuracy")
    if not isinstance(accuracy, (int, float)) or accuracy < MIN_TRUSTED_ACCURACY:
        return None, 0.0

    sample = [
        {
            "season": farm.season,
            "soil_type": farm.soil_type,
            "market_priority": farm.market_priority,
            "ph": farm.ph,
            "nitrogen": farm.nitrogen,
            "phosphorus": farm.phosphorus,
            "potassium": farm.potassium,
            "temperature": farm.temperature,
            "humidity": farm.humidity,
            "rainfall": farm.rainfall,
        }
    ]

    try:
        predicted = model.predict(sample)[0]
        confidence = 0.0
        if hasattr(model, "predict_proba"):
            confidence = float(max(model.predict_proba(sample)[0]))
    except Exception as exc:  # A stale or corrupt artifact must not break ranking.
        logger.warning("Crop classifier prediction failed: %s", exc)
        return None, 0.0

    # Discount the vote by how well the model actually generalised.
    return str(predicted), confidence * float(accuracy)
