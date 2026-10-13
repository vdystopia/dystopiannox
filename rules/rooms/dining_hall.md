# Dining hall

Family: public. Feel: **balanced**: rows of tables, orderly. Kit kinds: `dining_hall` (a manor's), `mess_hall` (a
garrison's or a camp's), `ogre_hall` (where the ogres feast). Profile: `kit/roomtypes.py TYPES["dining_hall"]`.

## Purpose and feel

Where a household or a crew eats together at long tables. Orderly rows, seated along both sides; the hearth warms it.

## Focal point

The long tables in rows, the hearth on a back wall before them.

## Pieces

- Must: tables (2+), seated (chairs in a household, benches in a mess); the hearth.
- May: shelves of crockery either side of the hearth, hangings, a table of food, a carpet, statues, benches by the front
  walls, plants, a chest.
- Never: beds, desks, an altar, a throne, tombs, lab pieces, forges, counters, racks; barrels belong in the kitchen.

## Composition

- **A back wall:** the hearth centred, shelves of crockery either side.
- **The other back wall:** hangings above; a sideboard table of food.
- **Front walls:** benches; plants in the corners.
- **The middle:** long tables in rows, seated along both long sides (Westwood seats 75% of the chairs at its long
  tables there), a table with no seats left out.

## Density and openness

| | Westwood's campaign (3 rooms, Con05C, Con06a, Wiz05A) | Profile |
|---|---|---|
| coverage | 0.06-0.08-0.15 | 0.10-0.32 (target 0.17; a mess 0.24) |
| open floor | 0.51-0.61-0.76 | 0.30-0.80 |
| distinct types | 6-10-12 | 8+ |
| caps | Con06b's mess: 12 tables in 208 tiles | tables 1 per 16 tiles, at most 8 (a mess 1 per 17, at most 10; ogres 1 per 22) |

## Size

50-220 tiles.

## Culture variants

- `mess_hall`: long tables with benches, log shelves of crockery, no round tables.
- `ogre_hall`: crude round tables ringed by stools and ogre benches, a fire pit in the middle, carcasses and meat on the
  floor, straw in the corners, barrels; torch poles.

## Where people stand

The host at the hearth's side, else at a back wall facing the tables; never between the tables or in a row's gangway (2026-10-05: a quest giver stood "in a weird place in between two tables" in a hall). (`STANDS["dining_hall"]`: beside the hearth or fire pit, a back wall.)

## Common mistakes

- "Mess hall: good layout but needs more" (TreePlace review): more tables in rows, benches along the walls, crockery
  shelves, hangings.
- A mess too small for rows (TNorth's 32-tile mess held no table): a mess needs 50 tiles.

## Examples

- Westwood: Con06a, cell 81,211 (55 tiles, 12 types); Con05C, cell 139,92 (110 tiles: the ogres' feast).
- Ours: Starwell seed 4, room 15, the garrison's mess (99 tiles).

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

Westwood's three: Con06a (55 tiles), Con03B's miners' mess (108), the ogres' Con05C (110).
- **Two or three tables,** never a grid: a table piece per 26-32 tiles, at most one per 30; benches along them with a
  chair or two; a table of food or a round table with chairs in a big hall.
- **Crockery, not books:** two log shelves by the hearth at most (bookcases made it read as a library).
- **Casks and barrels** in a cluster or two, never down the walls; **no plants, no statues,** no benches topped up along
  the walls.
- **The ogres' hall:** two to five crude tables ringed by stools, barrels heaped, a little meat; no straw on the floor.

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.dining_hall, civic.ogre_hall`); ledger `review/qa1/civic.md` (Q1A-n).
These rules come before Westwood's statistics above wherever they disagree (the user's word over Westwood's habit).

Every room of the type:
- **The dead space is used** (Q1A-1, Q1A-7): the S corner takes a group of its own; the front corners and the SE and
  SW walls take mixed stock, benches or urns, mirrored; where the floor is still bare a group goes there, bigger rooms
  more. Checked: `civic.s_corner`.
- **Diversity** (Q1A-2): several kinds of piece, more in a bigger room; heaps mix their kinds (never one family alone,
  never the same piece side by side). Checked: `civic.kinds`.
- **The back walls dressed** (Q1A-3): the NE and NW walls hung at even steps, mirrored about each stretch, one
  tapestry colour to a room; a bare stretch takes a pair of the type's wall piece. Checked: `civic.bare_wall`.
- **Balance** (Q1A-4, Q1A-13): pieces centred on their wall or between a piece and a wall; mirrored pairs; one kind of
  table, column, statue to a room; lights in matching corners or flanking the focal piece.
- **Carpets** (Q1A-10): a table set at its carpet's exact middle; a carpet only where its whole rectangle and trim
  lie on the room's floor.

For this type:
- Composed on the axis from the door (Q1A-5): the high table across the far end, seated, a pair of lights
  flanking it, sideboards of crockery mirrored on that wall.
- The long tables in rows down the axis, evenly spaced, on one carpet centred under them (a mess hall's on the bare
  floor, benches both sides).
- The hearth centred on a side back wall between crockery shelves.
- Casks heaped in the W and E corners, barrels in the S corner, a pair of benches mirrored on a front wall, an urn in
  the N corner; tapestries of one colour (a mess hall's trophies) at even steps.
- **The ogres' feasting hall is its own category** (Q1A-12, the barracks set: "Ogre barracks are completely different"):
  minimal but balanced: the fire pit in the middle, crude tables with their stools mirrored about it (a second pair
  across the other axis in a hall of 150 tiles), meat between them, sacks and barrels heaped in matching corners, a
  carcass in the N corner, skulls hung on the back walls; never a bare corner.
