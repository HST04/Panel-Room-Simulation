# Panel Room Simulation

Panel Room Simulation is a two-part application:

- **Backend (`/backend`)**: FastAPI service that runs the electrical simulator, anomaly/optimization agents, and RAG-based diagnostic chat.
- **Frontend (`/frontend`)**: React + Vite dashboard that polls the backend and renders the single-line diagram, telemetry, alerts, and chat UI.

## Repository Structure

- `/backend/main.py` — main API server (`/api/state`, `/api/breaker`, `/api/reset`, `/api/fault`, `/api/tap`, `/api/solar-mode`, `/api/chat`, `/api/optimize`)
- `/backend/simulator.py` — core simulation logic and panel/fault behavior
- `/backend/agents.py` — anomaly, optimization, and diagnostic agents
- `/backend/rag_data.py` — manual ingestion + ChromaDB indexing/search
- `/backend/test_simulation.py` — backend verification tests
- `/backend/visualize_server.py` — optional ChromaDB embedding visualization app
- `/backend/manuals/*.txt` — manuals used by the RAG agent
- `/frontend/src/App.jsx` — main dashboard app
- `/frontend/package.json` — frontend scripts (`dev`, `build`, `preview`)

## Prerequisites

- Python 3.10+
- Node.js 18+

## Backend Setup and Run

From `/home/runner/work/Panel-Room-Simulation/Panel-Room-Simulation/backend`:

```bash
python -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn chromadb python-dotenv google-generativeai numpy umap-learn matplotlib
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Notes:

- The frontend expects the backend at `http://localhost:8000` (hardcoded in `/frontend/src/App.jsx`).
- Diagnostic chat works without Gemini, but to enable LLM responses set `GEMINI_API_KEY` in `/backend/.env`:

```env
GEMINI_API_KEY=your_api_key
```

## Frontend Setup and Run

From `/home/runner/work/Panel-Room-Simulation/Panel-Room-Simulation/frontend`:

```bash
npm install
npm run dev
```

Available scripts (from `/frontend/package.json`):

- `npm run dev` — start Vite dev server
- `npm run build` — production build
- `npm run preview` — preview production build

## Run Backend Verification Test

From `/home/runner/work/Panel-Room-Simulation/Panel-Room-Simulation/backend`:

```bash
python test_simulation.py
```

## Optional: Vector Space Visualization

To inspect indexed manual embeddings:

```bash
cd /home/runner/work/Panel-Room-Simulation/Panel-Room-Simulation/backend
uvicorn visualize_server:app --host 127.0.0.1 --port 8050
```
