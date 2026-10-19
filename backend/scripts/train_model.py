"""Train the optional crop classifier, measure it, and record what it is worth.

The previous script fit a RandomForest on 24 rows, printed the row count, and saved the model
with no evaluation of any kind. Nothing downstream could tell whether the thing it was deferring
to was any good, so an unmeasured model silently influenced every recommendation.

This version:

* trains on the derived envelope dataset (``build_dataset.py``) and holds out a stratified split,
* additionally scores against the hand-written observational sample the model never sees,
* runs stratified cross-validation and compares against a most-frequent-class baseline, and
* writes metrics next to the model so the API can refuse a model that is not better than
  guessing, and can report its quality to an operator.
"""

from __future__ import annotations

import csv
import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import joblib
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction import DictVectorizer
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.pipeline import Pipeline

BASE_DIR = Path(__file__).resolve().parents[1]
DERIVED_PATH = BASE_DIR / "data" / "crop_training_derived.csv"
OBSERVED_PATH = BASE_DIR / "data" / "crop_training_sample.csv"
MODEL_DIR = BASE_DIR / "models"
MODEL_PATH = MODEL_DIR / "crop_recommender.joblib"
METRICS_PATH = MODEL_DIR / "crop_recommender.metrics.json"

CATEGORICAL = ["season", "soil_type", "irrigation", "market_priority"]
NUMERIC = ["ph", "nitrogen", "phosphorus", "potassium", "temperature", "humidity", "rainfall"]
RANDOM_STATE = 42


def load(path: Path) -> tuple[list[dict], list[str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    features, labels = [], []
    for row in rows:
        item = {key: row.get(key, "") for key in CATEGORICAL if row.get(key)}
        item.update({key: float(row[key]) for key in NUMERIC if row.get(key) not in (None, "")})
        features.append(item)
        labels.append(row["crop"])
    return features, labels


def build_pipeline() -> Pipeline:
    return Pipeline(
        steps=[
            ("features", DictVectorizer(sparse=False)),
            (
                "classifier",
                RandomForestClassifier(
                    n_estimators=300,
                    # The envelopes overlap, so unlimited depth memorises sampling noise.
                    max_depth=12,
                    min_samples_leaf=3,
                    class_weight="balanced",
                    random_state=RANDOM_STATE,
                    n_jobs=-1,
                ),
            ),
        ]
    )


def git_revision() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], cwd=BASE_DIR, stderr=subprocess.DEVNULL, text=True
        ).strip()
    # Absent git or a tarball checkout is not an error here.
    except Exception:
        return None


def main() -> int:
    if not DERIVED_PATH.exists():
        print(f"missing {DERIVED_PATH}; run scripts/build_dataset.py first", file=sys.stderr)
        return 1

    features, labels = load(DERIVED_PATH)
    train_x, test_x, train_y, test_y = train_test_split(
        features, labels, test_size=0.2, stratify=labels, random_state=RANDOM_STATE
    )

    model = build_pipeline()
    model.fit(train_x, train_y)

    holdout_predictions = model.predict(test_x)
    holdout_accuracy = float(accuracy_score(test_y, holdout_predictions))
    holdout_f1 = float(f1_score(test_y, holdout_predictions, average="macro"))

    folds = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    cv_scores = cross_val_score(build_pipeline(), features, labels, cv=folds, scoring="accuracy")

    baseline = DummyClassifier(strategy="most_frequent", random_state=RANDOM_STATE)
    baseline.fit(train_x, train_y)
    baseline_accuracy = float(accuracy_score(test_y, baseline.predict(test_x)))

    # The observational sample is never trained on, so this is the only score that reflects
    # agreement with data the model has not seen the generating process for.
    observed_accuracy = None
    if OBSERVED_PATH.exists():
        observed_x, observed_y = load(OBSERVED_PATH)
        if observed_x:
            observed_accuracy = float(accuracy_score(observed_y, model.predict(observed_x)))

    metrics = {
        "trained_at": datetime.now(UTC).isoformat(),
        "git_revision": git_revision(),
        "algorithm": "RandomForestClassifier(n_estimators=300, max_depth=12, min_samples_leaf=3)",
        "training_rows": len(train_x),
        "holdout_rows": len(test_x),
        "classes": sorted(set(labels)),
        "holdout_accuracy": round(holdout_accuracy, 4),
        "holdout_macro_f1": round(holdout_f1, 4),
        "cross_validation_accuracy_mean": round(float(cv_scores.mean()), 4),
        "cross_validation_accuracy_std": round(float(cv_scores.std()), 4),
        "baseline_accuracy": round(baseline_accuracy, 4),
        "observational_sample_accuracy": None if observed_accuracy is None else round(observed_accuracy, 4),
        "observational_sample_rows": len(observed_y) if observed_accuracy is not None else 0,
        "data_provenance": (
            "Trained on rows derived from the documented agronomic envelopes in app/crop_data.py, "
            "not on observed field records. Scored additionally against a small hand-written "
            "observational sample that is never trained on. The model contributes a small bonus to "
            "a transparent rule-based ranking; it does not decide the recommendation."
        ),
    }

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, MODEL_PATH)
    METRICS_PATH.write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

    print(f"model={MODEL_PATH}")
    print(f"metrics={METRICS_PATH}")
    print(f"train/holdout rows   : {len(train_x)}/{len(test_x)}")
    print(f"holdout accuracy     : {holdout_accuracy:.3f}  (baseline {baseline_accuracy:.3f})")
    print(f"holdout macro F1     : {holdout_f1:.3f}")
    print(f"5-fold CV accuracy   : {cv_scores.mean():.3f} +/- {cv_scores.std():.3f}")
    if observed_accuracy is not None:
        print(f"observational sample : {observed_accuracy:.3f} over {len(observed_y)} rows")
    print()
    print(classification_report(test_y, holdout_predictions, zero_division=0))

    if holdout_accuracy <= baseline_accuracy:
        print("WARNING: the model does not beat a most-frequent-class baseline.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
