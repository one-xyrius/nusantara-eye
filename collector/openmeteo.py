"""Collector Open-Meteo: darat, udara, laut. Tanpa API key.

Perbaikan v0.2:
- Laut pakai titik perairan terpisah (param `coord`), bukan koordinat ibukota.
- Hujan & suhu harian pakai `daily` (precipitation_sum, temperature_2m_max/min)
  supaya tidak 0.0 seperti hourly per-jam.
"""
import json
import urllib.parse
import urllib.request

TIMEOUT = 20
UA = "nusantara-eye/0.2 (portfolio project; contact: one-xyrius)"

ENDPOINTS = {
    "land": "https://api.open-meteo.com/v1/forecast",
    "air": "https://air-quality-api.open-meteo.com/v1/air-quality",
    "sea": "https://marine-api.open-meteo.com/v1/marine",
}
LAND_HOURLY = "soil_moisture_0_to_1cm,soil_moisture_3_to_9cm,soil_temperature_0cm,temperature_2m,relative_humidity_2m,precipitation"
AIR_HOURLY = "pm10,pm2_5,nitrogen_dioxide,aerosol_optical_depth"
SEA_HOURLY = "wave_height,sea_surface_temperature,ocean_current_velocity"
HOURLY = {"land": LAND_HOURLY, "air": AIR_HOURLY, "sea": SEA_HOURLY}

DAILY = {
    "land": "precipitation_sum,temperature_2m_max,temperature_2m_min",
    "air": "pm10_max,pm2_5_max",
    "sea": "wave_height_max",
}


def _fetch(url, params):
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(f"{url}?{qs}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return json.loads(r.read().decode())


def _tail_block(block, n, key="time"):
    if not block or key not in block:
        return {}
    times = block[key]
    out = {}
    for k, vals in block.items():
        if k == key:
            continue
        pairs = [(t, v) for t, v in zip(times, vals) if v is not None]
        if not pairs:
            continue
        tail = pairs[-n:]
        out[k] = {"points": [{"t": t, "v": v} for t, v in tail], "last": tail[-1][1]}
    return out


def fetch(layer, lat, lon, days=3):
    if layer not in ENDPOINTS:
        raise ValueError(f"layer tidak dikenal: {layer}")
    params = {
        "latitude": lat, "longitude": lon,
        "hourly": HOURLY[layer],
        "forecast_days": days, "past_days": 1,
        "timezone": "Asia/Jakarta",
    }
    if layer in DAILY:
        params["daily"] = DAILY[layer]
    raw = _fetch(ENDPOINTS[layer], params)
    hourly = _tail_block(raw.get("hourly", {}), n=24)
    hunits = raw.get("hourly_units") or {}
    for k, v in hourly.items():
        v["unit"] = hunits.get(k)
    daily = _tail_block(raw.get("daily", {}), n=7, key="time")
    dunits = raw.get("daily_units") or {}
    for k, v in daily.items():
        v["unit"] = dunits.get(k)
    return {
        "layer": layer, "lat": raw.get("latitude"), "lon": raw.get("longitude"),
        "elevation": raw.get("elevation"), "timezone": raw.get("timezone"),
        "hourly": hourly, "daily": daily,
    }
