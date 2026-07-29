# Decision Log — Lamer Konekte

| # | Time (MUT) | Decision | Rationale |
|---|---|---|---|
| 1 | 29 14:26 | Development happens in WSL2 Ubuntu (repo lives there), not Windows-native. | That is where the repo and toolchain actually are. PowerShell resource scripts still provided for the Windows host; bash equivalents added for WSL. |
| 2 | 29 14:26 | Python 3.12.13 via `python3.12` for the backend venv. | Brief requires 3.11/3.12; 3.12 is the newest available. |
| 3 | 29 14:27 | Hosted provider built code-complete but gated on `GEMINI_API_KEY`; app defaults to disclosed mock mode until the key exists. | No key is configured. Faking inference is forbidden; blocking all work on the key is worse. |
| 4 | 29 14:27 | Deadline assumed 2026-07-30 13:36 MUT. | No official deadline recorded; repo creation ≈ start of the 24 h window. Documented as an assumption. |
| 5 | 29 14:27 | Kaggle training prepared but not launched. | No Kaggle credentials on the machine. Launch scripts ready for the moment auth exists. |
| 6 | 29 14:27 | Local edge proof kept at P3 and likely skipped. | WSL sees only 7.4 GB RAM; no HF auth/licence. Edge bonus must never be claimed from mock behaviour, and Morisyen bonus is the safer 10-point path. |
| 7 | 29 14:30 | Five P0 species: Octopus cyanea, Lethrinus nebulosus, Siganus sutor, Epinephelus merra, Naso unicornis. | Locally relevant lagoon/reef species with iNaturalist/GBIF presence; octopus required by the brief pending taxonomic verification. |
| 8 | 29 14:30 | SQLModel over raw SQLAlchemy. | Single class serves as Pydantic schema + table; faster under time pressure; brief allows either. |
| 9 | 29 14:30 | fpdf2 for PDF export. | Pure-python, tiny, no system deps. |
| 10 | 29 14:30 | Zustand for frontend state; TanStack Query for server state. | Brief-sanctioned, minimal boilerplate. |
| 11 | 29 14:30 | Fisheries rules dataset marked `verification: pending_official_confirmation`; engine returns `unknown` for any rule lacking a verified source. | We must not invent laws. Rules carry source URL/title/dates; unverified ⇒ `unknown` + "verify against the latest official fisheries notice." |
