"""Train the optional crop classifier and record how well it actually generalises.

The starter dataset is small on purpose: it is a demonstration, not validated
regional agronomy. Rather than hide that, training measures stratified
cross-validated accuracy and writes it next to the model. The API reads that
number and refuses to let a weak model influence rankings.
"""

import csv
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_PATH = BASE_DIR / "data" / "crop_training_sample.csv"
MODEL_DIR = Path(sys.argv[1]) if len(sys.argv) > 1 else BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "crop_recommender.joblib"
METRICS_PATH = MODEL_DIR / "crop_recommender.metrics.json"

CATEGORICAL = ["season", "soil_type", "market_priority"]
NUMERIC = ["ph", "nitrogen", "phosphorus", "potassium", "temperature", "humidity", "rainfall"]


def load_rows() -> tuple[list[dict], list[str]]:
    with DATA_PATH.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))

    features, labels = [], []
    for index, row in enumerate(rows, start=2):
        try:
            item = {key: row[key] for key in CATEGORICAL}
            item.update({key: float(row[key]) for key in NUMERIC})
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"{DATA_PATH.name} line {index}: {exc}") from exc
        features.append(item)
        labels.append(row["crop"])
    return features, labels


def build_pipeline(n_estimators: int) -> Pipeline:
    return Pipeline(
        steps=[
            ("features", DictVectorizer(sparse=False)),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=n_estimators,
                    random_state=42,
                    # The starter set has 2-4 examples per class; balancing stops the
                    # larger classes from dominating every split.
                    class_weight="balanced",
                ),
            ),
        ]
    )


def evaluate(features: list[dict], labels: list[str]) -> dict:
    """Stratified CV accuracy, with folds capped by the rarest class."""
    smallest_class = min(labels.count(label) for label in set(labels))
    folds = min(5, smallest_class)
    if folds < 2:
        return {
            "cv_accuracy": None,
            "cv_folds": 0,
            "note": "Not enough samples per class to cross-validate.",
        }

    scores = cross_val_score(
        build_pipeline(n_estimators=200),
        features,
        labels,
        cv=StratifiedKFold(n_splits=folds, shuffle=True, random_state=42),
        scoring="accuracy",
    )
    return {
        "cv_accuracy": round(float(scores.mean()), 4),
        "cv_accuracy_std": round(float(scores.std()), 4),
        "cv_folds": folds,
        "note": "Stratified cross-validation on the starter dataset.",
    }


def main() -> int:
    features, labels = load_rows()
    classes = sorted(set(labels))
    metrics = evaluate(features, labels)

    model = build_pipeline(n_estimators=200)
    model.fit(features, labels)

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)

    metrics.update(
        {
            "samples": len(labels),
            "classes": classes,
            "samples_per_class": {label: labels.count(label) for label in classes},
            "trained_at": datetime.now(UTC).isoformat(),
            "dataset": DATA_PATH.name,
        }
    )
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    accuracy = metrics["cv_accuracy"]
    print(f"trained_model={MODEL_PATH}")
    print(f"samples={len(labels)} classes={len(classes)}")
    print(f"cv_accuracy={accuracy} folds={metrics['cv_folds']}")

    if accuracy is None:
        print("WARNING: accuracy could not be measured; the API will ignore this model.")
    elif accuracy < 0.60:
        print(
            f"WARNING: cross-validated accuracy {accuracy:.0%} is below the 60% trust "
            "threshold. The API will load this model but exclude it from ranking."
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
