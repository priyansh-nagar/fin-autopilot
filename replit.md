# Fin-Autopilot

A financial anomaly detection tool that parses CSV/PDF financial data and detects issues like vendor duplicates, cloud spend spikes, procurement overpricing, and budget variances. Includes an AI-powered FinBot chat assistant powered by Google Gemini.

## Architecture

- **Frontend**: React + Vite + TypeScript + Tailwind CSS, runs on port 5000
- **Backend**: Python FastAPI, runs on port 8000
- Vite proxies all `/api/*` requests from the frontend to the backend (no CORS issues)

## Structure

```
frontend/
  src/
    lib/api.ts         - API client (uses relative /api/* paths via Vite proxy)
    components/        - UI components
    pages/             - Route pages
backend/
  main.py              - FastAPI routes: /api/parse, /api/detect, /api/analyze, /api/chat
  parser.py            - PDF/CSV extraction (pdfplumber primary, PyMuPDF fallback, regex fallback)
  cleaner.py           - Data cleaning, vendor normalization, table type detection
  analyzer.py          - Full analysis engine: duplicate vendors, transaction anomalies,
                         budget variance, procurement overpricing, cloud cost spikes
  requirements.txt     - Python dependencies (includes pymupdf)
```

## Workflows

- **Start application** - Runs `cd frontend && npm run dev` on port 5000 (webview)
- **Backend API** - Runs `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (console)

## API Endpoints

- `POST /api/parse` — Upload CSV/PDF, returns classified row data (legacy/frontend compatible)
- `POST /api/detect` — Run anomaly detection on pre-classified data (legacy compatible)
- `POST /api/analyze` — Full pipeline: upload → parse → clean → classify → analyze → JSON output
- `POST /api/chat` — FinBot AI assistant (requires GEMINI_API_KEY)

## Environment Variables

- `GEMINI_API_KEY` — Required for the /api/chat FinBot endpoint (Google AI Studio)

## Analysis Capabilities

- **Duplicate Vendor Detection**: groups by normalized name + tax ID (PAN/GSTIN)
- **Transaction Anomalies**: duplicate payments, high-value spikes
- **Budget Variance**: flags >10% variance with severity levels
- **Procurement Overpricing**: compares against benchmarks with 15% tolerance
- **Cloud Cost Analysis**: MoM spikes >30%, idle resources (zero usage, positive spend)
- **False Positive Filtering**: recurring subscriptions, internal transfers, seasonal patterns

## Replit-Specific Notes

- Vite dev server on port 5000 with proxy to backend at port 8000
- CORS allows `*.replit.dev` origins via regex
- Frontend uses relative API paths (`/api/...`) — no hardcoded localhost URLs
