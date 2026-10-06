# Guardroom

Family: martial. Feel: **balanced, lived in**. Kit kind: `guardroom` (a gatehouse's watch room, a gaol's gaoler's room,
a keep's guard post). Profile: `kit/roomtypes.py TYPES["guardroom"]`.

## Purpose and feel

Where the watch waits between rounds: they eat, dice and sleep in turns by the door they guard. Not a barracks (a crew's
bunks in rows) and not an armoury (arms on show): a few cots, a table with a meal on it, the arms within reach on the
walls. Westwood's guard rooms are by a gate or a cell block, with the archer and the swordsman standing in them.

## Focal point

The watch's table in the middle, chairs round it, a meal on it (RoundTableWithFood).

## Pieces

- Must: a table (with its chairs), a cot or two, arms on the wall (hanging swords, pole arms, a bow rack).
- May: a chest at each cot, barrels of water and ale by the front walls, shields and crossed arms or a hunting trophy
  hung on the back walls, a bench, a spittoon.
- Never: bars, counters, an altar, a throne, tombs, lab pieces, forges, stoves, desks, plants, bookcases, black powder.

## Composition

- **A back wall:** two or three cots for the watch off duty, a chest snug at each.
- **The other back wall:** swords, pole arms and bows on the wall; shields and crossed arms between them.
- **Front walls:** a barrel or two by the door; a bench.
- **The middle:** the table with its chairs, a meal on it; a clear way from the door past it.
- **Movement:** in at the door, past the table, to the cell door or the stair beyond.


## Archetypes

Westwood's 11 curated campaign guardroom rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| watch table | 45% | Con06b@104,79, Wiz06a@210,180, Wiz06a@84,151, Wiz06b@46,38, Con06b@179,71 | a guard post: a round table with three or four chairs (one fallen) off the middle, barrels or a chest by the walls; no beds (recipe engine: the kind's own recipe) |
| cot post | 36% | Con03A@110,112, Con03A@164,60, Con03A@81,83, Wiz06a@136,196 | a watch hut: two cots against the walls with chests, a table with food and chairs, barrels (recipe engine: the kind's own recipe) |
| armed hall | 18% | Con02a@93,175, Con06a@69,199 | the keep's guard room: arms on the walls (swords, shields, racks), a long table with benches and a round table, barrels and a chest (recipe engine: the kind's own recipe) |

## Density and openness

| | Westwood's campaign (5 rooms, 4 maps) | Profile |
|---|---|---|
| coverage | 0.10-0.13-0.24 | 0.10-0.32 (target 0.18) |
| open floor | 0.41-0.57-0.59 | 0.30-0.80 |
| pieces per tile | 0.24-0.29-0.47 | 0.15-0.90 |
| distinct types | 4-8-13 | 8+ |
| caps | 2 cots, 1 table at the median | cots 1 per 12 tiles, at most 4; tables 1 per 30, at most 2 |

## Size

20-90 tiles (Westwood's: 15-63).

## Culture variants

Dun Mir's (Con06b's guard posts): Dun Mir chests and hanging shields in place of chests and trophies.

## Where people stand

The guards by their arms on the wall (beside the racks), the sergeant on the far side of the table from the door; never
in the doorway or the way past the table. (`STANDS["guardroom"]`: beside a weapon rack, behind the table, a back wall.)

## Common mistakes

- Rows of cots: that is a barracks. Two or three, against one wall.
- A rack of armour stands in the middle: a guardroom's arms hang on its walls (an armoury racks them in rows).

## Examples

- Westwood: Con03A / War03a, cell 110,112 (63 tiles: two cots, four chests, a table of food with four chairs, hanging
  swords, a bear's head, a spittoon, the archer and the swordsman); Con06a, cell 69,199 (55 tiles: tables, benches,
  shields, hanging swords); Con06b, cell 179,71 (25 tiles); Con03A, cell 81,83 (15 tiles: a guard post with two cots);
  Con02a / War03b, cell 93,175 (25 tiles: the gaoler's room by the cells, a table, racks of bows and swords).
- Ours: the room lab's guardrooms (`py mapgen/designs/roomlab.py 1 guardroom --stands`).

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's 11 curated guard rooms (12-63 tiles, median 20): **the watch's table ringed by chairs** (a round table in
6, food on it in 2, a chair fallen over now and then), a cot or two in 4, Dun Mir chests in 5, barrels in 6, swords or
shields hung in 3-4, a single rack of pole arms or bows in 1-2; no trophies; back walls bare but for the arms (lined
0.05). Our ref gave itself away with lined racks, trophies, two or three cots in a 20-tile room and two table sets
side by side (a tavern). The recipe now: one cot under 120 tiles, the table group with a rug sometimes, one arms piece
(two in a big room) centred on its stretch, a second table only over 110 tiles on its own stretch, pieces 0.25 off
the wall. AUC 0.87 -> 0.73, hard rooms 4 -> 0.
