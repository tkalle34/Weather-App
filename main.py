import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
import sys
from datetime import datetime, date, timedelta, timezone
from zoneinfo import ZoneInfo
from astral import Observer
from astral.sun import dawn, dusk
from astral.moon import phase as moon_age
from skyfield.api import load, utc
from skyfield import almanac




WEATHER_API_KEY = "c5f746a982fb4c9ea6464739250709"
WEATHER_BASE_URL = "http://api.weatherapi.com/v1"
METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

LAT = 33.8847
LON = -118.41
TZ = ZoneInfo("America/Los_Angeles")


def main():

    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec_())


def getData():
    city = "Manhattan Beach"
    url = "{0}/current.json?key={1}&q={2}".format(WEATHER_BASE_URL, WEATHER_API_KEY, city)

    weatherResponse = requests.get(url)

    weatherData = weatherResponse.json()

    print(weatherData)

    params = {
        "latitude": LAT,
        "longitude": LON,
        "daily": "sunset,sunrise,precipitation_probability_max,precipitation_hours",
        #"hourly": "precipitation_probability",
        "current": "precipitation,is_day,temperature_2m,cloud_cover",
        "forecast_days": 7,
        "temperature_unit": "fahrenheit",
        "windspeed_unit": "mph",
        "precipitation_unit": "inch",
        "timezone": "America/Los_Angeles"
    }

    meteoResponse = requests.get(METEO_BASE_URL, params=params)
    meteoData = meteoResponse.json()

    print(meteoData)

    return meteoData

def astro_dawn_dusk(d: date | None = None):
    if d is None:
        d = date.today()
    observer = Observer(latitude=LAT, longitude=LON)
    adawn = dawn(observer, date=d, tzinfo=TZ, depression=18)
    adusk = dusk(observer, date=d, tzinfo=TZ, depression=18)
    return adawn, adusk

def moon_phase_name(d: date | None = None):
    if d is None:
        d = date.today()
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
    t1 = ts.utc(datetime.now(timezone.utc) + timedelta(days=90))  # generous window
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
        dt_utc = sftime.utc_datetime().replace(tzinfo=ZoneInfo("UTC"))
        return dt_utc.astimezone(TZ)

    return (to_local(next_new) if next_new is not None else None,
            to_local(next_full) if next_full is not None else None)


class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weather")
        self.setGeometry(200, 200, 450, 1000)



        self.currentLabel = QLabel("Current:", self)
        self.currentLabel.setAlignment(Qt.AlignCenter)
        self.currentLabel.setGeometry(50, 40, 200, 50)

        self.isDayLabel = QLabel("Loading weather...", self)
        self.isDayLabel.setAlignment(Qt.AlignCenter)
        self.isDayLabel.setGeometry(50, 40, 200, 70)

        self.tempLabel = QLabel("Loading weather...", self)
        self.tempLabel.setAlignment(Qt.AlignCenter)
        self.tempLabel.setGeometry(50, 40, 200, 90)

        self.cloudsLabel = QLabel("Loading weather...", self)
        self.cloudsLabel.setAlignment(Qt.AlignCenter)
        self.cloudsLabel.setGeometry(50, 40, 200, 110)

        self.precipCurrLabel = QLabel("Loading weather...", self)
        self.precipCurrLabel.setAlignment(Qt.AlignCenter)
        self.precipCurrLabel.setGeometry(50, 40, 200, 130)



        self.dailyLabel = QLabel("Daily:", self)
        self.dailyLabel.setAlignment(Qt.AlignCenter)
        self.dailyLabel.setGeometry(50, 40, 200, 170)


        self.sunriseLabel = QLabel("Loading weather...", self)
        self.sunriseLabel.setAlignment(Qt.AlignCenter)
        self.sunriseLabel.setGeometry(50, 40, 200, 190)

        self.sunsetLabel = QLabel("Loading weather...", self)
        self.sunsetLabel.setAlignment(Qt.AlignCenter)
        self.sunsetLabel.setGeometry(50, 40, 200, 210)

        self.precipProbLabel = QLabel("Loading weather...", self)
        self.precipProbLabel.setAlignment(Qt.AlignCenter)
        self.precipProbLabel.setGeometry(50, 40, 200, 230)

        self.precipHrsLabel = QLabel("Loading weather...", self)
        self.precipHrsLabel.setAlignment(Qt.AlignCenter)
        self.precipHrsLabel.setGeometry(50, 40, 200, 250)



        self.astroHeader = QLabel("Astronomy:", self)
        self.astroHeader.setAlignment(Qt.AlignCenter)
        self.astroHeader.setGeometry(50, 260, 260, 20)


        self.astroDuskLabel = QLabel("Astronomical dusk: …", self)
        self.astroDuskLabel.setAlignment(Qt.AlignCenter)
        self.astroDuskLabel.setGeometry(50, 280, 260, 20)

        self.astroDawnLabel = QLabel("Astronomical dawn: …", self)
        self.astroDawnLabel.setAlignment(Qt.AlignCenter)
        self.astroDawnLabel.setGeometry(50, 300, 260, 20)

        self.moonPhaseLabel = QLabel("Moon phase: …", self)
        self.moonPhaseLabel.setAlignment(Qt.AlignCenter)
        self.moonPhaseLabel.setGeometry(50, 320, 260, 20)

        self.nextFullLabel = QLabel("Next Full Moon: …", self)
        self.nextFullLabel.setAlignment(Qt.AlignCenter)
        self.nextFullLabel.setGeometry(50, 340, 260, 20)

        self.nextNewLabel = QLabel("Next New Moon: …", self)
        self.nextNewLabel.setAlignment(Qt.AlignCenter)
        self.nextNewLabel.setGeometry(50, 360, 260, 20)


        self.forecastLabel = QLabel("Forecast:", self)
        self.forecastLabel.setAlignment(Qt.AlignCenter)
        self.forecastLabel.setGeometry(50, 420, 260, 20)

        self.precipProbForecastLabel = QLabel("Forecast:", self)
        self.precipProbForecastLabel.setAlignment(Qt.AlignTop)
        self.precipProbForecastLabel.setGeometry(50, 460, 260, 250)

        self.precipHrsForecastLabel = QLabel("Forecast:", self)
        self.precipHrsForecastLabel.setAlignment(Qt.AlignTop)
        self.precipHrsForecastLabel.setGeometry(230, 460, 260, 250)


        self.timer = QTimer(self)
        self.timer.timeout.connect(self.updateWeatherCurrent)
        self.timer.start(60000)

        self.updateWeatherCurrent()

    def updateWeatherCurrent(self):
        meteoData = getData()
        temp = meteoData["current"]["temperature_2m"]
        clouds = meteoData["current"]["cloud_cover"]
        isDay = meteoData["current"]["is_day"]
        precipCurr = meteoData["current"]["precipitation"]

        sunrise = datetime.fromisoformat(str(meteoData["daily"]["sunrise"][0])).strftime("%I:%M %p")
        sunset = datetime.fromisoformat(str(meteoData["daily"]["sunset"][0])).strftime("%I:%M %p")


        precipProb = meteoData["daily"]["precipitation_probability_max"]
        precipHrs = meteoData["daily"]["precipitation_hours"]


        self.tempLabel.setText("Temperature: 🌡{0}°F".format(temp))
        self.cloudsLabel.setText("Cloud Cover: {0}%".format(clouds))
        self.isDayLabel.setText("{day}".format(day = "Day" if bool(isDay) else "Night"))
        self.precipCurrLabel.setText("Precipitation Amount: {0}\"".format(precipCurr))

        self.sunriseLabel.setText("Sunrise: {0}".format(sunrise))
        self.sunsetLabel.setText("Sunset: {0}".format(sunset))
        self.precipProbLabel.setText("Precipitation Probability: {0}%".format(precipProb[0]))
        self.precipHrsLabel.setText("Precipitation Hours: {0} hours".format(precipHrs[0]))


        self.moonPhaseLabel.setText(f"Moon Phase: {moon_phase_name()}")

        adawn, adusk = astro_dawn_dusk()
        self.astroDawnLabel.setText(f"Astronomical Dawn: {adawn.strftime('%I:%M %p')}")
        self.astroDuskLabel.setText(f"Astronomical Dusk: {adusk.strftime('%I:%M %p')}")

        new_dt, full_dt = next_new_and_full_local_tz()
        if (new_dt is not None) and (full_dt is not None):
            self.nextNewLabel.setText(f"Next New Moon: {new_dt.strftime('%b %d %I:%M %p')}")
            self.nextFullLabel.setText(f"Next Full Moon: {full_dt.strftime('%b %d %I:%M %p')}")


        self.precipProbForecastLabel.setText("<u>Precipitation Probability</u><br>{day1}: {prob1}%<br>{day2}: {prob2}%<br>{day3}: {prob3}%<br>{day4}: {prob4}%<br>{day5}: {prob5}%<br>{day6}: {prob6}%<br>{day7}: {prob7}%".format(day1 = datetime.fromisoformat(meteoData["daily"]["sunrise"][0]).strftime("%A"), prob1 = meteoData["daily"]["precipitation_probability_max"][0], day2 = datetime.fromisoformat(meteoData["daily"]["sunrise"][1]).strftime("%A"), prob2 = meteoData["daily"]["precipitation_probability_max"][1], day3 = datetime.fromisoformat(meteoData["daily"]["sunrise"][2]).strftime("%A"), prob3 = meteoData["daily"]["precipitation_probability_max"][2], day4 = datetime.fromisoformat(meteoData["daily"]["sunrise"][3]).strftime("%A"), prob4 = meteoData["daily"]["precipitation_probability_max"][3], day5 = datetime.fromisoformat(meteoData["daily"]["sunrise"][4]).strftime("%A"), prob5 = meteoData["daily"]["precipitation_probability_max"][4], day6 = datetime.fromisoformat(meteoData["daily"]["sunrise"][5]).strftime("%A"), prob6 = meteoData["daily"]["precipitation_probability_max"][5], day7 = datetime.fromisoformat(meteoData["daily"]["sunrise"][6]).strftime("%A"), prob7 = meteoData["daily"]["precipitation_probability_max"][6]))
        self.precipHrsForecastLabel.setText("<u>Precipitation Hours</u><br>{day1}: {hrs1} hours<br>{day2}: {hrs2} hours<br>{day3}: {hrs3} hours<br>{day4}: {hrs4} hours<br>{day5}: {hrs5} hours<br>{day6}: {hrs6} hours<br>{day7}: {hrs7} hours".format(day1 = datetime.fromisoformat(meteoData["daily"]["sunrise"][0]).strftime("%A"), hrs1 = meteoData["daily"]["precipitation_hours"][0], day2 = datetime.fromisoformat(meteoData["daily"]["sunrise"][1]).strftime("%A"), hrs2 = meteoData["daily"]["precipitation_hours"][1], day3 = datetime.fromisoformat(meteoData["daily"]["sunrise"][2]).strftime("%A"), hrs3 = meteoData["daily"]["precipitation_hours"][2], day4 = datetime.fromisoformat(meteoData["daily"]["sunrise"][3]).strftime("%A"), hrs4 = meteoData["daily"]["precipitation_hours"][3], day5 = datetime.fromisoformat(meteoData["daily"]["sunrise"][4]).strftime("%A"), hrs5 = meteoData["daily"]["precipitation_hours"][4], day6 = datetime.fromisoformat(meteoData["daily"]["sunrise"][5]).strftime("%A"), hrs6 = meteoData["daily"]["precipitation_hours"][5], day7 = datetime.fromisoformat(meteoData["daily"]["sunrise"][6]).strftime("%A"), hrs7 = meteoData["daily"]["precipitation_hours"][6]))


if __name__ == '__main__':
    main()
