from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, List, Tuple

from .models import Club, PlayerProfile

FORMATION_433 = ["GK", "LB", "CB", "CB", "RB", "DM", "CM", "AM", "LW", "ST", "RW"]

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


def attribute_map_from_ovr(ovr: int, pos: str) -> Dict[str, float]:
    base = float(ovr)
    attrs = {
        "passing": base,
        "vision": base,
        "decisions": base,
        "composure": base,
        "first_touch": base,
        "dribbling": base,
        "finishing": base,
        "tackling": base,
        "positioning": base,
        "pace": base,
        "stamina": base,
    }
    if pos == "GK":
        attrs["finishing"] -= 20
        attrs["dribbling"] -= 20
        attrs["tackling"] -= 15
        attrs["positioning"] += 5
    elif pos in ("CB", "LB", "RB", "DM"):
        attrs["tackling"] += 6
        attrs["positioning"] += 4
        attrs["finishing"] -= 6
    elif pos in ("CM", "AM"):
        attrs["passing"] += 5
        attrs["vision"] += 5
        attrs["decisions"] += 3
    elif pos in ("LW", "RW"):
        attrs["dribbling"] += 6
        attrs["pace"] += 4
    elif pos == "ST":
        attrs["finishing"] += 7
        attrs["composure"] += 4
    for key in attrs:
        attrs[key] = max(35.0, min(99.0, attrs[key]))
    return attrs


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
                    attributes=attribute_map_from_ovr(int(p["ovr"]), p["position"]),
                )
            )
        clubs[club_data["id"].upper()] = Club(
            id=club_data["id"].upper(),
            name=club_data["name"],
            players=players,
        )
    return clubs


def pick_best_xi(club: Club) -> Tuple[List[PlayerProfile], List[PlayerProfile]]:
    used_ids = set()
    xi: List[PlayerProfile] = []

    for slot in FORMATION_433:
        candidates = [
            p for p in club.players
            if p.id not in used_ids and p.position in FALLBACKS[slot]
        ]
        if not candidates:
            candidates = [p for p in club.players if p.id not in used_ids]
        candidates.sort(key=lambda p: p.ovr, reverse=True)
        chosen = candidates[0]
        xi.append(chosen)
        used_ids.add(chosen.id)

    bench = [p for p in club.players if p.id not in used_ids]
    bench.sort(key=lambda p: p.ovr, reverse=True)
    return xi, bench
