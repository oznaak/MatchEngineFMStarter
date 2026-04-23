from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple

from .models import Club, PlayerProfile

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


def formation_slots(formation: str | None) -> List[str]:
    return list(FORMATIONS.get(str(formation or "4-3-3"), FORMATION_433))


def available_formations() -> List[str]:
    return list(FORMATIONS.keys())


def position_fit_level(player_position: str, slot: str) -> int:
    if player_position == slot:
        return 2
    if player_position in FALLBACKS.get(slot, []):
        return 1
    return 0


def position_fit_label(player_position: str, slot: str) -> str:
    fit = position_fit_level(player_position, slot)
    if fit >= 2:
        return "natural"
    if fit == 1:
        return "cover"
    return "wrong"


def attribute_map_from_ovr(ovr: int, pos: str) -> Dict[str, float]:
    base = float(ovr)
    attrs = {
        "passing": base,
        "short_passing": base,
        "long_passing": base,
        "vision": base,
        "decisions": base,
        "anticipation": base,
        "composure": base,
        "first_touch": base,
        "dribbling": base,
        "finishing": base,
        "crossing": base,
        "off_ball": base,
        "tackling": base,
        "positioning": base,
        "acceleration": base,
        "pace": base,
        "stamina": base,
    }
    if pos == "GK":
        attrs["finishing"] -= 20
        attrs["dribbling"] -= 20
        attrs["tackling"] -= 15
        attrs["positioning"] += 5
        attrs["long_passing"] += 4
        attrs["crossing"] -= 18
        attrs["off_ball"] -= 15
        attrs["acceleration"] -= 5
    elif pos in ("CB", "LB", "RB", "DM"):
        attrs["tackling"] += 6
        attrs["positioning"] += 4
        attrs["finishing"] -= 6
        attrs["anticipation"] += 4
        attrs["off_ball"] -= 2
        if pos in ("LB", "RB"):
            attrs["crossing"] += 4
            attrs["acceleration"] += 2
    elif pos in ("CM", "AM"):
        attrs["passing"] += 5
        attrs["short_passing"] += 6
        attrs["long_passing"] += 3
        attrs["vision"] += 5
        attrs["decisions"] += 3
        attrs["anticipation"] += 2
    elif pos in ("LW", "RW"):
        attrs["dribbling"] += 6
        attrs["pace"] += 4
        attrs["acceleration"] += 5
        attrs["crossing"] += 7
        attrs["off_ball"] += 4
    elif pos == "ST":
        attrs["finishing"] += 7
        attrs["composure"] += 4
        attrs["off_ball"] += 8
        attrs["anticipation"] += 3
        attrs["passing"] -= 2
    for key in attrs:
        attrs[key] = max(35.0, min(99.0, attrs[key]))
    return attrs


def merge_player_attributes(ovr: int, pos: str, custom: Dict[str, float] | None) -> Dict[str, float]:
    attrs = attribute_map_from_ovr(ovr, pos)
    if not custom:
        return attrs
    for key, value in custom.items():
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
                    attributes=merge_player_attributes(int(p["ovr"]), p["position"], p.get("attributes")),
                    current_stamina=max(0.0, min(100.0, float(p.get("current_stamina", 100.0)))),
                )
            )
        clubs[club_data["id"].upper()] = Club(
            id=club_data["id"].upper(),
            name=club_data["name"],
            players=players,
            tactics=merge_team_tactics(club_data.get("tactics")),
            colors=merge_team_colors(club_data.get("colors")),
            formation=str(club_data.get("formation", "4-3-3")),
        )
    return clubs


def _lineup_from_saved_ids(club: Club, formation_name: str) -> Tuple[List[PlayerProfile], List[PlayerProfile]] | None:
    if len(club.lineup_xi) != 11:
        return None
    players_by_id = {player.id: player for player in club.players}
    if any(player_id not in players_by_id for player_id in club.lineup_xi):
        return None

    xi = [players_by_id[player_id] for player_id in club.lineup_xi]
    used_ids = set(club.lineup_xi)

    bench_ids = [player_id for player_id in club.lineup_bench if player_id in players_by_id and player_id not in used_ids]
    remaining_ids = [player.id for player in club.players if player.id not in used_ids and player.id not in bench_ids]
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

    for slot in formation_slots(formation_name):
        candidates = [
            p for p in club.players
            if p.id not in used_ids and p.position in FALLBACKS[slot]
        ]
        if not candidates:
            candidates = [p for p in club.players if p.id not in used_ids]
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

    bench = [p for p in club.players if p.id not in used_ids]
    bench.sort(key=lambda p: p.ovr, reverse=True)
    return xi, bench
