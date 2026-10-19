from pathlib import Path
from functools import lru_cache
import logging

import joblib

from .schemas import FarmProfile

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "crop_recommender.joblib"
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _load_model():
    """Load the optional starter model once; callers retain rule-based recommendations on failure."""
    if not MODEL_PATH.exists():
        return None
    try:
        return joblib.load(MODEL_PATH)
    except (OSError, ValueError, EOFError, ImportError) as exc:
        logger.warning("Crop model is unavailable; using transparent rules: %s", exc)
        return None


def model_available() -> bool:
    return _load_model() is not None


def predict_crop(farm: FarmProfile) -> tuple[str | None, float]:
    model = _load_model()
    if model is None:
        return None, 0.0
    sample = [
        {
            "season": farm.season,
            "soil_type": farm.soil_type,
            "ph": farm.ph,
            "nitrogen": farm.nitrogen,
            "phosphorus": farm.phosphorus,
            "potassium": farm.potassium,
            "temperature": farm.temperature,
            "humidity": farm.humidity,
            "rainfall": farm.rainfall,
            "market_priority": farm.market_priority,
        }
    ]
    predicted = model.predict(sample)[0]
    confidence = 0.0
    if hasattr(model, "predict_proba"):
        probabilities = model.predict_proba(sample)[0]
        confidence = float(max(probabilities))
    return str(predicted), confidence
