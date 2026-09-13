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


### Milestone 16 - Aurora Dependency Depth and Wayfarer's Henge Planning

- Resumed Aurora development from the existing implementation rather than rebuilding the tracker.
- Captured a fresh live Aurora baseline and compared the existing tracker against the generic dependency capabilities developed during the Vision milestone.
- Preserved the existing 87-objective Aurora I mastery framework and avoided unnecessary reclassification or scoring changes.
- Deepened Bitterfrost Frontier planning for Gift of Aurene:
  - Added all 8 achievement-bit objectives.
  - Modelled the five doll components as buy-or-craft acquisition choices.
  - Added prerequisite flow from doll components to Dragon Hatchling Doll to Aurenic Essence.
  - Reused generic nested `achievement_bits` dependency handling rather than adding Aurora-specific planner logic.
- Deepened Draconis Mons planning for the full Wayfarer's Henge chain:
  - The Druid Stone - 7 objectives.
  - Awakening the Druid Stone - 14 objectives.
  - Sprouting the Druid Stone - 21 objectives.
  - A Henge Away from Home - 32 objectives.
- Added a generic sequential `next_dependency` handoff so a completed achievement-bit dependency can automatically resolve into the next achievement in a chain.
- Added prerequisite-bit availability handling across the Henge chain so blocked turn-ins and crafted runestones do not appear actionable before their prerequisites are complete.
- Modelled daily Druid Runestone usage across the entire Henge chain:
  - The Druid Stone - 1.
  - Awakening the Druid Stone - 3.
  - Sprouting the Druid Stone - 5.
  - A Henge Away from Home - 7.
  - 16 total Druid Runestones across the complete chain.
- Modelled parallel work alongside the daily gate, including flowers, bouquets, event drops, elemental drops, Vision Crystal turn-in, lodestone tributes, and Fire Orchid seed planting.
- Modelled shared completion turn-ins such as Destroyer's Rest and Elemental Rest with multi-bit prerequisites.
- Recorded The Wayfarer's Henge as the final reward of A Henge Away from Home.
- Verified after every dependency-depth stage that the live tracker continued to resolve the account's current state correctly as The Druid Stone 2/7 with Druid Runestone as the next objective.
- Kept recommendation scoring unchanged; this milestone improved actionability through data and reusable dependency structure instead of score tuning.
- Incremental checkpoint commits:
  - `5c55b03` - Deepen Gift of Aurene dependency planning
  - `8031028` - Deepen Druid Stone dependency planning
  - `1512e2b` - Add Awakening Druid Stone dependency chain
  - `3e38f09` - Add Sprouting Druid Stone dependency chain
  - `9aa4272` - Complete Wayfarer's Henge dependency chain

#### Aurora dependency checkpoint

- Gift of Aurene and the full Wayfarer's Henge chain are now represented with nested, actionable dependency depth.
- Current live Wayfarer's Henge progress remains at The Druid Stone 2/7.
- The generic sequential dependency transition is implemented but its natural live transition from The Druid Stone into Awakening remains pending gameplay completion of the current tier.
- Further Aurora work should continue gap-by-gap and remain evidence-driven rather than expanding every collection pre-emptively.


### Milestone 17 - Aurora Dependency Normalisation and Reuse

- Completed the second Aurora dependency-depth pass across all six Living World Season 3 mastery reward requirements.
- Added generic `achievement_set` tracking for episode mastery meta-achievements whose API progress cannot be represented reliably by meta-achievement bit positions.
- Modelled all six episode mastery reward dependencies with live child-achievement state and required completion thresholds:
  - `"Out of the Shadows" Mastery` - 18 of 19 eligible achievements required.
  - `"Rising Flames" Mastery` - 23 of 30 eligible achievements required.
  - `"A Crack in the Ice" Mastery` - 21 of 21 eligible achievements required.
  - `"The Head of the Snake" Mastery` - 28 of 39 eligible achievements required.
  - `"Flashpoint" Mastery` - 20 of 32 eligible achievements required.
  - `"One Path Ends" Mastery` - 36 of 42 eligible achievements required.
- Added reusable dependency definitions using `definition_id` and `dependency_ref` so detailed achievement tracking is defined once and referenced wherever multiple goals depend on it.
- Reused canonical detailed tracking for:
  - Token Collector.
  - Cin Business.
  - Lessons Learned.
  - The full Wayfarer's Henge chain.
- Preserved the canonical Wayfarer's Henge definition under Draconis Mons Master while Flashpoint mastery children reference the appropriate Henge stage.
- Normalised dependency state semantics:
  - `available` means unfinished and currently actionable.
  - `prerequisites_complete` reports prerequisite state independently of completion.
- Removed stale `existing_tracking` metadata from Searing Ascent and Abaddon's Ascent rather than inventing dependency references to detail that does not exist.
- Updated Aurora recommendations to traverse reusable dependencies down to the currently actionable nested objective.
- Preserved objective context in session-plan steps instead of dropping rich recommendation objective metadata at the planner boundary.
- Added alternate acquisition-route recommendations from `acquisition_options`.
  - Achievement and reward-track routes can be represented as separate candidates for the same collection objective.
  - Reward-track alternatives preserve their PvP/WvW mode metadata without inventing account-aware reward-track progress.
  - Current public activity filtering still uses the existing WvW activity bucket for alternatives that include WvW; first-class PvP activity support remains future work.
- Normalised Aurora playability metadata immediately before scoring:
  - Existing explicit `availability_type` remains authoritative.
  - `event_dependent=true` maps to `availability_type="event"` when no explicit type exists.
  - Single active dependency/objective metadata can carry schedule, group, playability, and time-gate context into scoring.
  - Multi-objective bundles remain conservative rather than inheriting event dependence from only one child.
- Kept all existing scoring constants unchanged; the pass focused on schema consistency, reuse, and correct consumption of existing metadata.
- Completed the final Pass 3 architecture/duplication review with no additional dependency abstraction or scoring rewrite required.
- Key checkpoint commits:
  - `e8489d8` - Normalize dependency availability semantics
  - `c95c1de` - Add reusable Aurora dependency references
  - `6a7a7df` - Consume reusable Aurora dependencies in recommendations
  - `5f8bc20` - Reuse Token Collector dependency tracking
  - `a8cf9f5` - Reuse Cin Business dependency tracking
  - `c37a197` - Reuse Lessons Learned dependency tracking
  - `cc5c1a5` - Remove stale Aurora tracking metadata
  - `76e5c2b` - Preserve objective context in session plans
  - `e22d287` - Add Aurora acquisition route recommendations
  - `5475e44` - Normalize Aurora playability metadata

#### Aurora Pass 3 checkpoint

- Aurora dependency-depth architecture is now considered clean enough to freeze pending natural gameplay validation.
- Locked mastery collections continue to expose tracking state without leaking into recommendations.
- Current live recommendations remain correctly focused on unfinished Sentient Seed work: Cin Business 14/18 and Token Collector 20/40.
- Unlocked mastery recommendation behaviour, reusable nested dependency traversal, and later Wayfarer's Henge stage handoffs remain candidates for natural validation as the account progresses.
- Future Aurora changes should be driven by live planning gaps rather than broader pre-emptive expansion or score tuning.


### Milestone 18 - Vision Live Skin-Unlock Progress

- Corrected completed-dependency handling so a definitively completed prerequisite no longer emits a stale child `next_objective` when historical API bit state is incomplete.
- Preserved raw child-bit uncertainty rather than falsely marking every optional child objective complete.
- Added generic account-aware `skin_count` support.
- Added `/account/skins` to shared account state and use live unlocked skin IDs when resolving skin-count requirements.
- Resolved and stored the 32 eligible Astral/Stellar weapon skins for Vision of Equipment: Astral Weapons.
- Vision now reports live Astral/Stellar progress and the actual number of additional eligible skins required.
- Verified live account state at 4/6 eligible Astral/Stellar skins, producing the actionable recommendation `Acquire 2 more Astral or Stellar weapon skins`.
- Preserved the correct post-unlock action to speak to Yasna for the Vision collection item.
- The tracked account has now completed the Thunderhead Peaks reward track route that was intentionally left open during the earlier Vision dependency-depth milestone.
- The account is currently gathering the final materials for remaining Astral/Stellar and Dragonsblood weapon-skin requirements.
- Vision remains frozen unless live gameplay exposes a genuine planning problem; trivial end-stage Vision II mastery-kneeling steps do not currently justify deeper modelling.
- Checkpoint commit:
  - `5695215` - Track Vision skin unlock progress


### Milestone 19 - Aurora Natural Unlock and Daily Opportunity Prioritisation

- Naturally completed Sentient Seed and unlocked Aurora: Awakening without simulated account state.
- Validated all six Living World Season 3 mastery collections in their real unlocked state.
- Confirmed all six collections transitioned to `unlocked=true` and `actionable=true`.
- Confirmed locked Aurora II work did not leak into recommendations.
- Confirmed completed threshold-based episode mastery requirements no longer emit stale optional child work.
- Live unlocked mastery state validated as:
  - Bloodstone Fen Master - 1/12; `"Out of the Shadows" Mastery` complete at 18/18 required.
  - Ember Bay Master - 1/15; `"Rising Flames" Mastery` complete at 23/23 required.
  - Bitterfrost Frontier Master - 0/14; `"A Crack in the Ice" Mastery` 17/21 and Gift of Aurene 1/8.
  - Lake Doric Master - 0/16; `"The Head of the Snake" Mastery` 20/28.
  - Draconis Mons Master - 0/14; `"Flashpoint" Mastery` 17/20 and The Druid Stone 2/7.
  - Siren's Landing Master - 0/16; `"One Path Ends" Mastery` 24/36.
- Added `daily_opportunity_type` so daily work is prioritised by planning value instead of treating every daily limit equally.
- Current classes: `hard_gate`, `limited_attempt`, `soft_cap`, and `optional`.
- Verified Druid Runestone is prioritised ahead of softer repeatable daily work.
- Verified a live 60-minute Aurora plan stays in Draconis Mons: Druid Runestone first, then Albino Orchid gathering.
- Checkpoint commit: `89c835f` - Prioritize Aurora daily opportunities.

### Milestone 20 - Self-Hosted Docker and Portainer Deployment

- Prepared the FastAPI application for repeatable container deployment.
- Added `/health` and container health checking.
- Added explicit `GW2_API_KEY` environment handling.
- Added a dedicated Portainer Compose definition while preserving local development Compose.
- Added GitHub Actions publishing to GHCR.
- Current image: `ghcr.io/antastico/gw2-companion:aurora-dependency-depth`.
- GitHub Actions publishes both the branch tag and immutable commit-SHA tags.
- Deployed GW2 Companion as its own Portainer stack.
- Portainer host: `192.168.68.13`.
- Live application base URL: `http://192.168.68.13:8001`.
- Host port 8001 is used because Portainer already occupies host port 8000.
- Verified live `/`, `/health`, `/account`, and `/tracker/aurora`.
- Verified the API key is supplied through Portainer environment variables and is not committed.
- Verified the normal update path end to end: Git push -> GitHub Actions -> GHCR -> Portainer `Re-pull image and redeploy` -> healthy container.
- Deployment commits:
  - `acc130c` - Prepare Docker deployment for Portainer
  - `30038a3` - Add automated Docker image publishing
  - `60e2d36` - Use port 8001 for Portainer deployment


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
  |     |     +-- Generic achievement-bit/set objective resolution
  |     |     +-- Nested/sequential achievement dependencies
  |     |     +-- Reusable definition/reference dependency registry
  |     |     +-- Prerequisite availability and next-dependency handoff
  |     |     +-- Collection unlock/actionable state
  |     |     +-- Grouped missing-objective progress
  |     |
  |     +-- Acquisition-route alternatives
  |     +-- Aurora playability metadata normalisation
  |     +-- Account-aware skin-count requirements
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
- `/health`
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
- `/app`
- `/app/session-plan?minutes=30|60|90`
- `/app/goal/vision`
- `/app/goal/aurora`

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

Current branch: `feature/web-frontend`

Latest verified checkpoints:

- `af546d2` - Fix legendary completion and Henge daily tracking
- `301e15e` - Update project status for frontend MVP
- `b702126` - Polish goal crafting drill-downs
- `a33a0a1` - Add account-aware crafting acquisitions
- `3c8ae62` - Add recommendation explanations
- `2d413ed` - Add crafting component drill-down
- `79d64c4` - Publish frontend branch Docker image
- `f1226d0` - Add goal detail pages
- `255d68e` - Add expandable goal collection details
- `5695215` - Track Vision skin unlock progress
- `89c835f` - Prioritize Aurora daily opportunities
- `60e2d36` - Use port 8001 for Portainer deployment
- `30038a3` - Add automated Docker image publishing
- `acc130c` - Prepare Docker deployment for Portainer

The web frontend MVP is now implemented on `feature/web-frontend` and has been repeatedly validated against the live account and local Docker runtime.

Frontend capabilities now include:

- Server-rendered Jinja2 UI inside the existing FastAPI application.
- Account summary dashboard.
- Active goal cards for Vision, Aurora, and Regalia.
- 30 / 60 / 90 minute session-plan shortcuts.
- Live daily-priority recommendations with "Why this?" explanations.
- Dedicated Vision and Aurora goal-detail pages.
- Expandable collection/objective drill-downs.
- Expandable crafting-component and missing-material drill-downs.
- Compact navigation and shell polish.
- Automatic CSS cache-busting using the stylesheet modification time.
- Backend-owned tracker/planner logic; templates remain presentation-only.

Crafting/account-state capabilities added during frontend field testing:

- `/account/wallet` is included in shared `AccountState`.
- `/account/legendaryarmory` is included in shared `AccountState` so final legendary ownership can be distinguished from consumed crafting intermediates.
- Wallet currencies are available to requirement analysis alongside inventory items.
- `acquisitions.json` describes factual non-recipe acquisition routes separately from recipes.
- Acquisition options calculate live owned / required / missing costs and affordability.
- Coin costs are formatted as gold / silver / copper in the frontend.
- Daily acquisition limits can be displayed without treating them as recommendation scores.
- Static "preferred route" metadata was deliberately removed; route recommendation must come from account-aware planning, not data ordering.
- Gift of the Mists now preserves Gift of Glory and Gift of War as real intermediate items instead of flattening their currencies.
- Crystalline Ingot now has a real recipe node rather than being treated as an unexplained leaf.
- Aurora crafting can bridge achievement-reward items back to live Aurora stage progress.

The feature branch image is currently published with the temporary `web-frontend` GHCR tag so Portainer can run the frontend branch before merge. After merge, the workflow/tag should be restored to the production `main` path.

## Current Aurora State

Sentient Seed has been completed and Aurora: Awakening is naturally unlocked.

Current top-level stage state:

- Aurora: Awakening - in progress, 22/87 (25.3%).
- Aurora II: Empowering - locked, 0/21.

All six Aurora I mastery collections are unlocked and actionable. Natural gameplay has now progressed further into the Wayfarer's Henge chain and exposed a recurring-daily modelling gap that has been fixed and field-tested.

Current crafting state from live account testing:

- Spark of Sentience - 0/1; correctly identified as an achievement reward from Aurora II: Empowering rather than a recipe.
- Mystic Tribute - 0/1 after its shared materials/intermediates were consumed by the completed Vision craft; the resulting large missing-material list is intentionally preserved as a useful collection/shopping list.
- Gift of Sentience - 0/1; missing leaves continue to expose live account shortages and Gift of Valor progress.
- Gift of Valor - linked to live Aurora: Awakening progress rather than shown as a dead-end material.
- Gift of Draconic Mastery - 0/1; current missing leaf is Bloodstone Shard.
- Bloodstone Shard - account-aware acquisition route correctly recognises the Spirit Shard wallet balance and current affordability.
- Gift of War ownership is respected through the corrected Gift of the Mists recipe tree, so already-completed intermediate work no longer creates a false 250 Memory of Battle requirement.

Design rules reinforced by live crafting work:

`recipe structure should preserve real intermediate items`

`acquisition route != recipe`

`static acquisition data describes facts -> recommendation logic decides preference`

`achievement reward requirements should link back to live tracker progress`

`frontend presents account-aware analysis -> frontend does not recalculate it`

## Known Limitations / Technical Debt

### Aurora later-stage natural transition validation

The natural Sentient Seed -> Aurora: Awakening unlock transition has been validated successfully. The six mastery collections, `achievement_set` dependencies, reusable dependency references, acquisition alternatives, and nested recommendation traversal all survived the real unlock transition.

Natural gameplay has now progressed beyond the original first Druid Runestone stage. This exposed that `druid_runestones_required` metadata was not being consumed by recommendation logic after the first Henge tier. The tracker now emits an ongoing Druid Runestone `hard_gate` daily while future Wayfarer's Henge steps still consume Runestones. Because the ArenaNet account API cannot reliably prove whether today's Runestone was already obtained and consumed, the daily remains visible as informational priority context but is excluded from `SessionPlanner` allocation. This behaviour has been validated against the live account.

Later individual Henge stage handoffs should still be observed naturally as gameplay reaches them.

### First-class PvP planning

Acquisition alternatives can preserve `modes: ["PvP", "WvW"]`, but the public activity filter and session profiles do not yet have a dedicated PvP activity/profile. Alternatives that include WvW currently use the existing WvW activity bucket. Do not add first-class PvP scoring merely because a reward-track route exists; revisit this when the tracked account has a real Aurora or other planning need for PvP-specific sessions.

### Objective-bundle timing

Aurora mastery bundles sum per-objective timing metadata. This is more accurate than count-based timing, but it may still overestimate work when several objectives naturally overlap in the same event chain or route. Future refinement can account for overlap when live planning evidence shows a meaningful problem.

### Rich contextual metadata

Aurora data contains useful descriptive fields such as `event_details`, vendor/access details, `chance_based`, and `daily`. These are preserved as context but are not all direct scoring inputs. Do not invent score penalties or bonuses for them without field-test evidence.

### Recommendation candidate API boundary

`RecommendationService.get_recommendations()` still supports an internal `full_candidate_pool` option used by `SessionPlanner`. A future refactor could expose ranked eligible candidates through a dedicated internal method so presentation-oriented selection and planner candidate generation are more explicitly separated.

### ArenaNet API latency

Duplicate account fetching has been resolved by `AccountState`. Remaining latency is primarily influenced by the slowest ArenaNet endpoint in the concurrent snapshot, historically `/characters?page=0&page_size=200` in local instrumentation.

Possible future improvements include carefully scoped short-lived caching, determining whether every recommendation mode requires character inventory, and graceful partial-state handling when a non-critical ArenaNet endpoint fails.

### Natural dependency-transition validation

The reusable dependency/reference architecture and sequential Wayfarer's Henge chain are implemented. Natural transitions into later Aurora mastery and Henge stages should be validated as gameplay reaches them rather than simulated into additional architecture.


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

### Milestone 21 - Web Frontend MVP - COMPLETE

The original frontend MVP scope is complete:

- Account summary/dashboard.
- Vision, Aurora, and Regalia goal overview.
- 30 / 60 / 90 minute session planning.
- Live recommendation explanations and daily priorities.
- Vision and Aurora goal-detail views.
- Expandable collection/objective details.
- Expandable crafting/material details.
- Account-aware wallet/acquisition routes.
- Achievement-reward bridging for Aurora crafting requirements.
- LAN-first deployment through the existing Docker / GHCR / Portainer stack.

Frontend design rules remain:

`frontend presents planner/tracker output -> backend remains source of truth`

`do not duplicate tracker/dependency/acquisition logic in templates or JavaScript`

`compact by default -> detail on demand`

`static data describes facts -> account-aware services make decisions`

### Immediate Closeout

Before starting another product milestone:

- Completed: pushed `feature/web-frontend` through `af546d2`.
- Completed: re-pulled/redeployed the exact feature image in Portainer and smoke-tested Vision completion, Aurora daily priorities, the 60-minute planner, and Aurora crafting/material output.
- Next: merge `feature/web-frontend` into `main`.
- Restore GitHub Actions from the temporary `feature/web-frontend` / `:web-frontend` publishing path to the production `main` image path.
- Re-deploy production from the merged `main` image and perform a final smoke test.

### After Merge

Further development should remain evidence-driven. Priorities are likely to come from real gameplay use of the new UI rather than pre-emptive architecture expansion. Candidate areas include acquisition-route ranking based on current account state, additional acquisition coverage when real goals need it, later Aurora dependency-transition validation, and additional legendary goals.

## Future Work

- Continue validating Aurora recommendations as real account progress reaches later mastery and Henge stages.
- Validate later Wayfarer's Henge dependency transitions through natural account progress.
- Revisit Vision planner tuning only when gameplay exposes a genuine gap; Vision collection progress is complete.
- Let recommendation logic rank acquisition routes only when there is enough account-aware evidence to do so; do not restore static preferred-route flags.
- Expand acquisition-method coverage only where real goals require it: craft, buy, earn, achievement rewards, PvP/WvW reward tracks, vendor transitions, currencies, and time-gated acquisition.
- Consider exposing `units_affordable` / today's daily capacity for limited acquisition routes if real use shows the current all-units affordability flag is insufficient.
- Add first-class PvP planning only when a concrete account goal makes it useful.
- Add additional legendary goals.
- Refine objective/bundle timing where overlapping event or route work makes summed timing too conservative.
- Consider carefully scoped caching only if further latency reduction becomes worthwhile.
- Refactor planner candidate generation away from the public recommendation response shape if the planner grows substantially.
- Keep the GHCR -> Portainer deployment workflow simple and repeatable after restoring the production `main` path.

## Current State

Prismatic Champion's Regalia is complete for the tracked account; its tracker remains operational.

Vision is complete for the tracked account: Vision I: Awakening is 42/42 and Vision II: Farsight is 20/20, for 62/62 collection progress, and the final legendary has been crafted. Final completion is now determined from live Legendary Armory ownership rather than the presence of consumed intermediate components. After the final craft, the dashboard correctly reports Vision as Complete and the four top-level crafting components remain logically satisfied instead of regressing to missing.

Vision live crafting field tests also validated the wallet/acquisition model before completion. The Funerary Incense drill-down can compare Elegy Mosaic, Trade Contract, Vabbi heart-vendor, and Crystalline Ingot routes against current inventory and wallet balances without declaring a static preferred route.

Aurora tracking is operational with Aurora: Awakening currently at 22/87 and Aurora II: Empowering locked at 0/21. The tracker retains reusable achievement-bit / achievement-set dependency guidance, Gift of Aurene depth, the full sequential Wayfarer's Henge chain, reusable dependency definitions/references, normalised playability metadata, and daily-opportunity prioritisation. Recurring Druid Runestone pressure now remains visible as a hard daily gate throughout later Henge progress without consuming session-plan time when today's acquisition state cannot be proven. Aurora crafting continues to distinguish recipes, ordinary materials, vendor/currency acquisitions, and achievement-reward items; Spark of Sentience and Gift of Valor link back to their live Aurora achievement stages.

The recommendation engine remains operational across Vision, Aurora, and Regalia with progress, quick, and play modes. Normal responses remain concise and diversity-aware while objective bundles provide actionable grouped work. It supports collection-focused filtering, shared dependency/material recognition, prerequisite availability, playability metadata, acquisition alternatives, background-work horizons, and account-aware next-step resolution.

The session planner remains operational with time allocation, map-aware planning, useful unused-time handling, cross-goal awareness, collection focus, dependency-aware grouping, projected completion effects, shared-dependency value, multi-map handling, and access to the full eligible ranked candidate pool before presentation-oriented diversity trimming.

The project now has a working user-facing frontend as part of the existing FastAPI application. The dashboard, goal pages, session controls, recommendation explanations, collection drill-downs, crafting drill-downs, wallet-backed acquisition options, and compact navigation have all been exercised against live account state.

The application/deployment flow is now:

`game data + acquisition data -> shared live account state -> trackers / requirement analysis -> recommendations / session plans -> FastAPI/Jinja frontend`

`feature push -> GitHub Actions -> GHCR feature image -> Portainer re-pull/redeploy -> http://192.168.68.13:8001`

After the frontend branch is merged, the publishing path should return to the production `main` workflow/tag.

Recommendation, session-planning, tracker, and frontend requests can share request-scoped account state, including wallet currencies, Legendary Armory ownership, inventory holdings, achievements, recipes, and skins where required. This preserves fresh account-aware behaviour while avoiding unnecessary duplicate account fetching inside a single request.

Milestone-end architecture/efficiency reviews remain part of the development workflow and have now also caught flattened crafting intermediates, missing wallet context, misleading non-recipe material leaves, and static acquisition preference before those became permanent architecture.
