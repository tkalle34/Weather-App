import requests
from PyQt5.QtWidgets import QApplication, QWidget, QLabel
from PyQt5.QtCore import QTimer, Qt
import sys
from datetime import datetime

WEATHER_API_KEY = "c5f746a982fb4c9ea6464739250709"
WEATHER_BASE_URL = "http://api.weatherapi.com/v1"
METEO_BASE_URL = "https://api.open-meteo.com/v1/forecast"

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
        "latitude": 33.8847,
        "longitude": -118.41,
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


class WeatherApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Weather")
        self.setGeometry(200, 200, 300, 150)



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







        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_weather)
        self.timer.start(60000)

        self.update_weather()

    def update_weather(self):
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



if __name__ == '__main__':
    main()
