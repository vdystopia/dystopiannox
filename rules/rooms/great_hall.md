# Great hall

Family: ceremonial. Feel: **open**, the house's heart. Kit kind: `great_hall` (a manor's, a keep's, a town's moot hall).
Profile: `kit/roomtypes.py TYPES["great_hall"]`.

## Purpose and feel

The room every other room of the house opens onto, where the household gathers, feasts and holds the moot. It is big,
and most of it is open floor: a few long tables on a great carpet, the hearth, banners. People cross it from door to
door, so the ways between the doors stay clear. Not a dining room scaled up: fewer sets, more space.

## Focal point

The hearth, centred on a back wall (a second one on the far wall of a long hall), with the tables before it.

## Pieces

- Must: long tables (2+) with their benches; the hearth; hangings (2+: banners, shields and crossed arms, or trophies).
- May: statues in pairs, open hearths with benches round them at the ends of a long hall, columns, a chest or two,
  plants in the corners, a few chairs.
- Never: beds, desks, stoves, shelves, racks, stores (barrels, crates, sacks), lab pieces, tombs, an altar.

## Composition

- **Back wall:** the hearth centred; banners or shields either side.
- **The other back wall:** banners; a second hearth in a long hall.
- **Front walls:** a few benches; plants in the corners.
- **The middle:** long tables with a bench along each side, down the middle on a great carpet of floor tiles; open floor
  round them; open hearths at the ends of a long hall.
- **Movement:** clear ways from every door across the hall to the others; no table in a door's line.

## Density and openness

| | Westwood's campaign (2 rooms, Con06b, Con07E) | Profile |
|---|---|---|
| coverage | 0.16-0.21-0.21 | 0.05-0.18 (target 0.10) |
| open floor | 0.36-0.58-0.58 | 0.55-0.90 |
| pieces per tile | 0.21-0.48-0.48 | 0.08-0.35 |
| distinct types | 12-24-24 | 10+ |
| caps | Con06b: 12 tables, 16 benches; Con07E: 20 tables, 46 seats | tables 1 per 48 tiles, at most 6; benches 1 per 16 tiles in all (Harrowby: 20 of 32 pieces at 1 per 11), at most 24; chests 1 per 80, at most 3 |

## Size

120-400 tiles: the largest room of its building.

## Culture variants

Dun Mir (Con06b): tables and benches in rows, three hearths, eleven hangings. The kit's great halls are the towns' and
keeps': stone, banners, a carpet of floor tiles with the gold trim.

## Where people stand

The lord at the hearth's side, else by a statue or at a back wall facing the tables; never between the long tables or on the carpet's gangway (2026-10-05: a quest giver stood "in a weird place in between two tables" in a hall: StoryMap.free_px takes the open floor nearest the middle, which in a hall of tables lies between them; StoryMap.stand_px does not). (`STANDS["great_hall"]`: beside the hearth, beside a statue, a back wall.)

## Common mistakes

- One bull's head in a 273-tile hall (Harrowby): a hanging tries every type of the room's theme, not only the one drawn
  (a trophy drawn for one wall left the other back wall bare), and the compose step lays two.

- "the sheer number of tables and chairs was too much" (2026-10-04 review: 4-6 fewer table sets, a large floor-tile
  carpet).
- Benches along every wall and eight chests beside the tables' benches (Thornwick, 2026-10-05), and a top-up of 15
  plants and 15 statues once the benches were capped: a capped set must not hand its space to one other piece.
- Bare walls: with little on the floor, the hangings carry the room (Ambermere's moot hall had one).
- Harrowby playtest (2026-10-05, HB-2): "trophies on the wall with statues right on top of them. Double-placed objects. The two treasure chests are both too close to the hearth. It's also a little bit too empty ... along the southeast wall in the south corner." Hangings take bare wall only (Westwood hangs nothing above a piece against the wall), one chest at most and 3 units from any hearth, benches and plants in the front corners first (checker `pieces.hung`, `pieces.chests`, `pieces.clearance`).

## Examples

- Westwood: Con06b / War06b, cell 186,38: Hecubah's castle hall, 208 tiles, 12 tables in rows with 16 benches, three
  hearths, 11 hangings: coverage 0.16, open 0.59.
- Westwood: Con07E, cell 173,104: a feasting hall of 154 tiles, 20 tables of four kinds and 46 seats, a hearth, a
  trader's desk by the door (the classifier once called it a shop): coverage 0.21, open 0.36. These two are the
  campaign's only great halls.
- Ours: Thornwick's and Greywatch's great halls (see `review/out/<map>/rooms/`).
