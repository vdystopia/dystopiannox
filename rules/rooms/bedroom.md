# Bedroom

Family: private. Feel: **cosy and full**. Kit kind: `bedroom` (a family's, an innkeeper's, a lord's chamber). Profile:
`kit/roomtypes.py TYPES["bedroom"]`.

## Purpose and feel

Where one person (or a couple) sleeps and keeps their things. Small, personal, full: the bed, a chest, shelves, a place
to sit, something on the walls. Westwood's commonest building room (50 measured). The user: "many of the smaller
office/bedroom-type rooms seem to be very good".

## Focal point

The bed, headboard against a back wall, its nightstand beside it (apart from it, not touching).

## Pieces

- Must: one bed (two at most, side by side, in a couple's room); a chest.
- May: a nightstand, a run of bookcases end to end, a desk with its chair or a small table with chairs toward the front,
  a bench, a rug before the chest or a carpet, hangings on the back walls, plants in the corners, potion shelves (once).
- Never: three or more beds (that is a barracks), stores (barrels, crates, sacks), stoves, forges, bars, counters,
  racks, an altar, a throne, tombs, straw.

## Composition

- **A back wall:** the bed, headboard to the wall, the nightstand beside it; a run of shelves end to end.
- **The other back wall:** the chest snug and centred, a rug before it; hangings.
- **Front walls:** a desk or a small table with its chair; a bench.
- **The middle:** a rug or a carpet; clear enough to walk from the door to the bed.
- **The door:** a single door (never a double door into a bedroom), not in front of the bed.


## Archetypes

Westwood's 28 curated campaign bedroom rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| cot room | 14% | Con03B@132,98, Con07B@97,219, Con09b@188,86, Con09a@135,41 | a small sleeping room: the bed with its nightstand on the back wall across from the door, a chest by it or on the other back wall, a bookcase at most; nothing in the middle, no desk or table |
| bed and desk | 36% | Con02a@68,156, Con02a@74,98, Con05A@83,51, Con07B@173,213, Con07B@36,34, Con07B@40,38, Con07B@92,224, Con07B@38,28, Con07B@42,32, Con07B@46,36 | a snug chamber in two walls: the bed and nightstand on one back wall, the desk with its chair on the other, a bookcase or two beside one of them, the chest snug at the bed or free before it; the middle bare. In three the door is in a back wall and the bed stands across from it on a front wall |
| sitting end | 32% | Con02a@214,42, Con02a@78,126, Con02a@80,94, Con02a@76,174, Con03B@210,71, Con07B@113,203, Con07D@125,86, Con07D@137,75, War07A@122,199 | a chamber of two ends: the bed end (the bed with nightstands, often in a corner of a back wall) and a sitting or working end (a table with chairs, or a desk among bookcases, candles), a carpet under much of it |
| lords room | 18% | Con06b@85,218, Con06b@92,211, Con06b@149,60, Con07E@183,119, Con06b@97,200 | a big, sparse chamber: the bed on a back wall, a rug and an oval table standing free on the open floor, a chest, trophies or tapestries on the walls; most of the floor bare |

## Density and openness

| | Westwood's campaign (40 rooms, 14 maps) | Profile |
|---|---|---|
| coverage | 0.05-0.14-0.23 | 0.11-0.28 (target 0.14) |
| open floor | 0.34-0.57-0.79 | 0.30-0.80 |
| pieces per tile | 0.11-0.42-0.67 | 0.25-1.0 |
| distinct types | 4-7-12 | 8+ (fewer in a small room) |
| most of one stand-alone piece | 1-2-6 | 3, or 1 per 20 tiles |
| walls with a purpose | 2-2-3 | 3+ (2 under 32 tiles); back walls 25%+ lined |

## Size

14-60 tiles; a lord's chamber up to 90.

## Culture variants

Dun Mir bedrooms (23 of Westwood's 50) take Dun Mir chests and hangings; an ogre sleeps in a den (see barracks).

## Where people stand

The sleeper at the bed's side (never at its foot, where the chest is), else by the chest; never between the table and its chairs. (`STANDS["bedroom"]`: beside the bed, beside the chest, a back wall.)

## Common mistakes

- "Bedroom: very empty; nightstand too close to the bed" (TreePlace review).
- "Bedroom behind the bar: chests and rugs not centred" (DysVale review).
- A double door into a bedroom: "not believable".
- Barrels in a bedroom (DysVale v0.3: the checker's first identity finding).
- A big chamber filled with tables and chairs until it reads as a dining room: one sitting group, then open floor.
- Harrowby playtest (2026-10-05, HB-3): "Too many treasure chests in this room. Let's be real. Why are there four treasure chests? ... Hard rule: A bedroom should never have more than one table and chair set." One chest (two in a chamber of 100 tiles or more: kit/objects.py chest_cap), one table or desk with its chairs (the furnisher's `sets` rule; checker `pieces.chests`, `pieces.sets`).

## Examples

- Westwood: Wiz03b, cell 78,85 (98 tiles, 18 types); Con06b, cell 116,182 (132 tiles, Dun Mir). (G_ForesD's
  63-tile bedroom, once cited here, is a quest map's: not campaign evidence.)
- Ours: Starwell seed 4, room 10, the archmagister's chamber (36 tiles, 15 types, coverage 0.14, open 0.48), and room
  13, the innkeeper's room (28 tiles, 15 types): the smaller bedrooms the user praised.

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's campaign bedrooms (40, then 31 once cells, guard posts and lords' chambers were retyped), piece by piece (review/roomlab/westwood_features.json), against ten generated a round:

- **What they hold**: the bed (26 rooms; a wood bed 8, a cot 6), a nightstand (25), bookcases (25: one alone in about
  half), a desk with its chair (22), a chest (27, Dun Mir or plain). Median 7 kinds of object. A table set in a third of
  them, mostly the bigger rooms, and never a table and a desk together (the HB-3 rule). **No plants** (0 of 40); hangings
  in one in six; a rug object in one in five (a bearskin or a red rug); a carpet laid in the floor tiles far more often.
- **Where**: everything against the two back walls (walls used: median 2). The bed headboard to a back wall about
  0.7 of the room's diagonal from the door, with its nightstand and the chest beside it (bed to chest 0.6 units); the
  desk and its chair with a bookcase beside it (0.66) on the other back wall. A bookcase may stand alone on a short
  stretch between a door and a corner.
- **What gave ours away** (classifier AUC 0.99 at the start): plants in the corners, trophies and tapestries, two rugs
  and a table set on a rug in the middle, a bench on a front wall, a third wall used, too many kinds (9.5 against 7).
- **A stamp reads worse than a mix** (the lesson of rounds r1-r6): a recipe that put Westwood's commonest layout in
  every room (the bed far from the door with the chest and nightstand at its head, the desk and a bookcase beside it,
  two walls used) brought the classifier's AUC from 0.99 to 0.83-0.88, but an independent blind judge picked it out
  more easily (8/10, scored 4.8) than the kit's own recipe (6/10, scored 6.4, above Westwood's 6.0): "the chest pressed
  against the bed's head, a desk crowding the bed, a lone bench on the SE wall with a candelabra, the carpet's middle
  empty, single pieces instead of a run of shelves". The measures are a check, the eye the judge.
- **The recipe now** (`kit/identity.py ROOMS["bedroom"]`, r7): the kit's composition (the bed headboard to a wall with
  its nightstand, the chest centred on its own back wall with a rug before it, shelves end to end, the desk with its
  chair or a small table set, a carpet in some) with Westwood's proportions: the desk in 0.7 of rooms, a table in 0.4,
  a bench in 0.3, a plant in 0.3, at most two hangings and no decoration pass (`decorate=False`).
- **What still gives them away**: the lab's rooms are plain rectangles with doors in the back walls, and 1.25 times
  Westwood's size: with Westwood's pieces they come out at 0.10-0.12 cover, just under the checker's sparse line
  (Westwood's median, 0.117). Westwood's bedrooms are shaped (L-rooms round an alcove, niches, a carpet laid to the
  shape) and carry an odd lived-in piece (a barrel, a crate, a spittoon) the brief forbids.

**After the independent judge** (r7 9/10 and 4.8 against Westwood's 6.6): back to the kit's recipe, which the judge
could hardly tell from Westwood's (ref 6/10), with only the faults it named taken out: one rug, before the chest (not
"two identical rugs"); the table set on the bare floor (not on a rug in a corner); a single bookcase on a short stretch
between doors. The curated Westwood set: 28 bedrooms, p90 42 tiles.

## QA round 1 (2026-10-13; review/qa1/rooms.md Q1R-3..Q1R-7)

"overall very good - table and chest spacing and placement need improvement. more wall objects (banners, trophies,
bookshelves, etc) are needed. Dead spaces in the south corner are too common." RM-BEDROOM-10 is the gold standard: "The
tables on either side of the bed are well spaced and symmetric. The number of candelabras is realistic for the room.
The rug fills the space in the south corner. The chest is perfectly placed at the foot of the bed."

- **Nightstands:** one either side of the bed's head, one kind, 0.45 units off the bed's side (RM-BEDROOM-10: 0.28-0.40;
  -02's 0.22 "too close to the bed"), their centres 0.76 from the wall line (-01's 0.96 "too far from the wall"). The bed
  slides along its wall to make room; a bed in a corner, or sideways along a wall (-06: "attached to the northwest wall"),
  is set again headboard to a back wall, centred on its widest free stretch.
- **The chest** centred at the bed's foot (0.8 units off it) or centred on a wall, never in a corner (-03: "Center the
  chest on the northwest wall").
- **The S corner** never bare: a small table with two chairs when the room has no table (-08: "A small table with two
  chairs would be perfect here"), else a rug, far enough from the front walls to be seen (its edge 1.7 units off them).
  A bedroom of 62 tiles or more (45 as the checker counts them) may keep a desk and one table set
  (`kit/furnish.py BEDROOM_DESK_AND_TABLE`; still one of
  each, HB-3).
- **No table floating** in the middle (-08: "The table in the middle of the room looks out of place"): it goes, and the
  S corner takes the set.
- **Rugs** centred in their half of the room (-07: "more centered in the southeastern volume"); a big bedroom's other half
  its own small rug; never a rug on a carpet; a carpet never runs under the bed (nox20: "clipped and not blended").
- **Walls:** a pair of bookcases end to end on a long bare back-wall stretch (or in a room of 50+ tiles), then hangings
  on the bare stretches of the NE and NW walls, one centred or two symmetric on a stretch, only where there is wall
  behind them (-01, -02, -09: "banners or trophies").
- Checked: `rooms.qa1_nightstands`, `rooms.qa1_chest_corner`, `rooms.qa1_south_corner` (planted STq1Nst, STq1Chc,
  STq1Sth).

**Round 2 (2026-10-13).** Bigger bedrooms were still a bed and a big bare floor. A bedroom of 40+ tiles (room tiles;
about 30 as the checker counts) takes a **second zone** in the half of the room without the bed: a sitting group (a
small table with a chair either side) centred there, on the carpet's middle when a carpet lies there, else on a rug
(a table set standing off to one side moves there whole); the desk with its chair centred on that half's back wall,
else a pair of bookcases. A bench centred on the longest bare front wall (30+ tiles). A table with no chair gets two.
A bed not centred on its wall's stretch and within 2.6 units of a corner is set again centred (RM-BEDROOM-08). A rug
object on a carpet is taken up. A small bedroom's bare half takes a rug. No wardrobe or dresser exists among the
game's objects. Never a bedroom without its chest. Checked by `rooms.qa1_fullness` too.
