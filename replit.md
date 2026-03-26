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
    store/appStore.ts  - Zustand store for findings, parseResult, itemsScanned
    components/        - Sidebar, FindingsFeed, SavingsCard, AIChat, DemoLoader
    pages/             - Overview, CloudSpend, Procurement, Budgets
backend/
  main.py              - FastAPI routes: /api/parse, /api/detect, /api/analyze, /api/chat
  parser.py            - PDF/CSV extraction (pdfplumber primary, PyMuPDF fallback, regex fallback)
  cleaner.py           - Column repair, normalization, budget reshape (multi-quarter→rows),
                         cloud reshape (service columns→rows), numeric coercion (INR commas)
  analyzer.py          - Full analysis engine: duplicate vendors (by name + PAN/GSTIN),
                         transaction anomalies, budget variance, procurement overpricing,
                         cloud cost spikes (MoM + rolling average)
  requirements.txt     - Python dependencies (includes pymupdf, pdfplumber)
```

## Workflows

- **Start application** - Runs `cd frontend && npm run dev` on port 5000 (webview)
- **Backend API** - Runs `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000` (console, no --reload)

## API Endpoints

- `POST /api/parse` — Upload CSV/PDF, returns normalized + reshaped data classified by type
- `POST /api/detect` — Run anomaly detection on classified data, returns findings[]
- `POST /api/analyze` — Full pipeline: upload → parse → clean → classify → analyze
- `POST /api/chat` — FinBot AI assistant (requires GEMINI_API_KEY)

## Data Pipeline

1. **parser.py** extracts tables from PDF pages using pdfplumber
2. **cleaner.py** `normalize_records_for_frontend()` is called per table:
   - `_repair_split_cols()` — merges pdfplumber-split column headers (e.g. "Unit Price (IN" + "R)Benchmark")
   - `_apply_col_normalization()` — maps any column to standard snake_case (unit_price, benchmark, amount, etc.)
   - `reshape_budget()` — melts multi-quarter rows (Q1 Budget, Q2 Actual…) into {department, quarter, budget, actual}
   - `reshape_cloud()` — melts service columns (EC2, S3, RDS, Lambda, CloudFront) into {month, service, cost}
   - Numeric coercion using `clean_numeric()` handles Indian comma formatting (e.g. "94,000" → 94000.0)
3. **main.py** classifies tables using keyword scoring, maps transaction tables → vendor category
4. **analyzer.py** runs detection on cleaned DataFrames with broad `_find_col()` matching

## Frontend Column Expectations

- **Budgets.tsx**: reads `row.department`, `row.budget`, `row.actual`, `row.quarter`
- **CloudSpend.tsx**: reads `row.month`, `row.service`, `row.cost`
- **Procurement.tsx**: reads `row.unit_price`, `row.benchmark`, `row.qty`, `row.item`, `row.vendor`
- **Overview.tsx**: reads `findings[]` with `{category, severity, title, inrImpact, rootCause, recommendation}`

## Environment Variables

- `GEMINI_API_KEY` — Required for /api/chat FinBot (Google AI Studio). Optional for all other features.

## Analysis Capabilities

- **Duplicate Vendor Detection**: Groups by normalized name + tax ID (PAN/GSTIN)
- **Transaction Anomalies**: Duplicate payments (same vendor + amount appearing 2+ times)
- **Budget Variance**: Flags >10% overspend with CRITICAL/HIGH/MEDIUM severity
- **Procurement Overpricing**: Compares unit prices against benchmarks with 15% tolerance
- **Cloud Cost Analysis**: MoM spikes >30%, 2.5× rolling-average anomalies, idle resource detection
- **False Positive Filtering**: Recurring subscriptions, internal transfers excluded

## Replit-Specific Notes

- Vite dev server on port 5000 with proxy to backend at port 8000
- CORS allows `*.replit.dev` origins via regex
- Frontend uses relative API paths (`/api/...`) — no hardcoded localhost URLs
- Backend runs WITHOUT `--reload` flag (StatReload was causing process crashes in Replit environment)
