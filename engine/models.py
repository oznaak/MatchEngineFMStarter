from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

DEFAULT_TEAM_INSTRUCTIONS = {
    "passing": "balanced",
    "width": "balanced",
    "playstyle": "balanced",
    "set_pieces": "balanced",
    "tempo": "balanced",
    "gameplan": "balanced",
    "time_management": "balanced",
}

DEFAULT_PLAYER_INSTRUCTIONS = {
    "pressure": 50,
    "mindset": 50,
}

TEAM_INSTRUCTION_OPTIONS = {
    "passing": ["shorter", "balanced", "long_balls"],
    "width": ["narrow", "balanced", "wide"],
    "playstyle": ["park_the_bus", "defending", "balanced", "attacking", "all_out_attack"],
    "set_pieces": ["possession", "balanced", "direct"],
    "tempo": ["lower", "balanced", "higher"],
    "gameplan": ["possession", "balanced", "quick_play"],
    "time_management": ["often", "balanced", "ball_out"],
}

TEAM_INSTRUCTION_LABELS = {
    "passing": {"shorter": "SHORTER", "balanced": "BALANCED", "long_balls": "LONG BALLS"},
    "width": {"narrow": "NARROW", "balanced": "BALANCED", "wide": "WIDE"},
    "playstyle": {
        "park_the_bus": "PARK THE BUS",
        "defending": "DEFENDING",
        "balanced": "BALANCED",
        "attacking": "ATTACKING",
        "all_out_attack": "ALL OUT ATTACK",
    },
    "set_pieces": {"possession": "POSSESSION", "balanced": "BALANCED", "direct": "DIRECT"},
    "tempo": {"lower": "LOWER", "balanced": "BALANCED", "higher": "HIGHER"},
    "gameplan": {"possession": "POSSESSION", "balanced": "BALANCED", "quick_play": "QUICK PLAY"},
    "time_management": {"often": "OFTEN", "balanced": "BALANCED", "ball_out": "BALL OUT"},
}

PLAYER_INSTRUCTION_LABELS = {
    "pressure": ("CALM", "AGGRESSIVE"),
    "mindset": ("HELP TEAM DEFEND", "FOCUS ON ATTACK"),
}

PREFERRED_FOOT_OPTIONS = ("left", "right")

KNOWN_PREFERRED_FEET = {
    "DAVID RAYA": "right",
    "OLEKS ZINCHENKO": "left",
    "BEN WHITE": "right",
    "THOMAS PARTEY": "right",
    "MARTIN ODEGAARD": "left",
    "GABRIEL MARTINELLI": "right",
    "GABRIEL JESUS": "right",
    "BUKAYO SAKA": "left",
    "AARON RAMSDALE": "right",
    "LEANDRO TROSSARD": "right",
    "ANDRE ONANA": "right",
    "LUKE SHAW": "left",
    "LISANDRO MARTINEZ": "left",
    "BRUNO FERNANDES": "right",
    "MARCUS RASHFORD": "right",
    "ANTONY": "left",
    "BEN CHILWELL": "left",
    "ENZO FERNANDEZ": "right",
    "COLE PALMER": "left",
    "MYKHAILO MUDRYK": "right",
    "NONI MADUEKE": "left",
    "EDERSON": "left",
    "JOSKO GVARDIOL": "left",
    "KEVIN DE BRUYNE": "right",
    "BERNARDO SILVA": "left",
    "JEREMY DOKU": "right",
    "PHIL FODEN": "left",
    "JULIAN ALVAREZ": "left",
}


def normalize_team_instructions(custom: Dict[str, str] | None) -> Dict[str, str]:
    instructions = dict(DEFAULT_TEAM_INSTRUCTIONS)
    if not custom:
        return instructions
    for key, default in DEFAULT_TEAM_INSTRUCTIONS.items():
        value = str(custom.get(key, default))
        instructions[key] = value if value in TEAM_INSTRUCTION_OPTIONS[key] else default
    return instructions


def normalize_player_instruction_value(key: str, value: int | float | str | None) -> int:
    default = DEFAULT_PLAYER_INSTRUCTIONS.get(key, 50)
    try:
        numeric = int(round(float(value if value is not None else default)))
    except (TypeError, ValueError):
        numeric = default
    return max(0, min(100, numeric))


def normalize_player_instructions(custom: Dict[str, int] | None) -> Dict[str, int]:
    instructions = dict(DEFAULT_PLAYER_INSTRUCTIONS)
    if not custom:
        return instructions
    for key in DEFAULT_PLAYER_INSTRUCTIONS:
        instructions[key] = normalize_player_instruction_value(key, custom.get(key))
    return instructions


def normalize_player_instruction_map(custom: Dict[str, Dict[str, int]] | None) -> Dict[str, Dict[str, int]]:
    if not custom:
        return {}
    normalized: Dict[str, Dict[str, int]] = {}
    for player_id, values in custom.items():
        if not isinstance(player_id, str):
            continue
        normalized[player_id] = normalize_player_instructions(values if isinstance(values, dict) else None)
    return normalized


def normalize_preferred_foot(value: str | None) -> str:
    foot = str(value or "right").strip().lower()
    return foot if foot in PREFERRED_FOOT_OPTIONS else "right"


def infer_preferred_foot(name: str | None, position: str | None) -> str:
    lookup = KNOWN_PREFERRED_FEET.get(str(name or "").strip().upper())
    if lookup:
        return lookup
    pos = str(position or "").upper()
    if pos in {"LB", "LW"}:
        return "left"
    return "right"


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
        "straight_red_cards": 0.0,
        "second_yellow_red_cards": 0.0,
        "injuries": 0.0,
        "goalkeeper_saves": 0.0,
        "goalkeeper_high_claims": 0.0,
        "goalkeeper_goals_conceded": 0.0,
        "ball_recoveries": 0.0,
        "long_balls_attempted": 0.0,
        "long_balls_completed": 0.0,
    }


@dataclass
class PlayerProfile:
    id: str
    name: str
    position: str
    ovr: int
    attributes: Dict[str, float]
    preferred_foot: str = "right"
    current_stamina: float = 100.0
    yellow_card_count: int = 0
    suspension_matches_remaining: int = 0
    injury_days_remaining: int = 0
    injury_count: int = 0
    age: int = 0

    @property
    def is_available(self) -> bool:
        return self.suspension_matches_remaining <= 0 and self.injury_days_remaining <= 0


@dataclass
class Club:
    id: str
    name: str
    players: List[PlayerProfile]
    manager_name: str = ""
    tactics: Dict[str, float] = field(default_factory=dict)
    colors: Dict[str, str] = field(default_factory=dict)
    badge: Dict[str, str] = field(default_factory=dict)
    formation: str = "4-3-3"
    lineup_xi: List[str] = field(default_factory=list)
    lineup_bench: List[str] = field(default_factory=list)
    instructions: Dict[str, str] = field(default_factory=lambda: dict(DEFAULT_TEAM_INSTRUCTIONS))
    player_instructions: Dict[str, Dict[str, int]] = field(default_factory=dict)

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
    red_card_reason: Optional[str] = None
    injured: bool = False
    injury_days: int = 0
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
    formation: str = "4-3-3"
    substitutions_used: int = 0
    substitution_windows_used: int = 0
    subbed_out_ids: set[str] = field(default_factory=set)
    last_ai_sub_minute: int = -99

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
