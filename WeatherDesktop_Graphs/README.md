# Online Weather Tracker - Graph Analysis Edition

## Features
- Responsive PySide6 desktop weather app
- Current weather, AQI and 5-day forecast
- City/location search
- Dark, Light, Ocean and Sunset themes
- Celsius/Fahrenheit
- Auto refresh
- Desktop widget mode
- System tray/taskbar icon support
- Offline custom alert dialog
- Search history saved to JSON
- 7-day historical weather graphs:
  - Maximum / average / minimum temperature trend
  - 7-day precipitation
  - Simple factual trend analysis
- Graph snapshots saved locally in JSON
- Footer:
  Project by: Mohd Shoaib
  Institute: Silverwink IT Training Insitute
  Guide: Shubham Chaudhary
  Address: Muzaffarnagar

## Install
```bash
pip install -r requirements.txt
python main.py
```

The graph data uses Open-Meteo's forecast endpoint with `past_days=7`.
