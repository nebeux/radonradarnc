import numpy as np
import pandas as pd
from xgboost import XGBRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# ---------------------------------------------------------------------------
# Domain knowledge
# These values mirror what we'll get from real APIs:
#   geology_type  <- USGS mrdata.usgs.gov state geology layer
#   elevation_ft  <- USGS 3DEP elevation service (1/3 arc-second DEM)
#   soil_perm     <- NCDEQ / USDA Web Soil Survey (ksat, saturated hydraulic conductivity)
#   uranium_prox  <- derived from USGS geology vectors (distance to uraniferous units)
# ---------------------------------------------------------------------------

# Base radon (pCi/L) per bedrock type
# Sources: EPA radon geology reports, USGS open-file reports on NC geology
GEOLOGY_BASE = {
    "granite_gneiss":   6.5,   # Blue Ridge + Piedmont — high uranium felsic rocks
    "schist_phyllite":  4.8,   # Inner Piedmont — metamorphic, moderate-high uranium
    "limestone_marble": 3.4,   # Western NC carbonate units
    "mafic_volcanic":   2.9,   # Scattered Piedmont — low uranium mafic
    "triassic_basin":   2.1,   # Durham / Sanford basin — sedimentary fill
    "alluvium":         1.2,   # River valleys — reworked sediment
    "coastal_sediment": 0.9,   # Coastal Plain — sandy, low uranium
}

# Elevation multiplier — mountain counties measurably higher than Piedmont
# Derived from NCDHHS historical test data stratified by elevation
ELEV_MULT = {
    "mountain": 1.30,   # > 2000 ft  (Asheville, Boone, Highlands)
    "piedmont": 1.10,   # 400–2000 ft (Charlotte, Raleigh, Greensboro)
    "coastal":  0.80,   # < 400 ft   (Wilmington, New Bern)
}

# Soil permeability multiplier
# ksat classes from USDA Web Soil Survey — higher ksat = faster radon migration
SOIL_MULT = {
    "high":   1.30,   # ksat > 10 µm/s  — sandy/gravelly soils, sandhills
    "medium": 1.00,   # ksat 1–10 µm/s  — loamy soils, most of Piedmont
    "low":    0.75,   # ksat < 1 µm/s   — Cecil/Appling clay soils
}

# ---------------------------------------------------------------------------
# Realistic NC geographic distributions for sampling
# Based on actual land area proportions by geology and region
# ---------------------------------------------------------------------------

GEO_KEYS     = list(GEOLOGY_BASE.keys())
GEO_WEIGHTS  = [0.28, 0.18, 0.06, 0.10, 0.10, 0.08, 0.20]  # sums to 1.0
SOIL_KEYS    = ["high", "medium", "low"]
SOIL_WEIGHTS = [0.25, 0.45, 0.30]


def elev_band(elevation: float) -> str:
    if elevation >= 2000:
        return "mountain"
    elif elevation >= 400:
        return "piedmont"
    return "coastal"


def sample_elevation(geology: str, rng: np.random.Generator) -> float:
    """Elevation distribution conditioned on geology — reflects real NC geography."""
    if geology == "granite_gneiss":
        return rng.uniform(600, 5000)
    elif geology in ("coastal_sediment", "alluvium"):
        return rng.uniform(0, 300)
    elif geology == "triassic_basin":
        return rng.uniform(200, 600)
    elif geology == "limestone_marble":
        return rng.uniform(1500, 4500)   # western NC carbonate units are high elevation
    else:
        return rng.uniform(300, 2500)


def sample_uranium_prox(geology: str, rng: np.random.Generator) -> float:
    """
    Uranium proximity score 0–1.
    Will be derived from distance to uraniferous USGS geology polygons.
    Granite/gneiss and schist units carry the most uranium in NC.
    """
    if geology in ("granite_gneiss", "schist_phyllite"):
        return rng.uniform(0.55, 1.0)
    elif geology in ("limestone_marble", "mafic_volcanic"):
        return rng.uniform(0.2, 0.55)
    else:
        return rng.uniform(0.0, 0.25)


# ---------------------------------------------------------------------------
# Data generation
# ---------------------------------------------------------------------------

def generate_dataset(n: int = 10_000, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)

    geology   = rng.choice(GEO_KEYS,  n, p=GEO_WEIGHTS)
    soil_perm = rng.choice(SOIL_KEYS, n, p=SOIL_WEIGHTS)

    elevation    = np.array([sample_elevation(g, rng)    for g in geology])
    uranium_prox = np.array([sample_uranium_prox(g, rng) for g in geology])
    band         = np.array([elev_band(e) for e in elevation])

    radon = np.array([
        max(0.1,
            GEOLOGY_BASE[geology[i]]
            * ELEV_MULT[band[i]]
            * SOIL_MULT[soil_perm[i]]
            * (1.0 + uranium_prox[i] * 0.65)   # uranium adds up to ~65% boost
            * rng.normal(1.0, 0.15)             # real-world measurement noise
        )
        for i in range(n)
    ])

    return pd.DataFrame({
        "geology":      geology,
        "soil_perm":    soil_perm,
        "elevation_ft": elevation.round(1),
        "uranium_prox": uranium_prox.round(4),
        "elev_band":    band,
        "radon_pcil":   radon.round(2),
    })


# ---------------------------------------------------------------------------
# Feature encoding
# Ordinal encoding mirrors how we'll encode API responses at inference time
# ---------------------------------------------------------------------------

GEOLOGY_SCORE = {
    "granite_gneiss":   6,
    "schist_phyllite":  5,
    "limestone_marble": 4,
    "mafic_volcanic":   3,
    "triassic_basin":   2,
    "alluvium":         2,
    "coastal_sediment": 1,
}
SOIL_SCORE    = {"high": 3, "medium": 2, "low": 1}
ELEV_BAND_SCORE = {"mountain": 3, "piedmont": 2, "coastal": 1}


def encode(df: pd.DataFrame) -> pd.DataFrame:
    return pd.DataFrame({
        "geology_score":   df["geology"].map(GEOLOGY_SCORE),
        "soil_score":      df["soil_perm"].map(SOIL_SCORE),
        "elev_band_score": df["elev_band"].map(ELEV_BAND_SCORE),
        "elevation_ft":    df["elevation_ft"] / 1000.0,   # normalise to ~0–6
        "uranium_prox":    df["uranium_prox"],             # already 0–1
    })


# ---------------------------------------------------------------------------
# Train
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Generating 10,000 training samples...")
    df = generate_dataset(10_000)

    print("\nDataset summary:")
    print(df["radon_pcil"].describe().round(2))
    print(f"\nGeology distribution:\n{df['geology'].value_counts()}")
    print(f"\nPct above EPA action level (4.0 pCi/L): "
          f"{(df['radon_pcil'] >= 4.0).mean()*100:.1f}%")

    X = encode(df)
    y = df["radon_pcil"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print("\nTraining XGBoost...")
    model = XGBRegressor(
        n_estimators=300,
        max_depth=5,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        min_child_weight=3,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)

    preds = model.predict(X_test)
    mae   = mean_absolute_error(y_test, preds)
    r2    = r2_score(y_test, preds)

    print(f"\nTest MAE : {mae:.3f} pCi/L")
    print(f"Test R²  : {r2:.3f}")

    print("\nFeature importances:")
    for feat, imp in sorted(
        zip(X.columns, model.feature_importances_),
        key=lambda x: -x[1]
    ):
        print(f"  {feat:<20} {imp:.4f}")

    import joblib
    joblib.dump(model, "radon_model.pkl")
    print("\nSaved radon_model.pkl")