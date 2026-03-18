from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import astronomy
from datetime import datetime, timedelta
import math

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# -----------------------------
# CONSTANTS
# -----------------------------

NAKSHATRA_SIZE = 360 / 27

nakshatras = [
    "Ashwini","Bharani","Krittika","Rohini","Mrigashira",
    "Ardra","Punarvasu","Pushya","Ashlesha","Magha",
    "Purva Phalguni","Uttara Phalguni","Hasta","Chitra","Swati",
    "Vishakha","Anuradha","Jyeshtha","Mula","Purva Ashadha",
    "Uttara Ashadha","Shravana","Dhanishta","Shatabhisha",
    "Purva Bhadrapada","Uttara Bhadrapada","Revati"
]

rashis = [
    "Mesha","Vrishabha","Mithuna","Karka",
    "Simha","Kanya","Tula","Vrischika",
    "Dhanu","Makara","Kumbha","Meena"
]

lunar_months = [
    "Chaitra","Vaishakha","Jyeshtha","Ashadha",
    "Shravana","Bhadrapada","Ashwin","Kartika",
    "Margashirsha","Pausha","Magha","Phalguna"
]

tithi_names = [
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Purnima",
    "Pratipada","Dwitiya","Tritiya","Chaturthi","Panchami",
    "Shashthi","Saptami","Ashtami","Navami","Dashami",
    "Ekadashi","Dwadashi","Trayodashi","Chaturdashi","Amavasya"
]

# -----------------------------
# CORE ASTRONOMY
# -----------------------------

def ecliptic_longitude(body, t):
    vec = astronomy.GeoVector(body, t, True)
    x, y, z = vec.x, vec.y, vec.z
    eps = math.radians(23.43928)

    ye = y * math.cos(eps) + z * math.sin(eps)
    lon = math.degrees(math.atan2(ye, x))
    return lon % 360


def lahiri_ayanamsa(t):
    jd = 2451545 + t.ut
    ay = 22.460148 + 1.396042 * (jd - 2451545) / 36525
    return ay % 360


def sidereal_longitude(body, t):
    return (ecliptic_longitude(body, t) - lahiri_ayanamsa(t)) % 360


def get_lon(body, dt):
    utc = dt - timedelta(hours=5, minutes=30)
    t = astronomy.Time.Parse(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))
    return sidereal_longitude(body, t)

# -----------------------------
# ANGULAR DIFFERENCE
# -----------------------------

def angular_diff(dt):
    return (get_lon(astronomy.Body.Moon, dt) - get_lon(astronomy.Body.Sun, dt)) % 360


def normalize(diff):
    """Convert 0–360 → -180 to +180"""
    if diff > 180:
        diff -= 360
    return diff

# -----------------------------
# AMAVASYA (CRITICAL FIX)
# -----------------------------

def find_last_amavasya(dt):
    low = dt - timedelta(days=30)
    high = dt

    for _ in range(40):  # higher precision
        mid = low + (high - low) / 2
        diff = normalize(angular_diff(mid))

        if diff < 0:
            low = mid
        else:
            high = mid

    return high

# -----------------------------
# TITHI
# -----------------------------

def find_tithi_boundary(dt, target):
    low = dt - timedelta(days=1)
    high = dt + timedelta(days=1)

    for _ in range(30):
        mid = low + (high - low) / 2
        diff = angular_diff(mid)

        if target == 0 and diff > 180:
            diff -= 360

        if diff < target:
            low = mid
        else:
            high = mid

    return high.strftime("%b %d, %H:%M")

# -----------------------------
# PANCHANGA
# -----------------------------

def compute_panchanga(date, time):
    dt = datetime.strptime(date + " " + time, "%Y-%m-%d %H:%M")

    sun_lon = get_lon(astronomy.Body.Sun, dt)
    moon_lon = get_lon(astronomy.Body.Moon, dt)

    angle = (moon_lon - sun_lon) % 360
    tithi_index = int(angle / 12)

    # Tithi boundaries
    tithi_start = find_tithi_boundary(dt, tithi_index * 12)
    tithi_end = find_tithi_boundary(dt, ((tithi_index + 1) % 30) * 12)

    # Rashi & Nakshatra
    sun_rashi_idx = int(sun_lon / 30)
    moon_rashi_idx = int(moon_lon / 30)
    nak_index = int(moon_lon / NAKSHATRA_SIZE)

    # -----------------------------
    # ✅ FINAL CORRECT MONTH LOGIC
    # -----------------------------
    last_amavasya = find_last_amavasya(dt)

    sun_at_amavasya = get_lon(astronomy.Body.Sun, last_amavasya)
    amavasya_rashi = int(sun_at_amavasya / 30)

    lunar_month = lunar_months[(amavasya_rashi + 1) % 12]

    # Planets
    bodies = [
        astronomy.Body.Sun, astronomy.Body.Moon, astronomy.Body.Mercury,
        astronomy.Body.Venus, astronomy.Body.Mars, astronomy.Body.Jupiter,
        astronomy.Body.Saturn, astronomy.Body.Uranus, astronomy.Body.Neptune
    ]
    names = ["Sun","Moon","Mercury","Venus","Mars","Jupiter","Saturn","Uranus","Neptune"]

    utc = dt - timedelta(hours=5, minutes=30)
    t = astronomy.Time.Parse(utc.strftime("%Y-%m-%dT%H:%M:%SZ"))

    planets = {
        names[i]: sidereal_longitude(bodies[i], t)
        for i in range(len(bodies))
    }

    return {
        "Lunar_month": lunar_month,
        "Paksha": "Shukla Paksha" if tithi_index < 15 else "Krishna Paksha",
        "Tithi": tithi_names[tithi_index],
        "Tithi_start": tithi_start,
        "Tithi_end": tithi_end,
        "Nakshatra": nakshatras[nak_index],
        "Sun_Rashi": rashis[sun_rashi_idx],
        "Moon_Rashi": rashis[moon_rashi_idx],
        "planet_longitudes": planets
    }

# -----------------------------
# ROUTES
# -----------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    now = datetime.now()
    d, t = now.strftime("%Y-%m-%d"), now.strftime("%H:%M")

    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": compute_panchanga(d, t),
        "date": d,
        "time": t
    })


@app.get("/calculate", response_class=HTMLResponse)
def calculate(request: Request, date: str, time: str):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "result": compute_panchanga(date, time),
        "date": date,
        "time": time
    })


@app.get("/calculate_json")
def calculate_json(date: str, time: str):
    return JSONResponse(content=compute_panchanga(date, time))
