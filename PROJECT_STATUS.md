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

- Account-wide inventory aggregation across bank, material storage, shared inventory, and character inventories.
- Recursive recipe requirement analysis.
- Calculates owned, required, and missing quantities.
- Expands crafted components into underlying materials.
- Aggregates duplicate leaf materials and shared requirements.
- Produces flat missing-material summaries.

### Milestone 6 - Vision Tracker

- Vision I: Awakening and Vision II: Farsight tracking.
- Individual collection and objective-level progress.
- Final crafting-component and recursive requirement tracking.
- Mystic Tribute, Gift of Prescience, and Gift of Arid Mastery analysis.
- Combined Vision-wide achievement and missing-material summaries.
- Uses live account inventory and achievement data.

### Milestone 7 - Aurora Tracker

- Aurora: Awakening and Aurora II: Empowering tracking.
- Tracks the six Living World Season 3 mastery collections.
- Detects locked, in-progress, and completed collection stages.
- Tracks final crafting components and Living World Season 3 map currencies.
- Mystic Tribute, Gift of Sentience, and Gift of Draconic Mastery analysis.
- Combined Aurora achievement and missing-material summaries.
- Verified against live account data.

### Milestone 8 - Recommendation Engine

- Shared recommendation service across Vision, Aurora, and Regalia.
- Supports `progress`, `quick`, and `play` modes.
- Goal and activity filtering.
- Minimum/ideal session-time estimates, effort, and value classifications.
- Scoring based on goal value, progress, effort, activity type, and available time.
- Prevents one goal/activity combination from dominating results.
- Provides fallback and acquisition recommendations.

### Milestone 9 - Time-Aware Session Planner

- Added `/session-plan`.
- Builds multi-step plans from ranked recommendations.
- Supports session length, goal, and activity filtering.
- Allocates time using minimum and ideal estimates.
- Allows intentionally unused time when no worthwhile task fits.
- Location-aware planning with map-switch penalties and useful-time thresholds.
- Supports cross-goal planning without forcing artificial diversity.

### Milestone 10 - Vision Dependency-Aware Planning

- Added dependency data for Heavy Corsair Boots.
- Tracks `"War Eternal" Mastery` using live achievement bits.
- Maps all 18 meta-achievement bit positions.
- Reports dependency progress and missing objectives.
- Preserves Dragonfall Reward Track as an alternative acquisition route.
- Adds actionable objective metadata and Dragonfall focus bundling.
- Avoids double-counting bundled tasks as separate session time.

### Milestone 11 - Multi-Goal Dependency-Aware Planning

- Added actionable Aurora Sentient Seed unlock prerequisites:
  - Conspiracy of Dunces
  - Token Collector
  - Cin Business
  - Lessons Learned
- Added `unlock_requirement` scoring for hard prerequisites.
- Added dependency-aware Regalia handling for End Conjecture.
- Models the verified chain:
  - Return to Research
  - Studying Scarlet
  - Peer Review
  - Parallel Analysis
  - End Conjecture
- Regalia resolves the first incomplete actionable prerequisite rather than a locked downstream achievement.
- Verified unrestricted ranking across Vision, Aurora, and Regalia.
- Verified focused 60/90-minute plans and natural multi-goal behaviour in a 120-minute plan.
- Confirmed design rule: multi-goal planning enables cross-goal progress when worthwhile; it does not require every session to contain multiple goals.

### Milestone 12 - Shared Account State and API Optimisation

- Added request-scoped `AccountState`.
- Recommendation/session-planning requests fetch account data once and share the snapshot across Regalia, Vision, and Aurora.
- Shared state contains account achievements, achievement lookup by ID, and aggregated account-wide item counts.
- The five ArenaNet account requests are issued concurrently with `asyncio.gather`:
  - `/account/achievements`
  - `/account/bank`
  - `/account/materials`
  - `/account/inventory`
  - `/characters?page=0&page_size=200`
- Added shared `httpx.AsyncClient` injection to `GW2Client` so the snapshot reuses one HTTP client across all five requests.
- Preserved standalone tracker behaviour when no shared snapshot is supplied.
- Temporary instrumentation verified that one `/session-plan` request performs exactly the intended five account calls with no hidden duplicate account requests.
- `/characters` was the slowest observed endpoint during instrumentation.
- Five-run `/session-plan?minutes=60` benchmark before shared HTTP-client reuse averaged approximately 8.13 seconds, with a 4.13-12.40 second sample range.
- Five-run benchmark after shared HTTP-client reuse averaged approximately 4.87 seconds, with a 3.87-6.74 second sample range.
- The measured sample therefore showed roughly a 40% lower average request time and substantially reduced latency variance.
- Temporary timing/debug instrumentation was removed before commit.
- Established a short architecture/efficiency review at major milestone boundaries, checking for duplicate API calls, duplicate logic/data, unnecessary sequential work, growing coupling, performance bottlenecks, and error-handling weaknesses.

### Milestone 13 - Aurora Objective Depth and Full-Pool Session Planning

- Added reusable `achievement_bits` objective tracking for Aurora unlock requirements.
- Objective definitions are data-driven in `app/game_data/aurora.json`; the tracker resolves completed bits, missing objectives, progress percentages, and grouped missing objectives generically.
- Expanded Token Collector into all 40 bit-mapped objectives and verified live state at 10/40 with 30 missing.
- Added area-based Token Collector bundles so useful work is grouped within Ember Bay rather than emitted as dozens of individual tasks.
- Expanded Cin Business into all 18 bit-mapped objectives and verified live state at 14/18 with four remaining objectives: Doric Lumber Yard, Saidra's Haven, Fort Evennia, and Mantle's Breach.
- Expanded Lessons Learned into all 14 recording objectives with Draconis Mons area grouping and concise navigation guidance.
- Verified that an objective-tracked achievement with no `/account/achievements` entry is handled as zero progress; Lessons Learned resolved correctly at 0/14.
- Generalised objective-bundle wording so recommendation logic is not Token Collector-specific.
- Added `objective_bundle` scoring as high-value, medium-effort prerequisite work.
- Preserved normal recommendation diversity limits while allowing `SessionPlanner` to request the full eligible ranked candidate pool.
- Fixed the planner/recommendation boundary where `play`-mode diversity trimming could otherwise starve session planning of valid candidates.
- Verified a 60-minute Aurora plan using the full candidate pool: 40 minutes of remaining Cin Business work in Lake Doric followed by 20 minutes of Token Collector work at Caliph's Steps in Ember Bay.
- Architecture review passed. Objective timing refinement and a cleaner internal ranked-candidate API remain non-blocking future improvements.


---

## Current Architecture

FastAPI
  |
  +-- RecommendationService
  |     |
  |     +-- AccountState
  |     |     |
  |     |     +-- Achievements
  |     |     +-- Bank
  |     |     +-- Materials
  |     |     +-- Shared inventory
  |     |     +-- Character inventories
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
  +-- RequirementAnalyzer
  |     |
  |     +-- Recursive recipe analysis
  |     +-- Missing material aggregation
  |
  +-- GW2Client
        |
        +-- ArenaNet API

Static game, acquisition, session-profile, and recipe data live in `app/game_data/`.

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

`feature/dependency-depth`

This branch contains the completed Aurora objective-depth and full-candidate-pool session-planning work built on top of the shared account-state milestone.

Current branch commits:

- `0351475` - Add objective-aware Aurora unlock tracking
- `e9976a0` - Expand Aurora objective-aware unlock guidance
- `4071586` - Give session planner full recommendation candidate pool

The branch is three commits ahead of `main`, zero commits behind, and has passed the milestone architecture review.

---

## Current Multi-Goal Planning Behaviour

The planner has been verified against live account state.

Shorter sessions can remain focused on one goal when that is the best use of time. Longer sessions can naturally cross goals when enough useful time exists to justify changing location.

Verified examples include a Vision-focused 60-minute plan, a Vision-focused 90-minute plan, and a 120-minute plan combining Vision work in Dragonfall with Aurora Token Collector work in Ember Bay.

Design rule:

`multi-goal planning != mandatory goal diversity`

The planner optimises useful progress, time fit, and travel/location efficiency first.

---

## Known Limitations / Technical Debt

### Regalia external prerequisites

The End Conjecture chain is modelled, but some chain steps rely on external Return/meta-achievement prerequisites. The current resolver does not yet recursively combine those external Return achievements into one dependency graph.

### ArenaNet API latency

Duplicate account fetching has been resolved by `AccountState`. Remaining request latency is primarily influenced by the slowest ArenaNet endpoint in the concurrent snapshot. During instrumentation, `/characters?page=0&page_size=200` was the slowest observed account request.

Possible future improvements include carefully scoped short-lived caching, determining whether every recommendation mode requires character inventory, and graceful partial-state handling when a non-critical ArenaNet endpoint fails.

### Objective-bundle timing

Aurora objective-bundle minimum/ideal durations are currently derived from the number of missing objectives in a group rather than summed from each objective's own configured timing metadata.

This is adequate for current planning, but future refinement could use richer per-objective timing and event/time-gate awareness.

### Recommendation candidate API boundary

`RecommendationService.get_recommendations()` currently supports an internal `full_candidate_pool` option used by `SessionPlanner`.

This is intentionally small and working, but a future refactor could expose ranked eligible candidates through a dedicated internal method so presentation-oriented recommendation selection and planner candidate generation are more explicitly separated.

### Remaining objective depth

Aurora Sentient Seed prerequisite depth is now substantially improved. Deeper objective guidance can still be added for the six Aurora I Living World Season 3 mastery collections.

Vision remains another major source of rich objective-level data. Additional Vision dependencies can be expanded where they materially improve recommendations.

---

## Development Practice - Milestone Architecture Review

At the end of each major milestone, perform a short architecture/efficiency review before merging. The review should look specifically for:

- Duplicate API/database/network calls.
- Duplicate logic or static data.
- Unnecessary sequential work that can safely run concurrently.
- Services becoming too tightly coupled.
- New performance bottlenecks.
- Fragile or repeated error-handling paths.
- Opportunities to simplify before adding the next major feature.
- Presentation-layer limits accidentally constraining internal planning logic.

Optimisations should be measured where practical rather than retained solely because they appear architecturally cleaner.

---

## Next Milestone

Aurora Sentient Seed objective-depth work and full-candidate-pool session planning are complete and verified.

The next development step should focus on the highest-value remaining dependency/objective depth rather than expanding Regalia work that may soon become irrelevant to the tracked account.

Recommended priorities:

- Expand objective-level guidance for the six Aurora I Living World Season 3 mastery collections.
- Continue expanding Vision dependencies where richer objective data would improve planning.
- Improve objective-bundle time estimates where useful.
- Add event/meta/time-gate awareness when it materially changes the best session plan.
- Revisit Regalia dependency depth only if it remains useful after current account progress changes.
- Consider extracting ranked eligible candidate generation into a dedicated internal recommendation-service method when further planner work makes that separation worthwhile.

At the end of the next milestone, perform another architecture/efficiency review before merging.

---

## Future Work

- Expand dependency-aware tracking to additional Vision objectives.
- Expand Aurora I mastery-collection objective guidance.
- Add deeper Regalia objective-level guidance when useful.
- Add additional legendary goals.
- Improve handling of currencies and non-inventory requirements.
- Expand acquisition-method modelling: craft, buy, earn, achievement rewards, PvP/WvW reward tracks, and time-gated acquisition.
- Add event/meta awareness where useful.
- Improve estimated effort and time-gating awareness.
- Add planner support for grouped/meta-event tasks.
- Consider carefully scoped caching only if further latency reduction becomes worthwhile.
- Refactor planner candidate generation away from the public recommendation response shape if the planner grows substantially.
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Prismatic Champion's Regalia tracking is operational with live account progress and dependency-aware handling for End Conjecture.

Vision tracking is operational with live achievement progress, objective-level collection data, account inventory analysis, recursive crafting requirements, Vision II tracking, and dependency-aware War Eternal progress.

Aurora tracking is operational with locked-stage detection, live achievement progress, recursive crafting requirements, Living World Season 3 currency tracking, combined shortage reporting, Sentient Seed prerequisite tracking, and reusable achievement-bit objective depth for Token Collector, Cin Business, and Lessons Learned.

The recommendation engine is operational across Vision, Aurora, and Regalia with progress, quick, and play modes. Normal recommendation responses remain concise and diversity-aware while objective bundles provide actionable grouped work.

The session planner is operational with time allocation, map-aware planning, useful unused-time handling, cross-goal awareness, dependency-aware focus grouping, and access to the full eligible ranked candidate pool before presentation-oriented diversity trimming.

The project now has a working end-to-end pipeline:

`game data -> shared live account state -> trackers -> ranked candidates -> recommendations/session plans`

Recommendation and session-planning requests share one request-scoped account snapshot across all three trackers, eliminating duplicate account fetching while preserving fresh data and standalone tracker behaviour.

Milestone-end architecture/efficiency reviews are part of the development workflow and have now caught both duplicate API fetching and presentation-layer candidate trimming before those issues became embedded deeper in the project.
