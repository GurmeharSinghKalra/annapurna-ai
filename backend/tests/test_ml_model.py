"""The trained classifier must earn its influence over the ranking."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

from app import ml_model
from app.config import get_settings
from tests.helpers import make_farm

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture
def trained_model():
    """Run the real training script into the test model directory."""
    model_dir = get_settings().model_dir
    result = subprocess.run(
        [sys.executable, str(BACKEND_DIR / "scripts" / "train_model.py"), str(model_dir)],
        capture_output=True,
        text=True,
        cwd=BACKEND_DIR,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ml_model.reset_cache()
    yield model_dir
    for path in (ml_model.model_path(), ml_model.metrics_path()):
        path.unlink(missing_ok=True)
    ml_model.reset_cache()


def set_accuracy(value):
    metrics = json.loads(ml_model.metrics_path().read_text())
    metrics["cv_accuracy"] = value
    ml_model.metrics_path().write_text(json.dumps(metrics))
    ml_model.reset_cache()


def test_no_model_means_no_prediction():
    assert not ml_model.model_available()
    assert ml_model.predict_crop(make_farm()) == (None, 0.0)
    assert ml_model.model_status()["state"] == "not_trained"


def test_training_records_measured_accuracy(trained_model):
    metrics = json.loads(ml_model.metrics_path().read_text())
    assert metrics["samples"] == 24
    assert len(metrics["classes"]) == 8
    assert metrics["cv_folds"] >= 2
    # Cross-validated, not measured on the training data. The old script reported
    # nothing at all, and scoring on its own training set gives a useless 1.0.
    assert 0.0 <= metrics["cv_accuracy"] < 1.0
    assert "trained_at" in metrics


def test_a_low_accuracy_model_is_loaded_but_ignored(trained_model):
    set_accuracy(0.10)

    status = ml_model.model_status()
    assert status["state"] == "available"
    assert status["trusted"] is False

    crop, confidence = ml_model.predict_crop(make_farm())
    assert crop is None and confidence == 0.0


def test_a_model_with_unmeasured_accuracy_is_ignored(trained_model):
    set_accuracy(None)
    assert ml_model.model_status()["trusted"] is False
    assert ml_model.predict_crop(make_farm()) == (None, 0.0)


def test_a_trusted_model_predicts_with_discounted_confidence(trained_model):
    set_accuracy(0.90)

    status = ml_model.model_status()
    assert status["trusted"] is True

    crop, confidence = ml_model.predict_crop(make_farm())
    assert crop is not None
    # Confidence is scaled by measured accuracy, so it can never reach raw 1.0.
    assert 0.0 < confidence <= 0.90


def test_a_trusted_model_influences_the_ranking(client, trained_model, farm):
    from app.recommender import recommend

    set_accuracy(0.10)
    without = {item.crop: item.suitability for item in recommend(make_farm())}

    set_accuracy(0.95)
    ranked = recommend(make_farm())
    with_model = {item.crop: item.suitability for item in ranked}

    boosted = [item for item in ranked if item.ml_influence != "not_applied"]
    assert len(boosted) == 1, "exactly one crop should carry the model's vote"
    assert with_model[boosted[0].crop] > without[boosted[0].crop]
    assert "Trained model also selected this crop" in boosted[0].reasons


def test_the_model_is_cached_across_calls(trained_model, monkeypatch):
    """It used to be re-read from disk on every single request."""
    set_accuracy(0.90)
    ml_model.reset_cache()

    loads = {"count": 0}
    original = ml_model.joblib.load

    def counting_load(path):
        loads["count"] += 1
        return original(path)

    monkeypatch.setattr(ml_model.joblib, "load", counting_load)

    for _ in range(10):
        ml_model.predict_crop(make_farm())

    assert loads["count"] == 1


def test_a_corrupt_model_does_not_break_ranking(trained_model):
    """A truncated or incompatible artifact must degrade, not 500 every request."""
    from app.recommender import recommend

    set_accuracy(0.90)
    ml_model.model_path().write_bytes(b"this is not a joblib artifact")
    ml_model.reset_cache()

    assert ml_model.predict_crop(make_farm()) == (None, 0.0)

    ranked = recommend(make_farm())
    assert len(ranked) == 8
    assert all(item.ml_influence == "not_applied" for item in ranked)


def test_a_corrupt_model_is_not_re_read_on_every_call(trained_model, monkeypatch):
    set_accuracy(0.90)
    ml_model.model_path().write_bytes(b"this is not a joblib artifact")
    ml_model.reset_cache()

    attempts = {"count": 0}
    original = ml_model.joblib.load

    def counting_load(path):
        attempts["count"] += 1
        return original(path)

    monkeypatch.setattr(ml_model.joblib, "load", counting_load)

    for _ in range(5):
        ml_model.predict_crop(make_farm())

    assert attempts["count"] == 1


def test_a_corrupt_model_does_not_break_the_api(client, trained_model, farm):
    set_accuracy(0.90)
    ml_model.model_path().write_bytes(b"this is not a joblib artifact")
    ml_model.reset_cache()

    assert client.post("/recommendations", json=farm).status_code == 200
    assert client.post("/analysis", json=farm).status_code == 200


def test_admin_summary_reports_model_trust(client, trained_model, admin_headers):
    set_accuracy(0.95)
    payload = client.get("/admin/summary", headers=admin_headers).json()["ml_model"]
    assert payload["state"] == "available"
    assert payload["trusted"] is True
    assert payload["cv_accuracy"] == 0.95
