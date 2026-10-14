# Torture chamber

Family: confinement. Feel: **open, cold, each piece alone**. Kit kind: `torture_chamber` (a keep's or a dungeon's
question room). Profile: `kit/roomtypes.py TYPES["torture_chamber"]`.

## Purpose and feel

The question room under a keep or in a dungeon: the rack in the middle, the iron maiden and the stocks against the walls,
a brazier for the irons, the questioner's desk where he writes down what is said, a chest of instruments, remains on the
floor. Few pieces, set apart, the floor open round the rack: what is there is enough.

## Focal point

The rack (TortureRack4, 6 or 8) standing free in the middle, room all round it.

## Pieces

- Must: the rack; the iron maiden or the stocks; the questioner's desk and chair; a chest.
- May: a second rack in a big chamber, a brazier (DunMirFlameBasinLit), bones and skulls, a body's remains.
- Never: beds, shelves, tables of food, bars, counters, an altar, a throne, tombs, lab pieces, rugs, plants, benches,
  hangings, barrels and crates.

## Composition

- **A back wall:** the iron maiden; the desk and its chair on a stretch of their own.
- **The other back wall:** the stocks.
- **Front walls:** the chest of instruments in a corner; the brazier.
- **The middle:** the rack with room all round it; bones by it.

## QA round 1: the themes applied (2026-10-13)

The user rated other types in QA round 1 and asked that the round's themes apply to this one ("Much of the feedback
boiled down to": too empty, not enough object diversity; no balance or symmetry, things placed randomly, not lined up
with each other). These rules override the Westwood-measured sparseness above where they differ; `kit/works.py`
composes the room by them after the recipe (its loose pieces are taken up first: `SPEC[kind]['keep']`), ledger
`review/qa1/works.md` (Q1B-n).

- **The rack** in the middle with bone heaps mirrored either side of it on the long axis.
- **Back walls:** iron maidens and stocks in a centred row (both back walls in a big chamber), a chest centred on the
  shorter one, the space before it clear.
- **Corners:** flame basins in the W and E corners; a heap of barrels, a water barrel and a crate in the S corner.
- **Never emptier:** the room ends with at least the visible pieces and kinds its recipe gave it, and master's lab
  average for the type (a tenth more in a room of 80 tiles; `SPEC[kind]['least']`, `Finish.top_up`); bones, candles
  and small gears are one kind at most and never count as pieces.

## Density and openness

| | Westwood's campaign (2 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.01 | 0.00-0.25 (target 0.08) |
| open floor | 0.92-0.93 | 0.45-0.99 |
| pieces per tile | 0.05 | 0.01-0.50 |
| distinct types | 1-2 | 2+ |

The rack, the stocks and the iron maiden have no furniture family (rules/room_types.py), so the room score does not
count them in its coverage, variety or walls: a torture chamber measures nearly bare by design.

## Size

20-90 tiles (Westwood's: 20 and 40).

## Culture variants

None in the campaign beyond the ogres' stocks (see the cell's `ogre_pen`).

## Where people stand

The torturer beside the rack, the questioner behind his desk; never between the rack and the door. (`STANDS
["torture_chamber"]`: beside the rack, beside the desk, a back wall.)

## Common mistakes

- Racks in a row down the middle (the first lab version: three in 72 tiles): one rack, a second only in a big chamber.
- A torture chamber in a town house: it belongs to a keep, a gaol or a dungeon (the kit lifts the town style's exclusion
  of torture pieces for this kind only: ROOMS["torture_chamber"]["lift"]).

## Examples

- Westwood: Wiz07C, cell 132,124 (40 tiles: a rack, a body's remains, a chest, a candelabra, empty shelves); Con08d, cell
  151,170 (20 tiles: remains and a chest).
- Ours: the room lab's torture chambers.
