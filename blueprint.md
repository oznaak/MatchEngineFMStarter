Below is a full agent-based plan for a soccer manager match engine that is close to implementation level rather than a vague design brief.

## 1. Engine target

You want a **manager simulation engine**, not a manual-control physics game.

That means:

* realism over spectacle
* tactical identity matters
* player quality matters
* morale, fatigue, and match context matter
* randomness exists but is constrained
* results emerge from many weighted micro-events, not scripted scorelines

The correct model is:

1. **Pre-match tactical model**
2. **Continuous possession-state simulation**
3. **Contextual event resolution**
4. **Post-event state updates**
5. **Manager adaptation layer**
6. **Substitution/instruction layer**
7. **Outcome calibration layer**

---

# 2. Core philosophy

Do **not** simulate the match as “team rating A vs team rating B”.

Simulate it as:

* where the ball is
* who is near the ball
* what both teams are trying to do
* what options the player sees
* whether the player can execute
* whether opponents disrupt it
* how fatigue, morale, pressure, and shape distort decisions

So the engine should be driven by:

* **team agents**
* **unit agents** (defense, midfield, attack)
* **player agents**
* **ball state**
* **match context**

---

# 3. Simulation resolution

Use a **hybrid tick + event model**.

## Recommended match clock

* match duration: 90 + stoppage
* internal simulation step: **0.5s to 1.0s**
* possession decision window: every **1–3 seconds**
* major event resolution: immediate, event-driven

This avoids brute-force physics while still feeling alive.

## Why hybrid is better

Pure per-second simulation becomes noisy and expensive.
Pure event-only simulation becomes fake and detached from tactics.

Hybrid gives:

* shape movement
* spacing logic
* pressing windows
* duel frequency
* event outcomes tied to positioning

---

# 4. Data model

## 4.1 Team tactical profile

Each team needs a tactical object:

```ts
TeamTactics {
  formation: "4-3-3" | "4-2-3-1" | ...
  mentality: 0..100            // defensive to ultra attacking
  tempo: 0..100
  width: 0..100
  defensiveLine: 0..100
  lineOfEngagement: 0..100
  pressingIntensity: 0..100
  counterPress: 0..100
  directness: 0..100
  buildupRisk: 0..100
  overlapLeft: 0..100
  overlapRight: 0..100
  underlapLeft: 0..100
  underlapRight: 0..100
  offsideTrap: 0..100
  timeWasting: 0..100
  creativeFreedom: 0..100
  crossingFrequency: 0..100
  shootOnSight: 0..100
  workBallIntoBox: 0..100
  transitionAfterWin: "counter" | "hold" | "balanced"
  transitionAfterLoss: "counterpress" | "regroup" | "balanced"
  setPieceProfiles: ...
}
```

---

## 4.2 Player attributes

You need attribute groups, not random single stats.

## Technical

* first touch
* passing
* short passing
* long passing
* crossing
* dribbling
* finishing
* heading
* shooting power
* technique
* tackling
* marking

## Mental

* decisions
* anticipation
* composure
* vision
* positioning
* off the ball
* teamwork
* aggression
* concentration
* flair
* bravery
* work rate
* leadership

## Physical

* acceleration
* pace
* agility
* balance
* strength
* stamina
* jumping reach
* natural fitness

## Goalkeeper

* reflexes
* handling
* one-on-ones
* aerial reach
* command of area
* rushing out
* kicking
* throwing
* positioning
* communication

---

## 4.3 Hidden/context variables

These matter as much as raw attributes.

* morale: 0..100
* fatigue: 0..100
* sharpness/match fitness: 0..100
* consistency
* big match temperament
* injury risk
* weak foot quality
* role familiarity
* tactical familiarity
* chemistry links with nearby teammates
* discipline
* current confidence
* frustration
* momentum sensitivity

---

## 4.4 Match context

```ts
MatchContext {
  minute
  stoppageTime
  homeAdvantage
  weather
  pitchCondition
  refereeStrictness
  scoreDifference
  competitionImportance
  cardStatus
  substitutionsUsed
  momentum
  crowdPressure
}
```

---

# 5. Spatial model

Do not use only abstract possession zones. That is too crude.

Use a **simplified pitch grid**.

## Recommended grid

* length split into 6 bands:

  1. own box
  2. own defensive third
  3. own half central progression
  4. attacking half progression
  5. final third
  6. opposition box

* width split into 5 lanes:

  * far left wing
  * left half-space
  * center
  * right half-space
  * far right wing

Total: **30 zones**

This is enough for:

* overloads
* switches
* central congestion
* wing play
* cutbacks
* pressing traps
* offside line behavior

Each player has:

* base tactical zone map by formation/role
* dynamic zone offset by phase
* dynamic movement preference by ball location

---

# 6. Agents

This is the main structure.

## 6.1 Match Director Agent

Controls:

* current possession
* phase changes
* event queue
* clock
* momentum state
* tactical instruction updates

## 6.2 Team Intent Agent

For each team:

* determines attacking intent
* determines defensive shape
* modifies risk by score/minute/morale/fatigue

## 6.3 Unit Agents

Per team:

* defensive unit
* midfield unit
* attacking unit

They control:

* line compactness
* support distances
* pressing depth
* spacing discipline
* recovery speed

## 6.4 Player Decision Agent

For the player on the ball:

* evaluate candidate actions
* assign utility
* choose action probabilistically
* execute with attribute-weighted success

## 6.5 Off-ball Movement Agent

For surrounding players:

* offer support
* attack depth
* hold shape
* make underlap/overlap/run beyond
* cover passing lanes
* track runners

## 6.6 Duel Resolution Agent

Handles:

* shoulder duels
* headers
* interceptions
* tackles
* loose balls
* keeper duels

## 6.7 Shot Resolution Agent

Handles:

* shot selection
* shot quality
* body part
* pressure
* block chance
* save chance
* rebound

## 6.8 Discipline Agent

Handles:

* foul chance
* booking chance
* second-yellow caution bias
* referee style

## 6.9 Adaptation Agent

Handles:

* game state tactical drift
* confidence effects
* panic late on
* low-block preservation
* substitutions and instruction reactions

---

# 7. Match phases

Each possession should be in one of these phases:

1. **build-up**
2. **progression**
3. **final-third circulation**
4. **chance creation**
5. **shot/recovery duel**
6. **transition attack**
7. **transition defense**
8. **set piece**
9. **dead time**

This is essential because action weights must depend on phase.

Example:
A CB in build-up should heavily prefer:

* short pass
* switch
* carry

That same CB in a chaotic transition should heavily prefer:

* clearance
* safe vertical release
* emergency tackle

---

# 8. Team shape and role logic

Formation alone is meaningless unless linked to behavior.

A 4-3-3 high press and a 4-3-3 mid-block must play differently.

Each role needs:

* anchor zone
* phase behavior
* support radius
* risk preference
* movement triggers

Example role profile:

```ts
RoleProfile {
  name: "Inside Forward Attack"
  baseZones: [...]
  attackingRunBias: 0..100
  widthRetention: 0..100
  dribbleBias: 0..100
  cutInsideBias: 0..100
  crossingBias: 0..100
  shotBias: 0..100
  pressBias: 0..100
  trackBackBias: 0..100
}
```

---

# 9. Core event flow

Each tick or decision cycle:

1. update fatigue/morale/momentum drift
2. update player positions relative to ball and tactics
3. determine possession phase
4. choose acting player
5. generate action candidates
6. compute action scores
7. sample chosen action
8. resolve execution
9. resolve opponent reaction
10. update ball location and match state
11. check event aftermath:

* foul
* corner
* throw
* offside
* shot
* rebound
* injury
* card

---

# 10. Decision model

Every action should use:

## Utility score

How attractive the action looks to the player

## Execution score

How likely the player is to pull it off

## Opposition resistance

How likely opponents disrupt it

## Controlled RNG

Final weighted uncertainty

Formula:

```text
ActionFinalScore =
  UtilityWeight * TacticalFit *
  PlayerReadOfGame *
  ContextModifier *
  RandomNoise
```

Then if selected:

```text
ActionSuccessProbability =
  ExecutionSkill *
  PhysicalCondition *
  Composure *
  RoleFamiliarity *
  SupportStructure
  /
  DefensiveResistance
```

---

# 11. Candidate actions by phase

## Build-up

* short pass
* medium pass
* switch
* carry forward
* reset to keeper
* long direct pass
* risky line-break pass
* clearance under pressure

## Progression

* vertical pass
* diagonal pass
* dribble carry
* overlap release
* switch flank
* long ball behind line

## Final third

* through ball
* cross
* cutback
* combination pass
* dribble take-on
* recycle possession
* shot from distance

## Box actions

* near-post shot
* far-post shot
* low driven shot
* finesse shot
* header
* layoff
* penalty-box dribble
* square pass

## Defensive actions

* jockey
* press
* tackle
* stand off
* cover lane
* intercept
* foul cynically
* clear

---

# 12. Attribute influence map

This is where realism comes from.

## Passing

Use:

* passing
* technique
* vision
* decisions
* composure
* weak foot
* pressure resistance
* fatigue
* receiving target movement
* lane congestion

## Through balls / “crazy passes”

Use:

* vision heavily
* technique heavily
* decisions heavily
* passing heavily
* flair moderately
* composure moderately
* teammate off-the-ball movement
* opponent line height
* compactness of defense
* pressure on passer

A high-vision player should **attempt** and **see** passes others do not.
A high-passing player should **execute** them better.
A high-decisions player should **choose** them at better moments.
A high-flair player should attempt rarer actions more often.

That distinction matters.

---

## Finishing

Use:

* finishing
* composure
* technique
* weak foot
* body balance
* pressure level
* angle
* distance
* goalkeeper position
* defender closing speed

## Long shots

Use:

* shooting power
* technique
* long shot trait if you include traits
* composure
* decision making
* fatigue
* distance
* defensive pressure
* keeper positioning

## Headers

Use:

* heading
* jumping reach
* strength
* bravery
* positioning/off the ball
* cross quality
* marker pressure

## Duels

Ground duel:

* strength
* balance
* aggression
* tackling or dribbling depending on role
* pace/acceleration in recovery angle
* fatigue

Aerial duel:

* jumping reach
* strength
* heading
* bravery
* positioning

## Interceptions

Use:

* anticipation
* positioning
* concentration
* acceleration
* reach to lane
* line compactness

## Offside trap

Use:

* team offside trap setting
* backline cohesion
* concentration
* positioning
* anticipation
* communication
* fatigue
* opponent timing/off the ball

---

# 13. Proper offside simulation

Your example is correct but incomplete.

Do not do:

```text
offside = rng + positioning
```

Do:

## Offside event model

When an attacker attempts a run behind a line:

1. calculate **run timing quality**

   * attacker anticipation
   * off the ball
   * decisions
   * composure
   * fatigue penalty

2. calculate **defensive line synchronization**

   * average of back line positioning
   * concentration
   * teamwork
   * communication
   * offside trap instruction
   * fatigue penalty
   * morale/confidence modifier

3. calculate **pass release timing**

   * passer vision
   * decisions
   * technique
   * composure
   * pressure penalty

4. calculate **assistant/ref margin noise**

   * very small bounded random term

Then:

```text
OffsideMargin =
  defensiveStepTiming
  - attackerRunTiming
  - passerReleasePrecision
  + tinyNoise
```

If margin exceeds threshold, offside.

This creates realistic behavior:

* disciplined elite teams catch runs more often
* tired defenses mistime step-ups
* clever forwards bend and delay runs better
* elite playmakers release at the right instant

---

# 14. Goal scoring model

Goals should not come from a single shot roll. They must come from layered resolution.

## Layer 1: Can the shooter get the shot off?

Depends on:

* first touch
* composure
* balance
* pressure
* body orientation
* nearest defender distance
* support of shooting lane

## Layer 2: Shot quality generation

Produces:

* contact quality
* trajectory intent
* shot type
* placement vs power tradeoff

## Layer 3: Defensive interference

* block chance
* deflection chance
* partial block

## Layer 4: Keeper response

* reaction
* positioning
* handling/parry tendencies
* one-on-one quality
* sightline obstruction

## Layer 5: Rebound outcome

* who attacks second ball
* reflex finish chance
* scramble

---

## Sample shot quality formula

```text
BaseShotScore =
  0.25 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * shootingPower
+ 0.10 * balance
+ 0.10 * firstTouch
+ 0.10 * decisions
```

Apply modifiers:

```text
ShotScoreAdjusted =
  BaseShotScore
  * AngleModifier
  * DistanceModifier
  * PressureModifier
  * BodyPartModifier
  * WeakFootModifier
  * FatigueModifier
  * MoraleConfidenceModifier
```

For long-range shots, increase weight of:

* shooting power
* technique
* decisions

For tap-ins, increase weight of:

* composure
* positioning
* first touch

---

# 15. Defensive realism

Defending cannot be reduced to “tackle chance”.

Defending is mostly:

* delay
* channeling
* screening
* line control
* compactness
* denying good shots
* winning second balls

So create defensive contributions that do not always create visible stats.

## Defensive metrics driving the engine

* line compactness
* horizontal compactness
* vertical compactness
* pressure arrival time
* cover shadow quality
* lane denial score
* recovery run speed
* box occupation
* marking tightness

These should shape the opponent’s success rates even without direct tackles.

---

# 16. Morale, confidence, and momentum

These should alter behavior, not just ratings.

## Morale effects

High morale:

* better decisions
* more proactive movement
* slightly more technical execution
* more willingness to risk creative actions

Low morale:

* conservative choices
* heavy first touch errors
* delayed reactions
* worse composure
* more collapse after setbacks

## Confidence effects during match

Confidence rises after:

* successful dribbles
* key passes
* goals
* several completed actions
* keeper saves

Confidence falls after:

* missed sitter
* error leading to chance
* card
* repeated dispossession

Use confidence as a temporary modifier, separate from morale.

---

# 17. Fatigue model

Fatigue must be one of the most important systems.

## Fatigue affects

* sprint frequency
* acceleration
* recovery speed
* duel strength retention
* concentration
* technique execution
* off-ball movement quality
* late-game injury risk

## Fatigue accumulation drivers

* pressing intensity
* total distance
* number of sprints
* repeated transitions
* weather
* stamina
* natural fitness

## Simple model

```text
FatigueGainPerTick =
  movementLoad
  + sprintLoad
  + pressingLoad
  + duelLoad
  - recoveryFactor
```

Then convert fatigue to performance penalties nonlinearly:

* 0–30: small
* 30–60: noticeable
* 60–80: strong
* 80+: severe collapse

Late-match realism comes from this curve.

---

# 18. Tactical identity examples

These profiles should genuinely feel different.

## 18.1 High-possession 4-3-3

* short support distances
* frequent recycling
* high central overload
* wide wingers pin line
* fullbacks overlap
* lower long-shot rate
* more cutbacks and through balls
* higher counterpress

## 18.2 Direct 4-4-2

* faster vertical progression
* more early crosses
* more second-ball duels
* lower central combination frequency
* deeper midfield support
* more target-man layoff patterns

## 18.3 Low-block 5-4-1

* deep line
* narrow lanes
* low pressing
* high block probability
* low possession retention
* stronger counter transition bias

## 18.4 Gegenpress 4-2-3-1

* high turnovers in advanced areas
* rapid fatigue burn
* more chaotic shot volume
* more fouls/cards
* strong first 60–70 minutes if fit

---

# 19. Manager instructions and in-match adaptation

The engine must let managers modify macro behavior dynamically.

## Triggers for auto-adjustment

* scoreline
* red card
* fatigue thresholds
* momentum collapse
* dominant flank exploitation
* weak fullback being targeted

## Example tactical changes

At 75+ minutes while leading:

* lower tempo
* reduce risk passing
* slightly lower defensive line
* more time management
* narrower shape
* more clearances from danger

At 80+ minutes trailing:

* raise mentality
* add box presence
* increase directness
* increase shot volume tolerance
* more overlap and crossing
* higher press risk

---

# 20. Substitution logic

Substitutions should not be random freshness swaps.

They should answer:

* is fatigue causing tactical failure?
* is a role underperforming?
* is there a mismatch exploit?
* do we need more height, pace, control, or defense?

## Sub agent priorities

* tired fullbacks in high-intensity systems
* booked defenders under pressure
* isolated striker in low-possession systems
* AM/winger for creativity if chasing
* DM/CB if protecting result
* target man if going direct late

---

# 21. Set pieces

Do not leave this abstract. European-style realism requires serious set-piece modeling.

## Corners

Variables:

* delivery quality
* inswing/outswing
* near-post/far-post/crowd keeper
* blockers
* aerial dominance
* zonal vs man marking
* second-ball setup

## Free kicks

* shooting chance
* crossing chance
* disguised pass chance
* wall quality
* keeper wall setup

## Penalties

Use:

* finishing or penalty-specific stat if you include it
* composure
* technique
* goalkeeper penalty read
* pressure importance
* confidence state

Set pieces should account for around realistic scoring share.

---

# 22. Fouls and cards

Must be contextual.

## Foul probability depends on

* aggression
* tackling
* decisions
* fatigue
* pressure situation
* referee strictness
* transition danger
* positioning error recovery

## Card probability depends on

* foul severity
* denial of promising attack
* DOGSO
* repeat offender tendency
* referee strictness
* current card status

Players on yellow should defend more cautiously unless aggression overrides.

---

# 23. Calibration targets for realism

You need target distributions. Without calibration the engine will drift into nonsense.

For a realistic top-level European match, rough averages:

* total shots: 18–28
* shots on target: 6–10
* possession split usually 42–58, extreme styles beyond that
* pass accuracy: 76–91 depending on style and level
* xG total: 1.8–3.2
* fouls: 18–30
* yellow cards: 2–6
* reds: rare
* corners: 7–13
* offsides: 1–5
* crosses attempted: style dependent
* goals: typically 2–3 total average across many matches

Lower leagues should have:

* more technical errors
* lower pass completion
* more transitions
* weaker line coordination
* more ugly clearances
* more variance

---

# 24. RNG design

Randomness must be **bounded and contextual**, never dominant.

Use three layers:

## Micro noise

Tiny variance on each action

## Style variance

Some tactical personalities naturally create volatility

## Match variance

Rare unusual swings, referee weirdness, wondergoals, etc.

The mistake is using raw RNG directly.
Use:

```text
effectiveValue = deterministicCore * (1 + boundedNoise)
```

Where boundedNoise is typically narrow, like ±3% to ±12% depending on action chaos.

More chaotic actions get wider variance:

* speculative through balls
* long shots
* aerial scrambles
* rebounds

Less chaotic actions get narrow variance:

* simple short passes
* goalkeeper collecting easy balls
* uncontested recycling

---

# 25. Full action selection model

For each on-ball player, generate candidate actions with scores.

## Example candidates for a CM in progression

* safe short pass
* switch wide
* line-break pass
* carry forward
* dribble evade
* lofted pass to runner
* recycle backward
* shot from distance

For each action:

```text
CandidateScore =
  BaseRoleBias
+ TacticalInstructionFit
+ VisibleOpportunity
+ PlayerPreference
+ MatchContextBias
+ ConfidenceBias
- RiskPenalty
```

Then softmax sample rather than always taking highest score.

This prevents robotic play.

---

# 26. Example formulas

## 26.1 Pass vision / ambitious pass detection

```text
PassOpportunityScore =
  0.30 * vision
+ 0.20 * decisions
+ 0.15 * anticipation
+ 0.10 * composure
+ 0.10 * flair
+ 0.15 * tacticalFreedom
```

## 26.2 Pass execution

```text
PassExecutionScore =
  0.35 * passing
+ 0.20 * technique
+ 0.15 * composure
+ 0.10 * balance
+ 0.10 * weakFootAdjusted
+ 0.10 * firstTouchState
```

Then divide by:

* pressure factor
* distance factor
* lane congestion
* receiver markedness

---

## 26.3 Ground duel

```text
BallWinScore =
  0.25 * strength
+ 0.20 * balance
+ 0.15 * aggression
+ 0.15 * tackling_or_dribbling
+ 0.10 * acceleration
+ 0.10 * anticipation
+ 0.05 * morale
```

Apply:

* fatigue penalty
* body orientation
* support presence
* referee caution if tackling

---

## 26.4 Interception

```text
InterceptionScore =
  0.30 * anticipation
+ 0.25 * positioning
+ 0.15 * concentration
+ 0.10 * acceleration
+ 0.10 * teamwork
+ 0.10 * defensiveShapeSupport
```

---

## 26.5 Shot on target probability

```text
SOTScore =
  0.30 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * firstTouch
+ 0.10 * decisions
+ 0.05 * shootingPower
+ 0.10 * confidence
```

Apply:

* angle
* distance
* pressure
* weak foot
* fatigue
* aerial/body-balance context

---

## 26.6 Goal conversion after shot on target

```text
GoalScore =
  ShotPlacementQuality
  * PowerAppropriateness
  * KeeperBeatenFactor
  * ScreenedVisionFactor
  * PostShotLuckBounded
```

KeeperBeatenFactor uses:

* reflexes
* positioning
* reach
* one-on-ones
* handling/parry profile

---

# 27. Realistic emergent patterns you want

If the engine is correct, these should emerge naturally:

* tired fullbacks get beaten late
* high lines get punished by elite timing and passing
* low blocks concede territory but block central shots
* creative midfielders generate fewer but better chances
* physical strikers dominate weak CBs in direct systems
* strong pressing sides start sharp and fade if not rotated
* morale collapse after error can produce shaky 10-minute spells
* top keepers steal points
* lower-quality leagues have more chaos and broken possessions

---

# 28. Implementation architecture

## Layer A: Data

* players
* teams
* tactics
* match context
* role templates
* event templates

## Layer B: State

* current player states
* fatigue
* confidence
* position zone
* ball zone
* possession owner
* event history

## Layer C: Decision systems

* team intent
* player action generation
* off-ball movement
* defensive reaction

## Layer D: Resolution systems

* pass
* dribble
* duel
* shot
* foul
* set piece
* goalkeeper action

## Layer E: Tuning/calibration

* league modifiers
* competition modifiers
* pace of game
* chance quality
* error rate
* refereeing style

---

# 29. Recommended agent breakdown for development

Use multiple build agents with strict ownership.

## Agent 1 — Tactical Identity Agent

Build:

* formations
* role maps
* phase instructions
* line behavior
* pressing behavior

Output:

* team shape rules
* role behavior matrices

## Agent 2 — Spatial Simulation Agent

Build:

* zone grid
* player zone transitions
* compactness and spacing
* support and overload detection

Output:

* movement and occupation system

## Agent 3 — Player Decision Agent

Build:

* candidate action generation
* utility scoring
* softmax action choice
* role and trait biases

Output:

* action selection engine

## Agent 4 — Duel and Defensive Agent

Build:

* tackles
* interceptions
* aerial duels
* loose balls
* shielding
* fouls/cards

Output:

* ball contest engine

## Agent 5 — Chance Creation Agent

Build:

* through balls
* crossing
* cutbacks
* dribbles
* combination play
* transition chance logic

Output:

* final-third creation engine

## Agent 6 — Shot and Goalkeeper Agent

Build:

* shot types
* pressure models
* shot quality
* save logic
* rebound logic

Output:

* scoring engine

## Agent 7 — Human Factors Agent

Build:

* morale
* confidence
* fatigue
* momentum
* discipline psychology

Output:

* player state modifier system

## Agent 8 — Match Adaptation Agent

Build:

* in-game tactical drift
* score effects
* time effects
* substitutions
* red card reshaping

Output:

* dynamic match management system

## Agent 9 — Set Piece Agent

Build:

* corners
* free kicks
* penalties
* throw-ins in dangerous areas

Output:

* dead-ball engine

## Agent 10 — Calibration Agent

Build:

* statistical target matching
* league style profiles
* variance boundaries
* realism testing harness

Output:

* stable realistic tuning

---

# 30. Development order

Correct order matters.

## Phase 1

Build:

* data schema
* attributes
* tactics schema
* 30-zone pitch model
* possession state machine

## Phase 2

Build:

* player action generation
* pass/dribble/duel resolution
* off-ball movement basics

## Phase 3

Build:

* shot engine
* goalkeeping
* set pieces
* offside trap logic

## Phase 4

Build:

* morale/fatigue/confidence
* tactical adaptation
* substitutions
* referee/cards

## Phase 5

Build:

* league-level tuning
* thousands of automated simulation tests
* match report and analytics layer

---

# 31. Match report outputs

To tune realism, the engine must expose internal stats.

Track:

* possession
* territory
* passes by lane and depth
* line breaks
* progressive carries
* turnovers by zone
* press regains
* duel win rates
* xG
* shot map
* crossing success
* offside triggers
* set-piece xG
* fatigue curves
* confidence shifts

Without this, tuning becomes blind.

---

# 32. Pseudocode skeleton

```ts
while (matchClock < finalWhistle) {
  updateContext()
  updateFatigueAndConfidence()
  updateTeamIntent(teamA)
  updateTeamIntent(teamB)
  updatePlayerPositions()

  if (deadBallState) {
    resolveSetPieceOrRestart()
    continue
  }

  phase = determinePossessionPhase()
  actor = determineBallActor()

  candidates = generateActionCandidates(actor, phase, context)
  scoredCandidates = scoreCandidates(candidates, actor, context)
  chosenAction = sampleAction(scoredCandidates)

  result = resolveAction(chosenAction, actor, opponents, context)

  applyResult(result)
  resolveAftermath(result)

  if (needsTacticalAdaptation()) {
    adaptTactics()
  }

  if (needsSubstitutionDecision()) {
    resolveSubstitutionChoice()
  }

  advanceClock()
}
```

---

# 33. Non-negotiable realism rules

These are mandatory if you want the engine to feel European and credible.

1. **Shape beats isolated attributes**

   * good structure makes average players look better

2. **Decision quality must be separate from execution quality**

   * vision is not passing
   * positioning is not pace
   * composure is not finishing

3. **Fatigue must distort both body and mind**

   * not just speed

4. **Defending must mostly be prevention, not tackle spam**

5. **Chance quality matters more than shot count**

   * many weak shooters should not inflate goals unrealistically

6. **High-risk tactics must create volatility**

   * more transitions, more cards, more fatigue, more swings

7. **Elite players must create edge in narrow margins**

   * better timing, better choices, fewer mistakes

8. **RNG must decorate the simulation, not run it**

---

# 34. Closest-to-full-engine compact blueprint

This is the final condensed structure.

## Inputs

* formations
* tactical sliders
* roles
* player attributes
* morale/fatigue/sharpness
* match context

## Core loop

* update shape
* determine phase
* pick actor
* generate choices
* choose action via weighted utility
* resolve execution vs resistance
* update state
* trigger aftermath events

## Resolution families

* pass
* carry
* dribble
* duel
* interception
* cross
* through ball
* shot
* save
* rebound
* foul/card
* offside
* set piece

## Modifier families

* morale
* confidence
* fatigue
* momentum
* home advantage
* weather
* referee style
* tactical familiarity

## Tactical expression

* possession systems
* direct systems
* pressing systems
* low blocks
* transitional systems
* asymmetric flank attacks

## Calibration

* realistic league averages
* realistic event distributions
* realistic player impact
* bounded variance

---

# 35. Direct answer to your examples

## Offside trigger

Correct approach:

```text
OffsideChance =
  f(
    defensive line sync,
    offside trap setting,
    defender positioning,
    defender concentration,
    passer vision/decisions,
    runner off-ball/anticipation,
    pressure on passer,
    fatigue,
    tiny bounded rng
  )
```

## Scoring goals

Correct approach:

```text
GoalProbability =
  f(
    chance quality,
    finishing,
    composure,
    technique,
    shooting power when relevant,
    distance,
    angle,
    pressure,
    weak foot/body shape,
    keeper quality,
    block pressure,
    bounded rng
  )
```

## Disputing balls

Correct approach:

```text
DuelWinProbability =
  f(
    strength,
    balance,
    aggression,
    tackling or dribbling,
    anticipation,
    acceleration,
    body orientation,
    support presence,
    fatigue,
    morale,
    bounded rng
  )
```

## Vision / creative passes

Correct approach:

```text
CreativePassEvent =
  action availability from vision + decisions + tactical freedom
  then execution from passing + technique + composure
  then disruption from defensive spacing + pressure + anticipation
```

That separation is the key.

---

# 36. Final build standard

If you want the engine to feel like realistic European football, target this identity:

* slower than arcade
* structured phases
* tactical asymmetry
* fewer clean actions under pressure
* many possessions die from spacing and pressure
* elite players distort the match through timing and decisions
* late-game fatigue changes everything
* scorelines emerge from process, not canned scripts

This is the correct foundation for a near-full soccer manager match engine.
Below is a full agent-based plan for a soccer manager match engine that is close to implementation level rather than a vague design brief.

## 1. Engine target

You want a **manager simulation engine**, not a manual-control physics game.

That means:

* realism over spectacle
* tactical identity matters
* player quality matters
* morale, fatigue, and match context matter
* randomness exists but is constrained
* results emerge from many weighted micro-events, not scripted scorelines

The correct model is:

1. **Pre-match tactical model**
2. **Continuous possession-state simulation**
3. **Contextual event resolution**
4. **Post-event state updates**
5. **Manager adaptation layer**
6. **Substitution/instruction layer**
7. **Outcome calibration layer**

---

# 2. Core philosophy

Do **not** simulate the match as “team rating A vs team rating B”.

Simulate it as:

* where the ball is
* who is near the ball
* what both teams are trying to do
* what options the player sees
* whether the player can execute
* whether opponents disrupt it
* how fatigue, morale, pressure, and shape distort decisions

So the engine should be driven by:

* **team agents**
* **unit agents** (defense, midfield, attack)
* **player agents**
* **ball state**
* **match context**

---

# 3. Simulation resolution

Use a **hybrid tick + event model**.

## Recommended match clock

* match duration: 90 + stoppage
* internal simulation step: **0.5s to 1.0s**
* possession decision window: every **1–3 seconds**
* major event resolution: immediate, event-driven

This avoids brute-force physics while still feeling alive.

## Why hybrid is better

Pure per-second simulation becomes noisy and expensive.
Pure event-only simulation becomes fake and detached from tactics.

Hybrid gives:

* shape movement
* spacing logic
* pressing windows
* duel frequency
* event outcomes tied to positioning

---

# 4. Data model

## 4.1 Team tactical profile

Each team needs a tactical object:

```ts
TeamTactics {
  formation: "4-3-3" | "4-2-3-1" | ...
  mentality: 0..100            // defensive to ultra attacking
  tempo: 0..100
  width: 0..100
  defensiveLine: 0..100
  lineOfEngagement: 0..100
  pressingIntensity: 0..100
  counterPress: 0..100
  directness: 0..100
  buildupRisk: 0..100
  overlapLeft: 0..100
  overlapRight: 0..100
  underlapLeft: 0..100
  underlapRight: 0..100
  offsideTrap: 0..100
  timeWasting: 0..100
  creativeFreedom: 0..100
  crossingFrequency: 0..100
  shootOnSight: 0..100
  workBallIntoBox: 0..100
  transitionAfterWin: "counter" | "hold" | "balanced"
  transitionAfterLoss: "counterpress" | "regroup" | "balanced"
  setPieceProfiles: ...
}
```

---

## 4.2 Player attributes

You need attribute groups, not random single stats.

## Technical

* first touch
* passing
* short passing
* long passing
* crossing
* dribbling
* finishing
* heading
* shooting power
* technique
* tackling
* marking

## Mental

* decisions
* anticipation
* composure
* vision
* positioning
* off the ball
* teamwork
* aggression
* concentration
* flair
* bravery
* work rate
* leadership

## Physical

* acceleration
* pace
* agility
* balance
* strength
* stamina
* jumping reach
* natural fitness

## Goalkeeper

* reflexes
* handling
* one-on-ones
* aerial reach
* command of area
* rushing out
* kicking
* throwing
* positioning
* communication

---

## 4.3 Hidden/context variables

These matter as much as raw attributes.

* morale: 0..100
* fatigue: 0..100
* sharpness/match fitness: 0..100
* consistency
* big match temperament
* injury risk
* weak foot quality
* role familiarity
* tactical familiarity
* chemistry links with nearby teammates
* discipline
* current confidence
* frustration
* momentum sensitivity

---

## 4.4 Match context

```ts
MatchContext {
  minute
  stoppageTime
  homeAdvantage
  weather
  pitchCondition
  refereeStrictness
  scoreDifference
  competitionImportance
  cardStatus
  substitutionsUsed
  momentum
  crowdPressure
}
```

---

# 5. Spatial model

Do not use only abstract possession zones. That is too crude.

Use a **simplified pitch grid**.

## Recommended grid

* length split into 6 bands:

  1. own box
  2. own defensive third
  3. own half central progression
  4. attacking half progression
  5. final third
  6. opposition box

* width split into 5 lanes:

  * far left wing
  * left half-space
  * center
  * right half-space
  * far right wing

Total: **30 zones**

This is enough for:

* overloads
* switches
* central congestion
* wing play
* cutbacks
* pressing traps
* offside line behavior

Each player has:

* base tactical zone map by formation/role
* dynamic zone offset by phase
* dynamic movement preference by ball location

---

# 6. Agents

This is the main structure.

## 6.1 Match Director Agent

Controls:

* current possession
* phase changes
* event queue
* clock
* momentum state
* tactical instruction updates

## 6.2 Team Intent Agent

For each team:

* determines attacking intent
* determines defensive shape
* modifies risk by score/minute/morale/fatigue

## 6.3 Unit Agents

Per team:

* defensive unit
* midfield unit
* attacking unit

They control:

* line compactness
* support distances
* pressing depth
* spacing discipline
* recovery speed

## 6.4 Player Decision Agent

For the player on the ball:

* evaluate candidate actions
* assign utility
* choose action probabilistically
* execute with attribute-weighted success

## 6.5 Off-ball Movement Agent

For surrounding players:

* offer support
* attack depth
* hold shape
* make underlap/overlap/run beyond
* cover passing lanes
* track runners

## 6.6 Duel Resolution Agent

Handles:

* shoulder duels
* headers
* interceptions
* tackles
* loose balls
* keeper duels

## 6.7 Shot Resolution Agent

Handles:

* shot selection
* shot quality
* body part
* pressure
* block chance
* save chance
* rebound

## 6.8 Discipline Agent

Handles:

* foul chance
* booking chance
* second-yellow caution bias
* referee style

## 6.9 Adaptation Agent

Handles:

* game state tactical drift
* confidence effects
* panic late on
* low-block preservation
* substitutions and instruction reactions

---

# 7. Match phases

Each possession should be in one of these phases:

1. **build-up**
2. **progression**
3. **final-third circulation**
4. **chance creation**
5. **shot/recovery duel**
6. **transition attack**
7. **transition defense**
8. **set piece**
9. **dead time**

This is essential because action weights must depend on phase.

Example:
A CB in build-up should heavily prefer:

* short pass
* switch
* carry

That same CB in a chaotic transition should heavily prefer:

* clearance
* safe vertical release
* emergency tackle

---

# 8. Team shape and role logic

Formation alone is meaningless unless linked to behavior.

A 4-3-3 high press and a 4-3-3 mid-block must play differently.

Each role needs:

* anchor zone
* phase behavior
* support radius
* risk preference
* movement triggers

Example role profile:

```ts
RoleProfile {
  name: "Inside Forward Attack"
  baseZones: [...]
  attackingRunBias: 0..100
  widthRetention: 0..100
  dribbleBias: 0..100
  cutInsideBias: 0..100
  crossingBias: 0..100
  shotBias: 0..100
  pressBias: 0..100
  trackBackBias: 0..100
}
```

---

# 9. Core event flow

Each tick or decision cycle:

1. update fatigue/morale/momentum drift
2. update player positions relative to ball and tactics
3. determine possession phase
4. choose acting player
5. generate action candidates
6. compute action scores
7. sample chosen action
8. resolve execution
9. resolve opponent reaction
10. update ball location and match state
11. check event aftermath:

* foul
* corner
* throw
* offside
* shot
* rebound
* injury
* card

---

# 10. Decision model

Every action should use:

## Utility score

How attractive the action looks to the player

## Execution score

How likely the player is to pull it off

## Opposition resistance

How likely opponents disrupt it

## Controlled RNG

Final weighted uncertainty

Formula:

```text
ActionFinalScore =
  UtilityWeight * TacticalFit *
  PlayerReadOfGame *
  ContextModifier *
  RandomNoise
```

Then if selected:

```text
ActionSuccessProbability =
  ExecutionSkill *
  PhysicalCondition *
  Composure *
  RoleFamiliarity *
  SupportStructure
  /
  DefensiveResistance
```

---

# 11. Candidate actions by phase

## Build-up

* short pass
* medium pass
* switch
* carry forward
* reset to keeper
* long direct pass
* risky line-break pass
* clearance under pressure

## Progression

* vertical pass
* diagonal pass
* dribble carry
* overlap release
* switch flank
* long ball behind line

## Final third

* through ball
* cross
* cutback
* combination pass
* dribble take-on
* recycle possession
* shot from distance

## Box actions

* near-post shot
* far-post shot
* low driven shot
* finesse shot
* header
* layoff
* penalty-box dribble
* square pass

## Defensive actions

* jockey
* press
* tackle
* stand off
* cover lane
* intercept
* foul cynically
* clear

---

# 12. Attribute influence map

This is where realism comes from.

## Passing

Use:

* passing
* technique
* vision
* decisions
* composure
* weak foot
* pressure resistance
* fatigue
* receiving target movement
* lane congestion

## Through balls / “crazy passes”

Use:

* vision heavily
* technique heavily
* decisions heavily
* passing heavily
* flair moderately
* composure moderately
* teammate off-the-ball movement
* opponent line height
* compactness of defense
* pressure on passer

A high-vision player should **attempt** and **see** passes others do not.
A high-passing player should **execute** them better.
A high-decisions player should **choose** them at better moments.
A high-flair player should attempt rarer actions more often.

That distinction matters.

---

## Finishing

Use:

* finishing
* composure
* technique
* weak foot
* body balance
* pressure level
* angle
* distance
* goalkeeper position
* defender closing speed

## Long shots

Use:

* shooting power
* technique
* long shot trait if you include traits
* composure
* decision making
* fatigue
* distance
* defensive pressure
* keeper positioning

## Headers

Use:

* heading
* jumping reach
* strength
* bravery
* positioning/off the ball
* cross quality
* marker pressure

## Duels

Ground duel:

* strength
* balance
* aggression
* tackling or dribbling depending on role
* pace/acceleration in recovery angle
* fatigue

Aerial duel:

* jumping reach
* strength
* heading
* bravery
* positioning

## Interceptions

Use:

* anticipation
* positioning
* concentration
* acceleration
* reach to lane
* line compactness

## Offside trap

Use:

* team offside trap setting
* backline cohesion
* concentration
* positioning
* anticipation
* communication
* fatigue
* opponent timing/off the ball

---

# 13. Proper offside simulation

Your example is correct but incomplete.

Do not do:

```text
offside = rng + positioning
```

Do:

## Offside event model

When an attacker attempts a run behind a line:

1. calculate **run timing quality**

   * attacker anticipation
   * off the ball
   * decisions
   * composure
   * fatigue penalty

2. calculate **defensive line synchronization**

   * average of back line positioning
   * concentration
   * teamwork
   * communication
   * offside trap instruction
   * fatigue penalty
   * morale/confidence modifier

3. calculate **pass release timing**

   * passer vision
   * decisions
   * technique
   * composure
   * pressure penalty

4. calculate **assistant/ref margin noise**

   * very small bounded random term

Then:

```text
OffsideMargin =
  defensiveStepTiming
  - attackerRunTiming
  - passerReleasePrecision
  + tinyNoise
```

If margin exceeds threshold, offside.

This creates realistic behavior:

* disciplined elite teams catch runs more often
* tired defenses mistime step-ups
* clever forwards bend and delay runs better
* elite playmakers release at the right instant

---

# 14. Goal scoring model

Goals should not come from a single shot roll. They must come from layered resolution.

## Layer 1: Can the shooter get the shot off?

Depends on:

* first touch
* composure
* balance
* pressure
* body orientation
* nearest defender distance
* support of shooting lane

## Layer 2: Shot quality generation

Produces:

* contact quality
* trajectory intent
* shot type
* placement vs power tradeoff

## Layer 3: Defensive interference

* block chance
* deflection chance
* partial block

## Layer 4: Keeper response

* reaction
* positioning
* handling/parry tendencies
* one-on-one quality
* sightline obstruction

## Layer 5: Rebound outcome

* who attacks second ball
* reflex finish chance
* scramble

---

## Sample shot quality formula

```text
BaseShotScore =
  0.25 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * shootingPower
+ 0.10 * balance
+ 0.10 * firstTouch
+ 0.10 * decisions
```

Apply modifiers:

```text
ShotScoreAdjusted =
  BaseShotScore
  * AngleModifier
  * DistanceModifier
  * PressureModifier
  * BodyPartModifier
  * WeakFootModifier
  * FatigueModifier
  * MoraleConfidenceModifier
```

For long-range shots, increase weight of:

* shooting power
* technique
* decisions

For tap-ins, increase weight of:

* composure
* positioning
* first touch

---

# 15. Defensive realism

Defending cannot be reduced to “tackle chance”.

Defending is mostly:

* delay
* channeling
* screening
* line control
* compactness
* denying good shots
* winning second balls

So create defensive contributions that do not always create visible stats.

## Defensive metrics driving the engine

* line compactness
* horizontal compactness
* vertical compactness
* pressure arrival time
* cover shadow quality
* lane denial score
* recovery run speed
* box occupation
* marking tightness

These should shape the opponent’s success rates even without direct tackles.

---

# 16. Morale, confidence, and momentum

These should alter behavior, not just ratings.

## Morale effects

High morale:

* better decisions
* more proactive movement
* slightly more technical execution
* more willingness to risk creative actions

Low morale:

* conservative choices
* heavy first touch errors
* delayed reactions
* worse composure
* more collapse after setbacks

## Confidence effects during match

Confidence rises after:

* successful dribbles
* key passes
* goals
* several completed actions
* keeper saves

Confidence falls after:

* missed sitter
* error leading to chance
* card
* repeated dispossession

Use confidence as a temporary modifier, separate from morale.

---

# 17. Fatigue model

Fatigue must be one of the most important systems.

## Fatigue affects

* sprint frequency
* acceleration
* recovery speed
* duel strength retention
* concentration
* technique execution
* off-ball movement quality
* late-game injury risk

## Fatigue accumulation drivers

* pressing intensity
* total distance
* number of sprints
* repeated transitions
* weather
* stamina
* natural fitness

## Simple model

```text
FatigueGainPerTick =
  movementLoad
  + sprintLoad
  + pressingLoad
  + duelLoad
  - recoveryFactor
```

Then convert fatigue to performance penalties nonlinearly:

* 0–30: small
* 30–60: noticeable
* 60–80: strong
* 80+: severe collapse

Late-match realism comes from this curve.

---

# 18. Tactical identity examples

These profiles should genuinely feel different.

## 18.1 High-possession 4-3-3

* short support distances
* frequent recycling
* high central overload
* wide wingers pin line
* fullbacks overlap
* lower long-shot rate
* more cutbacks and through balls
* higher counterpress

## 18.2 Direct 4-4-2

* faster vertical progression
* more early crosses
* more second-ball duels
* lower central combination frequency
* deeper midfield support
* more target-man layoff patterns

## 18.3 Low-block 5-4-1

* deep line
* narrow lanes
* low pressing
* high block probability
* low possession retention
* stronger counter transition bias

## 18.4 Gegenpress 4-2-3-1

* high turnovers in advanced areas
* rapid fatigue burn
* more chaotic shot volume
* more fouls/cards
* strong first 60–70 minutes if fit

---

# 19. Manager instructions and in-match adaptation

The engine must let managers modify macro behavior dynamically.

## Triggers for auto-adjustment

* scoreline
* red card
* fatigue thresholds
* momentum collapse
* dominant flank exploitation
* weak fullback being targeted

## Example tactical changes

At 75+ minutes while leading:

* lower tempo
* reduce risk passing
* slightly lower defensive line
* more time management
* narrower shape
* more clearances from danger

At 80+ minutes trailing:

* raise mentality
* add box presence
* increase directness
* increase shot volume tolerance
* more overlap and crossing
* higher press risk

---

# 20. Substitution logic

Substitutions should not be random freshness swaps.

They should answer:

* is fatigue causing tactical failure?
* is a role underperforming?
* is there a mismatch exploit?
* do we need more height, pace, control, or defense?

## Sub agent priorities

* tired fullbacks in high-intensity systems
* booked defenders under pressure
* isolated striker in low-possession systems
* AM/winger for creativity if chasing
* DM/CB if protecting result
* target man if going direct late

---

# 21. Set pieces

Do not leave this abstract. European-style realism requires serious set-piece modeling.

## Corners

Variables:

* delivery quality
* inswing/outswing
* near-post/far-post/crowd keeper
* blockers
* aerial dominance
* zonal vs man marking
* second-ball setup

## Free kicks

* shooting chance
* crossing chance
* disguised pass chance
* wall quality
* keeper wall setup

## Penalties

Use:

* finishing or penalty-specific stat if you include it
* composure
* technique
* goalkeeper penalty read
* pressure importance
* confidence state

Set pieces should account for around realistic scoring share.

---

# 22. Fouls and cards

Must be contextual.

## Foul probability depends on

* aggression
* tackling
* decisions
* fatigue
* pressure situation
* referee strictness
* transition danger
* positioning error recovery

## Card probability depends on

* foul severity
* denial of promising attack
* DOGSO
* repeat offender tendency
* referee strictness
* current card status

Players on yellow should defend more cautiously unless aggression overrides.

---

# 23. Calibration targets for realism

You need target distributions. Without calibration the engine will drift into nonsense.

For a realistic top-level European match, rough averages:

* total shots: 18–28
* shots on target: 6–10
* possession split usually 42–58, extreme styles beyond that
* pass accuracy: 76–91 depending on style and level
* xG total: 1.8–3.2
* fouls: 18–30
* yellow cards: 2–6
* reds: rare
* corners: 7–13
* offsides: 1–5
* crosses attempted: style dependent
* goals: typically 2–3 total average across many matches

Lower leagues should have:

* more technical errors
* lower pass completion
* more transitions
* weaker line coordination
* more ugly clearances
* more variance

---

# 24. RNG design

Randomness must be **bounded and contextual**, never dominant.

Use three layers:

## Micro noise

Tiny variance on each action

## Style variance

Some tactical personalities naturally create volatility

## Match variance

Rare unusual swings, referee weirdness, wondergoals, etc.

The mistake is using raw RNG directly.
Use:

```text
effectiveValue = deterministicCore * (1 + boundedNoise)
```

Where boundedNoise is typically narrow, like ±3% to ±12% depending on action chaos.

More chaotic actions get wider variance:

* speculative through balls
* long shots
* aerial scrambles
* rebounds

Less chaotic actions get narrow variance:

* simple short passes
* goalkeeper collecting easy balls
* uncontested recycling

---

# 25. Full action selection model

For each on-ball player, generate candidate actions with scores.

## Example candidates for a CM in progression

* safe short pass
* switch wide
* line-break pass
* carry forward
* dribble evade
* lofted pass to runner
* recycle backward
* shot from distance

For each action:

```text
CandidateScore =
  BaseRoleBias
+ TacticalInstructionFit
+ VisibleOpportunity
+ PlayerPreference
+ MatchContextBias
+ ConfidenceBias
- RiskPenalty
```

Then softmax sample rather than always taking highest score.

This prevents robotic play.

---

# 26. Example formulas

## 26.1 Pass vision / ambitious pass detection

```text
PassOpportunityScore =
  0.30 * vision
+ 0.20 * decisions
+ 0.15 * anticipation
+ 0.10 * composure
+ 0.10 * flair
+ 0.15 * tacticalFreedom
```

## 26.2 Pass execution

```text
PassExecutionScore =
  0.35 * passing
+ 0.20 * technique
+ 0.15 * composure
+ 0.10 * balance
+ 0.10 * weakFootAdjusted
+ 0.10 * firstTouchState
```

Then divide by:

* pressure factor
* distance factor
* lane congestion
* receiver markedness

---

## 26.3 Ground duel

```text
BallWinScore =
  0.25 * strength
+ 0.20 * balance
+ 0.15 * aggression
+ 0.15 * tackling_or_dribbling
+ 0.10 * acceleration
+ 0.10 * anticipation
+ 0.05 * morale
```

Apply:

* fatigue penalty
* body orientation
* support presence
* referee caution if tackling

---

## 26.4 Interception

```text
InterceptionScore =
  0.30 * anticipation
+ 0.25 * positioning
+ 0.15 * concentration
+ 0.10 * acceleration
+ 0.10 * teamwork
+ 0.10 * defensiveShapeSupport
```

---

## 26.5 Shot on target probability

```text
SOTScore =
  0.30 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * firstTouch
+ 0.10 * decisions
+ 0.05 * shootingPower
+ 0.10 * confidence
```

Apply:

* angle
* distance
* pressure
* weak foot
* fatigue
* aerial/body-balance context

---

## 26.6 Goal conversion after shot on target

```text
GoalScore =
  ShotPlacementQuality
  * PowerAppropriateness
  * KeeperBeatenFactor
  * ScreenedVisionFactor
  * PostShotLuckBounded
```

KeeperBeatenFactor uses:

* reflexes
* positioning
* reach
* one-on-ones
* handling/parry profile

---

# 27. Realistic emergent patterns you want

If the engine is correct, these should emerge naturally:

* tired fullbacks get beaten late
* high lines get punished by elite timing and passing
* low blocks concede territory but block central shots
* creative midfielders generate fewer but better chances
* physical strikers dominate weak CBs in direct systems
* strong pressing sides start sharp and fade if not rotated
* morale collapse after error can produce shaky 10-minute spells
* top keepers steal points
* lower-quality leagues have more chaos and broken possessions

---

# 28. Implementation architecture

## Layer A: Data

* players
* teams
* tactics
* match context
* role templates
* event templates

## Layer B: State

* current player states
* fatigue
* confidence
* position zone
* ball zone
* possession owner
* event history

## Layer C: Decision systems

* team intent
* player action generation
* off-ball movement
* defensive reaction

## Layer D: Resolution systems

* pass
* dribble
* duel
* shot
* foul
* set piece
* goalkeeper action

## Layer E: Tuning/calibration

* league modifiers
* competition modifiers
* pace of game
* chance quality
* error rate
* refereeing style

---

# 29. Recommended agent breakdown for development

Use multiple build agents with strict ownership.

## Agent 1 — Tactical Identity Agent

Build:

* formations
* role maps
* phase instructions
* line behavior
* pressing behavior

Output:

* team shape rules
* role behavior matrices

## Agent 2 — Spatial Simulation Agent

Build:

* zone grid
* player zone transitions
* compactness and spacing
* support and overload detection

Output:

* movement and occupation system

## Agent 3 — Player Decision Agent

Build:

* candidate action generation
* utility scoring
* softmax action choice
* role and trait biases

Output:

* action selection engine

## Agent 4 — Duel and Defensive Agent

Build:

* tackles
* interceptions
* aerial duels
* loose balls
* shielding
* fouls/cards

Output:

* ball contest engine

## Agent 5 — Chance Creation Agent

Build:

* through balls
* crossing
* cutbacks
* dribbles
* combination play
* transition chance logic

Output:

* final-third creation engine

## Agent 6 — Shot and Goalkeeper Agent

Build:

* shot types
* pressure models
* shot quality
* save logic
* rebound logic

Output:

* scoring engine

## Agent 7 — Human Factors Agent

Build:

* morale
* confidence
* fatigue
* momentum
* discipline psychology

Output:

* player state modifier system

## Agent 8 — Match Adaptation Agent

Build:

* in-game tactical drift
* score effects
* time effects
* substitutions
* red card reshaping

Output:

* dynamic match management system

## Agent 9 — Set Piece Agent

Build:

* corners
* free kicks
* penalties
* throw-ins in dangerous areas

Output:

* dead-ball engine

## Agent 10 — Calibration Agent

Build:

* statistical target matching
* league style profiles
* variance boundaries
* realism testing harness

Output:

* stable realistic tuning

---

# 30. Development order

Correct order matters.

## Phase 1

Build:

* data schema
* attributes
* tactics schema
* 30-zone pitch model
* possession state machine

## Phase 2

Build:

* player action generation
* pass/dribble/duel resolution
* off-ball movement basics

## Phase 3

Build:

* shot engine
* goalkeeping
* set pieces
* offside trap logic

## Phase 4

Build:

* morale/fatigue/confidence
* tactical adaptation
* substitutions
* referee/cards

## Phase 5

Build:

* league-level tuning
* thousands of automated simulation tests
* match report and analytics layer

---

# 31. Match report outputs

To tune realism, the engine must expose internal stats.

Track:

* possession
* territory
* passes by lane and depth
* line breaks
* progressive carries
* turnovers by zone
* press regains
* duel win rates
* xG
* shot map
* crossing success
* offside triggers
* set-piece xG
* fatigue curves
* confidence shifts

Without this, tuning becomes blind.

---

# 32. Pseudocode skeleton

```ts
while (matchClock < finalWhistle) {
  updateContext()
  updateFatigueAndConfidence()
  updateTeamIntent(teamA)
  updateTeamIntent(teamB)
  updatePlayerPositions()

  if (deadBallState) {
    resolveSetPieceOrRestart()
    continue
  }

  phase = determinePossessionPhase()
  actor = determineBallActor()

  candidates = generateActionCandidates(actor, phase, context)
  scoredCandidates = scoreCandidates(candidates, actor, context)
  chosenAction = sampleAction(scoredCandidates)

  result = resolveAction(chosenAction, actor, opponents, context)

  applyResult(result)
  resolveAftermath(result)

  if (needsTacticalAdaptation()) {
    adaptTactics()
  }

  if (needsSubstitutionDecision()) {
    resolveSubstitutionChoice()
  }

  advanceClock()
}
```

---

# 33. Non-negotiable realism rules

These are mandatory if you want the engine to feel European and credible.

1. **Shape beats isolated attributes**

   * good structure makes average players look better

2. **Decision quality must be separate from execution quality**

   * vision is not passing
   * positioning is not pace
   * composure is not finishing

3. **Fatigue must distort both body and mind**

   * not just speed

4. **Defending must mostly be prevention, not tackle spam**

5. **Chance quality matters more than shot count**

   * many weak shooters should not inflate goals unrealistically

6. **High-risk tactics must create volatility**

   * more transitions, more cards, more fatigue, more swings

7. **Elite players must create edge in narrow margins**

   * better timing, better choices, fewer mistakes

8. **RNG must decorate the simulation, not run it**

---

# 34. Closest-to-full-engine compact blueprint

This is the final condensed structure.

## Inputs

* formations
* tactical sliders
* roles
* player attributes
* morale/fatigue/sharpness
* match context

## Core loop

* update shape
* determine phase
* pick actor
* generate choices
* choose action via weighted utility
* resolve execution vs resistance
* update state
* trigger aftermath events

## Resolution families

* pass
* carry
* dribble
* duel
* interception
* cross
* through ball
* shot
* save
* rebound
* foul/card
* offside
* set piece

## Modifier families

* morale
* confidence
* fatigue
* momentum
* home advantage
* weather
* referee style
* tactical familiarity

## Tactical expression

* possession systems
* direct systems
* pressing systems
* low blocks
* transitional systems
* asymmetric flank attacks

## Calibration

* realistic league averages
* realistic event distributions
* realistic player impact
* bounded variance

---

# 35. Direct answer to your examples

## Offside trigger

Correct approach:

```text
OffsideChance =
  f(
    defensive line sync,
    offside trap setting,
    defender positioning,
    defender concentration,
    passer vision/decisions,
    runner off-ball/anticipation,
    pressure on passer,
    fatigue,
    tiny bounded rng
  )
```

## Scoring goals

Correct approach:

```text
GoalProbability =
  f(
    chance quality,
    finishing,
    composure,
    technique,
    shooting power when relevant,
    distance,
    angle,
    pressure,
    weak foot/body shape,
    keeper quality,
    block pressure,
    bounded rng
  )
```

## Disputing balls

Correct approach:

```text
DuelWinProbability =
  f(
    strength,
    balance,
    aggression,
    tackling or dribbling,
    anticipation,
    acceleration,
    body orientation,
    support presence,
    fatigue,
    morale,
    bounded rng
  )
```

## Vision / creative passes

Correct approach:

```text
CreativePassEvent =
  action availability from vision + decisions + tactical freedom
  then execution from passing + technique + composure
  then disruption from defensive spacing + pressure + anticipation
```

That separation is the key.

---

# 36. Final build standard

If you want the engine to feel like realistic European football, target this identity:

* slower than arcade
* structured phases
* tactical asymmetry
* fewer clean actions under pressure
* many possessions die from spacing and pressure
* elite players distort the match through timing and decisions
* late-game fatigue changes everything
* scorelines emerge from process, not canned scripts

This is the correct foundation for a near-full soccer manager match engine.
Below is a full agent-based plan for a soccer manager match engine that is close to implementation level rather than a vague design brief.

## 1. Engine target

You want a **manager simulation engine**, not a manual-control physics game.

That means:

* realism over spectacle
* tactical identity matters
* player quality matters
* morale, fatigue, and match context matter
* randomness exists but is constrained
* results emerge from many weighted micro-events, not scripted scorelines

The correct model is:

1. **Pre-match tactical model**
2. **Continuous possession-state simulation**
3. **Contextual event resolution**
4. **Post-event state updates**
5. **Manager adaptation layer**
6. **Substitution/instruction layer**
7. **Outcome calibration layer**

---

# 2. Core philosophy

Do **not** simulate the match as “team rating A vs team rating B”.

Simulate it as:

* where the ball is
* who is near the ball
* what both teams are trying to do
* what options the player sees
* whether the player can execute
* whether opponents disrupt it
* how fatigue, morale, pressure, and shape distort decisions

So the engine should be driven by:

* **team agents**
* **unit agents** (defense, midfield, attack)
* **player agents**
* **ball state**
* **match context**

---

# 3. Simulation resolution

Use a **hybrid tick + event model**.

## Recommended match clock

* match duration: 90 + stoppage
* internal simulation step: **0.5s to 1.0s**
* possession decision window: every **1–3 seconds**
* major event resolution: immediate, event-driven

This avoids brute-force physics while still feeling alive.

## Why hybrid is better

Pure per-second simulation becomes noisy and expensive.
Pure event-only simulation becomes fake and detached from tactics.

Hybrid gives:

* shape movement
* spacing logic
* pressing windows
* duel frequency
* event outcomes tied to positioning

---

# 4. Data model

## 4.1 Team tactical profile

Each team needs a tactical object:

```ts
TeamTactics {
  formation: "4-3-3" | "4-2-3-1" | ...
  mentality: 0..100            // defensive to ultra attacking
  tempo: 0..100
  width: 0..100
  defensiveLine: 0..100
  lineOfEngagement: 0..100
  pressingIntensity: 0..100
  counterPress: 0..100
  directness: 0..100
  buildupRisk: 0..100
  overlapLeft: 0..100
  overlapRight: 0..100
  underlapLeft: 0..100
  underlapRight: 0..100
  offsideTrap: 0..100
  timeWasting: 0..100
  creativeFreedom: 0..100
  crossingFrequency: 0..100
  shootOnSight: 0..100
  workBallIntoBox: 0..100
  transitionAfterWin: "counter" | "hold" | "balanced"
  transitionAfterLoss: "counterpress" | "regroup" | "balanced"
  setPieceProfiles: ...
}
```

---

## 4.2 Player attributes

You need attribute groups, not random single stats.

## Technical

* first touch
* passing
* short passing
* long passing
* crossing
* dribbling
* finishing
* heading
* shooting power
* technique
* tackling
* marking

## Mental

* decisions
* anticipation
* composure
* vision
* positioning
* off the ball
* teamwork
* aggression
* concentration
* flair
* bravery
* work rate
* leadership

## Physical

* acceleration
* pace
* agility
* balance
* strength
* stamina
* jumping reach
* natural fitness

## Goalkeeper

* reflexes
* handling
* one-on-ones
* aerial reach
* command of area
* rushing out
* kicking
* throwing
* positioning
* communication

---

## 4.3 Hidden/context variables

These matter as much as raw attributes.

* morale: 0..100
* fatigue: 0..100
* sharpness/match fitness: 0..100
* consistency
* big match temperament
* injury risk
* weak foot quality
* role familiarity
* tactical familiarity
* chemistry links with nearby teammates
* discipline
* current confidence
* frustration
* momentum sensitivity

---

## 4.4 Match context

```ts
MatchContext {
  minute
  stoppageTime
  homeAdvantage
  weather
  pitchCondition
  refereeStrictness
  scoreDifference
  competitionImportance
  cardStatus
  substitutionsUsed
  momentum
  crowdPressure
}
```

---

# 5. Spatial model

Do not use only abstract possession zones. That is too crude.

Use a **simplified pitch grid**.

## Recommended grid

* length split into 6 bands:

  1. own box
  2. own defensive third
  3. own half central progression
  4. attacking half progression
  5. final third
  6. opposition box

* width split into 5 lanes:

  * far left wing
  * left half-space
  * center
  * right half-space
  * far right wing

Total: **30 zones**

This is enough for:

* overloads
* switches
* central congestion
* wing play
* cutbacks
* pressing traps
* offside line behavior

Each player has:

* base tactical zone map by formation/role
* dynamic zone offset by phase
* dynamic movement preference by ball location

---

# 6. Agents

This is the main structure.

## 6.1 Match Director Agent

Controls:

* current possession
* phase changes
* event queue
* clock
* momentum state
* tactical instruction updates

## 6.2 Team Intent Agent

For each team:

* determines attacking intent
* determines defensive shape
* modifies risk by score/minute/morale/fatigue

## 6.3 Unit Agents

Per team:

* defensive unit
* midfield unit
* attacking unit

They control:

* line compactness
* support distances
* pressing depth
* spacing discipline
* recovery speed

## 6.4 Player Decision Agent

For the player on the ball:

* evaluate candidate actions
* assign utility
* choose action probabilistically
* execute with attribute-weighted success

## 6.5 Off-ball Movement Agent

For surrounding players:

* offer support
* attack depth
* hold shape
* make underlap/overlap/run beyond
* cover passing lanes
* track runners

## 6.6 Duel Resolution Agent

Handles:

* shoulder duels
* headers
* interceptions
* tackles
* loose balls
* keeper duels

## 6.7 Shot Resolution Agent

Handles:

* shot selection
* shot quality
* body part
* pressure
* block chance
* save chance
* rebound

## 6.8 Discipline Agent

Handles:

* foul chance
* booking chance
* second-yellow caution bias
* referee style

## 6.9 Adaptation Agent

Handles:

* game state tactical drift
* confidence effects
* panic late on
* low-block preservation
* substitutions and instruction reactions

---

# 7. Match phases

Each possession should be in one of these phases:

1. **build-up**
2. **progression**
3. **final-third circulation**
4. **chance creation**
5. **shot/recovery duel**
6. **transition attack**
7. **transition defense**
8. **set piece**
9. **dead time**

This is essential because action weights must depend on phase.

Example:
A CB in build-up should heavily prefer:

* short pass
* switch
* carry

That same CB in a chaotic transition should heavily prefer:

* clearance
* safe vertical release
* emergency tackle

---

# 8. Team shape and role logic

Formation alone is meaningless unless linked to behavior.

A 4-3-3 high press and a 4-3-3 mid-block must play differently.

Each role needs:

* anchor zone
* phase behavior
* support radius
* risk preference
* movement triggers

Example role profile:

```ts
RoleProfile {
  name: "Inside Forward Attack"
  baseZones: [...]
  attackingRunBias: 0..100
  widthRetention: 0..100
  dribbleBias: 0..100
  cutInsideBias: 0..100
  crossingBias: 0..100
  shotBias: 0..100
  pressBias: 0..100
  trackBackBias: 0..100
}
```

---

# 9. Core event flow

Each tick or decision cycle:

1. update fatigue/morale/momentum drift
2. update player positions relative to ball and tactics
3. determine possession phase
4. choose acting player
5. generate action candidates
6. compute action scores
7. sample chosen action
8. resolve execution
9. resolve opponent reaction
10. update ball location and match state
11. check event aftermath:

* foul
* corner
* throw
* offside
* shot
* rebound
* injury
* card

---

# 10. Decision model

Every action should use:

## Utility score

How attractive the action looks to the player

## Execution score

How likely the player is to pull it off

## Opposition resistance

How likely opponents disrupt it

## Controlled RNG

Final weighted uncertainty

Formula:

```text
ActionFinalScore =
  UtilityWeight * TacticalFit *
  PlayerReadOfGame *
  ContextModifier *
  RandomNoise
```

Then if selected:

```text
ActionSuccessProbability =
  ExecutionSkill *
  PhysicalCondition *
  Composure *
  RoleFamiliarity *
  SupportStructure
  /
  DefensiveResistance
```

---

# 11. Candidate actions by phase

## Build-up

* short pass
* medium pass
* switch
* carry forward
* reset to keeper
* long direct pass
* risky line-break pass
* clearance under pressure

## Progression

* vertical pass
* diagonal pass
* dribble carry
* overlap release
* switch flank
* long ball behind line

## Final third

* through ball
* cross
* cutback
* combination pass
* dribble take-on
* recycle possession
* shot from distance

## Box actions

* near-post shot
* far-post shot
* low driven shot
* finesse shot
* header
* layoff
* penalty-box dribble
* square pass

## Defensive actions

* jockey
* press
* tackle
* stand off
* cover lane
* intercept
* foul cynically
* clear

---

# 12. Attribute influence map

This is where realism comes from.

## Passing

Use:

* passing
* technique
* vision
* decisions
* composure
* weak foot
* pressure resistance
* fatigue
* receiving target movement
* lane congestion

## Through balls / “crazy passes”

Use:

* vision heavily
* technique heavily
* decisions heavily
* passing heavily
* flair moderately
* composure moderately
* teammate off-the-ball movement
* opponent line height
* compactness of defense
* pressure on passer

A high-vision player should **attempt** and **see** passes others do not.
A high-passing player should **execute** them better.
A high-decisions player should **choose** them at better moments.
A high-flair player should attempt rarer actions more often.

That distinction matters.

---

## Finishing

Use:

* finishing
* composure
* technique
* weak foot
* body balance
* pressure level
* angle
* distance
* goalkeeper position
* defender closing speed

## Long shots

Use:

* shooting power
* technique
* long shot trait if you include traits
* composure
* decision making
* fatigue
* distance
* defensive pressure
* keeper positioning

## Headers

Use:

* heading
* jumping reach
* strength
* bravery
* positioning/off the ball
* cross quality
* marker pressure

## Duels

Ground duel:

* strength
* balance
* aggression
* tackling or dribbling depending on role
* pace/acceleration in recovery angle
* fatigue

Aerial duel:

* jumping reach
* strength
* heading
* bravery
* positioning

## Interceptions

Use:

* anticipation
* positioning
* concentration
* acceleration
* reach to lane
* line compactness

## Offside trap

Use:

* team offside trap setting
* backline cohesion
* concentration
* positioning
* anticipation
* communication
* fatigue
* opponent timing/off the ball

---

# 13. Proper offside simulation

Your example is correct but incomplete.

Do not do:

```text
offside = rng + positioning
```

Do:

## Offside event model

When an attacker attempts a run behind a line:

1. calculate **run timing quality**

   * attacker anticipation
   * off the ball
   * decisions
   * composure
   * fatigue penalty

2. calculate **defensive line synchronization**

   * average of back line positioning
   * concentration
   * teamwork
   * communication
   * offside trap instruction
   * fatigue penalty
   * morale/confidence modifier

3. calculate **pass release timing**

   * passer vision
   * decisions
   * technique
   * composure
   * pressure penalty

4. calculate **assistant/ref margin noise**

   * very small bounded random term

Then:

```text
OffsideMargin =
  defensiveStepTiming
  - attackerRunTiming
  - passerReleasePrecision
  + tinyNoise
```

If margin exceeds threshold, offside.

This creates realistic behavior:

* disciplined elite teams catch runs more often
* tired defenses mistime step-ups
* clever forwards bend and delay runs better
* elite playmakers release at the right instant

---

# 14. Goal scoring model

Goals should not come from a single shot roll. They must come from layered resolution.

## Layer 1: Can the shooter get the shot off?

Depends on:

* first touch
* composure
* balance
* pressure
* body orientation
* nearest defender distance
* support of shooting lane

## Layer 2: Shot quality generation

Produces:

* contact quality
* trajectory intent
* shot type
* placement vs power tradeoff

## Layer 3: Defensive interference

* block chance
* deflection chance
* partial block

## Layer 4: Keeper response

* reaction
* positioning
* handling/parry tendencies
* one-on-one quality
* sightline obstruction

## Layer 5: Rebound outcome

* who attacks second ball
* reflex finish chance
* scramble

---

## Sample shot quality formula

```text
BaseShotScore =
  0.25 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * shootingPower
+ 0.10 * balance
+ 0.10 * firstTouch
+ 0.10 * decisions
```

Apply modifiers:

```text
ShotScoreAdjusted =
  BaseShotScore
  * AngleModifier
  * DistanceModifier
  * PressureModifier
  * BodyPartModifier
  * WeakFootModifier
  * FatigueModifier
  * MoraleConfidenceModifier
```

For long-range shots, increase weight of:

* shooting power
* technique
* decisions

For tap-ins, increase weight of:

* composure
* positioning
* first touch

---

# 15. Defensive realism

Defending cannot be reduced to “tackle chance”.

Defending is mostly:

* delay
* channeling
* screening
* line control
* compactness
* denying good shots
* winning second balls

So create defensive contributions that do not always create visible stats.

## Defensive metrics driving the engine

* line compactness
* horizontal compactness
* vertical compactness
* pressure arrival time
* cover shadow quality
* lane denial score
* recovery run speed
* box occupation
* marking tightness

These should shape the opponent’s success rates even without direct tackles.

---

# 16. Morale, confidence, and momentum

These should alter behavior, not just ratings.

## Morale effects

High morale:

* better decisions
* more proactive movement
* slightly more technical execution
* more willingness to risk creative actions

Low morale:

* conservative choices
* heavy first touch errors
* delayed reactions
* worse composure
* more collapse after setbacks

## Confidence effects during match

Confidence rises after:

* successful dribbles
* key passes
* goals
* several completed actions
* keeper saves

Confidence falls after:

* missed sitter
* error leading to chance
* card
* repeated dispossession

Use confidence as a temporary modifier, separate from morale.

---

# 17. Fatigue model

Fatigue must be one of the most important systems.

## Fatigue affects

* sprint frequency
* acceleration
* recovery speed
* duel strength retention
* concentration
* technique execution
* off-ball movement quality
* late-game injury risk

## Fatigue accumulation drivers

* pressing intensity
* total distance
* number of sprints
* repeated transitions
* weather
* stamina
* natural fitness

## Simple model

```text
FatigueGainPerTick =
  movementLoad
  + sprintLoad
  + pressingLoad
  + duelLoad
  - recoveryFactor
```

Then convert fatigue to performance penalties nonlinearly:

* 0–30: small
* 30–60: noticeable
* 60–80: strong
* 80+: severe collapse

Late-match realism comes from this curve.

---

# 18. Tactical identity examples

These profiles should genuinely feel different.

## 18.1 High-possession 4-3-3

* short support distances
* frequent recycling
* high central overload
* wide wingers pin line
* fullbacks overlap
* lower long-shot rate
* more cutbacks and through balls
* higher counterpress

## 18.2 Direct 4-4-2

* faster vertical progression
* more early crosses
* more second-ball duels
* lower central combination frequency
* deeper midfield support
* more target-man layoff patterns

## 18.3 Low-block 5-4-1

* deep line
* narrow lanes
* low pressing
* high block probability
* low possession retention
* stronger counter transition bias

## 18.4 Gegenpress 4-2-3-1

* high turnovers in advanced areas
* rapid fatigue burn
* more chaotic shot volume
* more fouls/cards
* strong first 60–70 minutes if fit

---

# 19. Manager instructions and in-match adaptation

The engine must let managers modify macro behavior dynamically.

## Triggers for auto-adjustment

* scoreline
* red card
* fatigue thresholds
* momentum collapse
* dominant flank exploitation
* weak fullback being targeted

## Example tactical changes

At 75+ minutes while leading:

* lower tempo
* reduce risk passing
* slightly lower defensive line
* more time management
* narrower shape
* more clearances from danger

At 80+ minutes trailing:

* raise mentality
* add box presence
* increase directness
* increase shot volume tolerance
* more overlap and crossing
* higher press risk

---

# 20. Substitution logic

Substitutions should not be random freshness swaps.

They should answer:

* is fatigue causing tactical failure?
* is a role underperforming?
* is there a mismatch exploit?
* do we need more height, pace, control, or defense?

## Sub agent priorities

* tired fullbacks in high-intensity systems
* booked defenders under pressure
* isolated striker in low-possession systems
* AM/winger for creativity if chasing
* DM/CB if protecting result
* target man if going direct late

---

# 21. Set pieces

Do not leave this abstract. European-style realism requires serious set-piece modeling.

## Corners

Variables:

* delivery quality
* inswing/outswing
* near-post/far-post/crowd keeper
* blockers
* aerial dominance
* zonal vs man marking
* second-ball setup

## Free kicks

* shooting chance
* crossing chance
* disguised pass chance
* wall quality
* keeper wall setup

## Penalties

Use:

* finishing or penalty-specific stat if you include it
* composure
* technique
* goalkeeper penalty read
* pressure importance
* confidence state

Set pieces should account for around realistic scoring share.

---

# 22. Fouls and cards

Must be contextual.

## Foul probability depends on

* aggression
* tackling
* decisions
* fatigue
* pressure situation
* referee strictness
* transition danger
* positioning error recovery

## Card probability depends on

* foul severity
* denial of promising attack
* DOGSO
* repeat offender tendency
* referee strictness
* current card status

Players on yellow should defend more cautiously unless aggression overrides.

---

# 23. Calibration targets for realism

You need target distributions. Without calibration the engine will drift into nonsense.

For a realistic top-level European match, rough averages:

* total shots: 18–28
* shots on target: 6–10
* possession split usually 42–58, extreme styles beyond that
* pass accuracy: 76–91 depending on style and level
* xG total: 1.8–3.2
* fouls: 18–30
* yellow cards: 2–6
* reds: rare
* corners: 7–13
* offsides: 1–5
* crosses attempted: style dependent
* goals: typically 2–3 total average across many matches

Lower leagues should have:

* more technical errors
* lower pass completion
* more transitions
* weaker line coordination
* more ugly clearances
* more variance

---

# 24. RNG design

Randomness must be **bounded and contextual**, never dominant.

Use three layers:

## Micro noise

Tiny variance on each action

## Style variance

Some tactical personalities naturally create volatility

## Match variance

Rare unusual swings, referee weirdness, wondergoals, etc.

The mistake is using raw RNG directly.
Use:

```text
effectiveValue = deterministicCore * (1 + boundedNoise)
```

Where boundedNoise is typically narrow, like ±3% to ±12% depending on action chaos.

More chaotic actions get wider variance:

* speculative through balls
* long shots
* aerial scrambles
* rebounds

Less chaotic actions get narrow variance:

* simple short passes
* goalkeeper collecting easy balls
* uncontested recycling

---

# 25. Full action selection model

For each on-ball player, generate candidate actions with scores.

## Example candidates for a CM in progression

* safe short pass
* switch wide
* line-break pass
* carry forward
* dribble evade
* lofted pass to runner
* recycle backward
* shot from distance

For each action:

```text
CandidateScore =
  BaseRoleBias
+ TacticalInstructionFit
+ VisibleOpportunity
+ PlayerPreference
+ MatchContextBias
+ ConfidenceBias
- RiskPenalty
```

Then softmax sample rather than always taking highest score.

This prevents robotic play.

---

# 26. Example formulas

## 26.1 Pass vision / ambitious pass detection

```text
PassOpportunityScore =
  0.30 * vision
+ 0.20 * decisions
+ 0.15 * anticipation
+ 0.10 * composure
+ 0.10 * flair
+ 0.15 * tacticalFreedom
```

## 26.2 Pass execution

```text
PassExecutionScore =
  0.35 * passing
+ 0.20 * technique
+ 0.15 * composure
+ 0.10 * balance
+ 0.10 * weakFootAdjusted
+ 0.10 * firstTouchState
```

Then divide by:

* pressure factor
* distance factor
* lane congestion
* receiver markedness

---

## 26.3 Ground duel

```text
BallWinScore =
  0.25 * strength
+ 0.20 * balance
+ 0.15 * aggression
+ 0.15 * tackling_or_dribbling
+ 0.10 * acceleration
+ 0.10 * anticipation
+ 0.05 * morale
```

Apply:

* fatigue penalty
* body orientation
* support presence
* referee caution if tackling

---

## 26.4 Interception

```text
InterceptionScore =
  0.30 * anticipation
+ 0.25 * positioning
+ 0.15 * concentration
+ 0.10 * acceleration
+ 0.10 * teamwork
+ 0.10 * defensiveShapeSupport
```

---

## 26.5 Shot on target probability

```text
SOTScore =
  0.30 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * firstTouch
+ 0.10 * decisions
+ 0.05 * shootingPower
+ 0.10 * confidence
```

Apply:

* angle
* distance
* pressure
* weak foot
* fatigue
* aerial/body-balance context

---

## 26.6 Goal conversion after shot on target

```text
GoalScore =
  ShotPlacementQuality
  * PowerAppropriateness
  * KeeperBeatenFactor
  * ScreenedVisionFactor
  * PostShotLuckBounded
```

KeeperBeatenFactor uses:

* reflexes
* positioning
* reach
* one-on-ones
* handling/parry profile

---

# 27. Realistic emergent patterns you want

If the engine is correct, these should emerge naturally:

* tired fullbacks get beaten late
* high lines get punished by elite timing and passing
* low blocks concede territory but block central shots
* creative midfielders generate fewer but better chances
* physical strikers dominate weak CBs in direct systems
* strong pressing sides start sharp and fade if not rotated
* morale collapse after error can produce shaky 10-minute spells
* top keepers steal points
* lower-quality leagues have more chaos and broken possessions

---

# 28. Implementation architecture

## Layer A: Data

* players
* teams
* tactics
* match context
* role templates
* event templates

## Layer B: State

* current player states
* fatigue
* confidence
* position zone
* ball zone
* possession owner
* event history

## Layer C: Decision systems

* team intent
* player action generation
* off-ball movement
* defensive reaction

## Layer D: Resolution systems

* pass
* dribble
* duel
* shot
* foul
* set piece
* goalkeeper action

## Layer E: Tuning/calibration

* league modifiers
* competition modifiers
* pace of game
* chance quality
* error rate
* refereeing style

---

# 29. Recommended agent breakdown for development

Use multiple build agents with strict ownership.

## Agent 1 — Tactical Identity Agent

Build:

* formations
* role maps
* phase instructions
* line behavior
* pressing behavior

Output:

* team shape rules
* role behavior matrices

## Agent 2 — Spatial Simulation Agent

Build:

* zone grid
* player zone transitions
* compactness and spacing
* support and overload detection

Output:

* movement and occupation system

## Agent 3 — Player Decision Agent

Build:

* candidate action generation
* utility scoring
* softmax action choice
* role and trait biases

Output:

* action selection engine

## Agent 4 — Duel and Defensive Agent

Build:

* tackles
* interceptions
* aerial duels
* loose balls
* shielding
* fouls/cards

Output:

* ball contest engine

## Agent 5 — Chance Creation Agent

Build:

* through balls
* crossing
* cutbacks
* dribbles
* combination play
* transition chance logic

Output:

* final-third creation engine

## Agent 6 — Shot and Goalkeeper Agent

Build:

* shot types
* pressure models
* shot quality
* save logic
* rebound logic

Output:

* scoring engine

## Agent 7 — Human Factors Agent

Build:

* morale
* confidence
* fatigue
* momentum
* discipline psychology

Output:

* player state modifier system

## Agent 8 — Match Adaptation Agent

Build:

* in-game tactical drift
* score effects
* time effects
* substitutions
* red card reshaping

Output:

* dynamic match management system

## Agent 9 — Set Piece Agent

Build:

* corners
* free kicks
* penalties
* throw-ins in dangerous areas

Output:

* dead-ball engine

## Agent 10 — Calibration Agent

Build:

* statistical target matching
* league style profiles
* variance boundaries
* realism testing harness

Output:

* stable realistic tuning

---

# 30. Development order

Correct order matters.

## Phase 1

Build:

* data schema
* attributes
* tactics schema
* 30-zone pitch model
* possession state machine

## Phase 2

Build:

* player action generation
* pass/dribble/duel resolution
* off-ball movement basics

## Phase 3

Build:

* shot engine
* goalkeeping
* set pieces
* offside trap logic

## Phase 4

Build:

* morale/fatigue/confidence
* tactical adaptation
* substitutions
* referee/cards

## Phase 5

Build:

* league-level tuning
* thousands of automated simulation tests
* match report and analytics layer

---

# 31. Match report outputs

To tune realism, the engine must expose internal stats.

Track:

* possession
* territory
* passes by lane and depth
* line breaks
* progressive carries
* turnovers by zone
* press regains
* duel win rates
* xG
* shot map
* crossing success
* offside triggers
* set-piece xG
* fatigue curves
* confidence shifts

Without this, tuning becomes blind.

---

# 32. Pseudocode skeleton

```ts
while (matchClock < finalWhistle) {
  updateContext()
  updateFatigueAndConfidence()
  updateTeamIntent(teamA)
  updateTeamIntent(teamB)
  updatePlayerPositions()

  if (deadBallState) {
    resolveSetPieceOrRestart()
    continue
  }

  phase = determinePossessionPhase()
  actor = determineBallActor()

  candidates = generateActionCandidates(actor, phase, context)
  scoredCandidates = scoreCandidates(candidates, actor, context)
  chosenAction = sampleAction(scoredCandidates)

  result = resolveAction(chosenAction, actor, opponents, context)

  applyResult(result)
  resolveAftermath(result)

  if (needsTacticalAdaptation()) {
    adaptTactics()
  }

  if (needsSubstitutionDecision()) {
    resolveSubstitutionChoice()
  }

  advanceClock()
}
```

---

# 33. Non-negotiable realism rules

These are mandatory if you want the engine to feel European and credible.

1. **Shape beats isolated attributes**

   * good structure makes average players look better

2. **Decision quality must be separate from execution quality**

   * vision is not passing
   * positioning is not pace
   * composure is not finishing

3. **Fatigue must distort both body and mind**

   * not just speed

4. **Defending must mostly be prevention, not tackle spam**

5. **Chance quality matters more than shot count**

   * many weak shooters should not inflate goals unrealistically

6. **High-risk tactics must create volatility**

   * more transitions, more cards, more fatigue, more swings

7. **Elite players must create edge in narrow margins**

   * better timing, better choices, fewer mistakes

8. **RNG must decorate the simulation, not run it**

---

# 34. Closest-to-full-engine compact blueprint

This is the final condensed structure.

## Inputs

* formations
* tactical sliders
* roles
* player attributes
* morale/fatigue/sharpness
* match context

## Core loop

* update shape
* determine phase
* pick actor
* generate choices
* choose action via weighted utility
* resolve execution vs resistance
* update state
* trigger aftermath events

## Resolution families

* pass
* carry
* dribble
* duel
* interception
* cross
* through ball
* shot
* save
* rebound
* foul/card
* offside
* set piece

## Modifier families

* morale
* confidence
* fatigue
* momentum
* home advantage
* weather
* referee style
* tactical familiarity

## Tactical expression

* possession systems
* direct systems
* pressing systems
* low blocks
* transitional systems
* asymmetric flank attacks

## Calibration

* realistic league averages
* realistic event distributions
* realistic player impact
* bounded variance

---

# 35. Direct answer to your examples

## Offside trigger

Correct approach:

```text
OffsideChance =
  f(
    defensive line sync,
    offside trap setting,
    defender positioning,
    defender concentration,
    passer vision/decisions,
    runner off-ball/anticipation,
    pressure on passer,
    fatigue,
    tiny bounded rng
  )
```

## Scoring goals

Correct approach:

```text
GoalProbability =
  f(
    chance quality,
    finishing,
    composure,
    technique,
    shooting power when relevant,
    distance,
    angle,
    pressure,
    weak foot/body shape,
    keeper quality,
    block pressure,
    bounded rng
  )
```

## Disputing balls

Correct approach:

```text
DuelWinProbability =
  f(
    strength,
    balance,
    aggression,
    tackling or dribbling,
    anticipation,
    acceleration,
    body orientation,
    support presence,
    fatigue,
    morale,
    bounded rng
  )
```

## Vision / creative passes

Correct approach:

```text
CreativePassEvent =
  action availability from vision + decisions + tactical freedom
  then execution from passing + technique + composure
  then disruption from defensive spacing + pressure + anticipation
```

That separation is the key.

---

# 36. Final build standard

If you want the engine to feel like realistic European football, target this identity:

* slower than arcade
* structured phases
* tactical asymmetry
* fewer clean actions under pressure
* many possessions die from spacing and pressure
* elite players distort the match through timing and decisions
* late-game fatigue changes everything
* scorelines emerge from process, not canned scripts

This is the correct foundation for a near-full soccer manager match engine.
Below is a full agent-based plan for a soccer manager match engine that is close to implementation level rather than a vague design brief.

## 1. Engine target

You want a **manager simulation engine**, not a manual-control physics game.

That means:

* realism over spectacle
* tactical identity matters
* player quality matters
* morale, fatigue, and match context matter
* randomness exists but is constrained
* results emerge from many weighted micro-events, not scripted scorelines

The correct model is:

1. **Pre-match tactical model**
2. **Continuous possession-state simulation**
3. **Contextual event resolution**
4. **Post-event state updates**
5. **Manager adaptation layer**
6. **Substitution/instruction layer**
7. **Outcome calibration layer**

---

# 2. Core philosophy

Do **not** simulate the match as “team rating A vs team rating B”.

Simulate it as:

* where the ball is
* who is near the ball
* what both teams are trying to do
* what options the player sees
* whether the player can execute
* whether opponents disrupt it
* how fatigue, morale, pressure, and shape distort decisions

So the engine should be driven by:

* **team agents**
* **unit agents** (defense, midfield, attack)
* **player agents**
* **ball state**
* **match context**

---

# 3. Simulation resolution

Use a **hybrid tick + event model**.

## Recommended match clock

* match duration: 90 + stoppage
* internal simulation step: **0.5s to 1.0s**
* possession decision window: every **1–3 seconds**
* major event resolution: immediate, event-driven

This avoids brute-force physics while still feeling alive.

## Why hybrid is better

Pure per-second simulation becomes noisy and expensive.
Pure event-only simulation becomes fake and detached from tactics.

Hybrid gives:

* shape movement
* spacing logic
* pressing windows
* duel frequency
* event outcomes tied to positioning

---

# 4. Data model

## 4.1 Team tactical profile

Each team needs a tactical object:

```ts
TeamTactics {
  formation: "4-3-3" | "4-2-3-1" | ...
  mentality: 0..100            // defensive to ultra attacking
  tempo: 0..100
  width: 0..100
  defensiveLine: 0..100
  lineOfEngagement: 0..100
  pressingIntensity: 0..100
  counterPress: 0..100
  directness: 0..100
  buildupRisk: 0..100
  overlapLeft: 0..100
  overlapRight: 0..100
  underlapLeft: 0..100
  underlapRight: 0..100
  offsideTrap: 0..100
  timeWasting: 0..100
  creativeFreedom: 0..100
  crossingFrequency: 0..100
  shootOnSight: 0..100
  workBallIntoBox: 0..100
  transitionAfterWin: "counter" | "hold" | "balanced"
  transitionAfterLoss: "counterpress" | "regroup" | "balanced"
  setPieceProfiles: ...
}
```

---

## 4.2 Player attributes

You need attribute groups, not random single stats.

## Technical

* first touch
* passing
* short passing
* long passing
* crossing
* dribbling
* finishing
* heading
* shooting power
* technique
* tackling
* marking

## Mental

* decisions
* anticipation
* composure
* vision
* positioning
* off the ball
* teamwork
* aggression
* concentration
* flair
* bravery
* work rate
* leadership

## Physical

* acceleration
* pace
* agility
* balance
* strength
* stamina
* jumping reach
* natural fitness

## Goalkeeper

* reflexes
* handling
* one-on-ones
* aerial reach
* command of area
* rushing out
* kicking
* throwing
* positioning
* communication

---

## 4.3 Hidden/context variables

These matter as much as raw attributes.

* morale: 0..100
* fatigue: 0..100
* sharpness/match fitness: 0..100
* consistency
* big match temperament
* injury risk
* weak foot quality
* role familiarity
* tactical familiarity
* chemistry links with nearby teammates
* discipline
* current confidence
* frustration
* momentum sensitivity

---

## 4.4 Match context

```ts
MatchContext {
  minute
  stoppageTime
  homeAdvantage
  weather
  pitchCondition
  refereeStrictness
  scoreDifference
  competitionImportance
  cardStatus
  substitutionsUsed
  momentum
  crowdPressure
}
```

---

# 5. Spatial model

Do not use only abstract possession zones. That is too crude.

Use a **simplified pitch grid**.

## Recommended grid

* length split into 6 bands:

  1. own box
  2. own defensive third
  3. own half central progression
  4. attacking half progression
  5. final third
  6. opposition box

* width split into 5 lanes:

  * far left wing
  * left half-space
  * center
  * right half-space
  * far right wing

Total: **30 zones**

This is enough for:

* overloads
* switches
* central congestion
* wing play
* cutbacks
* pressing traps
* offside line behavior

Each player has:

* base tactical zone map by formation/role
* dynamic zone offset by phase
* dynamic movement preference by ball location

---

# 6. Agents

This is the main structure.

## 6.1 Match Director Agent

Controls:

* current possession
* phase changes
* event queue
* clock
* momentum state
* tactical instruction updates

## 6.2 Team Intent Agent

For each team:

* determines attacking intent
* determines defensive shape
* modifies risk by score/minute/morale/fatigue

## 6.3 Unit Agents

Per team:

* defensive unit
* midfield unit
* attacking unit

They control:

* line compactness
* support distances
* pressing depth
* spacing discipline
* recovery speed

## 6.4 Player Decision Agent

For the player on the ball:

* evaluate candidate actions
* assign utility
* choose action probabilistically
* execute with attribute-weighted success

## 6.5 Off-ball Movement Agent

For surrounding players:

* offer support
* attack depth
* hold shape
* make underlap/overlap/run beyond
* cover passing lanes
* track runners

## 6.6 Duel Resolution Agent

Handles:

* shoulder duels
* headers
* interceptions
* tackles
* loose balls
* keeper duels

## 6.7 Shot Resolution Agent

Handles:

* shot selection
* shot quality
* body part
* pressure
* block chance
* save chance
* rebound

## 6.8 Discipline Agent

Handles:

* foul chance
* booking chance
* second-yellow caution bias
* referee style

## 6.9 Adaptation Agent

Handles:

* game state tactical drift
* confidence effects
* panic late on
* low-block preservation
* substitutions and instruction reactions

---

# 7. Match phases

Each possession should be in one of these phases:

1. **build-up**
2. **progression**
3. **final-third circulation**
4. **chance creation**
5. **shot/recovery duel**
6. **transition attack**
7. **transition defense**
8. **set piece**
9. **dead time**

This is essential because action weights must depend on phase.

Example:
A CB in build-up should heavily prefer:

* short pass
* switch
* carry

That same CB in a chaotic transition should heavily prefer:

* clearance
* safe vertical release
* emergency tackle

---

# 8. Team shape and role logic

Formation alone is meaningless unless linked to behavior.

A 4-3-3 high press and a 4-3-3 mid-block must play differently.

Each role needs:

* anchor zone
* phase behavior
* support radius
* risk preference
* movement triggers

Example role profile:

```ts
RoleProfile {
  name: "Inside Forward Attack"
  baseZones: [...]
  attackingRunBias: 0..100
  widthRetention: 0..100
  dribbleBias: 0..100
  cutInsideBias: 0..100
  crossingBias: 0..100
  shotBias: 0..100
  pressBias: 0..100
  trackBackBias: 0..100
}
```

---

# 9. Core event flow

Each tick or decision cycle:

1. update fatigue/morale/momentum drift
2. update player positions relative to ball and tactics
3. determine possession phase
4. choose acting player
5. generate action candidates
6. compute action scores
7. sample chosen action
8. resolve execution
9. resolve opponent reaction
10. update ball location and match state
11. check event aftermath:

* foul
* corner
* throw
* offside
* shot
* rebound
* injury
* card

---

# 10. Decision model

Every action should use:

## Utility score

How attractive the action looks to the player

## Execution score

How likely the player is to pull it off

## Opposition resistance

How likely opponents disrupt it

## Controlled RNG

Final weighted uncertainty

Formula:

```text
ActionFinalScore =
  UtilityWeight * TacticalFit *
  PlayerReadOfGame *
  ContextModifier *
  RandomNoise
```

Then if selected:

```text
ActionSuccessProbability =
  ExecutionSkill *
  PhysicalCondition *
  Composure *
  RoleFamiliarity *
  SupportStructure
  /
  DefensiveResistance
```

---

# 11. Candidate actions by phase

## Build-up

* short pass
* medium pass
* switch
* carry forward
* reset to keeper
* long direct pass
* risky line-break pass
* clearance under pressure

## Progression

* vertical pass
* diagonal pass
* dribble carry
* overlap release
* switch flank
* long ball behind line

## Final third

* through ball
* cross
* cutback
* combination pass
* dribble take-on
* recycle possession
* shot from distance

## Box actions

* near-post shot
* far-post shot
* low driven shot
* finesse shot
* header
* layoff
* penalty-box dribble
* square pass

## Defensive actions

* jockey
* press
* tackle
* stand off
* cover lane
* intercept
* foul cynically
* clear

---

# 12. Attribute influence map

This is where realism comes from.

## Passing

Use:

* passing
* technique
* vision
* decisions
* composure
* weak foot
* pressure resistance
* fatigue
* receiving target movement
* lane congestion

## Through balls / “crazy passes”

Use:

* vision heavily
* technique heavily
* decisions heavily
* passing heavily
* flair moderately
* composure moderately
* teammate off-the-ball movement
* opponent line height
* compactness of defense
* pressure on passer

A high-vision player should **attempt** and **see** passes others do not.
A high-passing player should **execute** them better.
A high-decisions player should **choose** them at better moments.
A high-flair player should attempt rarer actions more often.

That distinction matters.

---

## Finishing

Use:

* finishing
* composure
* technique
* weak foot
* body balance
* pressure level
* angle
* distance
* goalkeeper position
* defender closing speed

## Long shots

Use:

* shooting power
* technique
* long shot trait if you include traits
* composure
* decision making
* fatigue
* distance
* defensive pressure
* keeper positioning

## Headers

Use:

* heading
* jumping reach
* strength
* bravery
* positioning/off the ball
* cross quality
* marker pressure

## Duels

Ground duel:

* strength
* balance
* aggression
* tackling or dribbling depending on role
* pace/acceleration in recovery angle
* fatigue

Aerial duel:

* jumping reach
* strength
* heading
* bravery
* positioning

## Interceptions

Use:

* anticipation
* positioning
* concentration
* acceleration
* reach to lane
* line compactness

## Offside trap

Use:

* team offside trap setting
* backline cohesion
* concentration
* positioning
* anticipation
* communication
* fatigue
* opponent timing/off the ball

---

# 13. Proper offside simulation

Your example is correct but incomplete.

Do not do:

```text
offside = rng + positioning
```

Do:

## Offside event model

When an attacker attempts a run behind a line:

1. calculate **run timing quality**

   * attacker anticipation
   * off the ball
   * decisions
   * composure
   * fatigue penalty

2. calculate **defensive line synchronization**

   * average of back line positioning
   * concentration
   * teamwork
   * communication
   * offside trap instruction
   * fatigue penalty
   * morale/confidence modifier

3. calculate **pass release timing**

   * passer vision
   * decisions
   * technique
   * composure
   * pressure penalty

4. calculate **assistant/ref margin noise**

   * very small bounded random term

Then:

```text
OffsideMargin =
  defensiveStepTiming
  - attackerRunTiming
  - passerReleasePrecision
  + tinyNoise
```

If margin exceeds threshold, offside.

This creates realistic behavior:

* disciplined elite teams catch runs more often
* tired defenses mistime step-ups
* clever forwards bend and delay runs better
* elite playmakers release at the right instant

---

# 14. Goal scoring model

Goals should not come from a single shot roll. They must come from layered resolution.

## Layer 1: Can the shooter get the shot off?

Depends on:

* first touch
* composure
* balance
* pressure
* body orientation
* nearest defender distance
* support of shooting lane

## Layer 2: Shot quality generation

Produces:

* contact quality
* trajectory intent
* shot type
* placement vs power tradeoff

## Layer 3: Defensive interference

* block chance
* deflection chance
* partial block

## Layer 4: Keeper response

* reaction
* positioning
* handling/parry tendencies
* one-on-one quality
* sightline obstruction

## Layer 5: Rebound outcome

* who attacks second ball
* reflex finish chance
* scramble

---

## Sample shot quality formula

```text
BaseShotScore =
  0.25 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * shootingPower
+ 0.10 * balance
+ 0.10 * firstTouch
+ 0.10 * decisions
```

Apply modifiers:

```text
ShotScoreAdjusted =
  BaseShotScore
  * AngleModifier
  * DistanceModifier
  * PressureModifier
  * BodyPartModifier
  * WeakFootModifier
  * FatigueModifier
  * MoraleConfidenceModifier
```

For long-range shots, increase weight of:

* shooting power
* technique
* decisions

For tap-ins, increase weight of:

* composure
* positioning
* first touch

---

# 15. Defensive realism

Defending cannot be reduced to “tackle chance”.

Defending is mostly:

* delay
* channeling
* screening
* line control
* compactness
* denying good shots
* winning second balls

So create defensive contributions that do not always create visible stats.

## Defensive metrics driving the engine

* line compactness
* horizontal compactness
* vertical compactness
* pressure arrival time
* cover shadow quality
* lane denial score
* recovery run speed
* box occupation
* marking tightness

These should shape the opponent’s success rates even without direct tackles.

---

# 16. Morale, confidence, and momentum

These should alter behavior, not just ratings.

## Morale effects

High morale:

* better decisions
* more proactive movement
* slightly more technical execution
* more willingness to risk creative actions

Low morale:

* conservative choices
* heavy first touch errors
* delayed reactions
* worse composure
* more collapse after setbacks

## Confidence effects during match

Confidence rises after:

* successful dribbles
* key passes
* goals
* several completed actions
* keeper saves

Confidence falls after:

* missed sitter
* error leading to chance
* card
* repeated dispossession

Use confidence as a temporary modifier, separate from morale.

---

# 17. Fatigue model

Fatigue must be one of the most important systems.

## Fatigue affects

* sprint frequency
* acceleration
* recovery speed
* duel strength retention
* concentration
* technique execution
* off-ball movement quality
* late-game injury risk

## Fatigue accumulation drivers

* pressing intensity
* total distance
* number of sprints
* repeated transitions
* weather
* stamina
* natural fitness

## Simple model

```text
FatigueGainPerTick =
  movementLoad
  + sprintLoad
  + pressingLoad
  + duelLoad
  - recoveryFactor
```

Then convert fatigue to performance penalties nonlinearly:

* 0–30: small
* 30–60: noticeable
* 60–80: strong
* 80+: severe collapse

Late-match realism comes from this curve.

---

# 18. Tactical identity examples

These profiles should genuinely feel different.

## 18.1 High-possession 4-3-3

* short support distances
* frequent recycling
* high central overload
* wide wingers pin line
* fullbacks overlap
* lower long-shot rate
* more cutbacks and through balls
* higher counterpress

## 18.2 Direct 4-4-2

* faster vertical progression
* more early crosses
* more second-ball duels
* lower central combination frequency
* deeper midfield support
* more target-man layoff patterns

## 18.3 Low-block 5-4-1

* deep line
* narrow lanes
* low pressing
* high block probability
* low possession retention
* stronger counter transition bias

## 18.4 Gegenpress 4-2-3-1

* high turnovers in advanced areas
* rapid fatigue burn
* more chaotic shot volume
* more fouls/cards
* strong first 60–70 minutes if fit

---

# 19. Manager instructions and in-match adaptation

The engine must let managers modify macro behavior dynamically.

## Triggers for auto-adjustment

* scoreline
* red card
* fatigue thresholds
* momentum collapse
* dominant flank exploitation
* weak fullback being targeted

## Example tactical changes

At 75+ minutes while leading:

* lower tempo
* reduce risk passing
* slightly lower defensive line
* more time management
* narrower shape
* more clearances from danger

At 80+ minutes trailing:

* raise mentality
* add box presence
* increase directness
* increase shot volume tolerance
* more overlap and crossing
* higher press risk

---

# 20. Substitution logic

Substitutions should not be random freshness swaps.

They should answer:

* is fatigue causing tactical failure?
* is a role underperforming?
* is there a mismatch exploit?
* do we need more height, pace, control, or defense?

## Sub agent priorities

* tired fullbacks in high-intensity systems
* booked defenders under pressure
* isolated striker in low-possession systems
* AM/winger for creativity if chasing
* DM/CB if protecting result
* target man if going direct late

---

# 21. Set pieces

Do not leave this abstract. European-style realism requires serious set-piece modeling.

## Corners

Variables:

* delivery quality
* inswing/outswing
* near-post/far-post/crowd keeper
* blockers
* aerial dominance
* zonal vs man marking
* second-ball setup

## Free kicks

* shooting chance
* crossing chance
* disguised pass chance
* wall quality
* keeper wall setup

## Penalties

Use:

* finishing or penalty-specific stat if you include it
* composure
* technique
* goalkeeper penalty read
* pressure importance
* confidence state

Set pieces should account for around realistic scoring share.

---

# 22. Fouls and cards

Must be contextual.

## Foul probability depends on

* aggression
* tackling
* decisions
* fatigue
* pressure situation
* referee strictness
* transition danger
* positioning error recovery

## Card probability depends on

* foul severity
* denial of promising attack
* DOGSO
* repeat offender tendency
* referee strictness
* current card status

Players on yellow should defend more cautiously unless aggression overrides.

---

# 23. Calibration targets for realism

You need target distributions. Without calibration the engine will drift into nonsense.

For a realistic top-level European match, rough averages:

* total shots: 18–28
* shots on target: 6–10
* possession split usually 42–58, extreme styles beyond that
* pass accuracy: 76–91 depending on style and level
* xG total: 1.8–3.2
* fouls: 18–30
* yellow cards: 2–6
* reds: rare
* corners: 7–13
* offsides: 1–5
* crosses attempted: style dependent
* goals: typically 2–3 total average across many matches

Lower leagues should have:

* more technical errors
* lower pass completion
* more transitions
* weaker line coordination
* more ugly clearances
* more variance

---

# 24. RNG design

Randomness must be **bounded and contextual**, never dominant.

Use three layers:

## Micro noise

Tiny variance on each action

## Style variance

Some tactical personalities naturally create volatility

## Match variance

Rare unusual swings, referee weirdness, wondergoals, etc.

The mistake is using raw RNG directly.
Use:

```text
effectiveValue = deterministicCore * (1 + boundedNoise)
```

Where boundedNoise is typically narrow, like ±3% to ±12% depending on action chaos.

More chaotic actions get wider variance:

* speculative through balls
* long shots
* aerial scrambles
* rebounds

Less chaotic actions get narrow variance:

* simple short passes
* goalkeeper collecting easy balls
* uncontested recycling

---

# 25. Full action selection model

For each on-ball player, generate candidate actions with scores.

## Example candidates for a CM in progression

* safe short pass
* switch wide
* line-break pass
* carry forward
* dribble evade
* lofted pass to runner
* recycle backward
* shot from distance

For each action:

```text
CandidateScore =
  BaseRoleBias
+ TacticalInstructionFit
+ VisibleOpportunity
+ PlayerPreference
+ MatchContextBias
+ ConfidenceBias
- RiskPenalty
```

Then softmax sample rather than always taking highest score.

This prevents robotic play.

---

# 26. Example formulas

## 26.1 Pass vision / ambitious pass detection

```text
PassOpportunityScore =
  0.30 * vision
+ 0.20 * decisions
+ 0.15 * anticipation
+ 0.10 * composure
+ 0.10 * flair
+ 0.15 * tacticalFreedom
```

## 26.2 Pass execution

```text
PassExecutionScore =
  0.35 * passing
+ 0.20 * technique
+ 0.15 * composure
+ 0.10 * balance
+ 0.10 * weakFootAdjusted
+ 0.10 * firstTouchState
```

Then divide by:

* pressure factor
* distance factor
* lane congestion
* receiver markedness

---

## 26.3 Ground duel

```text
BallWinScore =
  0.25 * strength
+ 0.20 * balance
+ 0.15 * aggression
+ 0.15 * tackling_or_dribbling
+ 0.10 * acceleration
+ 0.10 * anticipation
+ 0.05 * morale
```

Apply:

* fatigue penalty
* body orientation
* support presence
* referee caution if tackling

---

## 26.4 Interception

```text
InterceptionScore =
  0.30 * anticipation
+ 0.25 * positioning
+ 0.15 * concentration
+ 0.10 * acceleration
+ 0.10 * teamwork
+ 0.10 * defensiveShapeSupport
```

---

## 26.5 Shot on target probability

```text
SOTScore =
  0.30 * finishing
+ 0.20 * composure
+ 0.15 * technique
+ 0.10 * firstTouch
+ 0.10 * decisions
+ 0.05 * shootingPower
+ 0.10 * confidence
```

Apply:

* angle
* distance
* pressure
* weak foot
* fatigue
* aerial/body-balance context

---

## 26.6 Goal conversion after shot on target

```text
GoalScore =
  ShotPlacementQuality
  * PowerAppropriateness
  * KeeperBeatenFactor
  * ScreenedVisionFactor
  * PostShotLuckBounded
```

KeeperBeatenFactor uses:

* reflexes
* positioning
* reach
* one-on-ones
* handling/parry profile

---

# 27. Realistic emergent patterns you want

If the engine is correct, these should emerge naturally:

* tired fullbacks get beaten late
* high lines get punished by elite timing and passing
* low blocks concede territory but block central shots
* creative midfielders generate fewer but better chances
* physical strikers dominate weak CBs in direct systems
* strong pressing sides start sharp and fade if not rotated
* morale collapse after error can produce shaky 10-minute spells
* top keepers steal points
* lower-quality leagues have more chaos and broken possessions

---

# 28. Implementation architecture

## Layer A: Data

* players
* teams
* tactics
* match context
* role templates
* event templates

## Layer B: State

* current player states
* fatigue
* confidence
* position zone
* ball zone
* possession owner
* event history

## Layer C: Decision systems

* team intent
* player action generation
* off-ball movement
* defensive reaction

## Layer D: Resolution systems

* pass
* dribble
* duel
* shot
* foul
* set piece
* goalkeeper action

## Layer E: Tuning/calibration

* league modifiers
* competition modifiers
* pace of game
* chance quality
* error rate
* refereeing style

---

# 29. Recommended agent breakdown for development

Use multiple build agents with strict ownership.

## Agent 1 — Tactical Identity Agent

Build:

* formations
* role maps
* phase instructions
* line behavior
* pressing behavior

Output:

* team shape rules
* role behavior matrices

## Agent 2 — Spatial Simulation Agent

Build:

* zone grid
* player zone transitions
* compactness and spacing
* support and overload detection

Output:

* movement and occupation system

## Agent 3 — Player Decision Agent

Build:

* candidate action generation
* utility scoring
* softmax action choice
* role and trait biases

Output:

* action selection engine

## Agent 4 — Duel and Defensive Agent

Build:

* tackles
* interceptions
* aerial duels
* loose balls
* shielding
* fouls/cards

Output:

* ball contest engine

## Agent 5 — Chance Creation Agent

Build:

* through balls
* crossing
* cutbacks
* dribbles
* combination play
* transition chance logic

Output:

* final-third creation engine

## Agent 6 — Shot and Goalkeeper Agent

Build:

* shot types
* pressure models
* shot quality
* save logic
* rebound logic

Output:

* scoring engine

## Agent 7 — Human Factors Agent

Build:

* morale
* confidence
* fatigue
* momentum
* discipline psychology

Output:

* player state modifier system

## Agent 8 — Match Adaptation Agent

Build:

* in-game tactical drift
* score effects
* time effects
* substitutions
* red card reshaping

Output:

* dynamic match management system

## Agent 9 — Set Piece Agent

Build:

* corners
* free kicks
* penalties
* throw-ins in dangerous areas

Output:

* dead-ball engine

## Agent 10 — Calibration Agent

Build:

* statistical target matching
* league style profiles
* variance boundaries
* realism testing harness

Output:

* stable realistic tuning

---

# 30. Development order

Correct order matters.

## Phase 1

Build:

* data schema
* attributes
* tactics schema
* 30-zone pitch model
* possession state machine

## Phase 2

Build:

* player action generation
* pass/dribble/duel resolution
* off-ball movement basics

## Phase 3

Build:

* shot engine
* goalkeeping
* set pieces
* offside trap logic

## Phase 4

Build:

* morale/fatigue/confidence
* tactical adaptation
* substitutions
* referee/cards

## Phase 5

Build:

* league-level tuning
* thousands of automated simulation tests
* match report and analytics layer

---

# 31. Match report outputs

To tune realism, the engine must expose internal stats.

Track:

* possession
* territory
* passes by lane and depth
* line breaks
* progressive carries
* turnovers by zone
* press regains
* duel win rates
* xG
* shot map
* crossing success
* offside triggers
* set-piece xG
* fatigue curves
* confidence shifts

Without this, tuning becomes blind.

---

# 32. Pseudocode skeleton

```ts
while (matchClock < finalWhistle) {
  updateContext()
  updateFatigueAndConfidence()
  updateTeamIntent(teamA)
  updateTeamIntent(teamB)
  updatePlayerPositions()

  if (deadBallState) {
    resolveSetPieceOrRestart()
    continue
  }

  phase = determinePossessionPhase()
  actor = determineBallActor()

  candidates = generateActionCandidates(actor, phase, context)
  scoredCandidates = scoreCandidates(candidates, actor, context)
  chosenAction = sampleAction(scoredCandidates)

  result = resolveAction(chosenAction, actor, opponents, context)

  applyResult(result)
  resolveAftermath(result)

  if (needsTacticalAdaptation()) {
    adaptTactics()
  }

  if (needsSubstitutionDecision()) {
    resolveSubstitutionChoice()
  }

  advanceClock()
}
```

---

# 33. Non-negotiable realism rules

These are mandatory if you want the engine to feel European and credible.

1. **Shape beats isolated attributes**

   * good structure makes average players look better

2. **Decision quality must be separate from execution quality**

   * vision is not passing
   * positioning is not pace
   * composure is not finishing

3. **Fatigue must distort both body and mind**

   * not just speed

4. **Defending must mostly be prevention, not tackle spam**

5. **Chance quality matters more than shot count**

   * many weak shooters should not inflate goals unrealistically

6. **High-risk tactics must create volatility**

   * more transitions, more cards, more fatigue, more swings

7. **Elite players must create edge in narrow margins**

   * better timing, better choices, fewer mistakes

8. **RNG must decorate the simulation, not run it**

---

# 34. Closest-to-full-engine compact blueprint

This is the final condensed structure.

## Inputs

* formations
* tactical sliders
* roles
* player attributes
* morale/fatigue/sharpness
* match context

## Core loop

* update shape
* determine phase
* pick actor
* generate choices
* choose action via weighted utility
* resolve execution vs resistance
* update state
* trigger aftermath events

## Resolution families

* pass
* carry
* dribble
* duel
* interception
* cross
* through ball
* shot
* save
* rebound
* foul/card
* offside
* set piece

## Modifier families

* morale
* confidence
* fatigue
* momentum
* home advantage
* weather
* referee style
* tactical familiarity

## Tactical expression

* possession systems
* direct systems
* pressing systems
* low blocks
* transitional systems
* asymmetric flank attacks

## Calibration

* realistic league averages
* realistic event distributions
* realistic player impact
* bounded variance

---

# 35. Direct answer to your examples

## Offside trigger

Correct approach:

```text
OffsideChance =
  f(
    defensive line sync,
    offside trap setting,
    defender positioning,
    defender concentration,
    passer vision/decisions,
    runner off-ball/anticipation,
    pressure on passer,
    fatigue,
    tiny bounded rng
  )
```

## Scoring goals

Correct approach:

```text
GoalProbability =
  f(
    chance quality,
    finishing,
    composure,
    technique,
    shooting power when relevant,
    distance,
    angle,
    pressure,
    weak foot/body shape,
    keeper quality,
    block pressure,
    bounded rng
  )
```

## Disputing balls

Correct approach:

```text
DuelWinProbability =
  f(
    strength,
    balance,
    aggression,
    tackling or dribbling,
    anticipation,
    acceleration,
    body orientation,
    support presence,
    fatigue,
    morale,
    bounded rng
  )
```

## Vision / creative passes

Correct approach:

```text
CreativePassEvent =
  action availability from vision + decisions + tactical freedom
  then execution from passing + technique + composure
  then disruption from defensive spacing + pressure + anticipation
```

That separation is the key.

---

# 36. Final build standard

If you want the engine to feel like realistic European football, target this identity:

* slower than arcade
* structured phases
* tactical asymmetry
* fewer clean actions under pressure
* many possessions die from spacing and pressure
* elite players distort the match through timing and decisions
* late-game fatigue changes everything
* scorelines emerge from process, not canned scripts

This is the correct foundation for a near-full soccer manager match engine.
