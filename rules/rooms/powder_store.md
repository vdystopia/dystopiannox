# Powder store

Family: stores. Feel: **full, in rows, the middle clear**. Kit kind: `powder_store` (a keep's or a mine's magazine).
Profile: `kit/roomtypes.py TYPES["powder_store"]`.

## Purpose and feel

The one room black powder belongs in: kegs of it in tight rows along the walls, kept apart from the house, a few plain
barrels and crates by the door. Every other type never holds a powder keg; this one holds little else. It is a store, and
in a fight it is a trap: one fireball and the room goes up.

## Focal point

The rows of powder kegs (BlackPowderBarrel, BlackPowderBarrel2).

## Pieces

- Must: powder kegs (6+).
- May: a few plain barrels and crates.
- Never: anything that burns or lights (hearths, stoves, braziers), beds, tables, chairs, shelves, rugs, plants, statues,
  sacks.

## Composition

- **Back walls:** powder kegs in tight rows from the corners.
- **Front walls:** powder kegs; a plain barrel or a crate by the door.
- **The middle:** clear: a way to every row.

## QA round 1: the themes applied (2026-10-13)

The user rated other types in QA round 1 and asked that the round's themes apply to this one ("Much of the feedback
boiled down to": too empty, not enough object diversity; no balance or symmetry, things placed randomly, not lined up
with each other). These rules override the Westwood-measured sparseness above where they differ; `kit/finish.py`
composes the room by them after the recipe (its loose pieces are taken up first: `SPEC[kind]['keep']`), ledger
`review/qa1/works.md` (Q1B-n).

- **Stock in heaps, never one kind:** powder kegs heaped in the N and S corners with steel crates and barrels among
  them, the same mixed heap in the W and E corners, heaps along the walls ("Use crates more often alongside the
  barrels", Q1B-3, Q1B-15). Never the same piece twice in a row.
- **The middle** clear in a store under 60 tiles; stacks on the long axis in a bigger one. No lights.
- **Never emptier:** the room ends with at least the visible pieces and kinds its recipe gave it, and master's lab
  average for the type (a tenth more in a room of 80 tiles; `SPEC[kind]['least']`, `Finish.top_up`); bones, candles
  and small gears are one kind at most and never count as pieces.

## Density and openness

| | Westwood's campaign (2 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.17-0.41 | 0.15-0.45 (target 0.30) |
| open floor | 0.03-0.29 | 0.10-0.70 |
| pieces per tile | 0.43-1.00 | 0.30-1.30 |
| distinct types | 2-8 | 2+ |

One kind fills the room by nature (the profile's `monotony` lets it), and its kegs stand in rows along a wall like any
store's barrels (validate/checks.py LINED).

## Size

12-60 tiles (Westwood's: 30-31).

## Culture variants

None.

## Where people stand

Nobody lingers: a guard stands at a back wall clear of the rows, or in the clear middle. (`STANDS["powder_store"]`: a
back wall.)

## Common mistakes

- Powder kegs anywhere else (every other profile's `never_types` holds PowderBarrel).
- A candelabra among the kegs: the house's lights still stand in it (kit/furnish.py add_lights); a lantern by the door
  would be better, for the furnisher's lights to learn.

## Examples

- Westwood: Con07C, cell 119,195 (31 tiles: 22 powder kegs among workstations); Con09c / War09c, cell 62,232 (30 tiles:
  11 powder kegs and 2 barrels).
- Ours: the room lab's powder stores.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's Con09c (30 tiles): 11 powder kegs in knots, a third of them free of the walls, two plain barrels;
  coverage 0.17; no lights (an open flame by powder). Heaped as a store's (`store_heaps`, the "powder" pool).
  Compared with its pool (one Westwood room), so the AUC says little; the kegs counting as the focal piece and as a
  repeated stand-alone piece are the type itself.
