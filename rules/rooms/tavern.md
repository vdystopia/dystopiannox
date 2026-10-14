# Tavern

Family: public. Feel: **balanced, lively**: sets of tables with open floor between. Kit kind: `tavern` (an inn's common
room). Profile: `kit/roomtypes.py TYPES["tavern"]`.

## Purpose and feel

The public drinking room: drink at the bar, eat and talk at the tables, warm by the fire. Many kinds of seat and table,
so it looks lived in; enough open floor to walk from the door to the bar.

## Focal point

The bar, meeting the walls at both ends, its flap mid-run, kegs behind it; and the hearth on a back wall.

## Pieces

- Must: the bar; tables (3+) of three kinds of set; the hearth.
- May: round tables ringed by stools (or cushioned stools), a long table with a bench each side, tables of food with
  chairs, an open hearth with benches round it in a big room, log shelves of tankards beside the hearth, a cask with
  barrels by it, kegs heaped toward the corners, trophies and hangings, benches by the front walls, a rug, plants.
- Never: bookcases, beds, desks, an altar, a throne, tombs, lab pieces, forges, a shop counter, black-powder barrels.

## Composition

- **A back wall:** the hearth centred, a rug before it, shelves of tankards beside it.
- **The other back wall:** trophies and hangings.
- **The bar:** against a wall, meeting it at both ends, kegs behind it.
- **Front walls:** benches; kegs heaped toward the corners, never a whole wall of them (at most 40% of a wall).
- **The middle:** round tables with stools, a long table with benches, a table of food with chairs, open floor between.
- **Movement:** from the door to the bar, between the tables.


## Archetypes

Westwood's 5 curated campaign tavern rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Few rooms: the archetypes also draw on kin types' rooms (each counted half a room), as named. Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| common room | 33% | Con02a@86,105, Con07B@91,177 | the bar in a back corner with kegs behind it, the hearth on another wall, tables of two kinds over the floor with open floor between |
| hearth hall | 17% | Con06a@143,178 | free-standing hearths down the middle, round tables with cushioned stools clustered in one half, a short bar on a back wall with barrels |
| barroom | 17% | Wiz05A@43,19 | the bar across the room with great casks behind it and piled barrels, little seating |
| drinking room | 33% | Wiz05A@48,24; kin: Con06b@104,79, Wiz06a@210,180 | the seating room: round tables with stools against the walls, no bar or hearth of its own |

## Density and openness

| | Westwood's campaign (2 rooms, Con06a, Con07B; five since the room lab's index fix) | Profile |
|---|---|---|
| coverage | 0.12-0.14-0.14 | 0.10-0.30 (target 0.18) |
| open floor | 0.53-0.55-0.55 | 0.40-0.80 |
| pieces per tile | 0.28-0.31-0.31 | 0.15-0.60 |
| distinct types | 23-35-35 | 18+ |
| most of one piece (seats counted) | 3-12-13 | 10, or 1 per 18 tiles |
| caps | a table per 27-42 tiles (Con07B 8 in 216, Con06a 4 in 166) | tables 1 per 28 tiles, at most 12 |

## Size

180-360 tiles: most of an inn's floor (the checker's Westwood taverns run 166-216).

## Where people stand

The barkeep behind the bar (the furnisher's spot); patrons by the hearth; never between the tables or in the way to the bar. (`STANDS["tavern"]`: the keeper's spot, beside the hearth, a back wall.)

## Common mistakes

- 19 of one chair in a 324-tile common room (Harrowby): one dining set composed, a second only from the fill in a big
  room; seats count toward the most of one piece.

- "way too many benches and not enough object diversity ... too many of the same object (chapel benches, tavern tables
  and chairs)" (Greywatch, 2026-10-05: 24-28 tables and 76-83 chairs; then 24-29 of the building's one chair after the
  tables were capped: now round tables take stools).
- "The bar did not meet the walls; the flap read as a window; the tavern felt empty" (DysVale review).
- 17 piled barrels end to end along the Amber Eel's SW wall (Ambermere review, 2026-10-05).
- Bookcases in a common room (the recipe allowed them): shelves of tankards only.

## Examples

- Westwood: Con07B / War07A, cell 91,177 (216 tiles, 35 types: 8 tables of mixed kinds, 20 seats, a bar of 14 pieces,
  coverage 0.14, open 0.55); Con06a, cell 143,178 (166 tiles, 23 types).
- Ours: Starwell seed 4, room 11, the common room (342 tiles).

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

Westwood's five campaign taverns: Con02a (125 tiles, the bar on a raised dais in the E corner, its barman a Shopkeeper
object), Con06a (166, the L bar on the NE wall, two hearth pillars free in the middle, four round tables), Con07B (216,
a U bar ringed by stools, tables of food and long tables on an L of red carpet), Con07B's lower tavern (104, the bar in
the W corner, long tables round a woven carpet), Wiz05A (25, a tap room). Lab pool: taverns and dining halls.
- **The bar** is the room: 9-14 pieces, a long L in any back corner (N, E or W; never the front), ringed on its outer
  face by stools of one kind (Con07B 7 Stool1), a spittoon at its foot, barrels behind it, a pair of great casks against
  the wall just past its end. Never a hearth or shelf behind the counter.
- **Sets:** one or two kinds, each one table type and one seat (Con06a: four RoundTable2 with cushioned stools); the same
  stools at the bar and the round tables (the seat that dominates: 0.2-0.4 of a Westwood tavern's pieces), 2-3 to a
  round table, pulled out from it, the round tables together in one part of the floor; one long table with benches
  and a table of food along the walls or in a corner (Westwood's taverns carry half the benches two long tables gave);
  a table per 28 tiles.
- **Floor:** a bearskin before the hearth, or a woven carpet under the seating; never rugs under the tables.
- **Stores:** 5-8 kegs and casks, by the bar; never a wall of them.
- No plants, no bookcases, shelves of tankards rarely (Westwood's taverns hold none).
- A tavern reads as a living room too (hearth, tables, benches): Westwood's Con02a does; the living room is its kin.
- Still giving it away: fewer lights than Westwood (its taverns burn torch poles, which the house rule forbids), a plain
  rectangle where Westwood's have a dais, an L or a stair (the shell).

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.tavern`); ledger `review/qa1/civic.md` (Q1A-n).
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
- The bar in a back corner with kegs behind it (unchanged).
- The hearth centred on the other back wall, a rug before it, log shelves of crockery mirrored either side.
- The round tables in an even grid (2x2 to 3x3, within the type's table cap less two) centred on one carpet, each with
  four stools at the same distance.
- A pair of long tables with benches mirrored by a front wall.
- Kegs heaped in the S corner and mirrored on the front walls; round sets mirrored where the floor is still bare.
- Trophies and shields at even steps along both back walls.

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2C-6)

The user, the whole set: "Make the floor behind the bars solid brick consistent with no blending ... Terminate the bricks
at the bar ... Four out of five of these taverns have the exact same table and stool configuration, add a little
variance. Overall, they feel just a little bit too empty." RM-TAVERN-04/05: "The bar must be connected to the wall at
both ends." (**Recurring**, DV4-6.) -01: "The brick hearth is not centered on the fireplace"; -01/03/04/05: "The
bearskin rug is just slightly too close to the fireplace"; -03: a table "way too close to the bar"; -04: "The two giant
barrels are too close to each other"; -05: "too empty, especially the east side". Round 2's refinements (PROCESS.md top section) apply too: centred on the room, facing designed, pieces never touching, storage against the wall, floors ending at a hard line, fullness from kinds. Composed by `kit/civic.py`; ledger `review/qa2/ledger.md`.

- **The bar meets both walls:** `furnish.build_bar` takes every wall run of a side (a wall with a notch is two runs; it
  had kept whichever came last and stood both arms against a notch's short wall, ending in the open) and checks each arm
  ends against its own wall with the floor it encloses all the room's. **Recurring, caught now:** `composition.bar_gap`
  also flags a run ending with no wall within six units (it had looked for a wall near the end only).
- **Solid brick behind the bar** to the bar's line as drawn, the bar covering its edge, never blended
  (`civic.bar_floor`; `kit/shells.py lay_zones` leaves it alone); the floor before the bar and inside it kept clear of
  tables (`civic.bar_front`).
- **The hearth on a square's middle** (its patch centred), **the rug a step clear of the fire** (`civic.hearth_rug`),
  **the great casks apart** (`furnish.bar_casks`).
- **Four table layouts**, one drawn per room (`civic.TAVERN_LAYOUTS`): round tables in a grid on a carpet; long tables
  with benches in two mirrored rows, a stool at each end; mirrored clusters of a round table with stools and a square
  table with chairs; a table of food on a carpet flanked by round tables.
- **Fuller:** a table per 22 tiles (was 28, `kit/roomtypes.py`), kegs in all three front corners and in rows on the front
  walls, benches on a front wall, great casks on a front wall where the bar had no room for them, more light, tapestries
  besides the trophies.
