# Technical Decisions — Lamer Konekte

| Area | Decision | Why |
|---|---|---|
| Backend framework | FastAPI + Pydantic v2 + SQLModel + SQLite | Brief-sanctioned; SQLModel merges schema+ORM under time pressure |
| Python | 3.12.13, project venv `backend/.venv` | Newest available in [3.11, 3.12] |
| Gemma SDK | official `google-genai` | Brief requirement; native function calling + structured output |
| Hosted model | `gemma-4-26b-a4b-it` | Brief requirement; production reliability |
| Image processing | Pillow + OpenCV headless + NumPy | Blur/brightness/EXIF as specified; ≤4 workers |
| PDF | fpdf2 | Pure-python, lightweight |
| HTTP client | httpx (timeout + bounded retry) | Async-friendly, brief-sanctioned |
| Logging | structlog-style JSON via stdlib `logging` + request IDs, redaction filter | No extra deps, greppable, secrets redacted |
| Frontend | React 18 + TypeScript + Vite + React Router + TanStack Query + Zustand + Lucide | Brief-sanctioned |
| PWA | manifest + hand-rolled service worker (app shell + catalogue + rules snapshot precache), IndexedDB queue | vite-plugin-pwa avoided to keep the build dependency-light and the SW auditable |
| i18n | Minimal typed dictionary loader over `en.json` / `mfe.json` | No i18n framework needed for 2 locales |
| Function dispatch | Explicit dict of name → (PydanticModel, handler) | No eval/exec/globals; allow-list is the map itself |
| Tests | pytest + httpx TestClient; Playwright config for E2E | Brief-sanctioned |
| Deployment | Docker single image (backend serves built frontend) → Render/Cloud Run/HF Spaces | One container = simplest public URL |
| Mock provider | Deterministic, seeded by image hash + note keywords | Fully offline, repeatable demos, never claims real inference |
