import sys
import requests
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QGridLayout,
    QGroupBox, QFrame, QProgressBar, QScrollArea, QSizePolicy, QSpacerItem
)

from astral import Observer
from astral.sun import dawn, dusk
from astral.moon import phase as moon_age
from skyfield.api import load, wgs84
from skyfield import almanac


# -----------------------------
# Config
# -----------------------------
WEATHER_API_KEY = "c5f746a982fb4c9ea6464739250709"
WEATHER_BASE_URL = "http://api.weatherapi.com/v1"
METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

LAT = 33.8847
LON = -118.41
TZ = ZoneInfo("America/Los_Angeles")

CITY = "Manhattan Beach, CA"


# -----------------------------
# Data access
# -----------------------------
def getData():
    # WeatherAPI (kept so you can expand later if you want)
    url = f"{WEATHER_BASE_URL}/current.json?key={WEATHER_API_KEY}&q=Manhattan Beach"
    try:
        weatherResponse = requests.get(url, timeout=10)
        weatherResponse.raise_for_status()
        _ = weatherResponse.json()  # currently unused, but available
    except Exception:
        pass  # non-fatal; Open-Meteo provides the values we display

    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": "sunset,sunrise,precipitation_probability_max,precipitation_hours",
        "current": "precipitation,is_day,temperature_2m,cloud_cover",
        "forecast_days": 7,
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Los_Angeles"
    }

    meteoResponse = requests.get(METEO_BASE_URL, params=params, timeout=12)
    meteoResponse.raise_for_status()
    meteoData = meteoResponse.json()

    # Attach our astronomy (moonrise/set for 7 days) in a similar shape
    astroDaily = moonrise_moonset_7days(LAT, LON, TZ, days=7)
    meteoData["astronomy"] = astroDaily
    return meteoData


# -----------------------------
# Astronomy helpers (yours, kept)
# -----------------------------
def moonrise_moonset_7days(lat=LAT, lon=LON, tz=TZ, start_local=None, days=7):
    """
    Returns dict with lists 'time', 'moonrise', 'moonset' (ISO strings in tz).
    Mirrors Open-Meteo astronomy daily payload so UI code can stay tidy.
    """
    eph, ts = _load_ephemeris()
    loc = wgs84.latlon(lat, lon)

    if start_local is None:
        now_local = datetime.now(tz)
        start_local = now_local.replace(hour=0, minute=0, second=0, microsecond=0)

    out = {"time": [], "moonrise": [], "moonset": []}

    for i in range(days):
        day_local = start_local + timedelta(days=i)
        next_day_local = day_local + timedelta(days=1)

        t0 = ts.from_datetime(day_local.astimezone(timezone.utc))
        t1 = ts.from_datetime(next_day_local.astimezone(timezone.utc))

        f = almanac.risings_and_settings(eph, eph["Moon"], loc)
        times, events = almanac.find_discrete(t0, t1, f)

        rise_iso = ""
        set_iso = ""
        for t, e in zip(times, events):
            dt_local = t.utc_datetime().replace(tzinfo=timezone.utc).astimezone(tz)
            if e == 1 and not rise_iso:
                rise_iso = dt_local.isoformat(timespec="minutes")
            elif e == 0 and not set_iso:
                set_iso = dt_local.isoformat(timespec="minutes")

        out["time"].append(day_local.date().isoformat())
        out["moonrise"].append(rise_iso)
        out["moonset"].append(set_iso)

    return out


def astro_dawn_dusk(d: date | None = None):
    if d is None:
        d = date.today()
    observer = Observer(latitude=LAT, longitude=LON)
    adawn = dawn(observer, date=d, tzinfo=TZ, depression=18)
    adusk = dusk(observer, date=d, tzinfo=TZ, depression=18)
    return adawn, adusk


def moon_phase_name(d: date | datetime | str | None = None):
    if d is None:
        d = date.today()
    elif isinstance(d, str):
        d = datetime.fromisoformat(d).date()
    elif isinstance(d, datetime):
        d = d.date()
    elif not isinstance(d, date):
        raise TypeError(f"Unsupported type for d: {type(d)}")

    age = moon_age(d)
    if age < 1.0:
        return "New Moon"
    elif age < 6.0:
        return "Waxing Crescent"
    elif age < 8.5:
        return "First Quarter"
    elif age < 13.5:
        return "Waxing Gibbous"
    elif age < 15.5:
        return "Full Moon"
    elif age < 21.0:
        return "Waning Gibbous"
    elif age < 23.5:
        return "Last Quarter"
    elif age < 28.5:
        return "Waning Crescent"
    else:
        return "New Moon"


_SF_CACHE = {"eph": None, "ts": None}
def _load_ephemeris():
    if _SF_CACHE["eph"] is None:
        _SF_CACHE["eph"] = load("de421.bsp")
        _SF_CACHE["ts"] = load.timescale()
    return _SF_CACHE["eph"], _SF_CACHE["ts"]


def next_new_and_full_local_tz():
    eph, ts = _load_ephemeris()
    t0 = ts.now()
    t1 = ts.utc(datetime.now(timezone.utc) + timedelta(days=90))
    phase_func = almanac.moon_phases(eph)
    times, phases = almanac.find_discrete(t0, t1, phase_func)

    next_new = None
    next_full = None
    for t, ph in zip(times, phases):
        if ph == 0 and next_new is None:
            next_new = t
        if ph == 2 and next_full is None:
            next_full = t
        if next_new is not None and next_full is not None:
            break

    def to_local(sftime):
        if sftime is None:
            return None
        dt_utc = sftime.utc_datetime().replace(tzinfo=ZoneInfo("UTC"))
        return dt_utc.astimezone(TZ)

    return to_local(next_new), to_local(next_full)


# -----------------------------
# UI helpers
# -----------------------------
APP_STYLE = """
* { color: #E6E8EB; }
QWidget { background-color: #0F1115; font-family: Segoe UI, -apple-system, Roboto, Helvetica, Arial, sans-serif; }
QGroupBox {
    border: 1px solid #232831;
    border-radius: 14px;
    margin-top: 14px;
    padding: 12px 14px 16px 14px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 16px;
    padding: 2px 6px;
    color: #9AA4B2;
    font-weight: 600;
}
QLabel.h1 { font-size: 44px; font-weight: 800; }
QLabel.h2 { font-size: 18px; font-weight: 600; color: #B7C1CF; }
QLabel.mono { font-family: "Consolas","Menlo","Monaco","Courier New",monospace; letter-spacing: 0.3px; }
QFrame#line { background-color: #232831; min-height: 1px; max-height: 1px; }
QProgressBar {
    border: 1px solid #232831;
    border-radius: 10px;
    background: #151A21;
    text-align: center;
    padding: 2px;
}
QProgressBar::chunk {
    border-radius: 8px;
    background-color: #3B82F6;  /* accent */
}
.small { font-size: 12px; color: #9AA4B2; }
.big { font-size: 28px; font-weight: 700; }
"""


def hline():
    line = QFrame()
    line.setObjectName("line")
    line.setFrameShape(QFrame.NoFrame)
    line.setFrameShadow(QFrame.Plain)
    return line


def label(text="", cls=None, align=Qt.AlignLeft):
    w = QLabel(text)
    if cls:
        w.setProperty("class", cls)
        w.setObjectName(cls)
        # PyQt doesn't use CSS classes like web does, but we can apply names we target above.
        # We'll still set a couple of common class names for readability.
        if cls in ("h1", "h2", "mono", "small", "big"):
            w.setProperty("class", cls)
            w.setObjectName(cls)
    w.setAlignment(align)
    w.setWordWrap(True)
    return w


def fmt_time(iso_str, fallback="—", tz=TZ, fmt="%I:%M %p"):
    if not iso_str:
        return fallback
    try:
        return datetime.fromisoformat(str(iso_str)).astimezone(tz).strftime(fmt)
    except Exception:
        try:
            # If it's already localized or simple HH:MM
            return datetime.fromisoformat(str(iso_str)).strftime(fmt)
        except Exception:
            return fallback

def clock_str(dt):
    # Cross-platform 12-hour time without leading zero
    return dt.astimezone(TZ).strftime("%I:%M %p").lstrip("0")

def format_duration(td: timedelta) -> str:
    secs = int(td.total_seconds())
    h, m = secs // 3600, (secs % 3600) // 60
    return f"{h}h {m}m"

def tonight_dark_window(lat=LAT, lon=LON, tz=TZ, d=None):
    """
    Returns (start, end, duration) for tonight's *astronomical* darkness:
    tonight's astronomical dusk → tomorrow's astronomical dawn.
    """
    if d is None:
        d = date.today()
    _, adusk_today = astro_dawn_dusk(d)
    adawn_tomorrow, _ = astro_dawn_dusk(d + timedelta(days=1))

    if not adusk_today or not adawn_tomorrow or adawn_tomorrow <= adusk_today:
        return None, None, None
    return adusk_today, adawn_tomorrow, (adawn_tomorrow - adusk_today)

def moon_alt_and_illumination_at(dt, lat=LAT, lon=LON):
    """
    Altitude (deg) and illumination fraction (0..1) of the Moon at a given datetime.
    """
    eph, ts = _load_ephemeris()
    earth = eph["earth"]
    moon = eph["Moon"]
    t = ts.from_datetime(dt.astimezone(timezone.utc))
    observer = earth + wgs84.latlon(lat, lon)
    app = observer.at(t).observe(moon).apparent()
    alt, az, dist = app.altaz()
    illum = almanac.fraction_illuminated(eph, "Moon", t)  # 0..1
    return alt.degrees, illum

def astro_score(clouds_pct, alt_deg, illum_frac, dur: timedelta) -> int:
    # 0..100 (higher = better imaging night)
    # 50% weight clear sky, 20% moon altitude, 20% low illumination, 10% darkness length
    clouds = 100.0 if clouds_pct is None else max(0.0, min(100.0, float(clouds_pct)))
    clear_component = (100.0 - clouds) * 0.5                # 0..50
    alt_component   = 20.0 if alt_deg <= 0 else max(0.0, 20.0 - float(alt_deg))  # 0..20
    illum = max(0.0, min(1.0, float(illum_frac)))
    illum_component = (1.0 - illum) * 20.0                  # 0..20
    dark_component  = min(max(dur.total_seconds(), 0) / (8*3600.0), 1.0) * 10.0  # 0..10
    total = clear_component + alt_component + illum_component + dark_component
    return int(round(max(0.0, min(100.0, total))))

def set_pill(label_widget, ok: bool, text: str):
    bg = "#282b33" if ok else "#a1a6b5"   # green / amber
    label_widget.setText(text)
    label_widget.setStyleSheet(f"""
        QLabel {{
            background-color: {bg};
            color: #c9cbd1;
            padding: 3px 8px;
            border-radius: 10px;
            font-weight: 700;
        }}
    """)



# -----------------------------
# Main App
# -----------------------------
class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Skyscape • Weather & Astro")
        self.resize(640, 1220)
        self.setStyleSheet(APP_STYLE)

        # Scroll container (content can get tall)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        scroll.setWidget(container)

        root = QVBoxLayout(container)
        root.setContentsMargins(18, 18, 18, 18)
        root.setSpacing(16)

        # Header
        headerBox = QGroupBox()
        headerLayout = QVBoxLayout(headerBox)
        self.titleLabel = label("Manhattan Beach", "h2", Qt.AlignLeft)
        self.titleLabel.setText(CITY)
        self.tempBigLabel = label("—°F", "h1", Qt.AlignLeft)
        subRow = QHBoxLayout()
        self.dayNightLabel = label("—", "big", Qt.AlignLeft)
        self.updatedLabel = label("Updated: —", "small", Qt.AlignRight)
        subRow.addWidget(self.dayNightLabel, 1)
        subRow.addWidget(self.updatedLabel, 0)
        headerLayout.addWidget(self.tempBigLabel)
        headerLayout.addWidget(self.titleLabel)
        headerLayout.addLayout(subRow)

        # Current card
        currentBox = QGroupBox("Current")
        current = QGridLayout(currentBox)
        current.setHorizontalSpacing(12)
        current.setVerticalSpacing(8)

        self.cloudsBar = QProgressBar()
        self.cloudsBar.setRange(0, 100)
        self.cloudsBar.setFormat("Cloud Cover: %p%")
        self.precipNowBar = QProgressBar()
        self.precipNowBar.setRange(0, 100)  # we'll map inches to a rough 0-100 for feel
        self.precipNowValue = label("Precip: — in", "mono", Qt.AlignRight)

        current.addWidget(label("Cloud Cover", "small"), 0, 0)
        current.addWidget(self.cloudsBar, 0, 1)
        current.addWidget(label("Precipitation now", "small"), 1, 0)
        row2 = QHBoxLayout()
        row2.addWidget(self.precipNowBar, 1)
        row2.addSpacing(12)  # ← nudge “Precip:” a little to the right (tune 8/12/16)
        row2.addWidget(self.precipNowValue, 0, alignment=Qt.AlignRight)
        current.addLayout(row2, 1, 1)

        # Sun card
        sunBox = QGroupBox("Sun")
        sun = QGridLayout(sunBox)
        self.sunriseLabel = label("Sunrise: —", "mono")
        self.sunsetLabel = label("Sunset: —", "mono")
        self.astroDawnLabel = label("Astronomical Dawn: —", "mono")
        self.astroDuskLabel = label("Astronomical Dusk: —", "mono")
        sun.addWidget(self.sunriseLabel, 0, 0)
        sun.addWidget(self.sunsetLabel, 0, 1)
        sun.addWidget(self.astroDawnLabel, 1, 0)
        sun.addWidget(self.astroDuskLabel, 1, 1)

        # Moon card
        moonBox = QGroupBox("Moon")
        moon = QGridLayout(moonBox)
        self.moonPhaseLabel = label("Phase: —", "mono")
        self.nextNewLabel = label("Next New: —", "mono")
        self.nextFullLabel = label("Next Full: —", "mono")
        self.moonriseLabel = label("Moonrise: —", "mono")
        self.moonsetLabel = label("Moonset: —", "mono")
        moon.addWidget(self.moonPhaseLabel, 0, 0)
        moon.addWidget(self.moonriseLabel, 0, 1)
        moon.addWidget(self.moonsetLabel, 1, 1)
        moon.addWidget(self.nextNewLabel, 1, 0)
        moon.addWidget(self.nextFullLabel, 2, 0, 1, 2)

        # --- Astro Imaging (Tonight) card ---
        astroImgBox = QGroupBox("Astro Imaging (Tonight)")
        astro = QGridLayout(astroImgBox)

        self.darkWindowLabel = label("Darkness: —", "mono")
        self.darkCenterLabel = label("Midpoint: —", "mono")
        self.moonAltLabel = label("Moon Alt @ midpoint: —", "mono")
        self.moonAltLabel.setWordWrap(False)
        self.moonIllumLabel = label("Moon Illumination: —", "mono")
        self.moonBelowPill = QLabel("")  # horizon pill
        self.astroScoreBar = QProgressBar()
        self.astroScoreBar.setRange(0, 100)
        self.astroScoreBar.setFormat("Astro Score: %p%")

        astro.addWidget(self.darkWindowLabel, 0, 0, 1, 2)
        astro.addWidget(self.darkCenterLabel, 1, 0, 1, 2)
        astro.addWidget(self.moonAltLabel, 2, 0)
        astro.addWidget(self.moonIllumLabel, 2, 1)
        astro.addWidget(self.moonBelowPill, 3, 0)
        astro.addWidget(self.astroScoreBar, 3, 1)

        # Daily Overview card
        dailyBox = QGroupBox("Today")
        daily = QGridLayout(dailyBox)
        self.precipProbToday = label("Precip Probability: —%", "mono")
        self.precipHrsToday = label("Precip Hours: —", "mono")
        daily.addWidget(self.precipProbToday, 0, 0)
        daily.addWidget(self.precipHrsToday, 0, 1)

        # 7-Day Forecast card
        forecastBox = QGroupBox("7-Day Forecast")
        forecast = QGridLayout(forecastBox)
        forecast.setHorizontalSpacing(14)
        forecast.setVerticalSpacing(6)

        # headers
        forecast.addWidget(label("Day", "small"), 0, 0)
        forecast.addWidget(label("Chance (%)", "small"), 0, 1)
        forecast.addWidget(label("Hours", "small"), 0, 2)

        self.forecastRows = []
        for r in range(7):
            dayLbl = label("—", None)
            probLbl = label("—", "mono")
            hrsLbl = label("—", "mono")
            forecast.addWidget(dayLbl, r + 1, 0)
            forecast.addWidget(probLbl, r + 1, 1)
            forecast.addWidget(hrsLbl, r + 1, 2)
            self.forecastRows.append((dayLbl, probLbl, hrsLbl))

        # Status / footer
        self.statusLabel = label("", "small", Qt.AlignCenter)

        # Assemble
        root.addWidget(headerBox)
        root.addWidget(currentBox)
        root.addWidget(sunBox)
        root.addWidget(moonBox)
        root.addWidget(astroImgBox)
        root.addWidget(dailyBox)
        root.addWidget(forecastBox)
        root.addWidget(hline())
        root.addWidget(self.statusLabel)

        page = QVBoxLayout(self)
        page.setContentsMargins(0, 0, 0, 0)
        page.addWidget(scroll)

        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(60_000)  # 60s

        self.refresh(initial=True)

    # -------------------------
    # Data binding
    # -------------------------
    def refresh(self, initial=False):
        try:
            data = getData()
            self.bind_to_ui(data)
            self.statusLabel.setText("")
        except Exception as e:
            if initial:
                self.tempBigLabel.setText("—°F")
            self.statusLabel.setText(f"⚠️ Update failed: {e}")

    def bind_to_ui(self, meteoData: dict):
        # Current
        current = meteoData.get("current", {})
        temp = current.get("temperature_2m")
        clouds = current.get("cloud_cover")
        is_day = current.get("is_day")
        precip_now = current.get("precipitation")

        if temp is not None:
            self.tempBigLabel.setText(f"{round(float(temp))}°F")
        else:
            self.tempBigLabel.setText("—°F")

        self.dayNightLabel.setText("Daytime ☀️" if bool(is_day) else "Night 🌙")
        self.updatedLabel.setText("Updated: " + datetime.now(TZ).strftime("%I:%M %p").lstrip("0"))

        # Cloud cover
        try:
            self.cloudsBar.setValue(int(round(float(clouds))))
        except Exception:
            self.cloudsBar.setValue(0)

        # Precip now (map inches to a feel-based bar up to ~1.0in = 100%)
        try:
            inches = max(0.0, float(precip_now))
            pct = max(0, min(100, int(inches * 100)))
            self.precipNowBar.setValue(pct)
            self.precipNowValue.setText(f'Precip: {inches:.2f}"')
        except Exception:
            self.precipNowBar.setValue(0)
            self.precipNowValue.setText('Precip: —"')

        # Daily
        daily = meteoData.get("daily", {})
        sunrises = daily.get("sunrise", [])
        sunsets = daily.get("sunset", [])
        probs = daily.get("precipitation_probability_max", [])
        hours = daily.get("precipitation_hours", [])

        self.sunriseLabel.setText(f"Sunrise: {fmt_time(sunrises[0] if sunrises else '')}")
        self.sunsetLabel.setText(f"Sunset:  {fmt_time(sunsets[0] if sunsets else '')}")

        adawn, adusk = astro_dawn_dusk()
        self.astroDawnLabel.setText(f"Astronomical Dawn: {adawn.strftime('%I:%M %p')}")
        self.astroDuskLabel.setText(f"Astronomical Dusk: {adusk.strftime('%I:%M %p')}")

        # Today summary
        if probs:
            self.precipProbToday.setText(f"Precipitation Probability: {probs[0]}%")
        else:
            self.precipProbToday.setText("Precipitation Probability: —%")
        if hours:
            self.precipHrsToday.setText(f"Precipitation Hours: {hours[0]} h")
        else:
            self.precipHrsToday.setText("Precipitation Hours: —")

        # Moon
        self.moonPhaseLabel.setText(f"Phase: {moon_phase_name()}")
        new_dt, full_dt = next_new_and_full_local_tz()
        self.nextNewLabel.setText("Next New: " + (new_dt.strftime("%b %d %I:%M %p") if new_dt else "—"))
        self.nextFullLabel.setText("Next Full: " + (full_dt.strftime("%b %d %I:%M %p") if full_dt else "—"))

        astro = meteoData.get("astronomy", {})
        mr = (astro.get("moonrise") or [""])[0]
        ms = (astro.get("moonset") or [""])[0]
        self.moonriseLabel.setText("Moonrise: " + fmt_time(mr))
        self.moonsetLabel.setText("Moonset:  " + fmt_time(ms))

        # --- Astro Imaging (Tonight) ---
        start, end, dur = tonight_dark_window()
        if start and end:
            self.darkWindowLabel.setText(f"Darkness: {clock_str(start)} – {clock_str(end)} ({format_duration(dur)})")
            mid = start + (end - start) / 2
            self.darkCenterLabel.setText(f"Midpoint: {clock_str(mid)}")

            alt_deg, illum = moon_alt_and_illumination_at(mid)
            self.moonAltLabel.setText(f"Moon Altitude At Midpoint: {alt_deg:+.1f}°")
            self.moonIllumLabel.setText(f"        Moon Illumination: {illum * 100:.0f}%")

            # pill: green if moon is below horizon at midpoint, else amber
            set_pill(self.moonBelowPill, alt_deg <= 0, "            Moon below horizon" if alt_deg <= 0 else "            Moon above horizon")

            # score: uses current cloud cover as a quick proxy for tonight
            score = astro_score(clouds, alt_deg, illum, dur)
            self.astroScoreBar.setValue(score)
        else:
            self.darkWindowLabel.setText("Darkness: —")
            self.darkCenterLabel.setText("Midpoint: —")
            self.moonAltLabel.setText("Moon Alt @ midpoint: —")
            self.moonIllumLabel.setText("Moon Illumination: —")
            set_pill(self.moonBelowPill, False, "No darkness window")
            self.astroScoreBar.setValue(0)

        # 7-day forecast grid
        days = []
        try:
            # use sunrise timestamps to get weekday labels
            for i in range(7):
                dt = datetime.fromisoformat(str(sunrises[i])).astimezone(TZ) if i < len(sunrises) else None
                days.append(dt.strftime("%a") if dt else "—")
        except Exception:
            days = ["—"] * 7

        for i, (dayLbl, probLbl, hrsLbl) in enumerate(self.forecastRows):
            dname = days[i] if i < len(days) else "—"
            p = probs[i] if i < len(probs) else "—"
            h = hours[i] if i < len(hours) else "—"
            dayLbl.setText(dname)
            probLbl.setText(str(p))
            hrsLbl.setText(str(h))


# -----------------------------
# Entrypoint
# -----------------------------
def main():
    app = QApplication(sys.argv)
    w = WeatherApp()
    w.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
