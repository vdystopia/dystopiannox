# Barracks

Family: martial. Feel: **full, orderly**. Kit kinds: `barracks` (soldiers' or miners' bunks), `ogre_den` (where the
ogres sleep). Profile: `kit/roomtypes.py TYPES["barracks"]`.

## Purpose and feel

Bunks for a crew: everyone sleeps in one room, in rows. Order is the point: beds of one kind, evenly spaced, each with its
chest.

## Focal point

The row of bunks, headboards against a wall.

## Pieces

- Must: beds (2+, 3+ to read as a barracks), all of one kind.
- May: a nightstand between neighbours, a chest a step beyond each bed's foot, a rug before each bed, shelves for gear end
  to end, shields and trophies, a table with seats, a freestanding hearth, benches.
- Never: bars, counters, an altar, a throne, tombs, lab pieces, forges, stoves, black-powder barrels.

## Composition

- **A wall (a front wall when the back walls are wanted for shelves):** beds in a straight row side by side, headboards to
  the wall, at least 0.9 apart, a nightstand between neighbours.
- **A back wall:** shelves for gear end to end; shields and trophies.
- **The middle:** a table with its seats; a hearth with benches in a big room.


## Archetypes

Westwood's 7 curated campaign barracks rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| bunk row | 43% | Con06b@160,48, Con06b@106,192, Con05A@48,66 | bunks of one kind in a row on one wall with chests, the crew's tables and chairs free before them, arms hung (recipe engine: the kind's own recipe) |
| ogre den | 57% | Con05C@122,91, Con05C@140,109, Con09c@50,210, Con09c@62,206 | the ogres' den: straw heaped over the floor, crude beds on the back walls, a table with stools, barrels in a knot, meat (recipe engine: the kind's own recipe) |

## Density and openness

| | Westwood's campaign (16 rooms, 7 maps) | Profile |
|---|---|---|
| coverage | 0.03-0.06-0.25 | 0.12-0.34 (target 0.24) |
| open floor | 0.36-0.65-0.78 | 0.25-0.75 |
| pieces per tile | 0.11-0.23-0.77 | 0.20-0.80 |
| distinct types | 2-5-14 | 8+ |
| caps | 3+ beds always of one kind, in a row | beds 1 per 12 tiles, at most 12 |

## Size

40-200 tiles.

## Culture variants

- `ogre_den` (17 of Westwood's 26 barracks are ogres'): straw heaped free on the floor (72% of ogre rooms), crude beds
  against the back walls, a fire pit ringed by stools in the middle, meat and carcasses, barrels; torch poles. Its focus
  is the fire pit.

## Where people stand

A soldier beside his bunk (at its side, not at its foot where the chest is), an ogre by the fire pit; never in the row's walkway or between the table and its seats. (`STANDS["barracks"]`: beside a bed, beside the fire pit, a back wall.)

## Common mistakes

- An ogre den of 26 straw heaps in 32 pieces (Harrowby; `identity.monotony`): the straw scatter's per100 counts heaps of
  2-3, so 4 heaps per 100 tiles gives Westwood's 8.6 straw per 100; three crude beds; meat and carcasses 3 per 100.

- Beds of mixed kinds, or scattered: "All of Westwood's rooms with 3 or more beds use one kind, in a row."
- Cots read sideways (the cot numbering comes from the pillows).

## Examples

- Westwood: War09c / Con09c, cell 62,206 (56 tiles, 14-15 types: an ogre den); Con05C, cell 122,91 (136 tiles).
- Ours: Starwell seed 4, room 14, the soldiers' bunks (187 tiles).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's ogre barracks (Con05C, Con09c, Con11a, War02A) have no fire pit: straw heaped on the floor is the commonest
  piece, barrels in a knot, a crude bed or three, a crude table with stools in some, meat, a primitive obelisk. The ogre
  den follows them (AUC 1.0 -> 0.86). A den of straw is a pen's kin (`cell`).
- Westwood's curated town and Dun Mir barracks (Con05A, Con06b) hold bunks in a row, chests, the crew's table with chairs
  and a rack or two of arms; no nightstands, shelves, rugs or hangings (`bed_nightstands=False`, `decor_max` 0,
  `lined_goal` 0). The ogre den takes the crude table with its bench and stools in all but the smallest.


## QA round 1 (2026-10-13; review/qa1/rooms.md Q1R-8, Q1R-9)

"In general, too empty and not enough objects to complement the beds. instead of having two walls lined with beds, try
one wall of beds and one wall of weapon and armor racks. Transform the barracks from a giant room with beds to a place
where warriors sleep and keep their combat gear." The ogres' den is a type of its own now (`ogre_den.md`); this brief is
the human barracks. RM-BARRACKS-09 (56 tiles, a log cabin) is the best example: "It just needs more decorations on the
walls and a few more objects."

- **One wall of bunks:** the bunks of one kind headboard to one wall, evenly spaced 1.0-1.6 apart, the wall holding the
  most (a front wall before a back wall), a chest at each foot; never two walls of beds (`bed_row(single=True)`;
  `kit/finish.py bunk_wall`).
- **One back wall of racks:** a row of racks of arms and armour, the kinds alternating; a second row from 110 tiles.
- Arms hung on the bare back walls; the crew's table in a big room's middle with its chairs; knots of barrels in bare
  corners.
- Checked: `rooms.qa1_racks` (planted STq1Rck).
- Round 2: a barracks of 110+ tiles takes the crew's boards down its middle along its length (two long tables end on,
  benches both sides) with a pair of armour stands at the row's ends, mirrored; a small room whose back walls are
  taken puts its racks on any wall. Checked by `rooms.qa1_fullness`.

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2F-2)

Rated 3.8. The user's chest rule for the set: "if there is one treasure chest, put it against the wall. If there are 6
or fewer beds, multiple treasure chests can be placed, put them at the foot of every bed facing away from the bed"
(RM-BARRACKS-01/03/05 "fix chest"). -02 "Needs more banners or trophies on the northwest wall, especially the north
corner"; -03 "Slightly too much armor and weaponry in the south corner". Now (`kit/finish.py _barracks`):
- **Chests, two arrangements only** (`_barracks_chests`, placed right after the bunks): with six beds or fewer
  (`BARRACKS_FOOT_CHESTS`), a chest at every bed's foot, 0.5 units off it, its back to the bed (the variant for the bed's
  head wall), all or none; otherwise (or when a foot has no room) one chest flush against a wall, centred on its free
  stretch. Nothing else.
- **Racks** take at most 0.7 of their wall's stretch, centred (`RACK_SHARE`), and a big room's second row is half as
  long, on another wall, kept 3 units clear of the first row's ends, so two rows never meet in a corner.
- **Back walls dressed to their corners:** hangings (arms, tapestries, trophies) on every bare stretch of the NE and NW
  walls, 0.6 units from the corners (`hang_backs(edge=0.6)`).
- A heap of kegs and barrels of tools flush on the wall the racks left bare (a front wall first), kept off the racks:
  the room's fullness from other kinds than arms (Q2T-8).
- Checked: `rooms.qa2_gap`, `rooms.qa2_wall` (a chest flush; planted STq2Wal, STq2Mid).

## QA round 3 (2026-10-23; review/qa3/ledger-rooms.md Q3R-6..8)

Rated 4.4 (04, 05 kept at 5). RM-BARRACKS-01: "The chests are perpendicular to the beds. Change the way they are facing
so that their back is to the bed and their front is facing away from the bed." 02: "Move the three chests slightly
closer to the three beds." 03: "Add another chest in the empty gap between the pairs of beds." Round 2's rule stands
(one chest flush on a wall, or with six beds or fewer a chest at every bed's foot facing away); refined:

- **A foot chest's back to its bed, its front away, for every wall a bed heads on**: the chest is the head wall's
  chest, Westwood's numbering (`kit/finish.py CHEST_ON_WALL`): a bed headed on the NW wall takes Chest4 (facing SE), NE
  Chest3 (facing SW), SW Chest2 (facing NE), SE Chest1 (facing NW). Westwood's own beds show the same (Bed4 with Chest4
  at its SE foot, Bed3 with Chest3 at its SW foot, Bed2 with Chest2 at its NE foot, Bed1 with Chest1 at its NW foot:
  the corpus, 60 cases). The cause in round 3: the mined rule for a SW wall (`rules/out/decoration.json`, 3.5 weighted
  uses) named Chest4, the NW wall's chest, so 01's beds headed on the SW wall had their chests side-on.
- **Snug at the foot, as drawn**: a cot is drawn shorter than its footprint and above it, so a chest at a foot toward
  the camera (a bed headed on the NE or NW wall) reached a unit further off than its footprint stood (round 3's 0.5
  units read as a chest's length off the foot). Such a chest reaches into the footprint's empty end, its front just past
  it (`FOOT_CHEST_GAPS`: -0.55 units first); at a foot away from the camera (headed on the SE or SW wall), whose drawn
  foot comes nearer, it keeps 0.35. The chest is the bed's own piece: no gap is held between them.
- **A chest in every gap between pairs of beds**: a close row is laid in pairs (the knowledge base's runs of two beds
  along a wall leave every third bed's place empty: 03's gaps of 1.0 and 3.9 units in turn); each gap between pairs (a
  bed's width wider than the row's tightest gap) takes a chest flush on the head wall, centred, its back to the wall
  (`_pair_gap_chests`). With them the room keeps no other chest against a wall; a room of six beds or fewer keeps its
  foot chests as well.
- **Checked by** `rooms.qa3_foot_chest` (planted STq3Fac: a foot chest side-on; STq3Far: 0.6 units off a foot toward
  the camera) and `rooms.qa3_pair_gap` (STq3Gap); `rooms.qa2_chests` counts the chests between pairs apart. Pictures:
  review/out/roomlab/barracks/qa4/renders/.
