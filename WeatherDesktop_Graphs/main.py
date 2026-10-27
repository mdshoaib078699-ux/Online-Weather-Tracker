import sys
import os
import json
import random
import socket
import math
from datetime import datetime, timedelta

import requests

try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from PySide6.QtCore import (
    Qt, QThread, Signal, QObject, QTimer, QPoint, QSize
)
from PySide6.QtGui import (
    QFont, QAction, QIcon, QPainter, QPen, QColor, QLinearGradient,
    QPixmap
)
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout, QHBoxLayout, QGridLayout,
    QFrame, QCheckBox, QComboBox, QMessageBox, QSystemTrayIcon, QMenu,
    QSizePolicy, QScrollArea, QTabWidget, QDialog, QDialogButtonBox,
    QGraphicsDropShadowEffect
)

APP_NAME = "Online Weather Tracker"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(os.path.expanduser("~"), ".weather_desktop_config.json")
HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".weather_desktop_history.json")
WEATHER_HISTORY_FILE = os.path.join(os.path.expanduser("~"), ".weather_desktop_weather_history.json")
ICON_FILE = os.path.join(BASE_DIR, "assets", "weather.ico")
PNG_ICON_FILE = os.path.join(BASE_DIR, "assets", "weather.png")

WEATHER_CODES = {
    0: ("Clear Sky", "☀️", "clear"),
    1: ("Mainly Clear", "🌤️", "clear"),
    2: ("Partly Cloudy", "⛅", "cloudy"),
    3: ("Overcast", "☁️", "cloudy"),
    45: ("Fog", "🌫️", "fog"),
    48: ("Rime Fog", "🌫️", "fog"),
    51: ("Light Drizzle", "🌦️", "rain"),
    53: ("Moderate Drizzle", "🌦️", "rain"),
    55: ("Heavy Drizzle", "🌧️", "rain"),
    56: ("Freezing Drizzle", "🌧️", "rain"),
    57: ("Heavy Freezing Drizzle", "🌧️", "rain"),
    61: ("Light Rain", "🌦️", "rain"),
    63: ("Moderate Rain", "🌧️", "rain"),
    65: ("Heavy Rain", "🌧️", "rain"),
    66: ("Freezing Rain", "🌧️", "rain"),
    67: ("Heavy Freezing Rain", "🌧️", "rain"),
    71: ("Light Snow", "🌨️", "snow"),
    73: ("Moderate Snow", "🌨️", "snow"),
    75: ("Heavy Snow", "❄️", "snow"),
    77: ("Snow Grains", "❄️", "snow"),
    80: ("Light Showers", "🌦️", "rain"),
    81: ("Moderate Showers", "🌧️", "rain"),
    82: ("Heavy Showers", "⛈️", "storm"),
    85: ("Snow Showers", "🌨️", "snow"),
    86: ("Heavy Snow Showers", "❄️", "snow"),
    95: ("Thunderstorm", "⛈️", "storm"),
    96: ("Thunderstorm + Hail", "⛈️", "storm"),
    99: ("Heavy Thunderstorm", "⛈️", "storm"),
}

THEMES = {
    "Dark": {
        "window": "#0b1220", "surface": "#111c2f", "surface2": "#17243a",
        "text": "#f8fafc", "muted": "#94a3b8", "accent": "#38bdf8",
        "border": "#263750", "button": "#2563eb", "button_hover": "#3b82f6"
    },
    "Light": {
        "window": "#eef4fb", "surface": "#ffffff", "surface2": "#f5f8fc",
        "text": "#0f172a", "muted": "#64748b", "accent": "#0284c7",
        "border": "#d7e0ea", "button": "#2563eb", "button_hover": "#1d4ed8"
    },
    "Ocean": {
        "window": "#061a24", "surface": "#0b2835", "surface2": "#103746",
        "text": "#ecfeff", "muted": "#8fb9c4", "accent": "#22d3ee",
        "border": "#1d4e5d", "button": "#0891b2", "button_hover": "#06b6d4"
    },
    "Sunset": {
        "window": "#21131b", "surface": "#301a26", "surface2": "#432033",
        "text": "#fff7ed", "muted": "#d6a7b9", "accent": "#fb923c",
        "border": "#613249", "button": "#ea580c", "button_hover": "#f97316"
    },
}

def default_config():
    return {
        "city": "New Delhi, India",
        "latitude": 28.6139,
        "longitude": 77.2090,
        "widget": False,
        "theme": "Dark",
        "unit": "Celsius",
        "refresh_minutes": 15
    }

def load_json(path, fallback):
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return fallback

def save_json(path, data):
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception:
        pass

def load_config():
    data = load_json(CONFIG_FILE, default_config())
    base = default_config()
    base.update(data if isinstance(data, dict) else {})
    return base

def load_history():
    data = load_json(HISTORY_FILE, [])
    return data if isinstance(data, list) else []

def save_history(history):
    save_json(HISTORY_FILE, history[-100:])

def weather_description(code):
    return WEATHER_CODES.get(code, ("Unknown", "🌡️", "clear"))

def aqi_status(aqi):
    if aqi is None:
        return "Unavailable"
    if aqi <= 20:
        return "Good"
    if aqi <= 40:
        return "Fair"
    if aqi <= 60:
        return "Moderate"
    if aqi <= 80:
        return "Poor"
    if aqi <= 100:
        return "Very Poor"
    return "Extremely Poor"

def wind_direction(degrees):
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    return dirs[int((degrees + 22.5) / 45) % 8]

def c_to_f(c):
    return c * 9 / 5 + 32

def internet_available():
    try:
        socket.create_connection(("1.1.1.1", 53), timeout=2.5)
        return True
    except OSError:
        try:
            requests.get("https://api.open-meteo.com", timeout=3)
            return True
        except requests.RequestException:
            return False

class AlertDialog(QDialog):
    def __init__(self, parent, title, message, icon="⚠️"):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(380)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        top = QHBoxLayout()
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 34px;")
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 20px; font-weight: 700;")
        top.addWidget(icon_label)
        top.addWidget(title_label)
        top.addStretch()
        layout.addLayout(top)
        msg = QLabel(message)
        msg.setWordWrap(True)
        msg.setStyleSheet("font-size: 14px; line-height: 1.4;")
        layout.addWidget(msg)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok)
        buttons.accepted.connect(self.accept)
        layout.addWidget(buttons)
        self.setStyleSheet("""
            QDialog { background: #111827; color: #f8fafc; }
            QDialogButtonBox QPushButton {
                background: #2563eb; color: white; border: 0;
                border-radius: 8px; padding: 9px 22px; min-width: 80px;
            }
            QDialogButtonBox QPushButton:hover { background: #3b82f6; }
        """)

class WeatherBackground(QWidget):
    """Responsive animated background that changes with weather condition."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.condition = "clear"
        self.is_day = True
        self.drops = []
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate)
        self.timer.start(35)
        self.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        self.setMinimumSize(1, 1)

    def set_weather(self, condition, is_day=True):
        self.condition = condition
        self.is_day = bool(is_day)
        count = {
            "rain": 90, "storm": 120, "snow": 70,
            "fog": 35, "cloudy": 20, "clear": 8
        }.get(condition, 20)
        self.drops = [
            [random.random(), random.random(), random.uniform(0.007, 0.02)]
            for _ in range(count)
        ]
        self.update()

    def animate(self):
        if self.condition in ("rain", "storm", "snow"):
            for d in self.drops:
                d[1] += d[2]
                if d[1] > 1.05:
                    d[0] = random.random()
                    d[1] = -0.05
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        rect = self.rect()
        if self.condition == "rain":
            g = QLinearGradient(0, 0, 0, rect.height())
            g.setColorAt(0, QColor("#12243b"))
            g.setColorAt(1, QColor("#07111f"))
        elif self.condition == "storm":
            g = QLinearGradient(0, 0, 0, rect.height())
            g.setColorAt(0, QColor("#17182d"))
            g.setColorAt(1, QColor("#070914"))
        elif self.condition == "snow":
            g = QLinearGradient(0, 0, 0, rect.height())
            g.setColorAt(0, QColor("#263b52"))
            g.setColorAt(1, QColor("#101a28"))
        elif self.condition == "cloudy":
            g = QLinearGradient(0, 0, 0, rect.height())
            g.setColorAt(0, QColor("#334155"))
            g.setColorAt(1, QColor("#172033"))
        elif self.condition == "fog":
            g = QLinearGradient(0, 0, 0, rect.height())
            g.setColorAt(0, QColor("#64748b"))
            g.setColorAt(1, QColor("#273449"))
        else:
            if self.is_day:
                g = QLinearGradient(0, 0, 0, rect.height())
                g.setColorAt(0, QColor("#0c4a6e"))
                g.setColorAt(0.55, QColor("#0369a1"))
                g.setColorAt(1, QColor("#082f49"))
            else:
                g = QLinearGradient(0, 0, 0, rect.height())
                g.setColorAt(0, QColor("#090d25"))
                g.setColorAt(1, QColor("#111827"))
        p.fillRect(rect, g)

        if self.condition in ("rain", "storm"):
            pen = QPen(QColor(130, 200, 235, 110), 1.2)
            p.setPen(pen)
            for x, y, speed in self.drops:
                px = int(x * rect.width())
                py = int(y * rect.height())
                p.drawLine(px, py, px - 5, py + 18)
        elif self.condition == "snow":
            p.setPen(QPen(QColor(240, 248, 255, 180), 1.5))
            for x, y, speed in self.drops:
                p.drawEllipse(
                    int(x * rect.width()), int(y * rect.height()), 4, 4
                )
        elif self.condition == "fog":
            p.setPen(QPen(QColor(235, 245, 250, 35), 18))
            for i in range(7):
                y = int((i + 1) * rect.height() / 8)
                p.drawLine(0, y, rect.width(), y)

class WeatherWorker(QObject):
    finished = Signal(dict)
    error = Signal(str)
    no_internet = Signal()

    def __init__(self, latitude, longitude):
        super().__init__()
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        if not internet_available():
            self.no_internet.emit()
            return
        try:
            weather_url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": ",".join([
                    "temperature_2m", "relative_humidity_2m",
                    "apparent_temperature", "is_day", "precipitation",
                    "rain", "weather_code", "cloud_cover", "pressure_msl",
                    "surface_pressure", "wind_speed_10m",
                    "wind_direction_10m", "wind_gusts_10m",
                    "visibility", "uv_index"
                ]),
                "hourly": ",".join([
                    "temperature_2m", "relative_humidity_2m",
                    "precipitation_probability", "precipitation",
                    "weather_code", "wind_speed_10m"
                ]),
                "daily": ",".join([
                    "weather_code", "temperature_2m_max",
                    "temperature_2m_min", "precipitation_probability_max",
                    "sunrise", "sunset"
                ]),
                "forecast_days": 5,
                "timezone": "auto",
                "wind_speed_unit": "kmh",
                "temperature_unit": "celsius"
            }
            r = requests.get(weather_url, params=params, timeout=15)
            r.raise_for_status()

            aq_url = "https://air-quality-api.open-meteo.com/v1/air-quality"
            aq_params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "current": ",".join([
                    "european_aqi", "pm10", "pm2_5",
                    "carbon_monoxide", "nitrogen_dioxide",
                    "sulphur_dioxide", "ozone"
                ]),
                "timezone": "auto"
            }
            aq = requests.get(aq_url, params=aq_params, timeout=15)
            aq.raise_for_status()

            self.finished.emit({
                "weather": r.json(),
                "air_quality": aq.json()
            })
        except requests.RequestException as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))



class WeatherHistoryWorker(QObject):
    """Fetch the latest 7 days including today's weather data."""
    finished = Signal(dict)
    error = Signal(str)
    no_internet = Signal()

    def __init__(self, latitude, longitude):
        super().__init__()
        self.latitude = latitude
        self.longitude = longitude

    def run(self):
        if not internet_available():
            self.no_internet.emit()
            return

        try:
            url = "https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": self.latitude,
                "longitude": self.longitude,
                "daily": ",".join([
                    "temperature_2m_mean",
                    "temperature_2m_max",
                    "temperature_2m_min",
                    "precipitation_sum",
                    "weather_code"
                ]),
                "past_days": 6,
                "forecast_days": 1,
                "timezone": "auto",
                "temperature_unit": "celsius"
            }

            response = requests.get(url, params=params, timeout=20)
            response.raise_for_status()
            payload = response.json()

            daily = payload.get("daily", {})
            dates = daily.get("time", [])

            if not dates:
                self.error.emit("No daily weather data was returned.")
                return

            # Use the location's local date returned by the API.
            today = datetime.now().date()
            try:
                timezone_name = payload.get("timezone")
                if timezone_name:
                    from zoneinfo import ZoneInfo
                    today = datetime.now(ZoneInfo(timezone_name)).date()
            except Exception:
                pass

            # Keep dates up to today; exclude future forecast dates.
            selected_indices = [
                i for i, value in enumerate(dates)
                if datetime.fromisoformat(value).date() <= today
            ][-7:]

            if not selected_indices:
                self.error.emit("No weather data available for the selected dates.")
                return

            selected = {}
            for key, values in daily.items():
                if isinstance(values, list):
                    selected[key] = [
                        values[i] for i in selected_indices
                        if i < len(values)
                    ]
                else:
                    selected[key] = values

            self.finished.emit({
                "daily": selected,
                "timezone": payload.get("timezone"),
                "latitude": payload.get("latitude"),
                "longitude": payload.get("longitude")
            })

        except requests.RequestException as e:
            self.error.emit(f"Weather API request failed: {e}")
        except Exception as e:
            self.error.emit(f"Unable to process weather history: {e}")


class LocationWorker(QObject):
    finished = Signal(list)
    error = Signal(str)
    no_internet = Signal()

    def __init__(self, search_text):
        super().__init__()
        self.search_text = search_text

    def run(self):
        if not internet_available():
            self.no_internet.emit()
            return
        try:
            url = "https://geocoding-api.open-meteo.com/v1/search"
            params = {
                "name": self.search_text,
                "count": 10,
                "language": "en",
                "format": "json"
            }
            r = requests.get(url, params=params, timeout=10)
            r.raise_for_status()
            self.finished.emit(r.json().get("results", []))
        except requests.RequestException as e:
            self.error.emit(str(e))
        except Exception as e:
            self.error.emit(str(e))

class WeatherCard(QFrame):
    def __init__(self, title, value, icon=""):
        super().__init__()
        self.setObjectName("weatherCard")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(5)
        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 22px;")
        title_label = QLabel(title)
        title_label.setObjectName("cardTitle")
        value_label = QLabel(value)
        value_label.setObjectName("cardValue")
        value_label.setWordWrap(True)
        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        self.value_label = value_label

    def set_value(self, value):
        self.value_label.setText(value)

class ForecastCard(QFrame):
    def __init__(self):
        super().__init__()
        self.setObjectName("forecastCard")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 12, 10, 12)
        self.day = QLabel("--")
        self.icon = QLabel("🌤️")
        self.icon.setObjectName("forecastIcon")
        self.temp = QLabel("--° / --°")
        self.rain = QLabel("Rain --%")
        for w in (self.day, self.icon, self.temp, self.rain):
            w.setAlignment(Qt.AlignCenter)
            w.setWordWrap(True)
            layout.addWidget(w)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config = load_config()
        self.history = load_history()
        self.weather_thread = None
        self.location_thread = None
        self.drag_position = None
        self.widget_mode = False
        self.current_condition = "clear"
        self.last_weather = None

        self.setWindowTitle(APP_NAME)
        self.setMinimumSize(680, 620)
        self.resize(1100, 800)
        if os.path.exists(ICON_FILE):
            self.setWindowIcon(QIcon(ICON_FILE))
        elif os.path.exists(PNG_ICON_FILE):
            self.setWindowIcon(QIcon(PNG_ICON_FILE))

        self.build_ui()
        self.setup_tray()
        self.apply_theme()
        self.load_saved_location()
        self.refresh_history_tab()

        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_weather)
        self.set_refresh_interval()

        self.refresh_weather()

    def build_ui(self):
        self.root = QWidget()
        self.setCentralWidget(self.root)

        root_layout = QVBoxLayout(self.root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.background = WeatherBackground(self.root)
        self.background.lower()

        self.content = QWidget(self.root)
        content_layout = QVBoxLayout(self.content)
        content_layout.setContentsMargins(24, 20, 24, 20)
        content_layout.setSpacing(14)

        # Header
        header = QHBoxLayout()
        self.title = QLabel("🌤️ Online Weather Tracker")
        self.title.setObjectName("appTitle")
        header.addWidget(self.title)
        header.addStretch()
        self.refresh_button = QPushButton("↻ Refresh")
        self.refresh_button.clicked.connect(self.refresh_weather)
        header.addWidget(self.refresh_button)
        content_layout.addLayout(header)

        # Search
        search_box = QFrame()
        search_box.setObjectName("surface")
        search_layout = QHBoxLayout(search_box)
        search_layout.setContentsMargins(10, 10, 10, 10)
        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Search city, town or postal code...")
        self.location_input.returnPressed.connect(self.search_location)
        self.search_button = QPushButton("🔍 Search")
        self.search_button.clicked.connect(self.search_location)
        search_layout.addWidget(self.location_input, 1)
        search_layout.addWidget(self.search_button)
        content_layout.addWidget(search_box)

        self.location_list = QListWidget()
        self.location_list.setMaximumHeight(150)
        self.location_list.itemClicked.connect(self.select_location)
        self.location_list.hide()
        content_layout.addWidget(self.location_list)

        self.tabs = QTabWidget()
        content_layout.addWidget(self.tabs, 1)

        self.dashboard_tab = QWidget()
        self.history_tab = QWidget()
        self.settings_tab = QWidget()
        self.tabs.addTab(self.dashboard_tab, "🌤️ Weather")
        self.tabs.addTab(self.history_tab, "🕘 History")
        self.tabs.addTab(self.settings_tab, "⚙️ Settings")

        self.build_dashboard()
        self.build_history()
        self.build_settings()

        footer = QLabel(
            "Project by: Mohd Shoaib   |   "
            "Institute: Silverwink IT Training Insitute   |   "
            "Guide: Shubham Chaudhary   |   Address: Muzaffarnagar"
        )
        footer.setObjectName("footerLabel")
        footer.setAlignment(Qt.AlignCenter)
        footer.setWordWrap(True)
        footer.setMinimumHeight(34)

        root_layout.addWidget(self.content)
        root_layout.addWidget(footer)
        self.content.raise_()

    def build_dashboard(self):
        outer = QVBoxLayout(self.dashboard_tab)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroll)

        container = QWidget()
        self.dashboard_container = container
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 8)
        layout.setSpacing(14)

        current = QFrame()
        current.setObjectName("currentFrame")
        current_layout = QHBoxLayout(current)
        current_layout.setContentsMargins(22, 18, 22, 18)

        self.weather_icon = QLabel("☀️")
        self.weather_icon.setObjectName("weatherIcon")
        self.weather_icon.setAlignment(Qt.AlignCenter)
        current_layout.addWidget(self.weather_icon)

        middle = QVBoxLayout()
        self.city_label = QLabel("New Delhi, India")
        self.city_label.setObjectName("cityLabel")
        self.temperature_label = QLabel("--°C")
        self.temperature_label.setObjectName("temperatureLabel")
        self.condition_label = QLabel("Loading weather...")
        self.condition_label.setObjectName("conditionLabel")
        self.updated_label = QLabel("")
        self.updated_label.setObjectName("updatedLabel")
        middle.addWidget(self.city_label)
        middle.addWidget(self.temperature_label)
        middle.addWidget(self.condition_label)
        middle.addWidget(self.updated_label)
        current_layout.addLayout(middle, 1)

        self.feels_label = QLabel("Feels like\n--°C")
        self.feels_label.setObjectName("feelsLabel")
        self.feels_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        current_layout.addWidget(self.feels_label)
        layout.addWidget(current)

        self.details_grid = QGridLayout()
        self.details_grid.setSpacing(10)
        cards = [
            ("humidity_card", "Humidity", "--", "💧"),
            ("wind_card", "Wind", "--", "💨"),
            ("pressure_card", "Pressure", "--", "🔵"),
            ("visibility_card", "Visibility", "--", "👁️"),
            ("rain_card", "Precipitation", "--", "☔"),
            ("uv_card", "UV Index", "--", "☀️"),
        ]
        self.detail_cards = []
        for index, (attr, title, value, icon) in enumerate(cards):
            card = WeatherCard(title, value, icon)
            setattr(self, attr, card)
            self.detail_cards.append(card)
        self.reflow_detail_cards()
        layout.addLayout(self.details_grid)

        aq = QFrame()
        aq.setObjectName("aqiFrame")
        aq_layout = QGridLayout(aq)
        aq_layout.setContentsMargins(18, 14, 18, 14)
        aq_title = QLabel("🌫️ Air Quality")
        aq_title.setObjectName("sectionTitle")
        self.aqi_label = QLabel("AQI --")
        self.aqi_label.setObjectName("aqiValue")
        self.aqi_status_label = QLabel("Loading...")
        self.pm25_label = QLabel("PM2.5: --")
        self.pm10_label = QLabel("PM10: --")
        self.no2_label = QLabel("NO₂: --")
        self.ozone_label = QLabel("O₃: --")
        aq_layout.addWidget(aq_title, 0, 0)
        aq_layout.addWidget(self.aqi_label, 0, 1)
        aq_layout.addWidget(self.aqi_status_label, 0, 2)
        aq_layout.addWidget(self.pm25_label, 1, 0)
        aq_layout.addWidget(self.pm10_label, 1, 1)
        aq_layout.addWidget(self.no2_label, 1, 2)
        aq_layout.addWidget(self.ozone_label, 1, 3)
        layout.addWidget(aq)

        self.forecast_title = QLabel("5-Day Forecast")
        self.forecast_title.setObjectName("sectionTitle")
        layout.addWidget(self.forecast_title)

        self.forecast_grid = QGridLayout()
        self.forecast_grid.setSpacing(10)
        self.forecast_cards = [ForecastCard() for _ in range(5)]
        self.reflow_forecast_cards()
        layout.addLayout(self.forecast_grid)

        sun = QFrame()
        sun.setObjectName("surface")
        sun_layout = QHBoxLayout(sun)
        self.sunrise_label = QLabel("🌅 Sunrise: --")
        self.sunset_label = QLabel("🌇 Sunset: --")
        sun_layout.addWidget(self.sunrise_label)
        sun_layout.addStretch()
        sun_layout.addWidget(self.sunset_label)
        layout.addWidget(sun)
        layout.addStretch()
        scroll.setWidget(container)

    def build_history(self):
        layout = QVBoxLayout(self.history_tab)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        top = QHBoxLayout()
        title = QLabel("📊 Weather History & Analysis")
        title.setObjectName("sectionTitle")
        top.addWidget(title)
        top.addStretch()

        self.graph_location_label = QLabel("No weather data loaded")
        self.graph_location_label.setObjectName("infoText")
        top.addWidget(self.graph_location_label)

        self.graph_refresh_button = QPushButton("↻ Update Graphs")
        self.graph_refresh_button.clicked.connect(self.refresh_graphs)
        top.addWidget(self.graph_refresh_button)
        layout.addLayout(top)

        if MATPLOTLIB_AVAILABLE:
            self.graph_scroll = QScrollArea()
            self.graph_scroll.setWidgetResizable(True)
            self.graph_scroll.setFrameShape(QFrame.NoFrame)

            graph_container = QWidget()
            graph_layout = QVBoxLayout(graph_container)
            graph_layout.setContentsMargins(0, 0, 0, 8)
            graph_layout.setSpacing(10)

            # Both graphs side by side with equal width
            graph_row = QHBoxLayout()
            graph_row.setSpacing(10)

            self.temperature_graph_frame = QFrame()
            self.temperature_graph_frame.setObjectName("surface")
            self.temperature_graph_frame.setMinimumHeight(340)
            self.temperature_graph_frame.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            temp_layout = QVBoxLayout(self.temperature_graph_frame)
            temp_layout.setContentsMargins(8, 8, 8, 8)

            self.temperature_figure = Figure(figsize=(6, 3.5), dpi=100)
            self.temperature_canvas = FigureCanvas(self.temperature_figure)
            self.temperature_canvas.setMinimumHeight(300)
            self.temperature_canvas.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            temp_layout.addWidget(self.temperature_canvas)

            self.rain_graph_frame = QFrame()
            self.rain_graph_frame.setObjectName("surface")
            self.rain_graph_frame.setMinimumHeight(340)
            self.rain_graph_frame.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            rain_layout = QVBoxLayout(self.rain_graph_frame)
            rain_layout.setContentsMargins(8, 8, 8, 8)

            self.rain_figure = Figure(figsize=(6, 3.5), dpi=100)
            self.rain_canvas = FigureCanvas(self.rain_figure)
            self.rain_canvas.setMinimumHeight(300)
            self.rain_canvas.setSizePolicy(
                QSizePolicy.Expanding, QSizePolicy.Expanding
            )
            rain_layout.addWidget(self.rain_canvas)

            graph_row.addWidget(self.temperature_graph_frame, 1)
            graph_row.addWidget(self.rain_graph_frame, 1)
            graph_layout.addLayout(graph_row)

            self.analysis_label = QLabel(
                "Analysis will appear here after the 7-day weather history is loaded."
            )
            self.analysis_label.setWordWrap(True)
            self.analysis_label.setObjectName("analysisText")
            graph_layout.addWidget(self.analysis_label)

            self.graph_scroll.setWidget(graph_container)
            layout.addWidget(self.graph_scroll, 1)
            self.draw_empty_graphs()

        else:
            error = QLabel(
                "Matplotlib is not installed.\n\n"
                "Run: pip install matplotlib\n"
                "Then restart Online Weather Tracker."
            )
            error.setWordWrap(True)
            error.setAlignment(Qt.AlignCenter)
            layout.addWidget(error, 1)

        # Search history remains below both graphs
        search_title = QLabel("🕘 Search & Location History")
        search_title.setObjectName("sectionTitle")
        layout.addWidget(search_title)

        self.history_list = QListWidget()
        self.history_list.setMinimumHeight(55)
        self.history_list.setMaximumHeight(85)
        self.history_list.itemDoubleClicked.connect(self.use_history_item)
        layout.addWidget(self.history_list)

        history_buttons = QHBoxLayout()
        clear = QPushButton("Clear Search History")
        clear.clicked.connect(self.clear_history)
        history_buttons.addWidget(clear)
        history_buttons.addStretch()

        hint = QLabel("Double-click a saved location to load its weather.")
        hint.setObjectName("infoText")
        history_buttons.addWidget(hint)
        layout.addLayout(history_buttons)

    def draw_empty_graphs(self):
        if not MATPLOTLIB_AVAILABLE:
            return
        for fig, title in (
            (self.temperature_figure, "7-Day Temperature Trend"),
            (self.rain_figure, "7-Day Precipitation"),
        ):
            fig.clear()
            ax = fig.add_subplot(111)
            ax.text(
                0.5, 0.5, "Loading 7-day weather history…",
                ha="center", va="center", transform=ax.transAxes, fontsize=12
            )
            ax.set_title(title, fontsize=13, fontweight="bold")
            ax.set_xticks([])
            ax.set_yticks([])
            fig.tight_layout()
        self.temperature_canvas.draw()
        self.rain_canvas.draw()

    def refresh_graphs(self):
        if not MATPLOTLIB_AVAILABLE:
            return

        lat = self.config.get("latitude")
        lon = self.config.get("longitude")
        if lat is None or lon is None:
            return

        if not internet_available():
            self.show_offline_alert()
            return

        self.graph_refresh_button.setEnabled(False)
        self.graph_location_label.setText(
            f"Loading: {self.config.get('city', 'Selected location')}"
        )

        self.history_weather_thread = QThread()
        self.history_weather_worker = WeatherHistoryWorker(lat, lon)
        self.history_weather_worker.moveToThread(self.history_weather_thread)
        self.history_weather_thread.started.connect(self.history_weather_worker.run)
        self.history_weather_worker.finished.connect(self.weather_history_received)
        self.history_weather_worker.error.connect(self.weather_history_error)
        self.history_weather_worker.no_internet.connect(self.weather_history_offline)
        self.history_weather_worker.finished.connect(self.history_weather_thread.quit)
        self.history_weather_worker.error.connect(self.history_weather_thread.quit)
        self.history_weather_worker.no_internet.connect(self.history_weather_thread.quit)
        self.history_weather_thread.finished.connect(
            self.history_weather_thread.deleteLater
        )
        self.history_weather_thread.start()

    def weather_history_received(self, data):
        self.graph_refresh_button.setEnabled(True)
        self.graph_location_label.setText(
            f"Last 7 days • {self.config.get('city', 'Selected location')}"
        )
        self.last_weather_history = data
        self.save_weather_history_snapshot(data)
        self.draw_weather_graphs(data)

    def weather_history_error(self, message):
        self.graph_refresh_button.setEnabled(True)
        self.graph_location_label.setText("Unable to load history")
        AlertDialog(self, "History Graph Error", message, "📊").exec()

    def weather_history_offline(self):
        self.graph_refresh_button.setEnabled(True)
        self.graph_location_label.setText("Offline")
        self.show_offline_alert()


    def draw_weather_graphs(self, data):
        if not MATPLOTLIB_AVAILABLE:
            return

        daily = data.get("daily", {})
        dates = daily.get("time", [])
        means = daily.get("temperature_2m_mean", [])
        highs = daily.get("temperature_2m_max", [])
        lows = daily.get("temperature_2m_min", [])
        rain = daily.get("precipitation_sum", [])

        count = min(
            len(dates), len(means), len(highs), len(lows), len(rain)
        )

        if count == 0:
            self.draw_empty_graphs()
            self.analysis_label.setText("No weather history is available.")
            return

        dates = dates[:count]
        means = means[:count]
        highs = highs[:count]
        lows = lows[:count]
        rain = rain[:count]

        labels = [
            datetime.fromisoformat(d).strftime("%d %b %Y")
            for d in dates
        ]

        # Temperature graph
        self.temperature_figure.clear()
        ax = self.temperature_figure.add_subplot(111)

        ax.plot(labels, highs, marker="o", linewidth=2, label="Maximum")
        ax.plot(labels, means, marker="o", linewidth=2, label="Average")
        ax.plot(labels, lows, marker="o", linewidth=2, label="Minimum")
        ax.fill_between(range(count), lows, highs, alpha=0.10)

        ax.set_title("Daily Temperature Trend", fontsize=13, fontweight="bold")
        ax.set_ylabel("Temperature (°C)")
        ax.set_xlabel("Date")
        ax.grid(True, alpha=0.22)
        ax.legend(loc="best")
        ax.tick_params(axis="x", rotation=35)

        self.temperature_figure.tight_layout()
        self.temperature_canvas.draw()

        # Rainfall graph
        self.rain_figure.clear()
        ax2 = self.rain_figure.add_subplot(111)

        ax2.bar(labels, rain)
        ax2.set_title("Daily Precipitation", fontsize=13, fontweight="bold")
        ax2.set_ylabel("Rainfall (mm)")
        ax2.set_xlabel("Date")
        ax2.grid(True, axis="y", alpha=0.22)
        ax2.tick_params(axis="x", rotation=35)

        self.rain_figure.tight_layout()
        self.rain_canvas.draw()

        # Analysis based on returned data
        valid_highs = [v for v in highs if v is not None]
        valid_lows = [v for v in lows if v is not None]
        valid_means = [v for v in means if v is not None]
        valid_rain = [v for v in rain if v is not None]

        if not valid_highs or not valid_lows:
            self.analysis_label.setText(
                "Temperature analysis is unavailable for these dates."
            )
            return

        hottest = max(valid_highs)
        coldest = min(valid_lows)
        total_rain = sum(valid_rain)
        rainy_days = sum(1 for value in valid_rain if value >= 1.0)

        if len(valid_means) >= 2:
            change = valid_means[-1] - valid_means[0]
            if change > 1:
                trend = f"Average temperature increased by {change:.1f}°C."
            elif change < -1:
                trend = f"Average temperature decreased by {abs(change):.1f}°C."
            else:
                trend = f"Average temperature changed by only {change:+.1f}°C."
        else:
            trend = "Not enough data to calculate a temperature trend."

        latest_date = datetime.fromisoformat(dates[-1]).strftime("%d %B %Y")

        self.analysis_label.setText(
            f"<b>Weather Analysis through {latest_date}</b><br>"
            f"Temperature range: {coldest:.1f}°C to {hottest:.1f}°C"
            f" &nbsp; • &nbsp; Total precipitation: {total_rain:.1f} mm"
            f" &nbsp; • &nbsp; Rainy days: {rainy_days}<br>"
            f"<b>Trend:</b> {trend}"
        )

    def save_weather_history_snapshot(self, data):
        """Save graph data in JSON so the project keeps a local analysis record."""
        history = load_json(WEATHER_HISTORY_FILE, [])
        if not isinstance(history, list):
            history = []

        daily = data.get("daily", {})
        snapshot = {
            "saved_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "city": self.config.get("city", ""),
            "latitude": self.config.get("latitude"),
            "longitude": self.config.get("longitude"),
            "daily": daily,
        }
        history.append(snapshot)
        save_json(WEATHER_HISTORY_FILE, history[-30:])

    def build_settings(self):
        layout = QVBoxLayout(self.settings_tab)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(14)

        appearance = QFrame()
        appearance.setObjectName("surface")
        grid = QGridLayout(appearance)
        grid.setContentsMargins(18, 18, 18, 18)

        title = QLabel("Appearance")
        title.setObjectName("sectionTitle")
        grid.addWidget(title, 0, 0, 1, 2)

        grid.addWidget(QLabel("Theme"), 1, 0)
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(list(THEMES.keys()))
        self.theme_combo.setCurrentText(self.config.get("theme", "Dark"))
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        grid.addWidget(self.theme_combo, 1, 1)

        grid.addWidget(QLabel("Temperature unit"), 2, 0)
        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["Celsius", "Fahrenheit"])
        self.unit_combo.setCurrentText(self.config.get("unit", "Celsius"))
        self.unit_combo.currentTextChanged.connect(self.change_unit)
        grid.addWidget(self.unit_combo, 2, 1)

        grid.addWidget(QLabel("Refresh interval"), 3, 0)
        self.refresh_combo = QComboBox()
        self.refresh_combo.addItems(["5", "10", "15", "30", "60"])
        self.refresh_combo.setCurrentText(str(self.config.get("refresh_minutes", 15)))
        self.refresh_combo.currentTextChanged.connect(self.change_refresh_interval)
        grid.addWidget(self.refresh_combo, 3, 1)

        self.widget_checkbox = QCheckBox("📌 Desktop Widget Mode")
        self.widget_checkbox.setChecked(bool(self.config.get("widget", False)))
        self.widget_checkbox.stateChanged.connect(self.toggle_widget_mode)
        grid.addWidget(self.widget_checkbox, 4, 0, 1, 2)

        layout.addWidget(appearance)

        info = QFrame()
        info.setObjectName("surface")
        il = QVBoxLayout(info)
        h = QLabel("Saved files")
        h.setObjectName("sectionTitle")
        il.addWidget(h)
        il.addWidget(QLabel(f"Settings: {CONFIG_FILE}"))
        il.addWidget(QLabel(f"History: {HISTORY_FILE}"))
        layout.addWidget(info)
        layout.addStretch()

    def reflow_detail_cards(self):
        while self.details_grid.count():
            item = self.details_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        columns = self.responsive_columns(3, 2)
        for i, card in enumerate(self.detail_cards):
            self.details_grid.addWidget(card, i // columns, i % columns)

    def reflow_forecast_cards(self):
        while self.forecast_grid.count():
            item = self.forecast_grid.takeAt(0)
            if item.widget():
                item.widget().setParent(None)
        columns = self.responsive_columns(5, 2)
        for i, card in enumerate(self.forecast_cards):
            self.forecast_grid.addWidget(card, i // columns, i % columns)

    def responsive_columns(self, wide, narrow):
        width = max(self.width(), 680)
        if width < 820:
            return narrow
        return wide

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "background"):
            self.background.setGeometry(self.root.rect())
        if hasattr(self, "details_grid"):
            self.reflow_detail_cards()
        if hasattr(self, "forecast_grid"):
            self.reflow_forecast_cards()


    def make_shadow(self, widget):
        shadow = QGraphicsDropShadowEffect(widget)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 8)
        shadow.setColor(QColor(0, 0, 0, 70))
        widget.setGraphicsEffect(shadow)

    def apply_theme(self):
        theme_name = self.config.get("theme", "Dark")
        t = THEMES.get(theme_name, THEMES["Dark"])
        self.setStyleSheet(f"""
            QMainWindow, QWidget#centralWidget {{
                background: transparent;
                color: {t["text"]};
                font-family: "Segoe UI";
                font-size: 14px;
            }}
            QTabWidget::pane {{
                border: 1px solid {t["border"]};
                border-radius: 14px;
                background: rgba(10,20,35,180);
            }}
            QTabBar::tab {{
                background: {t["surface"]};
                color: {t["muted"]};
                padding: 11px 18px;
                margin-right: 4px;
                border-radius: 8px;
            }}
            QTabBar::tab:selected {{
                background: {t["button"]};
                color: white;
            }}
            #appTitle {{
                font-size: 28px;
                font-weight: 700;
                color: {t["text"]};
            }}
            #surface, #weatherCard, #forecastCard, #aqiFrame {{
                background: {t["surface"]};
                border: 1px solid {t["border"]};
                border-radius: 14px;
            }}
            QLineEdit, QComboBox, QListWidget {{
                background: {t["surface"]};
                border: 1px solid {t["border"]};
                border-radius: 9px;
                padding: 9px;
                color: {t["text"]};
            }}
            QComboBox QAbstractItemView {{
                background: {t["surface"]};
                color: {t["text"]};
                selection-background-color: {t["button"]};
            }}
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {t["accent"]};
            }}
            QPushButton {{
                background: {t["button"]};
                color: white;
                border: 0;
                border-radius: 9px;
                padding: 10px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: {t["button_hover"]};
            }}
            QListWidget::item {{
                padding: 9px;
                border-radius: 7px;
            }}
            QListWidget::item:hover {{
                background: {t["surface2"]};
            }}
            #currentFrame {{
                background: rgba(15, 55, 85, 210);
                border: 1px solid rgba(255,255,255,35);
                border-radius: 20px;
            }}
            #weatherIcon {{ font-size: 70px; min-width: 115px; }}
            #cityLabel {{ font-size: 22px; font-weight: 650; }}
            #temperatureLabel {{ font-size: 52px; font-weight: 750; }}
            #conditionLabel {{ font-size: 18px; color: {t["accent"]}; }}
            #updatedLabel, #infoText {{ color: {t["muted"]}; font-size: 12px; }}
            #feelsLabel {{ font-size: 17px; color: {t["text"]}; }}
            #cardTitle {{ color: {t["muted"]}; font-size: 12px; }}
            #cardValue {{ color: {t["text"]}; font-size: 17px; font-weight: 650; }}
            #forecastIcon {{ font-size: 34px; }}
            #sectionTitle {{ font-size: 18px; font-weight: 700; color: {t["text"]}; }}
            #aqiValue {{ font-size: 22px; font-weight: 750; color: {t["accent"]}; }}
            #footerLabel {{
                color: {t["muted"]};
                background: {t["surface"]};
                border-top: 1px solid {t["border"]};
                padding: 8px 12px;
                font-size: 11px;
            }}
            #analysisText {{
                color: {t["text"]};
                background: {t["surface"]};
                border: 1px solid {t["border"]};
                border-radius: 10px;
                padding: 10px;
                font-size: 13px;
            }}
            QCheckBox {{ spacing: 8px; }}
            QScrollArea {{ background: transparent; border: 0; }}
        """)
        self.background.raise_()
        self.content.raise_()
        self.background.setGeometry(self.root.rect())
        if hasattr(self, "theme_combo"):
            self.theme_combo.setCurrentText(theme_name)

    def load_saved_location(self):
        city = self.config.get("city", "New Delhi, India")
        self.city_label.setText(city)
        self.location_input.setText(city)

    def change_theme(self, theme):
        self.config["theme"] = theme
        save_json(CONFIG_FILE, self.config)
        self.apply_theme()

    def change_unit(self, unit):
        self.config["unit"] = unit
        save_json(CONFIG_FILE, self.config)
        if self.last_weather:
            self.display_weather(self.last_weather)

    def change_refresh_interval(self, value):
        try:
            minutes = int(value)
        except ValueError:
            minutes = 15
        self.config["refresh_minutes"] = minutes
        save_json(CONFIG_FILE, self.config)
        self.set_refresh_interval()

    def set_refresh_interval(self):
        minutes = int(self.config.get("refresh_minutes", 15))
        if hasattr(self, "refresh_timer"):
            self.refresh_timer.start(minutes * 60 * 1000)

    def add_history(self, search_text, result=None, status="success"):
        entry = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "search": search_text,
            "status": status
        }
        if result:
            entry.update({
                "city": result.get("name", ""),
                "country": result.get("country", ""),
                "admin1": result.get("admin1", ""),
                "latitude": result.get("latitude"),
                "longitude": result.get("longitude")
            })
        self.history.append(entry)
        save_history(self.history)
        self.refresh_history_tab()

    def refresh_history_tab(self):
        if not hasattr(self, "history_list"):
            return
        self.history_list.clear()
        for entry in reversed(self.history[-100:]):
            city = entry.get("city") or entry.get("search", "Unknown")
            country = entry.get("country", "")
            time = entry.get("time", "")
            status = entry.get("status", "")
            text = f"{city}, {country}   •   {time}"
            if status != "success":
                text += f"   •   {status}"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, entry)
            self.history_list.addItem(item)

    def clear_history(self):
        self.history = []
        save_history(self.history)
        self.refresh_history_tab()

    def use_history_item(self, item):
        entry = item.data(Qt.UserRole)
        if not entry or entry.get("latitude") is None:
            return
        self.config.update({
            "city": f'{entry.get("city", "Unknown")}, {entry.get("country", "")}'.strip(", "),
            "latitude": entry["latitude"],
            "longitude": entry["longitude"]
        })
        save_json(CONFIG_FILE, self.config)
        self.city_label.setText(self.config["city"])
        self.location_input.setText(self.config["city"])
        self.tabs.setCurrentWidget(self.dashboard_tab)
        self.refresh_weather()

    def search_location(self):
        text = self.location_input.text().strip()
        if not text:
            return
        if not internet_available():
            self.add_history(text, status="offline")
            self.show_offline_alert()
            return

        self.search_button.setEnabled(False)
        self.location_list.clear()
        self.location_list.show()

        self.location_thread = QThread()
        self.location_worker = LocationWorker(text)
        self.location_worker.moveToThread(self.location_thread)
        self.location_thread.started.connect(self.location_worker.run)
        self.location_worker.finished.connect(self.location_results)
        self.location_worker.error.connect(self.location_error)
        self.location_worker.no_internet.connect(self.location_worker_offline)
        self.location_worker.finished.connect(self.location_thread.quit)
        self.location_worker.error.connect(self.location_thread.quit)
        self.location_worker.no_internet.connect(self.location_thread.quit)
        self.location_thread.finished.connect(self.location_thread.deleteLater)
        self.location_thread.start()

    def location_results(self, results):
        self.search_button.setEnabled(True)
        self.location_list.clear()
        if not results:
            self.location_list.addItem("No location found")
            return
        for result in results:
            name = result.get("name", "")
            country = result.get("country", "")
            admin = result.get("admin1", "")
            text = ", ".join(x for x in [name, admin, country] if x)
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, result)
            self.location_list.addItem(item)

    def location_error(self, message):
        self.search_button.setEnabled(True)
        self.location_list.hide()
        AlertDialog(self, "Location Search Error", message, "⚠️").exec()

    def location_worker_offline(self):
        self.search_button.setEnabled(True)
        self.location_list.hide()
        self.show_offline_alert()

    def select_location(self, item):
        data = item.data(Qt.UserRole)
        if not data:
            return
        city = data.get("name", "Unknown")
        country = data.get("country", "")
        self.config.update({
            "city": f"{city}, {country}".strip(", "),
            "latitude": data.get("latitude"),
            "longitude": data.get("longitude")
        })
        save_json(CONFIG_FILE, self.config)
        self.add_history(self.location_input.text().strip(), data)
        self.city_label.setText(self.config["city"])
        self.location_input.setText(self.config["city"])
        self.location_list.hide()
        self.tabs.setCurrentWidget(self.dashboard_tab)
        self.refresh_weather()

    def refresh_weather(self):
        if not internet_available():
            self.show_offline_alert()
            self.condition_label.setText("Offline — showing last available data")
            return

        lat = self.config.get("latitude")
        lon = self.config.get("longitude")
        if lat is None or lon is None:
            return

        self.refresh_button.setEnabled(False)
        self.condition_label.setText("Updating weather…")

        self.weather_thread = QThread()
        self.weather_worker = WeatherWorker(lat, lon)
        self.weather_worker.moveToThread(self.weather_thread)
        self.weather_thread.started.connect(self.weather_worker.run)
        self.weather_worker.finished.connect(self.weather_received)
        self.weather_worker.error.connect(self.weather_error)
        self.weather_worker.no_internet.connect(self.weather_worker_offline)
        self.weather_worker.finished.connect(self.weather_thread.quit)
        self.weather_worker.error.connect(self.weather_thread.quit)
        self.weather_worker.no_internet.connect(self.weather_thread.quit)
        self.weather_thread.finished.connect(self.weather_thread.deleteLater)
        self.weather_thread.start()

    def weather_worker_offline(self):
        self.refresh_button.setEnabled(True)
        self.show_offline_alert()

    def weather_error(self, message):
        self.refresh_button.setEnabled(True)
        self.condition_label.setText("Unable to update weather")
        AlertDialog(self, "Weather Error", message, "⚠️").exec()

    def weather_received(self, data):
        self.refresh_button.setEnabled(True)
        self.last_weather = data
        self.display_weather(data)
        self.refresh_graphs()

    def display_weather(self, data):
        weather = data["weather"]
        air = data["air_quality"]
        current = weather["current"]

        code = current["weather_code"]
        description, icon, condition = weather_description(code)
        is_day = bool(current.get("is_day", 1))
        self.current_condition = condition
        self.background.set_weather(condition, is_day)

        c = current["temperature_2m"]
        apparent = current["apparent_temperature"]
        unit = self.config.get("unit", "Celsius")
        if unit == "Fahrenheit":
            temp_text = f"{c_to_f(c):.1f}°F"
            feels_text = f"Feels like\n{c_to_f(apparent):.1f}°F"
        else:
            temp_text = f"{c:.1f}°C"
            feels_text = f"Feels like\n{apparent:.1f}°C"

        self.weather_icon.setText(icon)
        self.temperature_label.setText(temp_text)
        self.condition_label.setText(description)
        self.feels_label.setText(feels_text)
        self.humidity_card.set_value(f'{current["relative_humidity_2m"]}%')

        wind = current["wind_speed_10m"]
        direction = current["wind_direction_10m"]
        self.wind_card.set_value(f"{wind:.1f} km/h\n{wind_direction(direction)} {direction:.0f}°")
        self.pressure_card.set_value(f'{current["pressure_msl"]:.0f} hPa')
        self.visibility_card.set_value(f'{current["visibility"] / 1000:.1f} km')
        self.rain_card.set_value(f'{current["precipitation"]:.1f} mm')
        self.uv_card.set_value(f'{current.get("uv_index", 0):.1f}')
        self.updated_label.setText(
            "Updated: " + datetime.now().strftime("%d %b %Y, %I:%M %p")
        )

        aq = air.get("current", {})
        aqi = aq.get("european_aqi")
        self.aqi_label.setText(f"AQI {aqi:.0f}" if aqi is not None else "AQI --")
        self.aqi_status_label.setText(aqi_status(aqi))
        self.pm25_label.setText(f'PM2.5: {aq.get("pm2_5", 0):.1f} μg/m³')
        self.pm10_label.setText(f'PM10: {aq.get("pm10", 0):.1f} μg/m³')
        self.no2_label.setText(f'NO₂: {aq.get("nitrogen_dioxide", 0):.1f}')
        self.ozone_label.setText(f'O₃: {aq.get("ozone", 0):.1f}')

        daily = weather["daily"]
        for i in range(min(5, len(daily["time"]))):
            day = datetime.fromisoformat(daily["time"][i]).strftime("%a")
            desc, icon, _ = weather_description(daily["weather_code"][i])
            card = self.forecast_cards[i]
            card.day.setText(day)
            card.icon.setText(icon)
            hi = daily["temperature_2m_max"][i]
            lo = daily["temperature_2m_min"][i]
            if unit == "Fahrenheit":
                card.temp.setText(f"{c_to_f(hi):.0f}° / {c_to_f(lo):.0f}°")
            else:
                card.temp.setText(f"{hi:.0f}° / {lo:.0f}°")
            card.rain.setText(f'Rain {daily["precipitation_probability_max"][i]}%')

        sunrise = datetime.fromisoformat(daily["sunrise"][0]).strftime("%I:%M %p")
        sunset = datetime.fromisoformat(daily["sunset"][0]).strftime("%I:%M %p")
        self.sunrise_label.setText(f"🌅 Sunrise: {sunrise}")
        self.sunset_label.setText(f"🌇 Sunset: {sunset}")

    def show_offline_alert(self):
        AlertDialog(
            self,
            "No Internet Connection",
            "Internet connection is not active.\n\n"
            "Please connect your computer to the internet and try again.",
            "📡"
        ).exec()

    def toggle_widget_mode(self, state):
        enabled = state == Qt.Checked
        self.widget_mode = enabled
        self.config["widget"] = enabled
        save_json(CONFIG_FILE, self.config)
        if enabled:
            self.enable_widget()
        else:
            self.disable_widget()

    def enable_widget(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool
        )
        self.resize(410, 550)
        self.show()
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            screen.right() - self.width() - 25,
            screen.bottom() - self.height() - 35
        )

    def disable_widget(self):
        self.setWindowFlags(Qt.Window)
        self.resize(1100, 800)
        self.show()

    def mousePressEvent(self, event):
        if self.widget_mode and event.button() == Qt.LeftButton:
            self.drag_position = (
                event.globalPosition().toPoint()
                - self.frameGeometry().topLeft()
            )
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if (
            self.widget_mode
            and event.buttons() & Qt.LeftButton
            and self.drag_position is not None
        ):
            self.move(
                event.globalPosition().toPoint() - self.drag_position
            )
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def setup_tray(self):
        self.tray = QSystemTrayIcon(self)
        if os.path.exists(ICON_FILE):
            self.tray.setIcon(QIcon(ICON_FILE))
        elif os.path.exists(PNG_ICON_FILE):
            self.tray.setIcon(QIcon(PNG_ICON_FILE))
        self.tray.setToolTip(APP_NAME)

        menu = QMenu()
        show_action = QAction("Open Weather", self)
        show_action.triggered.connect(self.show_window)
        refresh_action = QAction("Refresh Weather", self)
        refresh_action.triggered.connect(self.refresh_weather)
        widget_action = QAction("Toggle Widget", self)
        widget_action.triggered.connect(
            lambda: self.widget_checkbox.setChecked(
                not self.widget_checkbox.isChecked()
            )
        )
        quit_action = QAction("Exit", self)
        quit_action.triggered.connect(QApplication.quit)

        menu.addAction(show_action)
        menu.addAction(refresh_action)
        menu.addAction(widget_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.tray_clicked)
        self.tray.show()

    def show_window(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def tray_clicked(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self.show_window()

def create_icon_if_missing():
    # Creates a simple fallback PNG-based icon if no ICO exists.
    # The generated ICO is intentionally simple and does not require extra packages.
    if os.path.exists(ICON_FILE):
        return
    try:
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        p = QPainter(pix)
        p.setRenderHint(QPainter.Antialiasing)
        p.setBrush(QColor("#2563eb"))
        p.setPen(Qt.NoPen)
        p.drawRoundedRect(3, 3, 58, 58, 15, 15)
        p.setPen(QPen(QColor("#ffffff"), 3))
        p.drawEllipse(16, 14, 28, 28)
        p.setPen(QPen(QColor("#8be9fd"), 3))
        p.drawLine(32, 4, 32, 10)
        p.drawLine(32, 46, 32, 57)
        p.drawLine(5, 32, 11, 32)
        p.drawLine(53, 32, 59, 32)
        p.end()
        # Qt can use PNG directly for runtime taskbar/tray icon.
        png = os.path.join(assets_dir(), "weather.png")
        pix.save(png)
    except Exception:
        pass

def assets_dir():
    path = os.path.join(BASE_DIR, "assets")
    os.makedirs(path, exist_ok=True)
    return path

def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("WeatherDesktop")
    app.setQuitOnLastWindowClosed(False)

    icon_path = ICON_FILE
    png_path = PNG_ICON_FILE
    assets_dir()
    if os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))
    elif os.path.exists(png_path):
        app.setWindowIcon(QIcon(png_path))

    window = MainWindow()
    if os.path.exists(icon_path):
        window.setWindowIcon(QIcon(icon_path))
    elif os.path.exists(png_path):
        window.setWindowIcon(QIcon(png_path))

    window.show()

    if window.config.get("widget", False):
        window.widget_checkbox.setChecked(True)

    sys.exit(app.exec())

if __name__ == "__main__":
    main()


