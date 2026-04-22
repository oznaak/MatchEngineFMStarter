from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


def stamina_ratio_for_player(stamina: float, fatigue: float) -> float:
    usable_capacity = 8.5 + stamina * 0.16
    return max(0.08, min(1.0, 1.0 - (fatigue / usable_capacity)))


def fatigue_from_current_stamina(current_stamina: float) -> float:
    return max(0.0, (100.0 - max(0.0, min(100.0, current_stamina))) / 3.0)


def current_stamina_from_fatigue(fatigue: float) -> float:
    return max(0.0, min(100.0, 100.0 - fatigue * 3.0))


def default_team_match_stats() -> Dict[str, float]:
    return {
        "possession_seconds": 0.0,
        "shots_on_target": 0.0,
        "shots_off_target": 0.0,
        "passes_attempted": 0.0,
        "passes_completed": 0.0,
        "corners": 0.0,
        "offsides": 0.0,
        "fouls": 0.0,
        "yellow_cards": 0.0,
        "red_cards": 0.0,
    }


def default_player_match_stats() -> Dict[str, float]:
    return {
        "minutes": 0.0,
        "goals": 0.0,
        "assists": 0.0,
        "shots_on_target": 0.0,
        "shots_off_target": 0.0,
        "passes_attempted": 0.0,
        "passes_completed": 0.0,
        "tackles": 0.0,
        "interceptions": 0.0,
        "clearances": 0.0,
        "fouls_committed": 0.0,
        "fouls_suffered": 0.0,
        "dribbles_completed": 0.0,
        "duels_total": 0.0,
        "duels_won": 0.0,
        "yellow_cards": 0.0,
        "red_cards": 0.0,
        "rating": 6.8,
    }


@dataclass
class PlayerProfile:
    id: str
    name: str
    position: str
    ovr: int
    attributes: Dict[str, float]
    current_stamina: float = 100.0


@dataclass
class Club:
    id: str
    name: str
    players: List[PlayerProfile]
    tactics: Dict[str, float] = field(default_factory=dict)
    colors: Dict[str, str] = field(default_factory=dict)
    badge: Dict[str, str] = field(default_factory=dict)

    @property
    def badge_id(self) -> str:
        return str(self.badge.get("id", "1"))

    @property
    def badge_primary(self) -> str:
        return str(self.badge.get("primary", self.colors.get("primary", "#2E3A6A")))

    @property
    def badge_secondary(self) -> str:
        return str(self.badge.get("secondary", self.colors.get("secondary", "#F5F5F5")))


@dataclass
class PlayerState:
    profile: PlayerProfile
    side: str
    slot: str
    x: float
    y: float
    home_x: float
    home_y: float
    target_x: float
    target_y: float
    speed: float
    base_speed: float = 0.0
    fatigue: float = 0.0
    prev_x: float = 0.0
    prev_y: float = 0.0
    state: str = "shape"
    action_time: float = 0.0
    has_ball: bool = False
    control_cooldown: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    facing_x: float = 1.0
    facing_y: float = 0.0
    render_state: str = "shape"
    run_intent: Optional[str] = None
    run_commit_timer: float = 0.0
    commit_target_x: Optional[float] = None
    commit_target_y: Optional[float] = None
    yellow_cards: int = 0
    red_card: bool = False
    fouls_committed: int = 0
    fouls_suffered: int = 0

    def __post_init__(self) -> None:
        self.prev_x = self.x
        self.prev_y = self.y
        if self.base_speed <= 0.0:
            self.base_speed = self.speed

    @property
    def short_name(self) -> str:
        parts = self.profile.name.split()
        return parts[-1] if parts else self.profile.name


@dataclass
class TeamState:
    club: Club
    side: str
    xi: List[PlayerState]
    bench: List[PlayerProfile]
    avg_ovr: float

    @property
    def name(self) -> str:
        return self.club.name


@dataclass
class BallState:
    x: float
    y: float
    target_x: float
    target_y: float
    carrier_id: Optional[str] = None
    prev_x: float = 0.0
    prev_y: float = 0.0
    mode: str = "carried"  # carried, travelling, shot, loose
    start_x: float = 0.0
    start_y: float = 0.0
    travel_progress: float = 0.0
    travel_time: float = 0.0
    target_player_id: Optional[str] = None
    team_in_possession: str = "home"
    intended_side: str = "home"
    speed: float = 0.0
    pass_type: str = "short_ground"
    lead_player_id: Optional[str] = None
    loose_owner_bias: Optional[str] = None
    shot_outcome: Optional[str] = None
    offside_flag: bool = False

    def __post_init__(self) -> None:
        self.prev_x = self.x
        self.prev_y = self.y
        self.start_x = self.x
        self.start_y = self.y


@dataclass
class MatchEvent:
    minute: int
    second: int
    text: str


@dataclass
class MatchState:
    home: TeamState
    away: TeamState
    ball: BallState
    real_elapsed_seconds: float = 0.0
    elapsed_seconds: float = 0.0
    minute: int = 0
    second: int = 0
    home_score: int = 0
    away_score: int = 0
    possession: str = "home"
    phase: str = "first_half"
    is_finished: bool = False
    last_touch_player_id: Optional[str] = None
    events: List[MatchEvent] = field(default_factory=list)
    ball_zone: str = "middle_central"
    phase_in_possession: str = "progression"
    phase_out_of_possession: str = "mid_block"
    recent_turnover_seconds: float = 0.0
    last_action_type: str = "recovery"
    celebration_timer: float = 0.0
    celebration_side: Optional[str] = None
    celebration_scorer_id: Optional[str] = None
    pending_kickoff_side: Optional[str] = None
    goal_banner_text: Optional[str] = None
    restart_mode: Optional[str] = None
    restart_timer: float = 0.0
    restart_side: Optional[str] = None
    awaiting_start: bool = False
    throw_ins_count: int = 0
    corners_count: int = 0
    offsides_count: int = 0
    fouls_count_home: int = 0
    fouls_count_away: int = 0
    yellow_cards_home: int = 0
    yellow_cards_away: int = 0
    red_cards_home: int = 0
    red_cards_away: int = 0
    referee_strictness: float = 52.0
    restart_taker_id: Optional[str] = None
    fouled_player_id: Optional[str] = None
    player_goals: Dict[str, int] = field(default_factory=dict)
    player_assists: Dict[str, int] = field(default_factory=dict)
    assist_candidate_id: Optional[str] = None
    team_match_stats: Dict[str, Dict[str, float]] = field(
        default_factory=lambda: {"home": default_team_match_stats(), "away": default_team_match_stats()}
    )
    player_match_stats: Dict[str, Dict[str, float]] = field(default_factory=dict)
