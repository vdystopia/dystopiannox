"""The room lab's shared setup: import paths, output folders, and the room types it knows.

Every room lab module imports this first. The import order matters: rules/room_types.py and review/rooms.py share a
module name with rules/rooms.py, so the paths are set as review/roomscore.py sets them.

Outputs (all under review/out/, which git ignores):
- review/out/roomlab/<type>/<iter>/          one iteration of one type: the generated map, renders, scorecard
- review/out/roomlab/_westwood/<type>/       Westwood's campaign rooms of the type, rendered the same way (cached)
- review/out/renders/                        full-map renders (shared with review/review.py and review/rooms.py)
Committed reference data: review/roomlab/westwood_features.json (every Westwood campaign room's features).
"""
import os, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.dirname(HERE)
REPO = os.path.dirname(REVIEW)
for p in (os.path.join(REPO, "validate"), os.path.join(REPO, "mapgen"), os.path.join(REPO, "rules"), REVIEW, HERE):
    if p in sys.path: sys.path.remove(p)
    sys.path.insert(0, p)

import mapdata as MD          # noqa: E402
import checks as C            # noqa: E402

OUT = os.path.join(REVIEW, "out", "roomlab")
WW_OUT = os.path.join(OUT, "_westwood")
MAPS_OUT = os.path.join(REPO, "mapgen", "out", "roomlab")
WW_FEATURES = os.path.join(HERE, "westwood_features.json")
WW_INDEX = os.path.join(REPO, "rules", "rooms", "westwood.json")


def curate(rooms):
    """Westwood rooms with the verdicts by eye applied (rules/rooms/curated.json via rules/rooms/curated.py): misfiled
    rooms retyped, rooms not to learn from left out. Idempotent, so a fresh westwood.json passes through unchanged."""
    import importlib.util
    mod = sys.modules.get("ww_curated")
    if mod is None:
        spec = importlib.util.spec_from_file_location("ww_curated", os.path.join(REPO, "rules", "rooms", "curated.py"))
        mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
        sys.modules["ww_curated"] = mod
    return mod.apply(rooms)


def types():
    """The room types of kit/roomtypes.py, in the brief's order."""
    from kit.roomtypes import TYPES
    return list(TYPES)


def seed_of(*parts):
    """A reproducible integer from strings and numbers (never Python's hash(), which changes from run to run)."""
    return zlib.crc32("|".join(str(p) for p in parts).encode("utf-8"))


def iter_dir(typ, it):
    return os.path.join(OUT, typ, it)


def rel(path):
    """A path relative to the repository, with forward slashes, for reports."""
    return os.path.relpath(path, REPO).replace("\\", "/")
