from pathlib import Path

import joblib

from .schemas import FarmProfile

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL_PATH = BASE_DIR / "models" / "crop_recommender.joblib"


def model_available() -> bool:
    return MODEL_PATH.exists()


def predict_crop(farm: FarmProfile) -> tuple[str | None, float]:
    if not model_available():
        return None, 0.0

    model = joblib.load(MODEL_PATH)
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
