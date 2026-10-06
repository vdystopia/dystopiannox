"""The scene lab's shared setup: import paths, output folders, reproducible seeds.

Every scene lab module imports this first (the room lab's review/roomlab/labenv.py, copied and adapted).

Outputs (under review/out/, which git ignores):
- review/out/scenelab/<scene>/<iter>/        one iteration of one scene type: the lab map, renders, scorecard
- review/out/scenelab/_westwood/<scene>/     Westwood's campaign scenes of the type, rendered the same way (cached)
- review/out/renders/                        full-map renders of Westwood's maps (shared with review/review.py)
Committed reference data: review/scenelab/westwood_scenes.json (every labelled Westwood campaign scene, its pieces and
its features).
"""
import os, sys, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REVIEW = os.path.dirname(HERE)
REPO = os.path.dirname(REVIEW)
for p in (os.path.join(REPO, "validate"), os.path.join(REPO, "mapgen"), os.path.join(REPO, "rules"), REVIEW, HERE):
    if p in sys.path: sys.path.remove(p)
    sys.path.insert(0, p)

import mapdata as MD          # noqa: E402

OUT = os.path.join(REVIEW, "out", "scenelab")
WW_OUT = os.path.join(OUT, "_westwood")
RENDERS = os.path.join(REVIEW, "out", "renders")
WW_INDEX = os.path.join(HERE, "westwood_scenes.json")
CELL = 23


def seed_of(*parts):
    """A reproducible integer from strings and numbers (never Python's hash(), which changes from run to run)."""
    return zlib.crc32("|".join(str(p) for p in parts).encode("utf-8"))


def iter_dir(scene, it):
    return os.path.join(OUT, scene, it)


def rel(path):
    """A path relative to the repository, with forward slashes, for reports."""
    return os.path.relpath(path, REPO).replace("\\", "/")
