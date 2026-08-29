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
- Prevents one goal/activity combination from dominating normal recommendation results.
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
- Models the verified chain: Return to Research -> Studying Scarlet -> Peer Review -> Parallel Analysis -> End Conjecture.
- Regalia resolves the first incomplete actionable prerequisite rather than a locked downstream achievement.
- Verified unrestricted ranking across Vision, Aurora, and Regalia.
- Verified focused 60/90-minute plans and natural multi-goal behaviour in a 120-minute plan.
- Confirmed design rule: multi-goal planning enables cross-goal progress when worthwhile; it does not require every session to contain multiple goals.

### Milestone 12 - Shared Account State and API Optimisation

- Added request-scoped `AccountState`.
- Recommendation/session-planning requests fetch account data once and share the snapshot across Regalia, Vision, and Aurora.
- Shared state contains account achievements, achievement lookup by ID, and aggregated account-wide item counts.
- The five ArenaNet account requests are issued concurrently with `asyncio.gather`.
- Added shared `httpx.AsyncClient` injection to `GW2Client` so the snapshot reuses one HTTP client across all five requests.
- Preserved standalone tracker behaviour when no shared snapshot is supplied.
- Temporary instrumentation verified that one `/session-plan` request performs exactly the intended five account calls with no hidden duplicate account requests.
- Five-run `/session-plan?minutes=60` benchmark improved from approximately 8.13 seconds average to 4.87 seconds average after shared HTTP-client reuse.
- Established milestone-end architecture/efficiency reviews.

### Milestone 13 - Aurora Objective Depth and Full-Pool Session Planning

- Added reusable `achievement_bits` objective tracking for Aurora unlock requirements.
- Expanded Token Collector into all 40 bit-mapped objectives.
- Expanded Cin Business into all 18 bit-mapped objectives.
- Expanded Lessons Learned into all 14 recording objectives with Draconis Mons grouping and concise navigation guidance.
- Added area-based objective bundles so large collections do not flood recommendations with tiny tasks.
- Generalised objective-bundle wording so recommendation logic is not Token Collector-specific.
- Added `objective_bundle` scoring as high-value prerequisite work.
- Preserved normal recommendation diversity limits while allowing `SessionPlanner` to request the full eligible ranked candidate pool.
- Fixed the planner/recommendation boundary where presentation-oriented diversity trimming could otherwise starve session planning of valid candidates.
- Verified a 60-minute Aurora plan: 40 minutes of Cin Business in Lake Doric followed by 20 minutes of Token Collector in Ember Bay.
- Architecture review passed.

### Milestone 14 - Aurora I Mastery Objective Guidance

- Expanded all six Aurora I Living World Season 3 mastery collections to objective-level tracking.
- Added 87 bit-mapped objectives across:
  - Bloodstone Fen Master - 12 objectives
  - Ember Bay Master - 15 objectives
  - Bitterfrost Frontier Master - 14 objectives
  - Lake Doric Master - 16 objectives
  - Draconis Mons Master - 14 objectives
  - Siren's Landing Master - 16 objectives
- Reused the generic `achievement_bits` resolver for both unlock requirements and collection objectives, removing duplicated bit-resolution logic.
- Added explicit collection `unlocked` and `actionable` state.
- Locked collections expose objective state for tracking but remain non-actionable and do not leak into recommendations.
- Added planner-oriented objective classifications including gathering, combat/bosses, events/map tasks, exploration/chests, jumping puzzles/traversal, vendor/purchase, collection prerequisites, episode mastery rewards, and long-term collections.
- Added event-dependent and time-gated metadata where useful.
- Identified `A Henge Away from Home` as long-term/time-gated Draconis Mons work.
- Classified Searing Ascent as jumping-puzzle/traversal work rather than a generic collection objective.
- Unlocked collections can generate grouped `objective_bundle` recommendations by focus category.
- Bundle timing now sums per-objective minimum and ideal timing metadata rather than using objective count alone.
- Verified all 87 objectives received meaningful classifications with no generic fallback rows remaining.
- Verified live locked-state behaviour: all six collections currently show 0 progress, `unlocked=false`, `actionable=false`, and none appear in Aurora recommendations.
- Unlocked-state recommendation behaviour is implemented but remains pending natural live validation after Sentient Seed is acquired.

### Milestone 15 - Vision Dependency Depth and Field-Tested Session Planning

- Deepened Living World Season 4 Vision planning one sub-collection at a time rather than treating collection objectives as flat tasks.
- Expanded dependency-aware planning across Istan, Sandswept Isles, Kourna, Jahai Bluffs, and Dragonfall / War Eternal.
- Added focused collection filtering to both `/recommendations` and `/session-plan`.
- Added reusable dependency shapes and planner handling for `achievement_bits`, `achievement_options`, `achievement_set`, crafting dependencies, shared consumables, nested/sequential prerequisites, shared materials, shared achievements, completed-prerequisite `next_step` actions, projected completion effects, related objectives, and multi-prerequisite completion.
- Added account-aware prerequisite and availability handling so locked or unavailable achievement options are not treated as immediately actionable.
- Added playability metadata/scoring for direct work, events, event chains, metas, world bosses, multi-map work, story, crafting, bounties, repeat requirements, group recommendations, and schedule dependence.
- Added work-horizon handling so large material deficits are treated as background progression instead of consuming unrealistic portions of short play sessions.
- Corrected parent/child recommendation behaviour so actionable child dependencies replace misleading standalone parent tasks.
- Preserved achievement-option context during shared-achievement consolidation so shared objectives retain both shared-dependency value and original prerequisite value.
- Added multi-map handling that avoids false single-map bonuses and improves map-switch decisions.
- Field-tested recommendation and session-plan behaviour repeatedly against live account progress rather than tuning from static data alone.

#### Istan

- Fully resolved Heavy Corsair Turban through the Daybreak Mastery prerequisite instead of treating the turban as a short standalone task.
- Kept Brandstone Research / Astral Weapons time-gated work prominent where appropriate.
- Verified Istan recommendations against live progress and avoided overvaluing long prerequisite chains in short sessions.

#### Sandswept Isles

- Added deeper shared dependency handling for Lasting Bonds and related Vision requirements.
- Modelled shared consumable acquisition for the relevant Vision of Enemies objective.
- Added account-aware completion effects for linked achievement progression.
- Verified focused Sandswept planning against live account state.

#### Domain of Kourna

- Deepened shared dependency planning across Heavy Corsair Jerkin, Banner of the Commander, mastery-related work, Vision of Enemies: Troopmarshal Olori Ogun, and other collection objectives.
- Added realistic bounty, event, story, meta, repeat, group, and material-work-horizon behaviour.
- Prevented very large Inscribed Shard requirements from incorrectly dominating short sessions while preserving them as useful background progression.
- Added projected prerequisite/completion handling and shared achievement value.
- Repeatedly field-tested 120-minute Kourna plans while the tracked account was actively progressing the collection.
- Froze Kourna tuning once the planner produced stable, believable plans.

#### Jahai Bluffs

- Added shared-consumable planning for the Death-Branded Shatterer objective.
- Added completed-prerequisite guidance for `"A Star to Guide Us" Mastery` and Elegy Armor.
- Correctly transitioned completed prerequisites into the appropriate vendor-purchase next step.
- Verified against live account purchases and collection progress.

#### Dragonfall / War Eternal

- Replaced the old War Eternal bit-position approximation with curated `achievement_options` for the 18 achievements that actually count toward `"War Eternal" Mastery`.
- Correctly identified the six remaining qualifying achievements from live account state.
- Preserved the Dragonfall Reward Track as an alternative route for Heavy Corsair Boots.
- Added realistic playability metadata to remaining War Eternal achievement options.
- Modelled Tier 1 Mist Shard Armor as an `achievement_set` dependency for Vision of Equipment: Dragon Champion Armor.
- Correctly recognised Championship Bout and My Beautiful Infrastructure as shared achievements advancing both Heavy Corsair Boots and Dragon Champion Armor.
- Suppressed the fake standalone Dragon Champion Armor task while its child armor achievements remain incomplete.
- Preserved the final 5-gold Traveling Elonian Trader purchase as the next step once one Tier 1 Mist Shard armor weight class is complete.
- Corrected Vision of Enemies: Ley-Infused Enemy to post-meta/group-dependent work.
- Verified Vision of Landscapes: Dragonfall as a clean direct objective.
- Field-tested 120- and 240-minute focused Dragonfall plans against live account progress.
- Froze Dragonfall tuning after the planner produced sensible shared-dependency and post-meta behaviour.

#### Vision checkpoint

- Current Vision dependency/planner work is considered complete enough to freeze pending further gameplay validation.
- Thunderhead Peaks / All or Nothing has intentionally not received the same dependency-depth pass because the tracked account may complete that requirement through PvP reward-track progress.
- Future Vision changes should be evidence-driven rather than proactive score tuning.

---

## Current Architecture

FastAPI
  |
  +-- RecommendationService
  |     |
  |     +-- AccountState
  |     |     +-- Achievements
  |     |     +-- Bank
  |     |     +-- Materials
  |     |     +-- Shared inventory
  |     |     +-- Character inventories
  |     |
  |     +-- RegaliaTracker
  |     +-- VisionTracker
  |     |     +-- Nested dependency resolution
  |     |     +-- Achievement bits/options/sets
  |     |     +-- Shared consumables/materials/achievements
  |     |     +-- Prerequisite and next-step state
  |     |     +-- Projected completion effects
  |     +-- AuroraTracker
  |     |     +-- Generic achievement-bit objective resolution
  |     |     +-- Collection unlock/actionable state
  |     |     +-- Grouped missing-objective progress
  |     |
  |     +-- Acquisition metadata
  |     +-- Session profiles
  |     +-- Ranked eligible candidate pool
  |     +-- Collection-focused filtering
  |     +-- Playability/work-horizon scoring
  |     +-- Shared dependency/material recognition
  |     +-- Concise/diverse recommendation selection
  |
  +-- SessionPlanner
  |     +-- Full eligible candidate pool
  |     +-- Time allocation
  |     +-- Location-aware planning
  |     +-- Cross-goal awareness
  |     +-- Collection-focused planning
  |     +-- Dependency/objective focus grouping
  |     +-- Projected completion and blocker handling
  |     +-- Multi-map and shared-dependency awareness
  |
  +-- RequirementAnalyzer
  |     +-- Recursive recipe analysis
  |     +-- Missing material aggregation
  |
  +-- GW2Client
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
- `collection=<exact collection name>` for supported focused collection planning
- `activity=achievement|open_world|fractals|wvw|vendor|trading_post|acquisition`
- `minutes=5..360`

Normal recommendation responses remain concise and diversity-limited.

### Session Planner Query Options

`/session-plan`

- `minutes=5..360`
- `goal=vision|aurora|regalia`
- `collection=<exact collection name>` for supported focused collection planning
- `activity=achievement|open_world|fractals|wvw|vendor|trading_post|acquisition`

The planner requests the full eligible ranked candidate pool before recommendation diversity trimming and can preserve focused collection context throughout planning.

---

## Current Development State

Current branch: `feature/vision-dependency-depth`

Latest verified Vision checkpoint:

- `028ba5e` - Deepen Dragonfall Vision dependency planning
- `2e08dd6` - Refine Vision session planning from field testing
- `f0b7364` - Add Jahai completed prerequisite guidance
- `e2b7b9b` - Add Jahai shared consumable planning
- `fe05eaf` - Add projected Kourna achievement dependencies
- `7117236` - Add Kourna mastery dependency guidance

The branch is clean and pushed through `028ba5e`.

Vision dependency/planner development is now frozen pending further gameplay validation. Kourna and Dragonfall were deliberately stopped once live field tests produced sensible plans; future changes should respond to observed gameplay problems instead of continued score tuning.

Thunderhead Peaks / All or Nothing remains the least-developed Vision map dependency set and may be completed through PvP rather than receiving another full dependency-depth pass.

Prismatic Champion's Regalia is complete for the tracked account. Regalia support remains operational, but additional Regalia dependency-depth work is maintenance/low priority unless a future goal requires it.

---

## Current Aurora State

Sentient Seed is currently 1/4 complete:

- Conspiracy of Dunces - complete
- Token Collector - 10/40
- Cin Business - 14/18
- Lessons Learned - 0/14

The six Aurora I mastery collections remain locked until Sentient Seed is acquired. Their 87 objective definitions are already present and will become actionable automatically once the stage unlocks.

Design rules:

`objective depth != one recommendation per objective`

`locked tracking data != actionable recommendation`

`recommendation diversity != planner candidate diversity`

---

## Known Limitations / Technical Debt

### Aurora I unlocked-state validation

The mastery-objective implementation has been fully validated while the collections are locked. The grouped recommendation path for unlocked collections is implemented but has not yet been exercised against natural live account progress because Sentient Seed has not yet been acquired.

### Objective-bundle timing

Aurora mastery bundles now sum per-objective timing metadata. This is more accurate than count-based timing, but it may still overestimate work when several objectives naturally overlap in the same event chain or route. Future refinement can account for overlap, event schedules, and time gates.

### Recommendation candidate API boundary

`RecommendationService.get_recommendations()` still supports an internal `full_candidate_pool` option used by `SessionPlanner`. A future refactor could expose ranked eligible candidates through a dedicated internal method so presentation-oriented selection and planner candidate generation are more explicitly separated.

### ArenaNet API latency

Duplicate account fetching has been resolved by `AccountState`. Remaining latency is primarily influenced by the slowest ArenaNet endpoint in the concurrent snapshot, historically `/characters?page=0&page_size=200` in local instrumentation.

Possible future improvements include carefully scoped short-lived caching, determining whether every recommendation mode requires character inventory, and graceful partial-state handling when a non-critical ArenaNet endpoint fails.

### Remaining objective depth

Vision now has strong dependency depth across the actively developed Living World Season 4 collections and is intentionally frozen pending gameplay validation.

Aurora already has substantial objective-level coverage from the earlier Sentient Seed and Aurora I mastery work. The next development pass should resume Aurora by comparing the existing implementation against the richer generic dependency and planner capabilities learned during Vision, then fill only genuine gaps.

---

## Development Practice - Milestone Architecture Review

At the end of each major milestone, perform a short architecture/efficiency review before merging. Review specifically for:

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

Resume Aurora development from the substantial existing implementation rather than starting over.

Before changing Aurora code:

- Review the previous Aurora development history and current `aurora.json` / `AuroraTracker` implementation.
- Capture a fresh live `/tracker/aurora` baseline.
- Compare Aurora's existing dependency model with the generic capabilities added and field-tested during the Vision milestone.
- Produce an explicit gap analysis: already complete, still valid, superseded by newer generic architecture, and genuinely missing.
- Prioritise real blockers, shared requirements, nested prerequisites, event/meta/time-gate behaviour, vendor transitions, long-term material work, and planner actionability.
- Preserve the established rule that objective depth should improve actionable planning without turning every objective into a separate recommendation.
- Reuse generic dependency/planner machinery wherever possible instead of introducing Aurora-specific scoring hacks.

Vision is frozen pending gameplay validation. Thunderhead Peaks / All or Nothing may be completed through PvP and does not need to block the Aurora return.

Regalia development remains low priority because the tracked account has completed Prismatic Champion's Regalia.

At the end of the next major milestone, perform another architecture/efficiency review before merging.

---

## Future Work

- Resume and finish Aurora dependency-aware planning using the generic capabilities learned during Vision.
- Validate and refine unlocked Aurora I mastery recommendations once naturally available.
- Revisit Vision only when gameplay exposes a genuine planning gap; complete Thunderhead dependency depth only if still useful after PvP progress.
- Add additional legendary goals.
- Improve handling of currencies and non-inventory requirements.
- Continue expanding acquisition-method modelling: craft, buy, earn, achievement rewards, PvP/WvW reward tracks, vendor transitions, and time-gated acquisition.
- Refine objective/bundle timing where overlapping event or route work makes summed timing too conservative.
- Consider carefully scoped caching only if further latency reduction becomes worthwhile.
- Refactor planner candidate generation away from the public recommendation response shape if the planner grows substantially.
- Build a user-friendly frontend/dashboard.
- Prepare for self-hosted deployment.

---

## Current State

Prismatic Champion's Regalia is complete for the tracked account; its tracker remains operational.

Vision tracking is operational with live achievement progress, objective-level collection data, account inventory analysis, recursive crafting requirements, Vision II tracking, collection-focused recommendations/session plans, and deep dependency-aware planning across Istan, Sandswept Isles, Kourna, Jahai Bluffs, and Dragonfall / War Eternal. The current Vision planner state has been field-tested against live account progress and is frozen pending further gameplay evidence.

Aurora tracking is operational with locked-stage detection, live achievement progress, recursive crafting requirements, Living World Season 3 currency tracking, Sentient Seed prerequisite depth, and reusable achievement-bit objective guidance across all six Aurora I mastery collections. Aurora is the next active development focus and will be resumed from the existing implementation rather than rebuilt.

The recommendation engine is operational across Vision, Aurora, and Regalia with progress, quick, and play modes. Normal responses remain concise and diversity-aware while objective bundles provide actionable grouped work. Vision additionally exercises collection-focused filtering, shared dependency/material recognition, prerequisite availability, playability metadata, and background-work horizons.

The session planner is operational with time allocation, map-aware planning, useful unused-time handling, cross-goal awareness, collection focus, dependency-aware grouping, projected completion effects, shared-dependency value, multi-map handling, and access to the full eligible ranked candidate pool before presentation-oriented diversity trimming.

The project now has a working end-to-end pipeline:

`game data -> shared live account state -> trackers -> ranked candidates -> recommendations/session plans`

Recommendation and session-planning requests share one request-scoped account snapshot across all three trackers, eliminating duplicate account fetching while preserving fresh data and standalone tracker behaviour.

Milestone-end architecture/efficiency reviews remain part of the development workflow and have already caught duplicate API fetching, duplicated objective-bit logic, presentation-layer candidate trimming, misleading parent tasks, and metadata loss during shared-achievement consolidation before those issues became deeper technical debt.
