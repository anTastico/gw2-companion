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

### Milestone 7 - Aurora Tracker

- Aurora: Awakening tracking.
- Aurora II: Empowering tracking.
- Tracks the six Living World Season 3 mastery collections.
- Detects locked, in-progress, and completed collection stages.
- Tracks final Aurora crafting components.
- Reuses Mystic Tribute requirement analysis.
- Gift of Sentience requirement analysis.
- Gift of Draconic Mastery requirement analysis.
- Tracks Living World Season 3 map currency requirements.
- Produces an Aurora-wide missing-material summary.
- Produces combined Aurora achievement progress.
- Provides tracker-level status.
- Provides an initial next-step structure.
- Uses live account inventory and achievement data.
- Verified against live account data.

---

## Current Architecture

FastAPI
  |
  +-- Trackers
  |     |
  |     +-- RegaliaTracker
  |     +-- VisionTracker
  |     +-- AuroraTracker
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
- `/tracker/aurora`
- `/inventory/{item_id}`
- `/requirements/{item_id}`

---

## Current Development Branch

`feature/aurora`

This branch contains the Aurora tracker, Aurora recipe requirements,
stage status detection, and initial next-step structure.

---

## Next Milestone - Recommendation Engine

Planned next steps:

- Build on tracker-level status and next-step data.
- Identify actionable objectives for tracked goals.
- Distinguish locked goals from active goals.
- Understand prerequisite objectives.
- Compare achievement and material blockers.
- Prioritise useful next actions.
- Begin answering:
  - "What should I work on tonight?"
  - "What am I closest to completing?"
  - "Which materials are blocking my current goal?"

---

## Future Work

After the initial recommendation engine:

- Add additional legendary goals.
- Improve handling of currencies and non-inventory requirements.
- Distinguish acquisition methods such as:
  - Craft
  - Buy
  - Earn
  - Achievement reward
  - Time-gated acquisition
- Add richer recommendation/prioritisation logic.
- Add estimated effort and time-gating awareness.
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Prismatic Champion's Regalia tracking is operational.

Vision tracking is operational with live achievement progress, account
inventory analysis, recursive crafting requirements, and a combined
shortage summary.

Aurora tracking is operational with locked-stage detection, live
achievement progress, recursive crafting requirements, Living World
Season 3 currency tracking, and a combined shortage summary.

The project now has multiple legendary trackers sharing the same
account inventory and recursive requirement-analysis infrastructure.

Next target: recommendation and prioritisation logic.