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

NAKSHATRA_SIZE = 360/27

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
# ECLIPTIC LONGITUDE
# -----------------------------

def ecliptic_longitude(body, t):

    vec = astronomy.GeoVector(body, t, True)

    x = vec.x
    y = vec.y
    z = vec.z

    eps = math.radians(23.43928)

    xe = x
    ye = y * math.cos(eps) + z * math.sin(eps)

    lon = math.degrees(math.atan2(ye, xe))

    if lon < 0:
        lon += 360

    return lon


# -----------------------------
# AYANAMSA
# -----------------------------

def lahiri_ayanamsa(t):

    jd = 2451545 + t.ut
    ay = 22.460148 + 1.396042*(jd-2451545)/36525

    return ay % 360


# -----------------------------
# SIDEREAL LONGITUDE
# -----------------------------

def sidereal_longitude(body, t):

    tropical = ecliptic_longitude(body, t)

    ay = lahiri_ayanamsa(t)

    sid = tropical - ay

    if sid < 0:
        sid += 360

    return sid


# -----------------------------
# PANCHANGA CALCULATION
# -----------------------------

def compute_panchanga(date, time):

    dt = datetime.strptime(date + " " + time,"%Y-%m-%d %H:%M")

    utc = dt - timedelta(hours=5,minutes=30)

    t = astronomy.Time.Parse(
        utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    )

    sun_lon = sidereal_longitude(astronomy.Body.Sun, t)
    moon_lon = sidereal_longitude(astronomy.Body.Moon, t)

    angle = (moon_lon - sun_lon) % 360

    # Tithi
    tithi_index = int(angle / 12)
    paksha = "Shukla Paksha" if tithi_index < 15 else "Krishna Paksha"

    # Nakshatra
    nak_index = int(moon_lon / NAKSHATRA_SIZE)

    # Rashi
    sun_rashi_index = int(sun_lon / 30)
    moon_rashi_index = int(moon_lon / 30)

    # Lunar month
    if angle < 180:
        lunar_month = lunar_months[(sun_rashi_index + 1) % 12]
    else:
        lunar_month = lunar_months[sun_rashi_index]

    # Planet longitudes
    bodies = [
    astronomy.Body.Sun,
    astronomy.Body.Moon,
    astronomy.Body.Mercury,
    astronomy.Body.Venus,
    astronomy.Body.Mars,
    astronomy.Body.Jupiter,
    astronomy.Body.Saturn,
    astronomy.Body.Uranus,
    astronomy.Body.Neptune
    ]

    names = [
    "Sun","Moon","Mercury","Venus","Mars",
    "Jupiter","Saturn","Uranus","Neptune"
    ]

    planet_longitudes = {}

    for i in range(len(bodies)):
        planet_longitudes[names[i]] = sidereal_longitude(bodies[i], t)

    return {
        "Lunar_month": lunar_month,
        "Paksha": paksha,
        "Tithi": tithi_names[tithi_index],
        "Nakshatra": nakshatras[nak_index],
        "Sun_Rashi": rashis[sun_rashi_index],
        "Moon_Rashi": rashis[moon_rashi_index],
        "planet_longitudes": planet_longitudes
    }


# -----------------------------
# ROUTES
# -----------------------------

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    now = datetime.now()

    date = now.strftime("%Y-%m-%d")
    time = now.strftime("%H:%M")

    result = compute_panchanga(date, time)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": result, "date": date, "time": time}
    )


@app.get("/calculate", response_class=HTMLResponse)
def calculate(request: Request, date: str, time: str):

    result = compute_panchanga(date, time)

    return templates.TemplateResponse(
        "index.html",
        {"request": request, "result": result, "date": date, "time": time}
    )


# ✅ THIS IS THE CRITICAL ENDPOINT FOR ANIMATION
@app.get("/calculate_json")
def calculate_json(date: str, time: str):

    result = compute_panchanga(date, time)

    return JSONResponse(content=result)
