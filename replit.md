# Fin-Autopilot

A financial anomaly detection tool that parses CSV/PDF financial data and detects issues like vendor duplicates, cloud spend spikes, procurement overpricing, and budget variances. Includes an AI-powered FinBot chat assistant powered by Google Gemini.

## Architecture

- **Frontend**: React + Vite + TypeScript + Tailwind CSS, runs on port 5000
- **Backend**: Python FastAPI, runs on port 8000
- Vite proxies all `/api/*` requests from the frontend to the backend (no CORS issues)

## Structure

```
frontend/   - React + Vite frontend (port 5000)
  src/
    lib/api.ts       - API client (uses relative /api/* paths via Vite proxy)
    components/      - UI components
    pages/           - Route pages
backend/    - FastAPI Python backend (port 8000)
  main.py            - All API routes: /api/parse, /api/detect, /api/chat
  requirements.txt   - Python dependencies
```

## Workflows

- **Start application** - Runs `cd frontend && npm run dev` on port 5000 (webview)
- **Backend API** - Runs `cd backend && uvicorn main:app --host 0.0.0.0 --port 8000 --reload` (console)

## Environment Variables

- `GEMINI_API_KEY` - Required for the /api/chat FinBot endpoint (Google AI Studio)

## Replit-Specific Changes

- Vite dev server configured to port 5000 with proxy to backend at port 8000
- CORS updated to allow `*.replit.dev` origins via regex in addition to localhost
- Frontend `VITE_API_URL` set to empty string so all API calls use relative paths through the proxy
