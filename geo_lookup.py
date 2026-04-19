import requests
import math

URANIFEROUS_SYMBOLS = {"Zgn", "Ygn", "pCgn", "Xgn", "gr", "Qgr", "Pgr", "Zs", "Ys", "pCs", "phy", "Zph"}

USGS_LITH_MAP = {
    "granite":          "granite_gneiss",
    "gneiss":           "granite_gneiss",
    "granitic":         "granite_gneiss",
    "intrusive":        "granite_gneiss",
    "plutonic":         "granite_gneiss",
    "felsic":           "granite_gneiss",
    "schist":           "schist_phyllite",
    "phyllite":         "schist_phyllite",
    "metamorphic":      "schist_phyllite",
    "migmatite":        "schist_phyllite",
    "limestone":        "limestone_marble",
    "marble":           "limestone_marble",
    "carbonate":        "limestone_marble",
    "basalt":           "mafic_volcanic",
    "mafic":            "mafic_volcanic",
    "diabase":          "mafic_volcanic",
    "diorite":          "mafic_volcanic",
    "gabbro":           "mafic_volcanic",
    "volcanic":         "mafic_volcanic",
    "triassic":         "triassic_basin",
    "mudstone":         "triassic_basin",
    "sandstone":        "triassic_basin",
    "alluvium":         "alluvium",
    "alluvial":         "alluvium",
    "sand":             "coastal_sediment",
    "clay":             "coastal_sediment",
    "sediment":         "coastal_sediment",
}

GEOLOGY_SCORE = {
    "granite_gneiss":   6,
    "schist_phyllite":  5,
    "limestone_marble": 4,
    "mafic_volcanic":   3,
    "triassic_basin":   2,
    "alluvium":         2,
    "coastal_sediment": 1,
}

SOIL_SCORE = {"high": 3, "medium": 2, "low": 1}
ELEV_BAND_SCORE = {"mountain": 3, "piedmont": 2, "coastal": 1}


def get_elevation(lat: float, lng: float) -> float:
    url = "https://epqs.nationalmap.gov/v1/json"
    params = {"x": lng, "y": lat, "units": "Feet", "includeDate": False}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return float(r.json()["value"])


def get_geology(lat: float, lng: float) -> tuple[str, str]:
    r = requests.get(
        "https://macrostrat.org/api/v2/geologic_units/map",
        params={"lat": lat, "lng": lng, "response": "short"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()

    features = data.get("success", {}).get("data", [])
    if not features:
        return "coastal_sediment", "Unknown"

    unit      = features[0]
    lith_desc = (unit.get("lith") or unit.get("descrip") or unit.get("name") or "").lower()

    geology_key = "coastal_sediment"
    for keyword, key in USGS_LITH_MAP.items():
        if keyword in lith_desc:
            geology_key = key
            break

    return geology_key, lith_desc


def get_soil_permeability(lat: float, lng: float) -> str:
    point_wkt = f"POINT({lng} {lat})"
    query = f"""
        SELECT TOP 1 ch.ksat_r
        FROM component co
        INNER JOIN chorizon ch ON ch.cokey = co.cokey
        WHERE co.mukey IN (
            SELECT DISTINCT mukey
            FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{point_wkt}')
        )
        AND co.majcompflag = 'Yes'
        AND ch.hzdept_r = 0
        ORDER BY co.comppct_r DESC
    """
    payload = {"query": query.strip(), "FORMAT": "JSON"}
    r = requests.post(
        "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
        json=payload,
        timeout=20,
    )
    r.raise_for_status()
    rows = r.json().get("Table", [])
    if not rows or rows[0][0] is None:
        return "medium"

    ksat = float(rows[0][0])
    if ksat > 10:
        return "high"
    elif ksat > 1:
        return "medium"
    return "low"


def get_uranium_prox(lat: float, lng: float, geology_key: str, geology_raw: str) -> float:
    raw = geology_raw.lower()
    if geology_key == "granite_gneiss" or any(w in raw for w in ("granite", "intrusive", "plutonic", "felsic")):
        return 0.85
    elif geology_key == "schist_phyllite" or any(w in raw for w in ("schist", "metamorphic", "migmatite")):
        return 0.65
    elif geology_key in ("limestone_marble", "mafic_volcanic"):
        return 0.35
    return 0.10


def elev_band(elevation_ft: float) -> str:
    if elevation_ft >= 2000:
        return "mountain"
    elif elevation_ft >= 400:
        return "piedmont"
    return "coastal"


def lookup(lat: float, lng: float) -> dict:
    elevation    = get_elevation(lat, lng)
    geology_key, geology_raw = get_geology(lat, lng)
    soil_perm    = get_soil_permeability(lat, lng)
    uranium_prox = get_uranium_prox(lat, lng, geology_key, geology_raw)
    band         = elev_band(elevation)

    return {
        "lat":             lat,
        "lng":             lng,
        "elevation_ft":    round(elevation, 1),
        "geology":         geology_key,
        "geology_raw":     geology_raw,
        "soil_perm":       soil_perm,
        "uranium_prox":    uranium_prox,
        "elev_band":       band,
        "model_features": {
            "geology_score":   GEOLOGY_SCORE[geology_key],
            "soil_score":      SOIL_SCORE[soil_perm],
            "elev_band_score": ELEV_BAND_SCORE[band],
            "elevation_ft":    round(elevation / 1000.0, 4),
            "uranium_prox":    uranium_prox,
        }
    }


if __name__ == "__main__":
    import json
    result = lookup(35.2271, -80.8431)
    print(json.dumps(result, indent=2))