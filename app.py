from flask import Flask, render_template, request, jsonify
import joblib
import pandas as pd
from geo_lookup import lookup

app = Flask(__name__)
model = joblib.load("radon_model.pkl")


@app.route("/")
def home():
    return render_template("index.html", title="Home Page")


@app.route("/predict", methods=["POST"])
def predict():
    data = request.get_json()
    lat = data.get("lat")
    lng = data.get("lng")

    if lat is None or lng is None:
        return jsonify({"error": "Missing lat/lng"}), 400

    try:
        geo = lookup(float(lat), float(lng))
    except Exception as e:
        return jsonify({"error": f"Geo lookup failed: {str(e)}"}), 500

    features = geo["model_features"]
    df = pd.DataFrame([{
        "geology_score":   features["geology_score"],
        "soil_score":      features["soil_score"],
        "elev_band_score": features["elev_band_score"],
        "elevation_ft":    features["elevation_ft"],
        "uranium_prox":    features["uranium_prox"],
    }])

    try:
        prediction = float(model.predict(df)[0])
    except Exception as e:
        return jsonify({"error": f"Model prediction failed: {str(e)}"}), 500

    return jsonify({
        "radon_pci_l":      round(prediction, 2),
        "elevation_ft":     geo["elevation_ft"],
        "geology":          geo["geology"],
        "geology_raw":      geo["geology_raw"],
        "soil_perm":        geo["soil_perm"],
        "uranium_prox":     geo["uranium_prox"],
        "elev_band":        geo["elev_band"],
        "estimated":        geo["estimated"],
        "estimated_fields": geo["estimated_fields"],
    })


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
