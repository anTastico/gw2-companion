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

### Milestone 11 - Multi-Goal Dependency-Aware Planning

- Added actionable Aurora unlock-prerequisite tracking for `Aurora: Awakening`.
- Models the Sentient Seed unlock chain using:
  - Conspiracy of Dunces
  - Token Collector
  - Cin Business
  - Lessons Learned
- Detects completed sentient-item requirements using achievement completion and inventory ownership.
- Reports Aurora unlock progress and missing prerequisites.
- Adds Aurora unlock requirements as real recommendation candidates with:
  - Location
  - Minimum and ideal time
  - Action text
  - Unlock context
- Added `unlock_requirement` scoring support so hard prerequisites are treated as high-value work.
- Added dependency-aware Regalia handling for End Conjecture.
- Models the verified End Conjecture chain:
  - Return to Research
  - Studying Scarlet
  - Peer Review
  - Parallel Analysis
  - End Conjecture
- Regalia now resolves the first incomplete actionable prerequisite instead of recommending a locked downstream achievement.
- Adds accurate Eye of the North location and short 5-10 minute estimates for the Taimi/Gorrik chain.
- Verified that unrestricted recommendation ranking compares Vision, Aurora, and Regalia using real actionable candidates.
- Verified that planner behaviour remains focused when that is best:
  - 60-minute plans can stay entirely on Vision.
  - 90-minute plans can still remain Vision-focused when the alternatives are less efficient.
- Verified genuine multi-goal planning:
  - A 120-minute unrestricted session naturally selected Vision work in Dragonfall followed by Aurora work in Ember Bay.
- Confirmed design principle:
  - Multi-goal planning should enable cross-goal progress when worthwhile.
  - It should not force every session to include multiple goals.
- Confirmed that better underlying game data is preferable to compensating with scoring tweaks.

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
  |     +-- Cross-goal awareness
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

`feature/multi-goal-planning`

This branch contains the completed multi-goal planning work built on top of the merged recommendation/session-planning milestone.

Current verified behaviour includes:

- Vision dependency-aware planning.
- Aurora unlock-prerequisite recommendations.
- Regalia dependency-chain resolution.
- Cross-goal recommendation ranking.
- Location-aware multi-goal session planning.

---

## Current Multi-Goal Planning Behaviour

The current planner has been verified against live account state.

### Short and medium sessions

Shorter sessions can remain focused on a single goal when that produces the best use of time.

Example behaviour:

- 60-minute unrestricted session:
  - Vision-focused Dragonfall plan.
- 90-minute unrestricted session:
  - Vision-focused plan can still win even when Aurora and Regalia are available.

This is intentional.

### Longer sessions

Longer sessions can naturally cross goals when there is enough useful time to justify changing location.

Verified example:

- 120-minute unrestricted session:
  - Vision work in Dragonfall.
  - Aurora `Token Collector` work in Ember Bay.
  - Small amount of unused time left rather than filling the plan with a weak task.

Design rule:

`multi-goal planning != mandatory goal diversity`

The planner should optimise useful progress, time fit, and travel/location efficiency first, while still recognising when a second goal becomes worthwhile.

---

## Known Limitations / Technical Debt

### Regalia external prerequisites

The End Conjecture dependency chain is modelled, but some chain steps themselves rely on external Return/meta-achievement prerequisites.

Examples:

- Peer Review depends on Return to Siren's Landing.
- Parallel Analysis depends on Return to Dragonfall.
- End Conjecture depends on Return to the Dragonstorm.

The current resolver tracks the Taimi/Gorrik chain itself, but does not yet recursively combine those external Return-achievement prerequisites into one dependency graph.

### Duplicate account/API work

Recommendation and session-plan requests currently cause multiple trackers to fetch overlapping account data independently.

This can result in repeated calls for:

- Account achievements.
- Characters.
- Bank.
- Material storage.
- Shared inventory.

A GW2 API `ReadTimeout` has already been observed during `/session-plan` while fetching characters.

Future improvement:

- Fetch account state once per recommendation/session request.
- Share that state across trackers and services.
- Reduce ArenaNet API call volume and timeout risk.

### Incomplete objective depth

Vision currently has the richest objective-level data.

Aurora and Regalia now have meaningful prerequisite-aware recommendations, but deeper objective-level guidance can still be added for:

- Aurora Living World Season 3 mastery collections.
- Remaining Regalia Return achievements.
- Additional Vision collections and dependencies.

---

## Next Milestone

The multi-goal planning architecture is now proven.

The next development step should focus on one of two areas:

1. **Shared account-state / API optimisation**
   - Reduce duplicate ArenaNet calls.
   - Improve response speed.
   - Reduce timeout risk.

2. **Broader dependency/objective modelling**
   - Expand Aurora objective-level guidance.
   - Expand Regalia dependency depth.
   - Model external Return-achievement prerequisites.
   - Reuse the same dependency structures across additional tracked goals.

Before starting the next milestone, this branch should be reviewed and merged into `main` once the current status update is committed.

---

## Future Work

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
- Share account state across trackers to reduce duplicate API calls.
- Add caching where appropriate.
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Prismatic Champion's Regalia tracking is operational with live account progress and dependency-aware handling for End Conjecture.

Vision tracking is operational with live achievement progress, objective-level collection data, account inventory analysis, recursive crafting requirements, Vision II tracking, and dependency-aware War Eternal progress.

Aurora tracking is operational with locked-stage detection, live achievement progress, recursive crafting requirements, Living World Season 3 currency tracking, combined shortage reporting, and Sentient Seed prerequisite tracking.

The recommendation engine is operational across Vision, Aurora, and Regalia with progress, quick, and play modes.

The session planner is operational with time allocation, map-aware planning, useful unused-time handling, cross-goal awareness, and dependency-aware focus grouping.

The project now has a working end-to-end pipeline:

`game data -> live account state -> trackers -> recommendations -> session plans`

The current branch proves that multiple goals can now compete fairly in the same planner without forcing artificial diversity.
