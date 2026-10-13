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


## Archetypes

Westwood's 2 curated campaign great hall rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Few rooms: the archetypes also draw on kin types' rooms (each counted half a room), as named. Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| hearth in the round | 33% | Con06b@186,38 | a free-standing hearth in the middle, benches in rows round it, shields and banners on the back walls |
| feast hall | 33% | Con07E@173,104 | the hearth on a back wall, many small tables of mixed kinds with chairs along the walls and over the floor, torch poles, trophies |
| long boards | 33% | -kin: Con06a@81,211, Con05C@139,92 | the hearth on a back wall, long boards in parallel on a great carpet with benches down both sides |

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

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

- **Boards, not sets:** the tables joined end to end into long boards (three pieces), benches down both sides at every
  other piece (Con06b: twelve Table1/2 in a U, sixteen benches); a table piece per 24 tiles reads as two to four
  boards, never a grid of little sets.
- **Fire:** the hearth on a back wall and, in a big hall, one free hearth in the middle, standing alone (no benches
  ringing it), the tables set round it (Con06b's U).
- **Walls:** shields, banners or trophies of one theme along the back walls; a bench in each front corner (HB-2).
- **Nothing else:** no plants, no statues (Westwood's great halls hold neither).
- Still missing: the boards in a U round a free hearth (Con06b), and the shell's shape.

## QA round 1 (2026-10-13; review/qa1/rooms.md Q1R-15..Q1R-18)

"The layouts, tables, and chairs are generally pretty good, but the spaces are universally too empty. We need much more
diversity of objects and to fill some of the dead space. It can't just be a room full of tables and chairs." This
overrides Westwood's "no plants, no statues" (its two great halls): the user's word.

- **The tables:** the boards centred on their carpet (RM-GREATHALL-01: "they just need to be centered more"); a table
  off the carpet when the others are on it goes ("the seventh table should be removed"; -02 "the table randomly placed
  in the south corner"; -07 "the fifth one looks out of place"), and a table within 2.2 units of a wall hearth (-04 "too close
  to it"); a bench with no table at it, standing off the walls, goes (-07 "a bench that is out of place").
- **More kinds, in pairs:** statues flanking the hearth, a pair of suits of armour on the other back wall (120+ tiles),
  plants in the two side corners, a chest centred on a back wall, the back walls hung (banners, then arms), a bench along
  each front wall at a bare S corner.
- **The band:** three halls in four a band of brick or cobble one square wide round the whole room, broken only by the
  doorways' own squares, bordered where it meets the floor (-07: "I really like the brick cobblestone tiling around the
  outside of this room ... build this perimeter around the entire room").
- **The hearth** on its own patch of brick, centred on it (-02 "brick cobblestone tiling underneath the oven"; -04 "the
  floor tiling around the hearth is a little bit off-center"): `kit/shells.py hearth_squares`, every hearth.
- Checked: `rooms.qa1_hearth_patch`, `rooms.qa1_south_corner`.
- Round 2 (fullness): a table taken up (a stray, or by the hearth) is set again with two seats on the open floor
  nearest the middle; a hall of 220+ tiles takes four table sets mirrored about its middle. Checked by
  `rooms.qa1_fullness`.
