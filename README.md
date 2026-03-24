# Fin-Autopilot 🚀

An AI-powered enterprise Cost Intelligence Platform targeting Indian CFOs and finance teams. Built for the Economic Times Hackathon 2026.

## Overview
Fin-Autopilot acts as an autonomous agent that ingests enterprise financial data and surfaces prioritised alerts with exact ₹ savings impact.

### Key Features
- **4 Detection Engines**: Duplicate Vendors, Cloud Cost Spikes, Procurement Benchmarks, and Budget Variance.
- **₹ Savings Scorecard**: Animated counter ticking up as anomalies are discovered.
- **AI Insights Chat**: An interactive slide-out pane to converse dynamically with your ingested data.
- **Remediation Workflows**: One-click recommended actions mapping straight to ROI.
- **CFO Report Generation**: Export current findings directly to PDF.

---

## 🛠️ Tech Stack
- **Frontend**: React 18, TypeScript, Vite, TailwindCSS, Framer Motion, Recharts
- **Backend**: Python 3.10, FastAPI, Pandas, Uvicorn
- **Containerization**: Docker & Docker Compose

---

## 🚀 One-Command Startup (Recommended)
Ensure Docker and `docker-compose` are installed, then simply run:
```bash
docker-compose up -d
```
The application will be available at:
- **Frontend UI**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

---

## 💻 Manual Setup (Local Dev)
If you prefer not to use Docker:

### 1. Backend (FastAPI)
```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 🎬 2-Minute Demo Script (For Judges)

1. **Open Application**: Navigate to `http://localhost:5173`. Point out the pristine UI and zero-state landing.
2. **Start Ingestion**: Click the **"Load Demo Dataset"** button on the bottom left of the sidebar. This auto-loads the Prism Retail Pvt Ltd dataset scenario.
3. **Observe the AI Agents in Action**:
   - The UI will gracefully populate anomalies one by one over 8 seconds.
   - Point out the **"Total Waste Identified"** counter dynamically ticking up, stopping exactly at ₹45.3 Lakh.
   - Show the severity badging.
4. **Remediate a Finding**:
   - Click the "AWS EC2 Spike" card to open the remediation pane.
   - Walk through the recommended action and owner mapping.
   - Click "Execute Fix & Reclaim ₹6,20,000". Note how it transitions from the Waste column to the "Savings Unlocked" counter.
5. **AI Chat**:
   - Open the "Ask AI" sidebar.
   - Send: `"Which department is bleeding the most?"`
   - Observe the agent utilizing context to directly call out the Marketing department.
6. **Export**:
   - Click "Export CFO Report (PDF)" on the scorecard to show the generation of the summarized PDF.

---
*Built with ❤️ for the Economic Times Hackathon.*
