"""Shared test data builders.

Kept out of conftest.py deliberately: importing conftest from a test module
creates a second module object and re-runs its import-time setup, which would
repoint the test database at a fresh empty directory.
"""

import random

from app.schemas import FarmProfile

VALID_FARM = {
    "location": "Sonipat, Haryana",
    "season": "Kharif",
    "previous_crop": "None",
    "soil_type": "Alluvial",
    "market_priority": "Balanced",
    "land_size": 2,
    "ph": 6.6,
    "nitrogen": 62,
    "phosphorus": 41,
    "potassium": 48,
    "temperature": 29,
    "humidity": 64,
    "rainfall": 115,
    "budget": 95000,
}

SEASONS = ["Kharif", "Rabi", "Zaid"]
SOILS = ["Alluvial", "Black", "Clayey", "Loamy", "Sandy loam"]
PRIORITIES = ["Balanced", "Profit", "Sustainability", "Water saving"]
PREVIOUS = ["None", "Rice", "Wheat", "Maize", "Chickpea", "Cotton"]


def make_farm(**overrides) -> FarmProfile:
    return FarmProfile(**{**VALID_FARM, **overrides})


def random_farms(count, seed=1234):
    """Deterministic sweep across the whole valid input space."""
    rng = random.Random(seed)
    for _ in range(count):
        yield make_farm(
            season=rng.choice(SEASONS),
            soil_type=rng.choice(SOILS),
            market_priority=rng.choice(PRIORITIES),
            previous_crop=rng.choice(PREVIOUS),
            land_size=rng.choice([0.5, 1, 2, 5, 10]),
            ph=round(rng.uniform(4, 9), 1),
            nitrogen=rng.randint(0, 100),
            phosphorus=rng.randint(0, 100),
            potassium=rng.randint(0, 100),
            temperature=rng.randint(-5, 50),
            humidity=rng.randint(0, 100),
            rainfall=rng.randint(0, 500),
            budget=rng.randint(0, 500_000),
        )
