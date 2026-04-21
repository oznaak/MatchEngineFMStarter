from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class PlayerProfile:
    id: str
    name: str
    position: str
    ovr: int
    attributes: Dict[str, float]


@dataclass
class Club:
    id: str
    name: str
    players: List[PlayerProfile]


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
