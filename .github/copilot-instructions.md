## Quick orientation — swef_site

This repository is a small Flask-based tournament manager + streaming overlay for osu!.
Key runtime concepts:

- App entrypoints: `run.py` (development) and `passenger_wsgi.py` (Namecheap/WSGI).
- Flask app factory: `app/__init__.py` creates the app and exposes `api` (an Ossapi client).
- Routes are organized as Blueprints under `app/routes/` (public, admin, host, dev, player).
- File-backed persistence: tournament state is stored in JSON files (see `config.py`):
  - `TOURNAMENT_FILE` (default: `tournament.json`) — managed by `app/data_manager.py`.
  - `OVERLAY_STATE_FILE` (`overlay_state.json`) — managed by `app/overlay_state.py` for streaming overlays.

What to know when editing code

- Bracket and match model (typical fields):
  - match: `{'id','bracket','round_index','player1','player2','winner','score_p1','score_p2','mp_room_url','status'}`
  - `status` values: `'next_up'`, `'in_progress'`, `'completed'` (used throughout UI and overlay polling).
  - `match_state` (for pick/ban flow) includes `phase`, `current_turn`, `picked_maps`, `banned_maps`, `abilities_used`.

- When changing bracket logic, update or call `generate_bracket()` and `advance_round_if_ready()` in `app/bracket_logic.py`. Persist via `save_tournament_data()` so the UI and overlay pick up changes.
- `save_tournament_data()` sorts competitors by `pp` and writes `TOURNAMENT_FILE` — keep that behaviour when mutating competitors.

External integrations and auth

- osu! API client: created using `Ossapi` in `app/__init__.py` and used via `from .. import api`. Example callers: `app/routes/*`, `app/services/*`.
- OAuth flows: `public_routes.py` and `admin_routes.py` implement osu! OAuth using `TOKEN_URL`, `AUTHORIZATION_URL` and callback URLs from `config.py`. Tests and dev runs may need env vars (see below).

Overlay / Streaming behavior

- This project supports Namecheap hosting (no SocketIO). Overlays use HTTP polling endpoints:
  - `/api/match-data` — current match for overlay
  - `/api/overlay-events` — events, AFK, victory screens
- Overlay state is file-backed in `overlay_state.json` via `app/overlay_state.py`. Broadcast functions in `app/http_events.py` write this state (search for `broadcast_*` usages in `app/routes/admin_routes.py`).

Developer workflows (concrete)

- Create a Python venv, install deps, run locally (Windows PowerShell examples):
  - python -m venv .venv; .\.venv\Scripts\Activate.ps1
  - pip install -r requirements.txt
  - Create a `.env` with values for: `FLASK_SECRET_KEY`, `OSU_CLIENT_ID`, `OSU_CLIENT_SECRET`, `OSU_CALLBACK_URL`.
  - Run: `python run.py` (dev port is parsed from `OSU_CALLBACK_URL`; fallback 5000).
- Tests: this project uses plain pytest files under `tests/` and `app/tests/`. Run from project root:
  - `.\.venv\Scripts\Activate.ps1` then `pytest -q`

Project-specific conventions and gotchas

- File-based state is canonical. Avoid introducing database layers without migrating `TOURNAMENT_FILE` and `OVERLAY_STATE_FILE` logic.
- Many routes assume `TOURNAMENT_FILE` is in the working directory. Tests/CI run from repo root — keep file paths relative.
- Mappool upload expectations: player mappools are exactly 10 beatmaps. See `app/routes/player_routes.py::upload_mappool()` for parsing/validation.
- Match scoring is Best-of-7 (first to 4). `services.match_service` enforces score ranges (0–4) and sets winners accordingly.

Quick file map (start here):

- `config.py` — env-backed settings used across the app.
- `run.py` / `passenger_wsgi.py` — how the app is started in dev/prod.
- `app/__init__.py` — app factory and `api` client.
- `app/data_manager.py` — read/write of `tournament.json` (sorting behaviour).
- `app/bracket_logic.py` — generate/advance bracket logic (complex, change carefully).
- `app/routes/` — blueprint implementations and permission decorators (`admin_required`, `host_required`, `full_admin_required`).
- `app/services/` — encapsulated logic for matches, seeding, streaming.

If anything is missing or unclear in the short instructions above, tell me which area you want expanded (examples, tests, or a walkthrough to run a dev scenario) and I'll iterate.
