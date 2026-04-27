from __future__ import annotations

from .models import PlayerProfile

TEAM_TRAINING_FOCUS_OPTIONS = {
    "balanced": {
        "label": "Balanced",
        "attributes": ("decisions", "teamwork", "stamina", "first_touch"),
        "sharpness": 1.0,
        "load": 1.0,
    },
    "recovery": {
        "label": "Recovery",
        "attributes": ("natural_fitness", "stamina"),
        "sharpness": 0.45,
        "load": 0.35,
    },
    "technical": {
        "label": "Technical",
        "attributes": ("first_touch", "technique", "passing", "dribbling"),
        "sharpness": 0.9,
        "load": 0.85,
    },
    "tactical": {
        "label": "Tactical",
        "attributes": ("decisions", "positioning", "off_ball", "teamwork"),
        "sharpness": 1.15,
        "load": 0.75,
    },
    "attacking": {
        "label": "Attacking",
        "attributes": ("finishing", "off_ball", "composure", "long_shots"),
        "sharpness": 1.05,
        "load": 0.95,
    },
    "defending": {
        "label": "Defending",
        "attributes": ("tackling", "marking", "positioning", "strength"),
        "sharpness": 1.0,
        "load": 0.95,
    },
    "physical": {
        "label": "Physical",
        "attributes": ("stamina", "pace", "acceleration", "strength", "natural_fitness"),
        "sharpness": 0.75,
        "load": 1.35,
    },
    "set_pieces": {
        "label": "Set Pieces",
        "attributes": ("corners", "free_kick_taking", "penalty_taking", "long_throws"),
        "sharpness": 0.65,
        "load": 0.55,
    },
}

TRAINING_INTENSITY_OPTIONS = {
    "light": {"label": "Light", "load": 0.65, "growth": 0.70, "stamina_cost": 0.18, "injury": 0.45},
    "normal": {"label": "Normal", "load": 1.0, "growth": 1.0, "stamina_cost": 0.38, "injury": 1.0},
    "double": {"label": "Double", "load": 1.45, "growth": 1.32, "stamina_cost": 1.25, "injury": 1.75},
}

PLAYER_TRAINING_FOCUS_OPTIONS = {
    "auto": {"label": "Auto", "attributes": ()},
    "fitness": {"label": "Fitness", "attributes": ("stamina", "natural_fitness", "pace", "acceleration")},
    "final_third": {"label": "Final Third", "attributes": ("finishing", "off_ball", "composure", "long_shots")},
    "playmaking": {"label": "Playmaking", "attributes": ("passing", "short_passing", "vision", "decisions", "technique")},
    "defending": {"label": "Defending", "attributes": ("tackling", "marking", "positioning", "strength")},
    "goalkeeping": {"label": "Goalkeeping", "attributes": ("reflexes", "handling", "one_on_ones", "aerial_reach", "command_of_area")},
}


def normalize_training_focus(value: str | None) -> str:
    text = str(value or "balanced")
    return text if text in TEAM_TRAINING_FOCUS_OPTIONS else "balanced"


def normalize_training_intensity(value: str | None) -> str:
    text = str(value or "normal")
    return text if text in TRAINING_INTENSITY_OPTIONS else "normal"


def normalize_player_training_focus(value: str | None, player: PlayerProfile | None = None) -> str:
    text = str(value or "auto")
    if text in PLAYER_TRAINING_FOCUS_OPTIONS:
        return text
    if player and player.position == "GK":
        return "goalkeeping"
    return "auto"


def default_player_training_focus(player: PlayerProfile) -> str:
    if player.position == "GK":
        return "goalkeeping"
    if player.position in {"CB", "LB", "RB", "DM"}:
        return "defending"
    if player.position in {"AM", "CM"}:
        return "playmaking"
    if player.position in {"LW", "RW", "ST"}:
        return "final_third"
    return "auto"


def training_attribute_gain(
    player: PlayerProfile,
    attribute: str,
    *,
    focus_match: bool,
    intensity: str,
    current_day: int,
) -> float:
    intensity_info = TRAINING_INTENSITY_OPTIONS[normalize_training_intensity(intensity)]
    base = 0.005 * float(intensity_info["growth"])
    age_factor = 1.0
    # No ages exist yet; deterministic player-id variation gives different growth curves without randomness.
    age_factor += ((sum(ord(ch) for ch in player.id) + current_day) % 7 - 3) * 0.015
    current = float(player.attributes.get(attribute, player.ovr))
    potential_factor = max(0.25, min(1.15, (96.0 - current) / 36.0))
    focus_factor = 1.75 if focus_match else 1.0
    availability_factor = 0.0 if not player.is_available else max(0.20, min(1.0, player.current_stamina / 100.0))
    return base * focus_factor * age_factor * potential_factor * availability_factor


def training_stamina_delta(player: PlayerProfile, team_focus: str, intensity: str) -> float:
    focus_info = TEAM_TRAINING_FOCUS_OPTIONS[normalize_training_focus(team_focus)]
    intensity_info = TRAINING_INTENSITY_OPTIONS[normalize_training_intensity(intensity)]
    natural_fitness = float(player.attributes.get("natural_fitness", 70.0))
    resilience = 0.85 + max(0.0, natural_fitness - 55.0) / 180.0
    readiness_guard = max(0.12, min(1.0, (player.current_stamina - 58.0) / 34.0))
    return -float(intensity_info["stamina_cost"]) * float(focus_info["load"]) * readiness_guard / resilience
