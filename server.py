from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

import astronomy
from datetime import datetime, timedelta
import math

app = FastAPI()

# -------------------------------------------------
# STATIC + TEMPLATE CONFIG
# -------------------------------------------------

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

# -------------------------------------------------
# CONSTANTS
# -------------------------------------------------

NAKSHATRA_SIZE = 360 / 27
RASHI_SIZE = 30

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

# -------------------------------------------------
# CORE ASTRONOMY FUNCTIONS
# -------------------------------------------------

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

    t = astronomy.Time.Parse(

        utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    )

    return sidereal_longitude(body, t)

# -------------------------------------------------
# PANCHANGA CALCULATIONS
# -------------------------------------------------

def find_tithi_boundary(dt, target):

    low = dt - timedelta(days=1)

    high = dt + timedelta(days=1)

    for _ in range(30):

        mid = low + (high - low) / 2

        diff = (

            get_lon(astronomy.Body.Moon, mid)

            - get_lon(astronomy.Body.Sun, mid)

        ) % 360

        if target == 0 and diff > 180:

            diff -= 360

        if diff < target:

            low = mid

        else:

            high = mid

    return high.strftime("%b %d, %H:%M")


def find_body_boundary(dt, body, target_lon):

    low = dt - timedelta(days=2)

    high = dt + timedelta(days=2)

    for _ in range(30):

        mid = low + (high - low) / 2

        lon = get_lon(body, mid)

        if target_lon == 0 and lon > 180:

            lon -= 360

        if lon < target_lon:

            low = mid

        else:

            high = mid

    return high.strftime("%b %d, %H:%M")


def find_last_amavasya(dt):

    low = dt - timedelta(days=30)

    high = dt

    for _ in range(40):

        mid = low + (high - low) / 2

        diff = (

            get_lon(astronomy.Body.Moon, mid)

            - get_lon(astronomy.Body.Sun, mid)

        ) % 360

        if diff > 180:

            diff -= 360

        if diff < 0:

            low = mid

        else:

            high = mid

    return high


def compute_panchanga(date, time):

    dt = datetime.strptime(

        date + " " + time,

        "%Y-%m-%d %H:%M"

    )

    sun_lon = get_lon(astronomy.Body.Sun, dt)

    moon_lon = get_lon(astronomy.Body.Moon, dt)

    angle = (moon_lon - sun_lon) % 360

    tithi_index = int(angle / 12)

    tithi_start = find_tithi_boundary(

        dt,

        tithi_index * 12

    )

    tithi_end = find_tithi_boundary(

        dt,

        ((tithi_index + 1) % 30) * 12

    )

    nak_index = int(moon_lon / NAKSHATRA_SIZE)

    nak_start = find_body_boundary(

        dt,

        astronomy.Body.Moon,

        nak_index * NAKSHATRA_SIZE

    )

    nak_end = find_body_boundary(

        dt,

        astronomy.Body.Moon,

        ((nak_index + 1) % 27) * NAKSHATRA_SIZE

    )

    moon_rashi_idx = int(moon_lon / 30)

    moon_rashi_start = find_body_boundary(

        dt,

        astronomy.Body.Moon,

        moon_rashi_idx * 30

    )

    moon_rashi_end = find_body_boundary(

        dt,

        astronomy.Body.Moon,

        ((moon_rashi_idx + 1) % 12) * 30

    )

    sun_rashi_idx = int(sun_lon / 30)

    last_amavasya = find_last_amavasya(dt)

    sun_at_amavasya = get_lon(

        astronomy.Body.Sun,

        last_amavasya

    )

    amavasya_rashi = int(sun_at_amavasya / 30)

    lunar_month = lunar_months[(amavasya_rashi + 1) % 12]

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

        "Sun","Moon","Mercury","Venus",

        "Mars","Jupiter","Saturn",

        "Uranus","Neptune"

    ]

    utc = dt - timedelta(hours=5, minutes=30)

    t = astronomy.Time.Parse(

        utc.strftime("%Y-%m-%dT%H:%M:%SZ")

    )

    planets = {

        names[i]:

        sidereal_longitude(bodies[i], t)

        for i in range(len(bodies))

    }

    return {

        "Lunar_month": lunar_month,

        "Paksha":

        "Shukla Paksha"

        if tithi_index < 15

        else "Krishna Paksha",

        "Tithi":

        tithi_names[tithi_index],

        "Tithi_start":

        tithi_start,

        "Tithi_end":

        tithi_end,

        "Nakshatra":

        nakshatras[nak_index],

        "Nakshatra_start":

        nak_start,

        "Nakshatra_end":

        nak_end,

        "Sun_Rashi":

        rashis[sun_rashi_idx],

        "Moon_Rashi":

        rashis[moon_rashi_idx],

        "Moon_Rashi_start":

        moon_rashi_start,

        "Moon_Rashi_end":

        moon_rashi_end,

        "planet_longitudes":

        planets

    }

# -------------------------------------------------
# ROUTES
# -------------------------------------------------

@app.get("/", response_class=HTMLResponse)

def hub(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="index.html"

    )


@app.get("/worldcalendar", response_class=HTMLResponse)

def world_calendar(request: Request):

    now = datetime.now()

    d = now.strftime("%Y-%m-%d")

    t = now.strftime("%H:%M")

    return templates.TemplateResponse(

        request=request,

        name="worldcalendar.html",

        context={

            "result": compute_panchanga(d, t),

            "date": d,

            "time": t

        }

    )


@app.get("/calculate_json")

def calculate_json(date: str, time: str):

    return JSONResponse(

        compute_panchanga(date, time)

    )


@app.get("/monitor", response_class=HTMLResponse)

def monitor(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="worlddaynightmap.html"

    )


@app.get("/solarsystem", response_class=HTMLResponse)

def solar_system(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="solarsystem.html"

    )


# -------------------------------------------------
# NEW ECLIPSE TOOL
# -------------------------------------------------

@app.get("/eclipse", response_class=HTMLResponse)

def eclipse_view(request: Request):

    return templates.TemplateResponse(

        request=request,

        name="eclipse.html"

    )
