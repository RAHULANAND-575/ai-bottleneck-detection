# 📈 AI based Bottleneck Detection in Heterogeneous Systems

![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-lightgrey?logo=flask)
![License](https://img.shields.io/badge/license-MIT-green)

A **full-stack web application** that provides a predictive framework for identifying CPU/GPU bottlenecks in heterogeneous computing systems and recommending targeted optimization strategies — all viewable live in the browser.

---

## ✨ Features

- 📊 **Live gauges** — CPU, GPU, RAM, and PCIe throughput updated every 2 seconds
- 🔍 **AI bottleneck detection** — hybrid rule-based + ML-scored engine classifying compute-, memory-, I/O-, and communication-bound bottlenecks
- 💡 **Optimization recommendations** — prioritised, actionable strategies per bottleneck type
- 📈 **Historical trend chart** — rolling 30-sample Chart.js line chart
- 🎨 **Dark-theme dashboard** — responsive, card-based, professional UI
- 🖥️ **GPU fallback** — simulated GPU metrics when no physical GPU is present

---

## 🏗️ Architecture

```
Browser (index.html / app.js / style.css)
        │   fetch() every 2–10 s
        ▼
Flask REST API (backend/app.py)  :5000
  ├── GET /api/metrics  →  monitor.SystemMonitor.get_all_metrics()
  ├── GET /api/detect   →  detector.BottleneckDetector.detect()
  └── GET /api/recommend→  recommender.Recommender.recommend()
```

---

## 📁 Project Structure

```
ai-bottleneck-detection/
├── index.html          # Dashboard UI
├── style.css           # Dark theme styles
├── app.js              # Frontend logic & chart
├── backend/
│   ├── __init__.py
│   ├── app.py          # Flask REST API server
│   ├── detector.py     # Hybrid bottleneck detector
│   ├── recommender.py  # Optimization recommendation engine
│   └── monitor.py      # System metrics collector
├── requirements.txt
└── README.md
```

---

## 🚀 Installation & Usage

### 1. Clone the repository

```bash
git clone https://github.com/RAHULANAND-575/ai-bottleneck-detection.git
cd ai-bottleneck-detection
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the Flask server

```bash
python -m backend.app
```

### 5. Open the dashboard

Navigate to **http://localhost:5000** in your browser.

---

## 🔌 API Reference

| Method | Endpoint          | Description                                               |
|--------|-------------------|-----------------------------------------------------------|
| GET    | `/`               | Serves the frontend dashboard (`index.html`)              |
| GET    | `/api/metrics`    | Returns CPU %, GPU %, RAM %, PCIe throughput              |
| GET    | `/api/detect`     | Runs bottleneck detector; returns type/severity/confidence|
| GET    | `/api/recommend`  | Returns prioritised optimization strategies               |

### Example response — `/api/metrics`

```json
{
  "status": "ok",
  "data": {
    "cpu_percent": 42.3,
    "memory_percent": 61.8,
    "memory_used_gb": 9.88,
    "memory_total_gb": 16.0,
    "gpu_available": false,
    "gpu_name": "Simulated GPU",
    "gpu_load_percent": 58.1,
    "gpu_memory_percent": 44.7,
    "pcie_throughput_gbps": 7.34,
    "timestamp": 1710000000.0
  }
}
```

### Example response — `/api/detect`

```json
{
  "status": "ok",
  "data": [
    {
      "type": "memory-bound",
      "severity": "high",
      "confidence": 0.871,
      "description": "RAM at 82%, GPU memory at 80% — memory pressure is limiting throughput.",
      "timestamp": 1710000000.0
    }
  ]
}
```

---

## 🛠️ Tech Stack

| Layer     | Technology                  |
|-----------|-----------------------------|
| Frontend  | HTML5, CSS3, Vanilla JS     |
| Charts    | Chart.js 4 (CDN)            |
| Fonts     | Google Fonts – Inter        |
| Backend   | Python 3.10+, Flask 3.0     |
| Metrics   | psutil, GPUtil              |
| ML        | NumPy, scikit-learn         |
| CORS      | flask-cors                  |

---

## 📸 Screenshots

The dashboard features:
- A sticky dark header with live/offline status badge and "Run Analysis" button
- Four metric gauge cards (CPU, GPU, RAM, PCIe) with animated progress bars
- A real-time Chart.js line chart tracking the last 30 data points
- A "Detected Bottlenecks" panel with colour-coded severity cards
- An "Optimization Recommendations" panel with priority-tagged strategy cards

---

## 📄 License

MIT © 2024 RAHULANAND-575
