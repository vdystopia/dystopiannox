"""Westwood's campaign rooms judged by eye: rules/rooms/curated.json.

The classifier (westwood.py classify) files each room by its contents; looking at the rooms showed many filed under the
wrong type (a guard post with a cot as a bedroom, a keg cellar as a storeroom, an ogre pen as a barracks) or not rooms
to learn from at all (a corridor, a cave pocket, an outdoor graveyard, a burning house or a trap set piece, a second
campaign's copy of a room already counted). curated.json records the verdict for every indexed room, keyed by its
stable id `<map>@<x>,<y>` (the room centre in the index):

    {"keep": true, "why": ...}                 it is the type it is filed as
    {"retype": "<type>", "why": ...}           it is really this type (any kit/roomtypes.py type, or "passage")
    {"exclude": true, "why": ...}              not a room to measure or show (dropped from the index and the lab)

Each entry also keeps `filed`: the type the classifier gave when it was judged.

apply() is the hook: westwood.py calls it on the rooms it finds before it writes westwood.json, and the room lab calls
it on the index and on westwood_features.json as it loads them, so a stale file still honours the verdicts. Idempotent.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, "curated.json")
_CACHE = None


def room_id(r):
    """The stable id of an index room (or anything with `map` and `centre`)."""
    return f"{r['map']}@{r['centre'][0]},{r['centre'][1]}"


def load():
    global _CACHE
    if _CACHE is None:
        if os.path.exists(PATH):
            with open(PATH, encoding="utf-8") as f:
                _CACHE = json.load(f)["rooms"]
        else:
            _CACHE = {}
    return _CACHE


def verdict(r):
    return load().get(room_id(r))


def apply(rooms, excluded=None):
    """The rooms with the verdicts applied: retyped rooms take their true type (the classifier's type kept as
    `classed`), excluded rooms are left out (appended to `excluded` when a list is given). Rooms with no verdict pass
    unchanged."""
    out = []
    for r in rooms:
        v = verdict(r)
        if not v:
            out.append(r); continue
        if v.get("exclude"):
            if excluded is not None:
                excluded.append(dict(r, why=v.get("why", "")))
            continue
        if v.get("retype") and r["type"] != v["retype"]:
            r = dict(r, type=v["retype"], classed=r.get("classed", r["type"]))
        out.append(r)
    return out
