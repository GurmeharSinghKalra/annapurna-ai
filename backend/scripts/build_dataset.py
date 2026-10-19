"""Derive a labelled training set from the documented agronomic envelopes.

Honesty note, because this matters for how the model should be read: these rows are **derived,
not observed**. Each one is a point sampled from a crop's published season, soil, pH, temperature
and water ranges in ``app/crop_data.py``. They encode the same agronomic knowledge the rule engine
uses, so a model trained on them largely re-learns those rules; its value is smoother interpolation
between them and tolerance of partially-contradictory inputs, not independent evidence.

The 24-row ``crop_training_sample.csv`` is the opposite: a small set of hand-written observational
examples. It is held out entirely and used only to score the model, so the reported accuracy
measures agreement with something the model never trained on.

Replacing the derived rows with real field records from state agriculture departments is the
single highest-value upgrade to the model, and nothing else here has to change when that happens.
"""

from __future__ import annotations

import csv
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.crop_data import CROPS

BASE_DIR = Path(__file__).resolve().parents[1]
OUTPUT = BASE_DIR / "data" / "crop_training_derived.csv"

ROWS_PER_CROP = 220
SEED = 20261019

FIELDS = [
    "season",
    "soil_type",
    "irrigation",
    "ph",
    "nitrogen",
    "phosphorus",
    "potassium",
    "temperature",
    "humidity",
    "rainfall",
    "market_priority",
    "crop",
]

# What a farmer plausibly has, weighted towards the common cases.
IRRIGATION_BY_WATER = {
    "Low": ["Rainfed", "Rainfed", "Limited", "Limited", "Assured"],
    "Medium": ["Rainfed", "Limited", "Limited", "Assured"],
    "High": ["Limited", "Assured", "Assured"],
    "Very high": ["Assured", "Assured", "Limited"],
}
IRRIGATION_MM = {"Rainfed": 0, "Limited": 250, "Assured": 900}
PRIORITIES = ["Balanced", "Balanced", "Profit", "Sustainability", "Water saving"]


def jitter(rng: random.Random, low: float, high: float, spread: float = 0.12) -> float:
    """A value inside the band, occasionally just outside it so the model sees boundaries."""
    width = high - low
    value = rng.uniform(low, high)
    if rng.random() < 0.18:
        value += rng.choice((-1, 1)) * width * rng.uniform(0.02, spread)
    return value


def build() -> list[dict]:
    rng = random.Random(SEED)
    rows: list[dict] = []
    for crop in CROPS:
        for _ in range(ROWS_PER_CROP):
            irrigation = rng.choice(IRRIGATION_BY_WATER[crop.water_demand])
            need_low, need_high = crop.rainfall_mm_season
            # Rainfall is whatever is left once irrigation has contributed, floored at zero.
            total_water = jitter(rng, need_low, need_high)
            rainfall = max(0.0, total_water - IRRIGATION_MM[irrigation] * rng.uniform(0.6, 1.0))

            nutrients = rng.triangular(25, 95, 58)
            rows.append(
                {
                    "season": crop.season,
                    "soil_type": rng.choice(crop.soils),
                    "irrigation": irrigation,
                    "ph": round(jitter(rng, *crop.ph), 2),
                    "nitrogen": round(min(100, max(0, rng.gauss(nutrients, 11))), 1),
                    "phosphorus": round(min(100, max(0, rng.gauss(nutrients - 6, 11))), 1),
                    "potassium": round(min(100, max(0, rng.gauss(nutrients - 3, 11))), 1),
                    "temperature": round(jitter(rng, *crop.temperature_c), 1),
                    "humidity": round(min(100, max(10, rng.gauss(62, 14))), 1),
                    "rainfall": round(rainfall, 1),
                    "market_priority": rng.choice(PRIORITIES),
                    "crop": crop.name,
                }
            )
    rng.shuffle(rows)
    return rows


def main() -> None:
    rows = build()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    print(f"derived_dataset={OUTPUT}")
    print(f"rows={len(rows)} crops={len({row['crop'] for row in rows})}")


if __name__ == "__main__":
    main()
