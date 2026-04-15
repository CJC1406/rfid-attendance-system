# AttendEase — RFID Attendance System

A full-stack RFID-based attendance management platform built with ESP32, Flask, and SQLite.

## Features

-  **RFID Card Scanning** via ESP32 + RC522 over Wi-Fi
-  **Admin Portal** — dashboard, student management, attendance, analytics, reports, settings
-  **Student Portal** — personal attendance, analytics, calendar heatmap, profile
-  **Chart.js Analytics** — trends, branch stats, top/low attendance
-  **Export** — CSV and PDF reports
-  **Real-time** — live scan feed polling every 3 seconds
-  **Professional Blue UI** — dark navy glassmorphism theme

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Hardware | ESP32 + RC522 RFID |
| Backend | Python / Flask |
| Database | SQLite |
| Frontend | HTML, CSS, JavaScript, Chart.js |

## Quick Start

### 1. Install dependencies
```bash
pip3 install -r requirements.txt
```

### 2. Initialise database (first time only)
```bash
python3 init_db.py
```

### 3. Run the server
```bash
python3 app.py
```

### 4. Open in browser
```
http://127.0.0.1:5001
```

## Default Credentials

| Role | Username | Password |
|------|----------|----------|
| Admin | `admin` | `admin123` |
| Student | USN (e.g. `1SI22CS045`) | `chiranth123` |

> ⚠️ Change these after first login.

## Project Structure

```
rfid_attendance/
├── app.py                  # Flask backend (all routes + API)
├── init_db.py              # Database initialiser + seed data
├── requirements.txt
├── database/
│   └── schema.sql
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── admin/             # 6 admin pages
│   └── student/           # 4 student pages
├── static/
│   ├── css/style.css
│   └── js/
│       ├── main.js
│       ├── charts.js
│       └── admin.js
└── esp32_code/
    └── rfid_wifi.ino      # Arduino sketch for ESP32 + RC522
```

## ESP32 Setup

Edit the top of `esp32_code/rfid_wifi.ino`:
```cpp
const char* WIFI_SSID     = "YOUR_WIFI_SSID";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";
const char* SERVER_URL    = "http://YOUR_SERVER_IP:5001/api/scan";
const char* API_KEY       = "rfid-secret-key-2024";  // Match Settings page
```

### RC522 Wiring (ESP32)
| RC522 | ESP32 GPIO |
|-------|-----------|
| SDA   | 5  |
| SCK   | 18 |
| MOSI  | 23 |
| MISO  | 19 |
| RST   | 22 |
| 3.3V  | 3.3V |
| GND   | GND |

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/scan` | Receive RFID scan from ESP32 |
| `POST` | `/login` | Login |
| `GET`  | `/api/dashboard/stats` | Dashboard statistics |
| `GET`  | `/api/attendance/live` | Today's live scans |
| `GET`  | `/api/students` | All students |
| `POST` | `/api/students` | Add student |
| `GET`  | `/api/analytics/trend` | Attendance trend data |
| `GET`  | `/api/export/csv` | Export CSV |
| `GET`  | `/api/export/pdf` | Export PDF |

## Author

Chiranth J — PES1UG24AM072
