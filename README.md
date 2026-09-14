# nusantara-eye

Dashboard pemantauan Indonesia berbasis data satelit Copernicus (Sentinel-1/2/3/5/6)
dan model iklim ERA5-Land / Open-Meteo. Peta Indonesia dengan dropdown 38 provinsi,
tiga panel layer: **Darat**, **Udara**, **Laut**.

> Portofolio / eksperimen belajar — arsitektur API on-demand, bukan penyimpan data satelit.

## Status

| Fase | Isi | Status |
|---|---|---|
| 1 | Collector data + struktur repo | ✅ selesai |
| 2 | FastAPI + cache SQLite + endpoint | ⬜ |
| 3 | UI Leaflet + 3 panel layer | ⬜ |
| 4 | Sentinel STAC metadata (Sentinel-1/2/3/5/6) | ⬜ |
| 5 | Insight otomatis (LLM) + deploy | ⬜ |

## Sumber data

| Layer | Sumber | Auth |
|---|---|---|
| Darat | Open-Meteo forecast (soil moisture, suhu, hujan) | tanpa key |
| Udara | Open-Meteo Air Quality (PM10, PM2.5, NO2, AOD) | tanpa key |
| Laut | Open-Meteo Marine (SST, gelombang, arus) | tanpa key |
| Metadata citra | Copernicus Data Space STAC (Sentinel-1/2/3/5/6) | registrasi gratis |

Semua data masuk hanya berupa **angka + metadata**, bukan raster. Hemat kuota, hemat RAM.

## Struktur

```
collector/   collector data + cache SQLite
api/         FastAPI (fase 2)
web/         UI statis Leaflet + Chart.js (fase 3)
data/        provinces.json (38 provinsi, titik darat + titik laut), cache.db
docs/        dokumentasi arsitektur
```

## Pemakaian (fase 1)

```bash
python3 - <<'PY'
import sys, json; sys.path.insert(0, 'collector')
from openmeteo import fetch
prov = json.load(open('data/provinces.json'))[0]
d = fetch('land', prov['lat'], prov['lon'])
print(prov['name'], d['hourly']['soil_moisture_0_to_1cm']['last'])
PY
```

## Catatan

- `data/provinces.json` memuat **dua titik per provinsi**: `lat`/`lon` (ibukota, untuk
  layer darat & udara) dan `sea: {name, lat, lon}` (perairan terdekat, untuk layer laut).
  Layer laut tidak valid bila dipanggil dari koordinat darat.
- Air quality Open-Meteo bersumber dari model CAMS, **bukan sensor lapangan**.
  Kategori kualitas udara mengikuti ambang ISPU/WHO dan ditampilkan sebagai indikasi.
