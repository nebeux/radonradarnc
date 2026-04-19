import requests
import math

USGS_LITH_MAP = {
    # Felsic igneous / granite-gneiss family
    "granite":          "granite_gneiss",
    "granitic":         "granite_gneiss",
    "gneiss":           "granite_gneiss",
    "gneissic":         "granite_gneiss",
    "orthogneiss":      "granite_gneiss",
    "paragneiss":       "granite_gneiss",
    "intrusive":        "granite_gneiss",
    "plutonic":         "granite_gneiss",
    "felsic":           "granite_gneiss",
    "rhyolite":         "granite_gneiss",
    "monzonite":        "granite_gneiss",
    "tonalite":         "granite_gneiss",
    "granodiorite":     "granite_gneiss",
    "syenite":          "granite_gneiss",
    "pegmatite":        "granite_gneiss",
    "aplite":           "granite_gneiss",
    # Metamorphic / schist-phyllite family
    "schist":           "schist_phyllite",
    "phyllite":         "schist_phyllite",
    "slate":            "schist_phyllite",
    "metamorphic":      "schist_phyllite",
    "migmatite":        "schist_phyllite",
    "amphibolite":      "schist_phyllite",
    "mylonite":         "schist_phyllite",
    "quartzite":        "schist_phyllite",
    "metasediment":     "schist_phyllite",
    "metavolcanic":     "schist_phyllite",
    "greenstone":       "schist_phyllite",
    # Carbonate family
    "limestone":        "limestone_marble",
    "marble":           "limestone_marble",
    "carbonate":        "limestone_marble",
    "dolomite":         "limestone_marble",
    "dolostone":        "limestone_marble",
    "calcareous":       "limestone_marble",
    # Mafic family
    "basalt":           "mafic_volcanic",
    "mafic":            "mafic_volcanic",
    "diabase":          "mafic_volcanic",
    "diorite":          "mafic_volcanic",
    "gabbro":           "mafic_volcanic",
    "volcanic":         "mafic_volcanic",
    "andesite":         "mafic_volcanic",
    "ultramafic":       "mafic_volcanic",
    "peridotite":       "mafic_volcanic",
    "dunite":           "mafic_volcanic",
    # Triassic basin sedimentary
    "triassic":         "triassic_basin",
    "mudstone":         "triassic_basin",
    "shale":            "triassic_basin",
    "conglomerate":     "triassic_basin",
    "arkose":           "triassic_basin",
    "redbeds":          "triassic_basin",
    "red bed":          "triassic_basin",
    # Alluvium
    "alluvium":         "alluvium",
    "alluvial":         "alluvium",
    "fluvial":          "alluvium",
    "terrace":          "alluvium",
    "gravel":           "alluvium",
    # Coastal / low-lying sediment — should only trigger on explicit coastal terms
    "coastal":          "coastal_sediment",
    "marine":           "coastal_sediment",
    "estuarine":        "coastal_sediment",
    "beach":            "coastal_sediment",
    "swamp":            "coastal_sediment",
    "peat":             "coastal_sediment",
}

# Note: "sandstone", "sand", "clay", "sediment" are intentionally removed from
# the coastal_sediment bucket — they appear in Triassic basin and alluvium
# descriptions too, so we let the more specific keys above catch them first,
# and only fall back to the elevation-based heuristic if nothing matches.

GEOLOGY_SCORE = {
    "granite_gneiss":   6,
    "schist_phyllite":  5,
    "limestone_marble": 4,
    "mafic_volcanic":   3,
    "triassic_basin":   2,
    "alluvium":         2,
    "coastal_sediment": 1,
}

SOIL_SCORE      = {"high": 3, "medium": 2, "low": 1}
ELEV_BAND_SCORE = {"mountain": 3, "piedmont": 2, "coastal": 1}


# ---------------------------------------------------------------------------
# Elevation fallback grid (coarse 0.5° NC DEM, values in feet)
# ---------------------------------------------------------------------------
_ELEV_GRID = {
    (36.0, -84.0): 3200, (36.0, -83.5): 3400, (36.0, -83.0): 3600,
    (36.0, -82.5): 4100, (36.0, -82.0): 3800, (36.0, -81.5): 2900,
    (36.0, -81.0): 2200, (36.0, -80.5): 1200, (36.0, -80.0):  900,
    (36.0, -79.5):  700, (36.0, -79.0):  600, (36.0, -78.5):  500,
    (36.0, -78.0):  450, (36.0, -77.5):  350, (36.0, -77.0):  200,
    (36.0, -76.5):  100, (36.0, -76.0):   50, (36.0, -75.5):   20,
    (35.5, -84.0): 2800, (35.5, -83.5): 3100, (35.5, -83.0): 3500,
    (35.5, -82.5): 4500, (35.5, -82.0): 3200, (35.5, -81.5): 2400,
    (35.5, -81.0): 1100, (35.5, -80.5):  800, (35.5, -80.0):  750,
    (35.5, -79.5):  600, (35.5, -79.0):  500, (35.5, -78.5):  430,
    (35.5, -78.0):  350, (35.5, -77.5):  250, (35.5, -77.0):  150,
    (35.5, -76.5):   80, (35.5, -76.0):   30, (35.5, -75.5):   15,
    (35.0, -84.0): 1800, (35.0, -83.5): 2000, (35.0, -83.0): 2200,
    (35.0, -82.5): 2600, (35.0, -82.0): 1800, (35.0, -81.5): 1200,
    (35.0, -81.0):  900, (35.0, -80.5):  750, (35.0, -80.0):  700,
    (35.0, -79.5):  550, (35.0, -79.0):  430, (35.0, -78.5):  350,
    (35.0, -78.0):  250, (35.0, -77.5):  150, (35.0, -77.0):   90,
    (35.0, -76.5):   40, (35.0, -76.0):   20, (35.0, -75.5):   10,
    (34.5, -84.0): 1200, (34.5, -83.5): 1400, (34.5, -83.0): 1600,
    (34.5, -82.5): 1800, (34.5, -82.0): 1200, (34.5, -81.5):  900,
    (34.5, -81.0):  700, (34.5, -80.5):  600, (34.5, -80.0):  500,
    (34.5, -79.5):  380, (34.5, -79.0):  280, (34.5, -78.5):  180,
    (34.5, -78.0):  100, (34.5, -77.5):   55, (34.5, -77.0):   25,
    (34.5, -76.5):   12, (34.5, -76.0):    8, (34.5, -75.5):    5,
    (34.0, -79.5):  200, (34.0, -79.0):  150, (34.0, -78.5):   90,
    (34.0, -78.0):   50, (34.0, -77.5):   25, (34.0, -77.0):   12,
    (34.0, -76.5):    8, (34.0, -76.0):    5,
}


def _fallback_elevation(lat: float, lng: float) -> float:
    lat0 = math.floor(lat * 2) / 2
    lng0 = math.floor(lng * 2) / 2
    lat1, lng1 = lat0 + 0.5, lng0 + 0.5
    corners = [(lat0, lng0), (lat0, lng1), (lat1, lng0), (lat1, lng1)]
    vals = [_ELEV_GRID.get(c) for c in corners]
    known = [(c, v) for c, v in zip(corners, vals) if v is not None]
    if not known:
        if lng < -81.0: return 2500.0
        elif lng < -79.0: return 700.0
        else: return 50.0
    if len(known) == 4:
        tx = (lat - lat0) / 0.5
        ty = (lng - lng0) / 0.5
        v00, v01, v10, v11 = vals
        return v00*(1-tx)*(1-ty) + v01*(1-tx)*ty + v10*tx*(1-ty) + v11*tx*ty
    total_w, total_v = 0.0, 0.0
    for (clat, clng), v in known:
        d = math.hypot(lat - clat, lng - clng) + 1e-9
        w = 1.0 / d
        total_w += w; total_v += w * v
    return total_v / total_w


def _geology_from_elevation(elevation_ft: float) -> tuple[str, str]:
    """
    When the geology API fails or returns unrecognisable lithology,
    infer geology from elevation — a reliable proxy for NC bedrock zones.
    """
    if elevation_ft >= 2000:
        return "granite_gneiss",   "estimated from elevation (mountain zone)"
    elif elevation_ft >= 800:
        return "schist_phyllite",  "estimated from elevation (upper piedmont)"
    elif elevation_ft >= 400:
        return "triassic_basin",   "estimated from elevation (piedmont/triassic)"
    else:
        return "coastal_sediment", "estimated from elevation (coastal plain)"


def get_elevation(lat: float, lng: float) -> tuple[float, bool]:
    """Returns (elevation_ft, is_estimated)."""
    url = "https://epqs.nationalmap.gov/v1/json"
    params = {"x": lng, "y": lat, "units": "Feet", "includeDate": False}
    for timeout in (12, 20):
        try:
            r = requests.get(url, params=params, timeout=timeout)
            r.raise_for_status()
            val = r.json().get("value")
            if val is not None:
                return float(val), False
        except Exception:
            continue
    return _fallback_elevation(lat, lng), True


def get_geology(lat: float, lng: float, elevation_ft: float) -> tuple[str, str, bool]:
    """Returns (geology_key, geology_raw, is_estimated)."""
    try:
        r = requests.get(
            "https://macrostrat.org/api/v2/geologic_units/map",
            params={"lat": lat, "lng": lng, "response": "short"},
            timeout=15,
        )
        r.raise_for_status()
        features = r.json().get("success", {}).get("data", [])
        if features:
            unit = features[0]
            lith_desc = (unit.get("lith") or unit.get("descrip") or unit.get("name") or "").lower()
            geology_key = None
            for keyword, key in USGS_LITH_MAP.items():
                if keyword in lith_desc:
                    geology_key = key
                    break
            if geology_key:
                return geology_key, lith_desc, False
            # API responded but we couldn't classify the lithology —
            # fall through to elevation-based estimate rather than
            # wrongly returning "coastal_sediment"
    except Exception:
        pass

    key, raw = _geology_from_elevation(elevation_ft)
    return key, raw, True


def get_soil_permeability(lat: float, lng: float) -> tuple[str, bool]:
    """Returns (permeability_class, is_estimated)."""
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
    try:
        r = requests.post(
            "https://sdmdataaccess.nrcs.usda.gov/Tabular/post.rest",
            json={"query": query.strip(), "FORMAT": "JSON"},
            timeout=20,
        )
        r.raise_for_status()
        rows = r.json().get("Table", [])
        if rows and rows[0][0] is not None:
            ksat = float(rows[0][0])
            if ksat > 10:   return "high",   False
            elif ksat > 1:  return "medium", False
            return "low", False
    except Exception:
        pass
    # Fallback: elevation-based (mountains = clay soils = low permeability)
    if lng < -80.5:   return "low",    True   # mountain clay
    elif lng < -78.5: return "medium", True   # piedmont loam
    return "high", True                        # sandy coastal plain


def get_uranium_prox(geology_key: str, geology_raw: str) -> float:
    raw = geology_raw.lower()
    if geology_key == "granite_gneiss" or any(w in raw for w in ("granite", "intrusive", "plutonic", "felsic", "pegmatite")):
        return 0.85
    elif geology_key == "schist_phyllite" or any(w in raw for w in ("schist", "metamorphic", "migmatite", "amphibolite")):
        return 0.65
    elif geology_key in ("limestone_marble", "mafic_volcanic"):
        return 0.35
    return 0.10


def elev_band(elevation_ft: float) -> str:
    if elevation_ft >= 2000:   return "mountain"
    elif elevation_ft >= 400:  return "piedmont"
    return "coastal"


def lookup(lat: float, lng: float) -> dict:
    elevation_ft, elev_estimated  = get_elevation(lat, lng)
    geology_key, geology_raw, geo_estimated = get_geology(lat, lng, elevation_ft)
    soil_perm, soil_estimated     = get_soil_permeability(lat, lng)
    uranium_prox                  = get_uranium_prox(geology_key, geology_raw)
    band                          = elev_band(elevation_ft)
    any_estimated                 = elev_estimated or geo_estimated or soil_estimated

    return {
        "lat":             lat,
        "lng":             lng,
        "elevation_ft":    round(elevation_ft, 1),
        "geology":         geology_key,
        "geology_raw":     geology_raw,
        "soil_perm":       soil_perm,
        "uranium_prox":    uranium_prox,
        "elev_band":       band,
        "estimated":       any_estimated,
        "estimated_fields": {
            "elevation": elev_estimated,
            "geology":   geo_estimated,
            "soil":      soil_estimated,
        },
        "model_features": {
            "geology_score":   GEOLOGY_SCORE[geology_key],
            "soil_score":      SOIL_SCORE[soil_perm],
            "elev_band_score": ELEV_BAND_SCORE[band],
            "elevation_ft":    round(elevation_ft / 1000.0, 4),
            "uranium_prox":    uranium_prox,
        },
    }


if __name__ == "__main__":
    import json
    result = lookup(35.5951, -82.5515)  # Asheville
    print(json.dumps(result, indent=2))
