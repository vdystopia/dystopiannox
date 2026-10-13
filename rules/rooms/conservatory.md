# Conservatory

Family: ceremonial. Feel: **open, green**. Kit kind: `conservatory` (a manor's or a college's garden hall). Profile:
`kit/roomtypes.py TYPES["conservatory"]`.

## Purpose and feel

A garden indoors: a fountain or a well in the middle with benches facing it, plants massed along the walls and in clumps
on the floor with paths between, a pair of statues. Westwood's two great garden halls (in the Galava house) hold 33-35
potted plants and a pair of columns; Ix's fountain court has a fountain among barren plants.

## Focal point

The fountain or the well in the middle.

## Pieces

- Must: plants (6+; 8+ to read as a conservatory), a bench.
- May: the fountain or the well, more benches facing it, a pair of statues, statues toward the far corners, a pair of
  columns.
- Never: tables, desks, beds, shelves, hearths, stoves, forges, lab pieces, bars, counters, racks, tombs, barrels,
  crates, sacks, trophies.

## Composition

- **Back walls:** plants massed along them.
- **Front walls:** plants in the corners; a statue toward each far corner.
- **The middle:** the fountain or the well, benches facing it, clumps of plants with paths between.
- **Movement:** round the fountain along the paths.

## Density and openness

| | Westwood's campaign (3 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.02-0.06 | 0.00-0.25 (target 0.06) |
| open floor | 0.76-0.91-1.00 | 0.40-0.95 |
| pieces per tile | 0.08-0.08-0.34 | 0.08-0.60 |
| distinct types | 1-4-9 | 5+ |
| caps | 35 plants in 155 tiles | benches 1 per 25 tiles, at most 6 |

Potted plants do not block the way (they are not solid), so a conservatory measures nearly bare in coverage however green
it is.

## Size

24-220 tiles (Westwood's: 24-177).

## Culture variants

Ix's (Wiz01A): a fountain with lily pads among barren plants.

## Where people stand

The gardener beside the fountain or the well, else against a back wall; never on a path between the clumps. (`STANDS
["conservatory"]`: beside the fountain, a back wall.)

## Common mistakes

- Plants in rows like a storeroom: in clumps, with paths.
- Every plant the same: three or four kinds (Plant1-5, ferns, the flowering one).

## Examples

- Westwood: Con07B / War07A, cell 150,198 (155-177 tiles: 33-35 potted plants and two columns); Con07B, cell 153,226 (72
  tiles: plants); Wiz01A, cell 115,105 (24 tiles: a fountain, lily pads, barren plants, a court half open to the
  sky).
- Ours: the room lab's conservatories.

## QA round 1 (2026-10-13; review/qa1/rooms.md Q1R-14)

All ten rated 2: "Make the floors grass/dirt/outdoor. Occasionally include small patches of cobblestone or tile floor in
sections with proper borders. Make sure plants are situated on dirt or grass so that they look natural. Plants coming
out of the floor tile do not look right. Overall, every single example in this set looks extremely scattered and lacks
any kind of organization or balance. Limit these rooms to a maximum of one well. When there are multiple fountains,
organize them so that they have a balanced, symmetrical layout within the room. Improve the diversity of objects. Add
some different trees, especially apple trees with apples on the ground. Try some similar techniques as the exterior
gardens - occasional rows of crops. Include additional objects related to gardening, like wheelbarrows and barrels of
tools. Include a few crates and barrels rarely. Make sure benches are against the walls."

The room is composed whole now (`kit/finish.py _conservatory`; the recipe above is its list of pieces):
- **Ground:** grass (GrassNorm) over the whole floor; beds of dirt (DirtDark2) along the NE and NW walls, bordered,
  planted in clumps with gaps between; two in five rooms a bordered square of paving (cobble) under each fountain.
- **The fountain** in the middle; two, mirrored along the room's length, in a room of 140 tiles or more (three in five);
  or the one well (a quarter of the one-fountain rooms, and a narrow room). Never two wells.
- **Benches** against the long walls, facing each fountain.
- **Apple trees** (TreeApple) in the side corners on their own dirt, apples (RedApple, the item a player picks up) fallen
  round them.
- **Crops:** in a room of 90 tiles or more with one fountain, two beds of a crop each, mirrored at the room's ends, two
  rows to a bed (corn, tomatoes, cabbage, as the exterior gardens).
- A barrel of tools by the beds; a third of the rooms a barrel or a crate. No wheelbarrow exists among the game's
  objects (none in `corpus/out/nox_corpus.db`): the barrel of tools stands for the gardener's gear.
- Checked: `rooms.qa1_garden_floor`, `rooms.qa1_wells` (planted STq1Grd, STq1Wel).
- Round 2 (fullness): a pair of statues flanking the first fountain along the room's length, facing it; four clumps of
  plants on dirt at each fountain's diagonals in a room of 90+ tiles or with two fountains, mirrored; a small room
  (under 80 tiles) plants its front walls' ends as well. Checked by `rooms.qa1_fullness`.
