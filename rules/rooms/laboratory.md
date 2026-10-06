# Laboratory

Family: work. Feel: **balanced**, used in zones. Kit kind: `laboratory` (a college's, an observatory's workroom).
Profile: `kit/roomtypes.py TYPES["laboratory"]`.

## Purpose and feel

A wizard's workroom: reading, brewing, conjuring, experiments with lightning. A long room is used in zones along its
length, each zone with its own purpose; every wall has a job; one theme throughout. Showpieces stand once.

## Focal point

The work wall: a short bench of wizards' workstations of three kinds with a hanging between, one alchemist's desk beside
it. In the middle, the alchemist's work table.

## Pieces

- Must: lab pieces (3+: workstations, an alchemist's desk, an orrery, a crystal globe, a telescope, generators, fairy
  jars); bookcases (2+); a desk.
- May: one work table (Table1-4) with stools, the bubbling cauldron, a pair of potion shelves, a chest, statues by the
  front walls, tapestries, a carpet, plants.
- Never: a dining or reading table set (round tables, oval tables, tables of food), more than one table, beds, bars,
  counters, forges, an altar, a throne, tombs, benches, stores (barrels, crates, sacks).

## Composition

- **The study end:** the desk on the back wall with the most room before it, near a corner, bookcases either side.
- **The work wall:** a bench of three or four workstations with a hanging between; one alchemist's desk; a pair of
  potion shelves; the chest.
- **The middle:** the alchemist's work table with its stools, glowing jars and the cauldron beside it; a conjuring
  circle (an orrery or crystal globe ringed by four candelabras); a pair of generators apart, mirrored down the length.
- **Front walls:** statues; plants.
- **Movement:** along the length between the zones.

## Density and openness

| | Westwood's campaign (19 rooms, 12 maps) | Profile |
|---|---|---|
| coverage | 0.01-0.09-0.25 | 0.05-0.25 (target 0.14) |
| open floor | 0.22-0.62-0.95 | 0.40-0.85 |
| pieces per tile | 0.12-0.26-0.67 | 0.20-0.70 |
| distinct types | 4-7-15 | 12+ |
| most of one stand-alone piece | 1-2-12 | 2, or 1 per 60 tiles (showpieces once) |
| caps | 1-9 lab pieces, a table in a quarter | lab pieces 1 per 12 tiles, at most 10; one table |

## Size

30-140 tiles.

## Culture variants

Dun Mir laboratories take Dun Mir chests; an apothecary's brewing room is a herbalist.

## Where people stand

The wizard at his work bench (beside a workstation or the alchemist's desk), else by his desk; never in the conjuring circle or between the work table and its stools. (`STANDS["laboratory"]`: beside a workstation, beside the desk, a back wall.)

## Common mistakes

- "It almost looks like some sort of shoddy mess hall with random objects stuffed in it. This room has no sense of
  identity or purpose. No continuity of theme or real feel." (Starwell's college laboratory, 2026-10-05: eight tesla
  coils end to end down the long wall, five dining and reading tables with their chairs down the middle.) The room
  score flags a room whose contents read as another type.
- "The shelves on the NE wall in this room are more of a single instance object. These are not repeatable shelves that
  should line a whole wall" (potion shelves and alchemist's desks in runs).
- A lone showpiece topped up against every wall: the top-up takes a chest or a plant.

## Examples

- Westwood: Wiz07D's laboratory (bookcases with a desk among them, a work island of workstations, the tesla coils
  apart); War07C, cell 134,63 (102 tiles, 19 types); Con07B, cell 121,219 (97 tiles, 18 types).
- Ours: Starwell seed 4, room 8, the college laboratory after its rework (115 tiles, 23 types, coverage 0.10, open
  0.59).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's 19 campaign laboratories keep the middle bare and hold no cauldron, plant or rug: the alchemy table on
  its rug with the cauldron, and the conjuring circle of candelabras, gave every generated room away (AUC 1.0). The
  recipe now keeps to the walls: the desk centred on the deep back wall with a bookcase, two workstations in corners
  on any wall (Westwood stands them on the front walls the most), the alchemist's desk alone, a chest; from 38 tiles a
  table with a chair and a glowing jar; from 80 a pair of coils on a wall, gargoyles, more bookcases and workstations.
- Back walls 0.06-0.35 lined (median 0.15): the recipe's `lined_goal` is 0.15 and `decor_max` 1, else the decor
  pass hangs tapestries to the house's 0.38.
- A desk "toward the corner" never fitted (its end 0.05 from the cross wall, under the snug 0.1): fixed in
  `wall_candidates`, so the small laboratory has its desk.
- Still a giveaway: the back walls are lined more than Westwood's, since its big labs stand their bookcases on the SE
  wall (a house rule forbids it) and the checker wants the room as covered as Westwood's median.
