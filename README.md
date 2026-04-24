<img width="3840" height="1440" alt="GitHub Banner (9)" src="https://github.com/user-attachments/assets/62d1da40-b0da-42fe-8f26-c3d5824b94fd" />

---
## Achievement

Our team won the **Most Innovative Solution** award at the *College of Computing and Informatics **(UNCC)** 2026 Hackathon*.

---
# NC Radon Radar - About The Project

A web application that predicts radon (Rr) concentrations across North Carolina based on a clicked or searched map location. The frontend is built with HTML and the backend is a Flask API powered by a gradient boosting model.

---
## How It Works

The user selects a location in North Carolina via the map or by entering an address. On confirmation, the frontend sends the coordinates to the Flask backend, which does three things:

1. Fetches live environmental data for that coordinate from the Open-Meteo Air Quality and Elevation APIs — including SO2, NH3, PM2.5, CO, NO2, dust, and elevation
2. Combines those live readings with geographic features derived from the coordinates (proximity to hog farm clusters, wetlands, industrial corridors, coastal plain classification, etc.)
3. Runs the combined feature vector through a trained gradient boosting model and returns a predicted H2S concentration in PPM, a risk level, and the top contributing factors

The model was trained on 100K rows of simulated North Carolina data constructed from domain knowledge about H2S sources in the state — primarily concentrated animal feeding operations in the eastern coastal plain, wetland estuary zones, and industrial corridors along I-85 and I-40.

---
## Authors
Built by **codersushi (SushiTheCoder)**, **nebeux (Krish Sakthivel)**, **sumeete123 (summete)**, and **coder175 (green)**  for the 2026 UNCC Hackathon!

---
## Live Demo
https://radonradar.onrender.com

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
## Built With
| Layer | Technology |
|---|---|
| Backend | Python, Flask, Gunicorn |
| ML Model | XGBoost (trained on synthetic NC radon data) |
| Geo APIs | USGS EPQS, Macrostrat, USDA SDA |
| Frontend | Vanilla JS, Leaflet.js, Turf.js |
| Deployment | Render |

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
## Live Data Sources

All external data is fetched at prediction time with no API key required.

| Source | Data |
|---|---|
| Open-Meteo Air Quality API | SO2, NH3, PM2.5, CO, NO2, dust |
| Open-Meteo Elevation API | Elevation in meters |

---
## Accessibility

The UI includes a colorblind mode selector (protanopia, deuteranopia, tritanopia, achromatopsia) and a light/dark theme toggle, both accessible via the settings panel.

---
## Limitations

- The model was trained on synthetic data generated from domain knowledge and NC geological surveys, not measured radon readings. Predictions are estimates, not measurements.
- Radon levels vary significantly within a small area depending on foundation type, ventilation, and seasonal pressure changes. Always confirm with a certified test kit.
- Location must be within North Carolina — the map enforces this via a polygon boundary check.
