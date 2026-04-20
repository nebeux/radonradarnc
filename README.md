# RadonRadarNC

**Most Innovative/Technical Award — UNC Charlotte Highschool Hackathon on April 19th**

A web application that estimates residential radon risk for any location in North Carolina. Enter an address, drop a pin on the map, or use your current location — the app queries real geological and environmental data, runs it through a trained XGBoost model, and returns a predicted radon concentration in pCi/L with a plain-English breakdown of what's driving the estimate.

---

## What is Radon?

Radon is a naturally occurring radioactive gas produced by the decay of uranium in bedrock. It's colorless, odorless, and the second leading cause of lung cancer in the US after smoking. North Carolina has significant radon variability — the western mountain counties (built on uranium-rich granite) can run 3–5× higher than the coastal plain. The only way to know for certain is to test your home, but this tool gives you a fast, data-driven starting point.

---

## How It Works

When a location is confirmed, the backend fetches three real-time data sources:

- **USGS Elevation Point Query Service** — actual elevation in feet at the coordinate
- **Macrostrat Geologic Map API** — bedrock lithology (granite, schist, limestone, etc.)
- **USDA Soil Data Access** — saturated hydraulic conductivity (ksat), used to classify soil permeability as high, medium, or low

These are mapped to five model features: geology score, soil score, elevation band score, normalized elevation, and uranium proximity. The XGBoost regressor outputs a predicted radon level in pCi/L.

If any external API is unavailable, the app falls back to regional estimates derived from elevation — mountain zone → granite/gneiss, upper piedmont → schist, piedmont → Triassic basin, coastal plain → sediment. Fallback fields are flagged in the UI.

---

## Stack

| Layer | Technology |
|---|---|
| Backend | Python, Flask, Gunicorn |
| ML Model | XGBoost (trained on synthetic NC radon data) |
| Geo APIs | USGS EPQS, Macrostrat, USDA SDA |
| Frontend | Vanilla JS, Leaflet.js, Turf.js |
| Deployment | Render |

---

## Project Structure

```
.
├── app.py                  # Flask app and /predict endpoint
├── geo_lookup.py           # API calls, fallback logic, feature engineering
├── radon_model.pkl         # Trained XGBoost model
├── radon.py                # Standalone model smoke test
├── requirements.txt
├── modeltraining/
│   └── model.py            # Training script
├── templates/
│   └── index.html          # Full frontend (map, UI, result popup)
└── static/
    └── styles.css
```

---


## API

### `POST /predict`

**Request**
```json
{ "lat": 35.5951, "lng": -82.5515 }
```

**Response**
```json
{
  "radon_pci_l": 4.87,
  "elevation_ft": 2134.0,
  "geology": "granite_gneiss",
  "geology_raw": "granitic gneiss, amphibolite",
  "soil_perm": "low",
  "uranium_prox": 0.85,
  "elev_band": "mountain",
  "estimated": false,
  "estimated_fields": {
    "elevation": false,
    "geology": false,
    "soil": false
  }
}
```

The EPA recommends taking action at **4 pCi/L** and considering action at **2 pCi/L**. The US indoor average is 1.3 pCi/L.

---

## Accessibility

The UI includes a colorblind mode selector (protanopia, deuteranopia, tritanopia, achromatopsia) and a light/dark theme toggle, both accessible via the settings panel.

---

## Limitations

- The model was trained on synthetic data generated from domain knowledge and NC geological surveys, not measured radon readings. Predictions are estimates, not measurements.
- Radon levels vary significantly within a small area depending on foundation type, ventilation, and seasonal pressure changes. Always confirm with a certified test kit.
- Location must be within North Carolina — the map enforces this via a polygon boundary check.
