import joblib
import pandas as pd

model = joblib.load("radon_model.pkl")

test = pd.DataFrame([{
    "geology_score":   1,      # coastal sediment
    "soil_score":      1,      # low permeability
    "elev_band_score": 0.5,      # coastal
    "elevation_ft":    0.1,    # 100ft normalised
    "uranium_prox":    0.03,
}])

pred = model.predict(test)[0]
print(f"Predicted radon: {pred:.2f} pCi/L")