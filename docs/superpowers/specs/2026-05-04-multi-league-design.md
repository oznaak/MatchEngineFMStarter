# Multi-League Simulation, Cups & World Menu — Design Spec

**Date:** 2026-05-04  
**Status:** Approved

---

## 1. Goals

- All leagues simulate simultaneously regardless of which league the user manages
- Real promotion/relegation rules per country (correct spots, playoffs)
- Five domestic cups (FA Cup, Taça de Portugal, Copa del Rey, Coupe de France, DFB-Pokal) with real phases and dates
- "World → Competitions" menu showing all competitions with drill-down to league tables and cup brackets
- AI clubs outside the user's league perform transfers and squad rotation for realism

---

## 2. Database Schema

### New / modified tables

```sql
-- competitions: one row per competition per season
CREATE TABLE competitions (
    id          TEXT PRIMARY KEY,   -- e.g. "ENG1_2025", "FA_CUP_2025"
    name        TEXT NOT NULL,
    country     TEXT NOT NULL,      -- "ENG", "ESP", "FRA", "GER", "PRT"
    type        TEXT NOT NULL,      -- "league" | "cup"
    season      INTEGER NOT NULL,   -- e.g. 2025
    save_id     TEXT NOT NULL
);

-- fixtures: add competition_id, leg, is_neutral
ALTER TABLE fixtures ADD COLUMN competition_id TEXT;
ALTER TABLE fixtures ADD COLUMN leg            INTEGER DEFAULT 1;
ALTER TABLE fixtures ADD COLUMN is_neutral     INTEGER DEFAULT 0;

-- cup_brackets: bracket state for all cup rounds
CREATE TABLE cup_brackets (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    save_id         TEXT NOT NULL,
    competition_id  TEXT NOT NULL,
    round           TEXT NOT NULL,  -- "R64","R32","R16","QF","SF","F"
    slot            INTEGER NOT NULL,
    club_a          TEXT,
    club_b          TEXT,
    score_a_leg1    INTEGER,
    score_b_leg1    INTEGER,
    score_a_leg2    INTEGER,
    score_b_leg2    INTEGER,
    winner          TEXT
);

-- save_league_clubs: per-save membership (enables promotion/relegation)
CREATE TABLE save_league_clubs (
    save_id     TEXT NOT NULL,
    league_id   TEXT NOT NULL,
    club_id     TEXT NOT NULL,
    season      INTEGER NOT NULL,
    PRIMARY KEY (save_id, league_id, club_id, season)
);

-- standings: pre-aggregated per competition (replaces on-the-fly calculation)
CREATE TABLE standings (
    save_id         TEXT NOT NULL,
    competition_id  TEXT NOT NULL,
    club_id         TEXT NOT NULL,
    season          INTEGER NOT NULL,
    played          INTEGER DEFAULT 0,
    won             INTEGER DEFAULT 0,
    drawn           INTEGER DEFAULT 0,
    lost            INTEGER DEFAULT 0,
    gf              INTEGER DEFAULT 0,
    ga              INTEGER DEFAULT 0,
    points          INTEGER DEFAULT 0,
    PRIMARY KEY (save_id, competition_id, club_id, season)
);
```

---

## 3. Simulation Engine

### Poisson model for AI fixtures

```
λ_home = (attack_home / defense_away) * base_goals * home_advantage
λ_away = (attack_away / defense_home) * base_goals

attack  = avg OVR of starting XI / 75
defense = avg OVR of starting XI / 75
base_goals = 1.35
home_advantage = 1.2 (multiplier on λ_home)
```

- Goals drawn from Poisson distribution
- Result saved to `fixtures`, standings incremented atomically
- Cup draws after 90 min → extra time (coin-flip ±1 goal) → penalties if still level

### `simulate_ai_fixture(fixture)` — called for every non-user fixture on a given day

### `apply_training_all_clubs(save_id)` — runs daily for all clubs using default "balanced" schedule for AI clubs

### `simulate_ai_transfers(save_id)` — runs weekly (Monday):
- Check each AI club for squad gaps
- Free-agent pickup or inter-club transfer
- Offer = OVR × 500k; seller accepts if within tolerance

---

## 4. Promotion & Relegation

### England
- **ENG1 → ENG2:** Bottom 3 relegated directly
- **ENG2 → ENG1:** Top 2 promoted automatically; 3rd–6th play playoffs (2-leg semis + 1-leg final at Wembley)

### Spain
- **ESP1 → ESP2:** Bottom 3 relegated directly
- **ESP2 → ESP1:** Top 2 promoted automatically; 3rd–6th play playoffs

### France
- **FRA1 → FRA2:** 18th relegated directly; 16th–17th play 2-leg playoff vs FRA2 3rd–4th
- **FRA2 → FRA1:** Top 2 promoted automatically

### Germany
- **GER1 → GER2:** Bottom 2 relegated directly; 16th plays 2-leg playoff vs GER2 3rd
- **GER2 → GER1:** Top 2 promoted automatically

### Portugal
- **PRT1 → PRT2:** Bottom 2 relegated directly; 15th–16th play 2-leg playoff vs PRT2 3rd–4th
- **PRT2 → PRT1:** Top 2 promoted automatically

### Implementation
- `save_league_clubs` seeded from `league_clubs` at save creation
- Each season end: `apply_promotion_relegation(save_id, season)` updates `save_league_clubs` for next season
- Playoffs generated as cup-style fixtures in `fixtures` with `competition_id = "ENG1_PLAYOFF_2025"`

---

## 5. Domestic Cups

### FA Cup (England)
- Clubs: 20 ENG1 + 24 ENG2 (44 total)
- PL clubs enter at 3rd Round (January)
- Rounds: 3rd (Jan) → 4th (Jan) → 5th (Feb) → QF (Mar) → SF (Apr) → Final (May)
- Single-leg knockout; random draw, no seeding

### Taça de Portugal
- Clubs: 18 PRT1 + 18 PRT2 (from R32)
- Rounds: R32 (Sep) → R16 (Nov) → QF (Jan) → SF (Mar) → Final (May)
- Single-leg; neutral venue final

### Copa del Rey (Spain)
- Clubs: 20 ESP1 + 22 ESP2
- Rounds: R32 (Nov) → R16 (Dec) → QF (Jan/Feb, 2-leg) → SF (Feb/Mar, 2-leg) → Final (Apr, neutral)
- QF and SF: home-and-away; away goals tiebreaker; penalties if still level

### Coupe de France
- Clubs: 20 FRA1 + 20 FRA2
- Rounds: R64 (Dec) → R32 (Jan) → R16 (Feb) → QF (Mar) → SF (Apr) → Final (May)
- Single-leg throughout

### DFB-Pokal (Germany)
- Clubs: 18 GER1 + 18 GER2 (36 total)
- Rounds: R1 (Aug) → R2 (Oct) → R16 (Jan) → QF (Feb) → SF (Apr) → Final (May)
- Single-leg; GER2 clubs host GER1 in R1

### Cup bracket storage
- `cup_brackets` table stores each matchup per round/slot
- `schedule_cup_draw(save_id, competition_id, round)` fills bracket slots randomly
- Triggered on scheduled date (stored in a `cup_draw_schedule` lookup)
- User's cup fixtures appear in their calendar automatically

---

## 6. Daily Advance Overhaul

### New `advance_save_one_day` flow

```
advance_save_one_day(conn, save_id, managed_club_id, date)
  1. apply_training_all_clubs(save_id, date)
  2. fixtures_today = get_all_fixtures(save_id, date)
  3. user_fixture  = fixture where managed_club_id in (home, away)
  4. ai_fixtures   = all other fixtures
  5. for each ai_fixture: simulate_ai_fixture(ai_fixture)
  6. if Monday: simulate_ai_transfers(save_id)
  7. if cup draw scheduled today: schedule_cup_draw(...)
  8. if season end reached: apply_promotion_relegation + seed_next_season
  9. return user_fixture (or None)
```

---

## 7. World / Competitions UI

### Screen state additions

```python
SCREEN_WORLD_COMPETITIONS = "world_competitions"
SCREEN_CUP_BRACKET        = "cup_bracket"
```

### Competitions screen layout (1560×900, dark theme)

- Left panel: Leagues (10 cards) — name, country, top 3 clubs + points, matchday progress
- Right panel: Cups (5 cards) — name, current round, last 4 results
- Click league card → existing standings screen filtered by `competition_id`
- Click cup card → new cup bracket screen

### Cup bracket screen

- Rounds as columns left→right (R64/R32 → … → Final)
- Each slot: club name | score (or "TBD")
- Completed rounds greyed; current round highlighted
- 2-leg ties: show both leg scores + aggregate
- Back button → Competitions screen

### New DB queries

- `load_all_competitions(save_id)` → list with current round/matchday metadata
- `load_cup_bracket(save_id, competition_id)` → bracket rows grouped by round

### New render functions

- `draw_competitions_screen(view)` — two-panel layout
- `draw_cup_bracket(view)` — bracket columns

---

## 8. Key Constraints

- Global `league_clubs` table is never mutated — all per-save membership goes through `save_league_clubs`
- `fixtures` standings queries always filter by `competition_id` to avoid cross-competition pollution
- AI clubs in all leagues buy/sell players and rotate squads every week
- Promotion/relegation runs at season end before next season fixtures are seeded
