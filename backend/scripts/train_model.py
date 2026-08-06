import csv
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "crop_training_sample.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "crop_recommender.joblib"

CATEGORICAL = ["season", "soil_type", "market_priority"]
NUMERIC = [
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "temperature",
    "humidity",
    "rainfall",
]
FEATURES = CATEGORICAL + NUMERIC


def load_rows() -> tuple[list[dict], list[str]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)

    features = []
    labels = []
    for row in rows:
        item = {key: row[key] for key in CATEGORICAL}
        item.update({key: float(row[key]) for key in NUMERIC})
        features.append(item)
        labels.append(row["crop"])
    return features, labels


def main() -> None:
    features, labels = load_rows()
    model = Pipeline(
        steps=[
            ("features", DictVectorizer(sparse=False)),
            ("classifier", RandomForestClassifier(n_estimators=120, random_state=42)),
        ]
    )
    model.fit(features, labels)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    print(f"trained_model={MODEL_PATH}")
    print(f"samples={len(labels)}")


if __name__ == "__main__":
    main()
