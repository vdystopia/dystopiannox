"""Shared data model for generated structures (buildings, rooms, crossings).

Coordinates: grid cells (x, y) for walls and floor tiles (both on cells with x + y even); world
pixels for objects (23 px per cell). Rotated coordinates u = x + y, v = x - y: walls run along
constant u ('/' lines) or constant v ('\\' lines). A floor tile at (x, y) is drawn centred on grid
corner (x+1, y+1).

Generators write into a nox.Spec (walls via spec.wall, floor via spec.tile, objects via
spec.obj_px, doors via spec.door) and return these records so later steps (furnishing,
townsfolk, validation) know what was built.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

Cell = Tuple[int, int]


@dataclass
class Door:
    gap: Cell                     # wall cell left open for the door
    line: str                     # '\\' or '/': direction of the wall it sits in
    type: str                     # door object type, e.g. WoodenDoor
    connects: Tuple[str, str]     # (room id, room id or "outside")
    px: Tuple[float, float] = (0.0, 0.0)   # door object position (world pixels)


@dataclass
class Room:
    id: str
    tiles: Set[Cell]              # floor tile cells inside the room
    floor: str                    # floor material
    walls: Set[Cell]              # wall cells bounding the room
    doors: List[Door] = field(default_factory=list)
    kind: Optional[str] = None    # room type (bedroom, tavern, shop, ...) set by the planner or furnisher
    building: Optional[str] = None


@dataclass
class Building:
    id: str
    style: str                    # building style key (see rules/out/buildings.json)
    wall_material: str
    rooms: List[Room] = field(default_factory=list)
    footprint: Set[Cell] = field(default_factory=set)   # all floor cells of the building
    entrances: List[Door] = field(default_factory=list)  # doors to the outside


def uv(x, y):
    return x + y, x - y


def xy(u, v):
    return (u + v) // 2, (u - v) // 2
