from __future__ import annotations
import hashlib
import json
from pathlib import Path
from typing import Dict, List, Tuple

from .models import Club, PlayerProfile, infer_preferred_foot, normalize_preferred_foot

FORMATIONS: Dict[str, List[str]] = {
    "4-3-3": ["GK", "LB", "CB", "CB", "RB", "DM", "CM", "AM", "LW", "ST", "RW"],
    "4-2-3-1": ["GK", "LB", "CB", "CB", "RB", "DM", "DM", "AM", "LW", "RW", "ST"],
    "4-4-2": ["GK", "LB", "CB", "CB", "RB", "CM", "CM", "LW", "RW", "ST", "ST"],
    "4-1-4-1": ["GK", "LB", "CB", "CB", "RB", "DM", "CM", "CM", "LW", "RW", "ST"],
}

FORMATION_433 = FORMATIONS["4-3-3"]

FALLBACKS = {
    "GK": ["GK"],
    "LB": ["LB", "RB", "CB", "DM", "CM"],
    "CB": ["CB", "LB", "RB", "DM", "CM"],
    "RB": ["RB", "LB", "CB", "DM", "CM"],
    "DM": ["DM", "CM", "CB", "AM"],
    "CM": ["CM", "DM", "AM", "LW", "RW"],
    "AM": ["AM", "CM", "ST", "LW", "RW"],
    "LW": ["LW", "RW", "AM", "ST", "CM"],
    "ST": ["ST", "AM", "LW", "RW", "CM"],
    "RW": ["RW", "LW", "AM", "ST", "CM"],
}

DEFAULT_TACTICS = {
    "tempo": 50.0,
    "width": 50.0,
    "defensive_line": 50.0,
    "pressing": 50.0,
    "directness": 50.0,
    "crossing": 50.0,
    "counter": 50.0,
}

DEFAULT_COLORS = {
    "primary": "#2E3A6A",
    "secondary": "#F5F5F5",
}

PLAYER_ATTRIBUTE_KEYS: Tuple[str, ...] = (
    "corners",
    "crossing",
    "dribbling",
    "finishing",
    "first_touch",
    "free_kick_taking",
    "heading",
    "long_passing",
    "long_shots",
    "long_throws",
    "marking",
    "passing",
    "penalty_taking",
    "short_passing",
    "tackling",
    "technique",
    "aggression",
    "anticipation",
    "bravery",
    "composure",
    "concentration",
    "decisions",
    "determination",
    "flair",
    "leadership",
    "off_ball",
    "positioning",
    "teamwork",
    "vision",
    "work_rate",
    "acceleration",
    "agility",
    "balance",
    "jumping_reach",
    "natural_fitness",
    "pace",
    "stamina",
    "strength",
    "handling",
    "one_on_ones",
    "reflexes",
    "aerial_reach",
    "command_of_area",
    "rushing_out",
    "kicking",
    "throwing",
    "communication",
)


def _stable_variation(identity: str, key: str, spread: int) -> float:
    digest = hashlib.sha256(f"{identity}:{key}".encode("utf-8")).digest()
    raw = int.from_bytes(digest[:2], "big") / 65535.0
    return (raw * 2.0 - 1.0) * float(spread)


def _apply_delta(attrs: Dict[str, float], changes: Dict[str, float]) -> None:
    for key, delta in changes.items():
        attrs[key] = attrs.get(key, 50.0) + float(delta)


def formation_slots(formation: str | None) -> List[str]:
    return list(FORMATIONS.get(str(formation or "4-3-3"), FORMATION_433))


def available_formations() -> List[str]:
    return list(FORMATIONS.keys())


def position_fit_level(player_position: str, slot: str, alt_positions: List[str] | None = None) -> int:
    if player_position == slot:
        return 2
    if alt_positions and slot in alt_positions:
        return 1
    if player_position in FALLBACKS.get(slot, []):
        return 1
    return 0


def position_fit_label(player_position: str, slot: str, alt_positions: List[str] | None = None) -> str:
    fit = position_fit_level(player_position, slot, alt_positions)
    if fit >= 2:
        return "natural"
    if fit == 1:
        return "cover"
    return "wrong"


def attribute_map_from_ovr(ovr: int, pos: str, *, player_id: str = "", name: str = "") -> Dict[str, float]:
    base = float(ovr)
    identity = f"{player_id}|{name}|{pos}|{ovr}"
    attrs = {key: base + _stable_variation(identity, key, 4) for key in PLAYER_ATTRIBUTE_KEYS}
    _apply_delta(
        attrs,
        {
            "first_touch": 1.0,
            "technique": 1.0,
            "anticipation": 1.0,
            "decisions": 1.0,
            "composure": 1.0,
            "concentration": 1.0,
            "determination": 1.5,
            "teamwork": 1.0,
            "work_rate": 1.0,
            "natural_fitness": 1.0,
            "stamina": 1.0,
            "balance": 1.0,
            "agility": 0.5,
            "strength": 0.5,
        },
    )
    if pos == "GK":
        _apply_delta(
            attrs,
            {
                "handling": 10.0,
                "reflexes": 11.0,
                "one_on_ones": 9.0,
                "aerial_reach": 9.0,
                "command_of_area": 7.0,
                "rushing_out": 6.0,
                "kicking": 5.0,
                "throwing": 5.0,
                "communication": 6.0,
                "positioning": 7.0,
                "concentration": 6.0,
                "anticipation": 4.0,
                "composure": 2.0,
                "long_passing": 4.0,
                "passing": 2.0,
                "jumping_reach": 5.0,
                "strength": 3.0,
                "agility": 2.0,
                "finishing": -24.0,
                "dribbling": -18.0,
                "crossing": -22.0,
                "tackling": -18.0,
                "marking": -14.0,
                "off_ball": -18.0,
                "heading": -12.0,
                "long_shots": -14.0,
                "free_kick_taking": -12.0,
                "corners": -12.0,
                "acceleration": -5.0,
            },
        )
    elif pos in ("CB", "LB", "RB", "DM"):
        _apply_delta(
            attrs,
            {
                "tackling": 6.0,
                "positioning": 5.0,
                "marking": 5.0,
                "anticipation": 4.0,
                "aggression": 2.0,
                "bravery": 3.0,
                "strength": 2.0,
                "heading": 3.0,
                "off_ball": -2.0,
                "finishing": -6.0,
                "flair": -2.0,
            },
        )
        if pos == "CB":
            _apply_delta(
                attrs,
                {
                    "marking": 4.0,
                    "heading": 5.0,
                    "jumping_reach": 5.0,
                    "strength": 5.0,
                    "passing": 1.0,
                    "long_passing": 2.0,
                    "pace": -1.0,
                },
            )
        elif pos in ("LB", "RB"):
            _apply_delta(
                attrs,
                {
                    "crossing": 6.0,
                    "acceleration": 5.0,
                    "pace": 6.0,
                    "stamina": 5.0,
                    "work_rate": 5.0,
                    "agility": 3.0,
                    "long_throws": 3.0,
                },
            )
        elif pos == "DM":
            _apply_delta(
                attrs,
                {
                    "passing": 5.0,
                    "short_passing": 4.0,
                    "long_passing": 4.0,
                    "vision": 3.0,
                    "decisions": 4.0,
                    "teamwork": 4.0,
                    "work_rate": 4.0,
                    "strength": 3.0,
                    "concentration": 2.0,
                },
            )
    elif pos in ("CM", "AM"):
        _apply_delta(
            attrs,
            {
                "passing": 5.0,
                "short_passing": 6.0,
                "long_passing": 4.0,
                "vision": 5.0,
                "decisions": 4.0,
                "anticipation": 2.0,
                "first_touch": 3.0,
                "technique": 3.0,
                "teamwork": 3.0,
            },
        )
        if pos == "CM":
            _apply_delta(
                attrs,
                {
                    "work_rate": 3.0,
                    "stamina": 2.0,
                    "tackling": 1.0,
                    "positioning": 1.0,
                },
            )
        else:
            _apply_delta(
                attrs,
                {
                    "technique": 3.0,
                    "flair": 6.0,
                    "dribbling": 4.0,
                    "off_ball": 4.0,
                    "long_shots": 4.0,
                    "finishing": 1.0,
                },
            )
    elif pos in ("LW", "RW"):
        _apply_delta(
            attrs,
            {
                "dribbling": 7.0,
                "pace": 7.0,
                "acceleration": 7.0,
                "agility": 6.0,
                "crossing": 6.0,
                "off_ball": 5.0,
                "flair": 4.0,
                "technique": 3.0,
                "first_touch": 3.0,
                "finishing": 2.0,
                "stamina": 2.0,
            },
        )
    elif pos == "ST":
        _apply_delta(
            attrs,
            {
                "finishing": 8.0,
                "composure": 5.0,
                "off_ball": 8.0,
                "anticipation": 4.0,
                "first_touch": 4.0,
                "technique": 3.0,
                "heading": 4.0,
                "strength": 4.0,
                "long_shots": 3.0,
                "penalty_taking": 3.0,
                "passing": -2.0,
                "marking": -5.0,
                "tackling": -6.0,
            },
        )
    if pos != "GK":
        _apply_delta(
            attrs,
            {
                "handling": -18.0,
                "reflexes": -16.0,
                "one_on_ones": -16.0,
                "aerial_reach": -16.0,
                "command_of_area": -16.0,
                "rushing_out": -14.0,
                "kicking": -8.0,
                "throwing": -8.0,
                "communication": -8.0,
            },
        )
    for key in attrs:
        attrs[key] = max(35.0, min(99.0, attrs[key]))
    return attrs


def merge_player_attributes(
    ovr: int,
    pos: str,
    custom: Dict[str, float] | None,
    *,
    player_id: str = "",
    name: str = "",
) -> Dict[str, float]:
    attrs = attribute_map_from_ovr(ovr, pos, player_id=player_id, name=name)
    if not custom:
        return attrs
    for key, value in custom.items():
        if key not in PLAYER_ATTRIBUTE_KEYS:
            continue
        attrs[key] = max(35.0, min(99.0, float(value)))
    if "passing" in custom:
        if "short_passing" not in custom:
            attrs["short_passing"] = attrs["passing"]
        if "long_passing" not in custom:
            attrs["long_passing"] = attrs["passing"]
    return attrs


def merge_team_tactics(custom: Dict[str, float] | None) -> Dict[str, float]:
    tactics = dict(DEFAULT_TACTICS)
    if not custom:
        return tactics
    for key, default in DEFAULT_TACTICS.items():
        if key in custom:
            tactics[key] = max(0.0, min(100.0, float(custom[key])))
        else:
            tactics[key] = default
    return tactics


def merge_team_colors(custom: Dict[str, str] | None) -> Dict[str, str]:
    colors = dict(DEFAULT_COLORS)
    if not custom:
        return colors
    for key in DEFAULT_COLORS:
        value = custom.get(key)
        if isinstance(value, str) and value:
            colors[key] = value
    return colors


def load_league(path: Path) -> Dict[str, Club]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    clubs: Dict[str, Club] = {}
    for club_data in raw["clubs"]:
        players: List[PlayerProfile] = []
        for p in club_data["players"]:
            players.append(
                PlayerProfile(
                    id=p["id"],
                    name=p["name"],
                    position=p["position"],
                    ovr=int(p["ovr"]),
                    attributes=merge_player_attributes(
                        int(p["ovr"]),
                        p["position"],
                        p.get("attributes"),
                        player_id=str(p.get("id", "")),
                        name=str(p.get("name", "")),
                    ),
                    preferred_foot=normalize_preferred_foot(p.get("preferred_foot", infer_preferred_foot(p.get("name"), p.get("position")))),
                    current_stamina=max(0.0, min(100.0, float(p.get("current_stamina", 100.0)))),
                    yellow_card_count=max(0, int(p.get("yellow_card_count", 0))),
                    suspension_matches_remaining=max(0, int(p.get("suspension_matches_remaining", 0))),
                    injury_days_remaining=max(0, int(p.get("injury_days_remaining", 0))),
                    injury_count=max(0, int(p.get("injury_count", 0))),
                    age=max(0, int(p.get("age", 0))),
                )
            )
        clubs[club_data["id"].upper()] = Club(
            id=club_data["id"].upper(),
            name=club_data["name"],
            players=players,
            manager_name=str(club_data.get("manager_name", "")),
            tactics=merge_team_tactics(club_data.get("tactics")),
            colors=merge_team_colors(club_data.get("colors")),
            formation=str(club_data.get("formation", "4-3-3")),
        )
    return clubs


def _lineup_from_saved_ids(club: Club, formation_name: str) -> Tuple[List[PlayerProfile], List[PlayerProfile]] | None:
    if len(club.lineup_xi) != 11:
        return None
    players_by_id = {player.id: player for player in club.players if player.is_available}
    if any(player_id not in players_by_id for player_id in club.lineup_xi):
        return None

    xi = [players_by_id[player_id] for player_id in club.lineup_xi]
    used_ids = set(club.lineup_xi)

    bench_ids = [player_id for player_id in club.lineup_bench if player_id in players_by_id and player_id not in used_ids]
    remaining_ids = [player.id for player in club.players if player.id not in used_ids and player.id not in bench_ids and player.id in players_by_id]
    bench = [players_by_id[player_id] for player_id in bench_ids + remaining_ids]
    if len(xi) != len(formation_slots(formation_name)):
        return None
    return xi, bench


def pick_best_xi(club: Club, formation_name: str | None = None) -> Tuple[List[PlayerProfile], List[PlayerProfile]]:
    formation_name = str(formation_name or club.formation or "4-3-3")
    saved = _lineup_from_saved_ids(club, formation_name)
    if saved is not None:
        return saved

    used_ids = set()
    xi: List[PlayerProfile] = []
    available_players = [player for player in club.players if player.is_available]
    player_pool = available_players if len(available_players) >= len(formation_slots(formation_name)) else list(club.players)

    for slot in formation_slots(formation_name):
        candidates = [
            p for p in player_pool
            if p.id not in used_ids and p.position in FALLBACKS[slot]
        ]
        if not candidates:
            candidates = [p for p in player_pool if p.id not in used_ids]
        fallback_order = FALLBACKS[slot]
        candidates.sort(
            key=lambda p: (
                -(120.0 - fallback_order.index(p.position) * 12.0) if p.position in fallback_order else -20.0,
                -float(p.ovr),
            )
        )
        chosen = candidates[0]
        xi.append(chosen)
        used_ids.add(chosen.id)

    bench = [p for p in player_pool if p.id not in used_ids and p.is_available]
    bench.sort(key=lambda p: p.ovr, reverse=True)
    return xi, bench
