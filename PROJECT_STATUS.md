# GW2 Companion

## Project Goal

A self-hosted Guild Wars 2 Companion that uses ArenaNet account data to:

- Track progress toward account goals.
- Analyse legendary requirements.
- Compare requirements against account inventory.
- Identify missing materials and objectives.
- Eventually recommend the most useful thing to work on next.

The goal is not to replace GW2Efficiency, but to provide account-aware guidance such as:

"What should I work on tonight?"

---

## Completed Milestones

### Milestone 1 - Project Setup

- Git repository established.
- Docker development environment.
- FastAPI application.
- VS Code development workflow.
- Python virtual environment.

### Milestone 2 - GW2 API

- ArenaNet API integration.
- Account endpoint.
- Account achievements.
- Achievement lookup.
- Bank access.
- Material storage access.
- Shared inventory access.
- Character inventory access.
- Improved API timeout/retry handling.

### Milestone 3 - Tracker Engine

- JSON-backed tracker data.
- Regalia tracker.
- Achievement completion tracking.
- Partial achievement progress using achievement bits.
- Generic tracker foundation.

### Milestone 4 - Prismatic Champion's Regalia

- Replaced placeholder data with verified requirements.
- Tracks all 24 required achievements.
- Uses live ArenaNet account achievement data.
- Verified live account progress reporting.
- Moved static game data to `app/game_data`.

### Milestone 5 - Account Inventory and Requirement Engine

- Account-wide inventory aggregation.
- Counts items across:
  - Bank
  - Material storage
  - Shared inventory
  - Character inventories
- Recursive recipe requirement analysis.
- Calculates owned, required, and missing quantities.
- Expands crafted components into underlying materials.
- Aggregates duplicate leaf materials within recipe trees.
- Aggregates shared requirements across multiple recipes.
- Produces flat missing-material summaries.

### Milestone 6 - Vision Tracker

- Vision I: Awakening tracking.
- Vision II: Farsight tracking.
- Tracks individual collection progress.
- Tracks final crafting components.
- Mystic Tribute requirement analysis.
- Gift of Prescience requirement analysis.
- Gift of Arid Mastery requirement analysis.
- Combined Vision-wide missing-material summary.
- Combined Vision achievement progress summary.
- Uses live account inventory and achievement data.

---

## Current Architecture

FastAPI
  |
  +-- Trackers
  |     |
  |     +-- RegaliaTracker
  |     +-- VisionTracker
  |
  +-- RequirementAnalyzer
  |     |
  |     +-- Recursive recipe analysis
  |     +-- Missing material aggregation
  |
  +-- AccountInventory
  |     |
  |     +-- Bank
  |     +-- Materials
  |     +-- Shared inventory
  |     +-- Character inventories
  |
  +-- GW2Client
        |
        +-- ArenaNet API

Static game and recipe data:

app/game_data/

---

## Current Working Endpoints

- `/account`
- `/achievement/{achievement_id}`
- `/tracker/regalia`
- `/tracker/vision`
- `/inventory/{item_id}`
- `/requirements/{item_id}`

---

## Current Development Branch

`feature/generic-trackers`

This branch contains the generic requirement engine and Vision tracker work.

---

## Next Milestone - Aurora

Planned next steps:

- Add Aurora achievement/collection tracking.
- Add Aurora crafting requirements.
- Reuse the generic RequirementAnalyzer.
- Produce an Aurora-wide missing-material summary.
- Verify progress against live account data.

---

## Future Work

After Aurora:

- Add additional legendary goals.
- Improve handling of currencies and non-inventory requirements.
- Distinguish acquisition methods such as:
  - Craft
  - Buy
  - Earn
  - Achievement reward
  - Time-gated acquisition
- Add recommendation/prioritisation logic.
- Answer questions such as:
  - "What should I work on tonight?"
  - "What am I closest to completing?"
  - "Which materials are blocking my current goal?"
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Regalia tracking is operational.

Vision tracking is operational with live achievement progress, account inventory analysis, recursive crafting requirements, and a combined shortage summary.

Next target: Aurora.