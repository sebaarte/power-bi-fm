"""Parsing des postes FM (ex. 'D/WB (L)')."""


def parse_position(pos_str: str) -> frozenset:
    """
    Retourne un frozenset de tuples (position, côté_ou_None).

    Chaque groupe séparé par une virgule génère toutes les combinaisons
    poste × côté explicitement mentionnés.

    Exemples :
      'GK'              → {('GK', None)}
      'ST (C)'          → {('ST', 'C')}
      'DM'              → {('DM', None)}
      'D/WB (L)'        → {('D', 'L'), ('WB', 'L')}
      'M/AM (RL)'       → {('M','R'),('M','L'),('AM','R'),('AM','L')}
      'D (C), AM (RL)'  → {('D','C'),('AM','R'),('AM','L')}
    """
    if not isinstance(pos_str, str):
        return frozenset()
    combos: set = set()
    for group in pos_str.split(", "):
        group = group.strip()
        if not group:
            continue
        if "(" in group and group.endswith(")"):
            idx = group.index("(")
            pos_part = group[:idx].strip()
            sides = [ch for ch in group[idx + 1 : -1] if ch in ("R", "L", "C")]
            for pos in pos_part.split("/"):
                pos = pos.strip()
                if pos:
                    for side in sides:
                        combos.add((pos, side))
        else:
            for pos in group.split("/"):
                pos = pos.strip()
                if pos:
                    combos.add((pos, None))
    return frozenset(combos)
