# GW2 Companion

## Current Milestone

✅ Milestone 1 - Project Setup
- Git
- Docker
- FastAPI
- VS Code

✅ Milestone 2 - GW2 API
- Account endpoint
- Achievement endpoint
- Achievement lookup

✅ Milestone 3 - Tracker Engine
- Regalia tracker
- JSON-backed requirements
- Progress calculation

---

## Current Architecture

FastAPI
    │
    ▼
Trackers
    │
    ▼
GW2Client
    │
    ▼
ArenaNet API

---

## Next Milestone

- [x] Replace placeholder Regalia data with verified achievement requirements.

---

## Long-term Vision

A self-hosted Guild Wars 2 Companion that recommends the best thing to do next based on the player's account and current goals.

---

## Latest Changes

### Milestone 4

- Replaced placeholder Regalia data with the verified Seasons of the Dragons achievement list.
- Renamed `app/data` to `app/game_data`.
- Fixed `.gitignore` so application data is tracked.