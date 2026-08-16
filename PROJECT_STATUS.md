# GW2 Companion

## Project Goal

A self-hosted Guild Wars 2 Companion that uses ArenaNet account data to:

- Track progress toward account goals.
- Analyse legendary requirements.
- Compare requirements against account inventory.
- Identify missing materials and objectives.
- Recommend useful next actions based on current progress.
- Build time-aware play-session plans.

The goal is not to replace GW2Efficiency, but to provide account-aware guidance such as:

"What should I work on tonight?"

"What am I closest to completing?"

"What can I make useful progress on in the next 30 or 60 minutes?"

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
- Objective-level tracking for Living World Season 4 Vision collections.
- Count-only tracking for Vision II: Farsight.
- Handles Vision I prerequisite state for Farsight.
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

### Milestone 8 - Recommendation Engine

- Added a shared recommendation service across Vision, Aurora, and Regalia.
- Supports recommendation modes:
  - `progress`
  - `quick`
  - `play`
- Supports goal filtering:
  - Vision
  - Aurora
  - Prismatic Champion's Regalia
- Supports activity filtering.
- Adds estimated minimum and ideal session time.
- Adds effort and value classifications.
- Scores recommendations using:
  - Goal value
  - Current progress
  - Estimated effort
  - Activity type
  - Available session time
- Prevents recommendation lists from being dominated by one goal/activity combination.
- Provides fallback recommendations when strict filters do not produce a direct match.
- Includes acquisition recommendations for relevant materials.
- Uses tracker data rather than maintaining separate account state.

### Milestone 9 - Time-Aware Session Planner

- Added `/session-plan`.
- Builds multi-step plans from ranked recommendations.
- Supports:
  - Session length
  - Goal filtering
  - Activity filtering
- Allocates time to tasks using minimum and ideal time estimates.
- Allows intentionally unused session time when no worthwhile task fits.
- Prefers staying in the current map/location when useful.
- Applies a map-switch penalty.
- Requires enough useful time before switching maps.
- Uses a 75% ideal-time threshold for cross-map tasks.
- Supports modest cross-goal awareness without forcing artificial goal diversity.
- Preserves location grouping and reports all planned locations.

### Milestone 10 - Vision Dependency-Aware Planning

- Added dependency data for Heavy Corsair Boots.
- Tracks `"War Eternal" Mastery` using live account achievement bits.
- Maps all 18 War Eternal meta-achievement bit positions.
- Reports:
  - Current dependency progress
  - Percentage complete
  - Completed dependency objectives
  - Missing dependency objectives
- Preserves the Dragonfall Reward Track as an alternative acquisition route.
- Recommendation scoring can use dependency progress rather than only parent-collection progress.
- Session plans preserve dependency details.
- Added actionable metadata to remaining War Eternal objectives.
- Supports dependency objective bundling by location.
- Groups Dragonfall focus work into:
  - `quick`
  - `active`
  - `opportunistic`
- Keeps story-specific objectives such as Dexterous Dodger outside the Dragonfall bundle.
- Avoids double-counting bundled focus tasks as separate session time.

---

## Current Architecture

FastAPI
  |
  +-- RecommendationService
  |     |
  |     +-- RegaliaTracker
  |     +-- VisionTracker
  |     +-- AuroraTracker
  |     +-- Acquisition metadata
  |     +-- Session profiles
  |
  +-- SessionPlanner
  |     |
  |     +-- Recommendation ranking
  |     +-- Time allocation
  |     +-- Location-aware planning
  |     +-- Dependency focus grouping
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

Static game, acquisition, session-profile, and recipe data:

`app/game_data/`

---

## Current Working Endpoints

- `/`
- `/account`
- `/achievements`
- `/achievement/{achievement_id}`
- `/tracker/regalia`
- `/tracker/vision`
- `/tracker/aurora`
- `/inventory/item/{item_id}`
- `/requirements/{item_id}`
- `/recommendations`
- `/session-plan`

### Recommendation Query Options

`/recommendations`

- `mode=progress|quick|play`
- `goal=vision|aurora|regalia`
- `activity=achievement|open_world|fractals|wvw|vendor|trading_post|acquisition`
- `minutes=5..360`

### Session Planner Query Options

`/session-plan`

- `minutes=5..360`
- `goal=vision|aurora|regalia`
- `activity=achievement|open_world|fractals|wvw|vendor|trading_post|acquisition`

---

## Current Development Branch

`feature/recommendations`

Current branch head:

`340d4c6 - Add dependency-aware Vision session planning`

This branch is ahead of `main` and contains the completed recommendation and session-planning milestone work.

---

## Next Milestone - Merge and Multi-Goal Planning

Immediate next steps:

1. Merge `feature/recommendations` into `main`.
2. Create a fresh feature branch for the next milestone.
3. Apply the proven dependency-aware planning model beyond the current Vision example.
4. Improve Aurora and Regalia recommendation depth so unrestricted plans can compare genuinely actionable tasks across goals.
5. Continue improving cross-goal session planning without forcing artificial goal diversity.

Target questions:

- "What should I work on tonight?"
- "What should I do if I only have 30 minutes?"
- "What can I work on without changing maps?"
- "Which goal has the best useful work for me right now?"
- "What can I combine in one play session?"

---

## Future Work

After multi-goal planning:

- Expand dependency-aware tracking to additional Vision objectives.
- Add deeper Aurora objective-level guidance.
- Add deeper Regalia objective-level guidance.
- Add additional legendary goals.
- Improve handling of currencies and non-inventory requirements.
- Expand acquisition method modelling:
  - Craft
  - Buy
  - Earn
  - Achievement reward
  - PvP/WvW reward track
  - Time-gated acquisition
- Add event/meta awareness where useful.
- Add stronger prerequisite modelling.
- Improve estimated effort and time-gating awareness.
- Add planner support for grouped/meta-event tasks.
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Prismatic Champion's Regalia tracking is operational.

Vision tracking is operational with live achievement progress, objective-level collection data, account inventory analysis, recursive crafting requirements, Vision II tracking, and dependency-aware War Eternal progress.

Aurora tracking is operational with locked-stage detection, live achievement progress, recursive crafting requirements, Living World Season 3 currency tracking, and combined shortage reporting.

The recommendation engine is operational across Vision, Aurora, and Regalia with progress, quick, and play modes.

The session planner is operational with time allocation, map-aware planning, useful unused-time handling, and dependency-aware focus grouping.

The project now has a working end-to-end pipeline:

`game data -> live account state -> trackers -> recommendations -> session plans`

The next project step is to merge the completed recommendation branch into `main`, then continue development from a fresh branch focused on broader multi-goal planning.
