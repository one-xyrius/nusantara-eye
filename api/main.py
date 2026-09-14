"""nusantara-eye API — FastAPI + cache SQLite. v0.2.1"""
import json
import os
import sys

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE, "collector"))
import cache
from openmeteo import fetch

TTL       = int(os.environ.get("NE_TTL", 1800))
PROVINCES = json.load(open(os.path.join(BASE, "data", "provinces.json")))
BY_CODE   = {p["code"]: p for p in PROVINCES}
LAYERS    = ("land", "air", "sea")

app = FastAPI(title="nusantara-eye", version="0.2.1")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"],
)
_conn = None


def db():
    global _conn
    if _conn is None:
        _conn = cache.connect(os.path.join(BASE, "data", "cache.db"))
    return _conn


def coord_for(prov, layer):
    if layer == "sea":
        s = prov.get("sea") or {}
        if "lat" not in s:
            return None, None
        return s["lat"], s["lon"]
    return prov["lat"], prov["lon"]


def get_layer(layer, prov, refresh=False):
    if layer not in LAYERS:
        raise HTTPException(400, f"layer harus salah satu dari {LAYERS}")
    key = f"v2:{layer}:{prov['code']}"
    if not refresh:
        hit = cache.get(db(), key)
        if hit is not None:
            hit["cached"] = True
            return hit
    lat, lon = coord_for(prov, layer)
    if lat is None:
        raise HTTPException(404, f"layer '{layer}' tidak tersedia untuk {prov['name']}")
    try:
        data = fetch(layer, lat, lon)
    except Exception as e:
        raise HTTPException(502, f"gagal ambil data {layer} {prov['name']}: {e}")
    data.update({"code": prov["code"], "name": prov["name"], "cached": False})
    cache.put(db(), key, data, ttl=TTL)
    return data


def summarize(layer, data):
    h = data.get("hourly") or {}
    d = data.get("daily") or {}
    if layer == "land":
        return {
            "soil_moisture":   (h.get("soil_moisture_0_to_1cm") or {}).get("last"),
            "soil_temperature":(h.get("soil_temperature_0cm") or {}).get("last"),
            "temperature":     (h.get("temperature_2m") or {}).get("last"),
            "humidity":        (h.get("relative_humidity_2m") or {}).get("last"),
            "rain_today":      (d.get("precipitation_sum") or {}).get("last"),
        }
    if layer == "air":
        return {
            "pm2_5": (h.get("pm2_5") or {}).get("last"),
            "pm10":  (h.get("pm10") or {}).get("last"),
            "no2":   (h.get("nitrogen_dioxide") or {}).get("last"),
            "aod":   (h.get("aerosol_optical_depth") or {}).get("last"),
        }
    return {
        "sst":     (h.get("sea_surface_temperature") or {}).get("last"),
        "wave":    (h.get("wave_height") or {}).get("last"),
        "current": (h.get("ocean_current_velocity") or {}).get("last"),
    }


@app.get("/api/health")
def health():
    return {"ok": True, "provinces": len(PROVINCES), "layers": list(LAYERS), "ttl": TTL}


@app.get("/api/provinces")
def provinces():
    return {"count": len(PROVINCES), "data": PROVINCES}


@app.get("/api/layers/{layer}/all")
def layer_all(layer: str, refresh: bool = False):
    out = []
    for p in PROVINCES:
        lat, lon = coord_for(p, layer)
        if lat is None:
            out.append({"code": p["code"], "name": p["name"], "available": False})
            continue
        try:
            d = get_layer(layer, p, refresh=refresh)
            out.append({
                "code": p["code"], "name": p["name"], "available": True,
                "cached": d.get("cached"), "summary": summarize(layer, d),
            })
        except HTTPException as e:
            out.append({"code": p["code"], "name": p["name"], "available": False, "error": e.detail})
    return {"layer": layer, "count": len(out), "data": out}


@app.get("/api/layers/{layer}/{code}")
def layer_one(layer: str, code: str, refresh: bool = False):
    prov = BY_CODE.get(code)
    if not prov:
        raise HTTPException(404, f"provinsi '{code}' tidak ada")
    d = get_layer(layer, prov, refresh=refresh)
    return {
        "layer": layer,
        "province": {"code": prov["code"], "name": prov["name"], "capital": prov["capital"]},
        "data": d, "summary": summarize(layer, d),
    }


@app.get("/api/provinces/{code}")
def province_detail(code: str, refresh: bool = False):
    prov = BY_CODE.get(code)
    if not prov:
        raise HTTPException(404, f"provinsi '{code}' tidak ada")
    result = {"province": prov, "layers": {}}
    for layer in LAYERS:
        try:
            d = get_layer(layer, prov, refresh=refresh)
            result["layers"][layer] = {
                "available": True, "cached": d.get("cached"),
                "summary": summarize(layer, d),
                "series": d.get("hourly"), "daily": d.get("daily"),
            }
        except HTTPException as e:
            result["layers"][layer] = {"available": False, "error": e.detail}
    return result
