"""The optional trained crop classifier, and how much it is allowed to matter.

The ranking is rule-based and explainable. This model exists only to nudge it, and the size of
that nudge is tied to the model's *measured* accuracy rather than assumed.

Three guards, each answering a way the previous version could mislead:

* **A model with no metrics is not used.** Previously any ``.joblib`` on disk silently influenced
  every recommendation, with nothing recording whether it was better than guessing.
* **A model that does not beat a most-frequent-class baseline is not used.**
* **Influence scales with the score on data the model never trained on.** The derived training
  rows encode the same envelopes the rules use, so a high score there says little; agreement with
  the held-out observational sample is the number that earns influence.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import joblib

from .schemas import FarmProfile

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "crop_recommender.joblib"
METRICS_PATH = BASE_DIR / "models" / "crop_recommender.metrics.json"

logger = logging.getLogger(__name__)

FEATURES = (
    "season",
    "soil_type",
    "irrigation",
    "market_priority",
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "temperature",
    "humidity",
    "rainfall",
)


@dataclass(frozen=True)
class LoadedModel:
    pipeline: object
    metrics: dict
    trust: float  # 0..1, how much weight the ranking gives this model's vote


def _trust_from(metrics: dict) -> float:
    """How much a model's opinion is worth, from what has actually been measured about it."""
    holdout = float(metrics.get("holdout_accuracy") or 0)
    baseline = float(metrics.get("baseline_accuracy") or 0)
    if holdout <= baseline:
        return 0.0
    observed = metrics.get("observational_sample_accuracy")
    if observed is None:
        # No independent check exists, so the model is treated as weakly informative at best.
        return min(0.4, holdout)
    # Agreement with data whose generating process the model never saw is what earns influence.
    return max(0.0, min(1.0, float(observed)))


@lru_cache(maxsize=1)
def _load() -> LoadedModel | None:
    if not MODEL_PATH.exists():
        return None
    if not METRICS_PATH.exists():
        logger.warning(
            "Found %s with no metrics file; refusing to use an unevaluated model. "
            "Run scripts/train_model.py to produce one.",
            MODEL_PATH.name,
        )
        return None
    try:
        metrics = json.loads(METRICS_PATH.read_text(encoding="utf-8"))
        pipeline = joblib.load(MODEL_PATH)
    # Deliberately broad: the model is an optional artefact, and a corrupt one raises whatever
    # the pickle happens to hit - KeyError, struct.error, anything. None of it should be able to
    # take down /health or every recommend()-backed route.
    except Exception as exc:
        logger.warning("Crop model unavailable; ranking continues on rules alone: %s", exc)
        return None

    trust = _trust_from(metrics)
    if trust <= 0:
        logger.warning("Crop model does not beat its baseline; ranking continues on rules alone.")
        return None
    logger.info(
        "Crop model loaded: holdout accuracy %.3f, observational accuracy %s, influence weight %.2f",
        metrics.get("holdout_accuracy", 0),
        metrics.get("observational_sample_accuracy"),
        trust,
    )
    return LoadedModel(pipeline=pipeline, metrics=metrics, trust=trust)


def reset_cache() -> None:
    """Forget the loaded model. Used by tests and after retraining."""
    _load.cache_clear()


def model_available() -> bool:
    return _load() is not None


def model_report() -> dict:
    """What an operator needs to judge the model, or why it is not in use."""
    loaded = _load()
    if loaded is None:
        return {
            "status": "not_in_use",
            "reason": (
                "No trained model found."
                if not MODEL_PATH.exists()
                else "The model has no metrics, could not be loaded, or does not beat its baseline."
            ),
            "effect": "Crop ranking uses the transparent rule engine alone.",
        }
    metrics = loaded.metrics
    return {
        "status": "in_use",
        "influence_weight": round(loaded.trust, 3),
        "holdout_accuracy": metrics.get("holdout_accuracy"),
        "cross_validation_accuracy_mean": metrics.get("cross_validation_accuracy_mean"),
        "baseline_accuracy": metrics.get("baseline_accuracy"),
        "observational_sample_accuracy": metrics.get("observational_sample_accuracy"),
        "trained_at": metrics.get("trained_at"),
        "data_provenance": metrics.get("data_provenance"),
        "effect": "Adds a small, weighted bonus to the rule-based score for the crop it selects.",
    }


def predict_crop(farm: FarmProfile) -> tuple[str | None, float]:
    """Return (crop, confidence). Confidence is already scaled by how much the model is trusted."""
    loaded = _load()
    if loaded is None:
        return None, 0.0

    sample = [{key: getattr(farm, key) for key in FEATURES}]
    try:
        predicted = loaded.pipeline.predict(sample)[0]
        confidence = 0.0
        if hasattr(loaded.pipeline, "predict_proba"):
            confidence = float(max(loaded.pipeline.predict_proba(sample)[0]))
    # A feature-set mismatch must not break the API.
    except Exception as exc:
        logger.warning("Crop model prediction failed; ranking continues on rules alone: %s", exc)
        reset_cache()
        return None, 0.0

    return str(predicted), confidence * loaded.trust
