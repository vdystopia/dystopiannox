# Room types

There is no one-size-fits-all room. The user, after the Starwell playtest (2026-10-05):

> "I'm not sure if it's a good idea to check every room against the one particular room that I called out as being very
> good. Different rooms have different dynamics and identities. What made that room good was the fact that it had
> everything a study should have and in the right arrangement. A throne room, however, is very different than a study
> and should, by its nature, be more open with less object density. The key is to classify structure and room types and
> build a knowledge of what makes each identity good."

So each room type has its own brief here (`<type>.md`: purpose and feel, focal point, pieces, composition, density,
size, culture variants, mistakes, examples), its own profile in `mapgen/kit/roomtypes.py` (the ranges and rules the
furnisher and the room score read), and its own recipe per kit kind in `mapgen/kit/identity.py ROOMS`. The room score
(`review/roomscore.py`) judges every room against its own type, never against another room.

The numbers come from Westwood's campaign maps only (Con, War, Wiz: never the quest maps G_* nor the multiplayer maps),
each building room classified by its contents and measured exactly as our rooms are (`py rules/rooms/westwood.py`
writes `westwood.json`; a room the three campaigns share counted once: 235 rooms; the great rooms the finder
misses, read by hand: `HAND`), from the playtester's verdicts, and from our own praised rooms. Westwood's figures below are
p10-p50-p90.

**Curated by eye (2026-10-05).** Every one of the 235 rooms was looked at in the room lab's render: `curated.json`
(applied by `curated.py` in `westwood.py` and the room lab) keeps 110 as filed, retypes 67 (guard posts filed as
bedrooms and armouries, keg cellars and winch rooms filed as storerooms, the ogres' pens filed as barracks, statue
tombs filed as halls, cottages filed as kitchens, households filed as libraries...) and excludes 58 (passages, cave
pockets, outdoor graveyards and gardens, burning-house and trap set pieces, unfurnished rooms, and a second campaign's
copy of a room already counted): 177 rooms. The Westwood counts in the table below are the classifier's, before the
curation; `westwood.json` has the curated ones.

## The types, by family

Ranked within each family by how often they occur (Westwood's building rooms / our 11 designs' rooms, 2026-10-05); the
types added for variety ("More types" below) follow their family's older types, ranked by use, their Westwood count
marked * (rooms read by hand from every campaign room the finder leaves untyped or types loosely; see each brief).

| Family | Type | Westwood | Ours | Kit kinds | What makes it good |
|---|---|---|---|---|---|
| private | [bedroom](bedroom.md) | 40 | 36 | bedroom | the bed headboard to a back wall with its nightstand, the chest snug with a rug before it, shelves end to end; cosy and full, one sleeper's things |
| private | [living room](living_room.md) | 15 | 32 | living_room, dwelling | the hearth centred on a back wall flanked by shelves, the table and chairs before it on a carpet: the household gathers here |
| private | [study](study.md) | 2 | 8 | study | the desk centred on a back wall among bookcases, a meeting table on a carpet, a curio, statues: everything a scholar needs, in the right places |
| private | [solar](solar.md) | 4* | - | solar | the lord's chamber in two ends: the bed end and the sitting end (the hearth between bookcases, the desk, a small table on a carpet) |
| work | [laboratory](laboratory.md) | 19 | 2 | laboratory | used in zones: the study end, the work wall of workstations, the alchemist's table and a conjuring circle in the middle; one of each showpiece |
| work | [kitchen](kitchen.md) | 10 | 9 | kitchen | the hearth with the cauldron a step off, provisions lining a back wall, a work table with its food, stores heaped by the front walls |
| work | [library](library.md) | 7 | 3 | library | books end to end on both back walls, stacks in rows in a big one, a reading table on a carpet |
| work | [smithy](smithy.md) | 2 | 7 | smithy | the forge's coals, the bellows beside them, the anvil before them, water to quench; the smith behind his counter |
| work | [herbalist](herbalist.md) | 2 | 3 | herbalist | the cauldron bubbling, one pair of potion shelves, books of remedies end to end, herbs in sacks and pots |
| work | [winch room](winch_room.md) | 6* | - | winch_room | gear trains on the walls, the great winch standing free with room to work it, spare parts by the door |
| work | [observatory](observatory.md) | 2* | - | observatory | a telescope free and one at a wall, star charts between the bookcases, the astronomer's desk, the chart table |
| work | [workshop](workshop.md) | 1* | - | workshop | the work bench with the job by it, tools on the shelves, wheels and gears, tool barrels toward the corners; no forge |
| work | [infirmary](infirmary.md) | 0 | - | infirmary | a row of cots with nightstands, the cauldron, a pair of potion shelves and books of remedies, the healer's table |
| stores | [storeroom](storeroom.md) | 22 | 21 | storeroom, ore_store, ogre_hoard, granary | supplies in good order: stocked shelves, heaps in the corners, crates side by side, an aisle to walk |
| stores | [cellar](cellar.md) | 4* | - | cellar | kegs in tight rows from the corners, a great cask standing free, aisles; never shelves or sacks |
| stores | [treasury](treasury.md) | 3* | - | treasury | a row of strongboxes on a back wall, the counting table, shields hung; open floor before the boxes |
| stores | [powder store](powder_store.md) | 2* | - | powder_store | powder kegs in rows along the walls, the middle clear: the one room black powder belongs in |
| martial | [barracks](barracks.md) | 16 | 5 | barracks, ogre_den | bunks of one kind in a row, a chest at each foot, gear shelves end to end, a table: orderly |
| martial | [armoury](armoury.md) | 16 | 4 | gear_store | racks in rows of one kind each with aisles between, shelves on the back wall, the stock by the front walls |
| martial | [guardroom](guardroom.md) | 5* | - | guardroom | the watch's table with a meal on it, two or three cots, arms on the walls within reach |
| confinement | [cell](cell.md) | 7* | - | cell, ogre_pen | bare: a cot, straw in heaps, the stocks in a bigger cell, a bone or two; nothing else |
| confinement | [torture chamber](torture_chamber.md) | 2* | - | torture_chamber | the rack free in the middle, the iron maiden and the stocks at the walls, the questioner's desk, a brazier |
| public | [shop](shop.md) | 16 | 8 | shop | the counter out from a back wall with the keeper behind it, goods lining the walls, racks for show three to a row, open floor before the counter |
| public | [tavern](tavern.md) | 2 | 8 | tavern | the bar with kegs behind it, the hearth, tables of three kinds of set with open floor between, lively but not packed |
| public | [dining hall](dining_hall.md) | 3 | 4 | dining_hall, mess_hall, ogre_hall | long tables in rows seated both sides, the hearth on a back wall flanked by crockery |
| ceremonial | [hall](hall.md) | 17 | 2 | hall | a colonnade in pairs either side of a clear aisle, statues facing across it, hangings: open and stately |
| ceremonial | [chapel](chapel.md) | 1 | 5 | chapel, dark_chapel | the altar across from the door in line with it, a carpeted aisle, a few rows of pews nearest the altar, open floor toward the door |
| ceremonial | [great hall](great_hall.md) | 2 | 3 | great_hall | the house's heart: the hearth, a few long tables on a great carpet, banners, and a lot of open floor |
| ceremonial | [throne room](throne_room.md) | 4 | 2 | throne_room | the throne facing the door down a runner, statues and braziers about it, a few pairs of columns, tapestries of one colour: open, processional, with character |
| ceremonial | [shrine](shrine.md) | 6* | - | shrine, dark_shrine | one holy thing across from the door, statues flanking it, candles and basins of fire, a kneeling bench, open |
| ceremonial | [conservatory](conservatory.md) | 3* | - | conservatory | a fountain or a well, benches facing it, plants massed along the walls and in clumps with paths |
| ceremonial | [gallery](gallery.md) | 1* | - | gallery | paintings at even spacing along both back walls, benches facing them, statues in pairs, open floor |
| dead | [crypt](crypt.md) | 30 | 5 | crypt, dark_crypt | sarcophagi in rows with aisles between, statues of the dead, a chest, quiet and sparse |
| dead | [ossuary](ossuary.md) | 4* | - | ossuary | bones in heaps, crypt chests in the corners, a monument; no rows of tombs |
| dead | [mausoleum](mausoleum.md) | 4* | - | mausoleum | one great tomb in the middle, statues of the dead in pairs facing it, monuments in the corners |

Westwood also has 9 **passages** (bare halls under 40 tiles, a statue or two): we build those as corridors, not rooms.

Merged and split: the dwelling is a one-room living room with a bed (a variant); mess halls and the ogres' feasting halls
are dining halls; ore stores and the ogres' hoards are storerooms; the ogres' den is a barracks of straw; the Land of the
Dead's chapel and crypt are variants of the chapel and the crypt. The **armoury** is split from the storeroom: a store
keeps supplies, an armoury shows arms on racks (Westwood: 29 rooms of racks with no counter or keeper, against 28 of
supplies). The **throne room** is split from the hall: a hall has no seat to face.

## More types (2026-10-05)

"Come up with more room types for more variety." Every enclosed campaign room (Con/War/Wiz, each layout once, the finder's
353 rooms with their natural-walled pockets) was read by what it holds, the rooms `westwood.py` leaves as empty, other or
passage and the ones it types loosely (a storeroom of gears, a hall of plants, an armoury with cots and a table of food).
Sixteen types came out of it, each distinct from the nineteen and from each other, each a brief, a profile
(`kit/roomtypes.py`, with its `evidence` rooms) and a recipe composed from the furnisher's existing steps
(`kit/identity.py ROOMS`). Ranked by how useful they are to our towns, castles and dungeons:

| # | Type | Family | Campaign evidence | Where it goes |
|---|---|---|---|---|
| 1 | guardroom | martial | 5: Con03A/War03a, Con06a, Con06b, Con03A, Con02a (the gaoler's) | gatehouses, gaols, keeps, town halls, barracks |
| 2 | cell | confinement | 7: War07A's three, Con11a's four ogre pens | gaols, keeps, gatehouses, ogre keeps |
| 3 | cellar | stores | 4: Con07B, Con06b, War02b, Con06a/War01A | inns, manors, keeps, town halls |
| 4 | solar | private | 4: Con07D, Con06b's two, Wiz03b | keeps, manors |
| 5 | shrine | ceremonial | 6: Con10c/Wiz10c, Con10d, Con07H, Wiz11A, Wiz02B, Con07D | chapels, keeps, groves, wayside, the Land of the Dead |
| 6 | treasury | stores | 3: Con05B, Wiz06c, Con06b | keeps, manors, town halls, dungeons |
| 7 | workshop | work | 1: Con06a/War01A | towns (the wheelwright), smithies |
| 8 | infirmary | work | none: design judgement (the barracks' cots, the herbalist's remedies) | healers' houses, barracks, apothecaries |
| 9 | torture chamber | confinement | 2: Wiz07C, Con08d | keeps, gaols, dungeons |
| 10 | ossuary | dead | 4: Con04a's three, War04b | chapels, mausoleums, barrows, dungeons |
| 11 | mausoleum | dead | 4: Con04a's two, Con04c's two | graveyards, chapels, dungeons |
| 12 | winch room | work | 6: Con06a, War07A, War02A, Con01A, War02b, Wiz03a | gatehouses, keeps, mills, mines |
| 13 | conservatory | ceremonial | 3: Con07B/War07A's two, Wiz01A | manors, colleges |
| 14 | observatory | work | 2: Con07B/War07A, Con07E | wizards' towns, observatories, colleges |
| 15 | gallery | ceremonial | 1: Con07E/War07D | manors, colleges |
| 16 | powder store | stores | 2: Con07C, Con09c | keeps, gatehouses, mines, demon forges |

Culture variants with them: `ogre_pen` (a cell: Con11a's pens) and `dark_shrine` (a shrine: the lich god's statue,
obelisks and incense basins).

Considered and left out: a counting house and a scriptorium (a study or a library by their pieces), a war room or a
council chamber (a dining hall's table; no map or chart table in the game), a trophy room (a living room with the
trophies theme), servants' quarters and a guest chamber (bedrooms: Westwood's cooks sleep in their kitchens, Con02a,
Con07B, Wiz06a), a nursery, a bathhouse, a bakery, a brewery, a stable or a kennel (no tub, oven, still, stall or
manger in the game's objects), a summoning chamber (the laboratory's conjuring circle; Westwood's pentagrams teleport),
an ogre larder (the ogre hoard's carcasses).

**Roles.** The default programs of the existing roles are unchanged; each role lists the new rooms it can hold
(`kit/identity.py ROLE_OPTIONS`), which a design adds with `BuildingIdentity(..., extra=("solar", "cell"))`
(`role_program`; `StoryMap.place_buildings` builds them). New roles: `gaol` (guardroom, two cells), `gatehouse`
(guardroom, winch room, armoury), `healer` (infirmary, herbalist, bedroom), `wheelwright` (workshop, storeroom),
`mausoleum` (mausoleum, ossuary), `shrine` (a shrine).

**Hooks the new types needed** (each a no-op for the older kinds): `ROOMS[kind]["lift"]` gives a kind back the
prefixes its furnishing style excludes (a torture chamber's racks, a winch room's pulley gears, a shrine's Dun Mir
altar in a town house: `kit/furnish.py` STYLE_EXCLUDE); `ROOMS[kind]["grand"]` lets statues stand in it in a town house
(as GRAND_ROOMS); `ROOMS[kind]["decor_at"] = "any"` hangs a gallery's paintings at the ends of each stretch of wall as
well as its middle; validate/checks.py LINED counts powder kegs as a store's rows.

**What the room score cannot see yet.** Torture racks, stocks, the iron maiden, gears, winches, monuments and bones have
no furniture family (rules/room_types.py FAMILIES): their rooms measure barer than they are, and their profiles' ranges
say so; the signatures read them by kind.

## Where people stand

Every type says where its people stand (each brief's "Where people stand"; `kit/roomtypes.py STANDS`): the keeper behind
his counter, the barkeep behind the bar, the priest at the altar's side, the lord by his hearth or beside his throne, the
gaoler by his arms or behind his table, the healer by the cauldron, the treasurer behind his counting table, the
astronomer by his telescope. `StoryMap.stand_px(room)` takes the first of the type's spots that is free; failing every
one, a back wall facing the room; failing that, `free_px`. The rule for every room: on the floor, off the walls, clear
of the furniture, never in a doorway or the way in from it, never among tables (2026-10-05: a quest giver stood "in a
weird place in between two tables" in a hall: `free_px` takes the open floor nearest the middle, which in a hall of
tables lies between them), never on a runner or an aisle, 40 px from anyone standing there already. A design places an
indoor person with `sm.person_in(donor, scr, room, name)`; `py mapgen/designs/roomlab.py 1 --stands` shows the spot in
every lab room.

## The families

- **Private** (bedroom, living room, study, solar): cosy and full. Every wall has a purpose, the back walls are lined, one
  group in the middle shows the use. Coverage 0.10-0.30, open floor 0.30-0.80.
- **Work** (laboratory, kitchen, library, smithy, herbalist, winch room, observatory, workshop, infirmary): the work station is the focus; tools and stock along the
  walls; a long room is used in zones along its length. Balanced to full.
- **Stores** (storeroom, cellar, treasury, powder store): full by nature: stocked walls, tidy rows, heaps in the corners, an aisle. Coverage up to 0.42.
- **Martial** (barracks, armoury, guardroom): rows of one kind, orderly; the gear on show.
- **Public** (shop, tavern, dining hall): sets of furniture with open floor between them to move about; the counter or
  bar is the focus.
- **Ceremonial** (hall, chapel, great hall, throne room, shrine, conservatory, gallery): open and processional. A way from the door to the focus, kept
  clear; few pieces, each placed for effect, in pairs; character from the walls (tapestries, banners) and from variety,
  never from more of one piece. Coverage 0.02-0.18, open floor 0.55-0.97.
- **Confinement** (cell, torture chamber): rooms that hold people against their will: bare, hard, few pieces each of
  iron or straw; the door the one way, kept clear.
- **The dead** (crypt, ossuary, mausoleum): rows of tombs with aisles, heaps of bones, or one great tomb; sparse and
  quiet.

## Culture variants

The ogres (rough wood, straw, meat, torch poles), the Land of the Dead (sconces, mana obelisks, tombstones, bones), Dun
Mir (its throne, altar, chests and hanging shields). A culture changes the pieces, not the type: an ogre den is still
where the ogres sleep, round a fire pit (`variants` in `kit/roomtypes.py`, the `ogre_*`, `dark_*` recipes).

## Rules for every room

These hold whatever the type (PROCESS.md keeps their history):

- **What the camera sees.** The NE wall is the room's top right on screen, the NW its top left, the SE its bottom right,
  the SW its bottom left. Pieces with a face (shelves, hangings, hearths, stoves, desks, chests, lab benches) go on the
  NE and NW walls, whose fronts face the camera; on the SE and SW walls the camera sees only their backs. Free-standing
  pieces lean toward the front of the room.
- **Pieces lie along their wall**, back to it, snug (Westwood's gap: shelves 0.18, chests 0.22, desks 0.25, hearths
  0.15 units), in the variant for that wall; beds headboard to the wall.
- **A clear way in from every door**: nothing within 4 units straight in (0.4 of the depth), no column or statue within
  12 (3/4 of the depth). Statues face into the room, never a wall within 3 units.
- **Spacing**: a cauldron 2 units from the hearth; supplies a unit from anything else and 2.4 from a fire; shelves and
  desks 2.2 out of corners; beds 0.9 apart; tables and desks off rugs (a rug centred under a round table is the one
  exception); plants only in real corners; nothing ever before a hearth, chest or stove.
- **Single and repeatable pieces**: bookcases, trader's shelves, workstations, beds in a bunk room,
  pews, columns, coffins and stores repeat and may line a wall end to end. Showpieces stand once (an alchemist's desk, a
  generator pair, a telescope, an orrery, a crystal ball, a desk; twice, 10 units apart, in a room of 120 tiles or
  more); potion shelves once, as a pair. "The shelves on the NE wall in this room are more of a single instance object.
  These are not repeatable shelves that should line a whole wall" (Starwell, 2026-10-05).
- **Every piece by Westwood's measure** (Harrowby playtest, 2026-10-05, review/FEEDBACK.md HB-1..HB-5): the object
  knowledge base (`rules/objects.py` -> `rules/out/objects.json`, read by `mapgen/kit/objects.py`) sets for every piece
  how many a room holds (one cauldron; chests by the type, a bedroom one; a showpiece once; a bedroom one table set),
  whether it lines walls (bookcases do; log shelves stand alone or in pairs: "some objects are suitable for lining an
  entire wall, and some are not"), how close it stands to each other category (a bed and a chest off the fires, a bench
  off the bed, statues apart), that hangings take bare wall, and that supplies stand in mixed clusters, not lines. The
  furnisher holds every placement to it; the checker's `pieces.*` rules find what breaks it.
- **Whole walls, not single pieces**: a lined wall is lined end to end ("put bookshelves end to end for the entire
  length of the wall", TreePlace v0.3), but nothing lines a wall from corner to corner unless it is a store.
- **Large rooms mix their pieces**: a repeated set stops at the type's cap ("way too many benches and not enough object
  diversity ... too many of the same object (chapel benches, tavern tables and chairs)", Greywatch, 2026-10-05). The
  floor left takes other groups of the type, or stays open.
- **Each wall has a purpose; one group in the middle shows the use; the pieces keep to one theme** ("This room has no
  sense of identity or purpose. No continuity of theme or real feel", the Starwell laboratory). The room reads as its
  type and no other.
- **Westwood's placement grammar** (2026-10-06, the fair blind judges; `rules/grammar.py` measures it on the curated
  campaign rooms into `rules/out/grammar.json`, `mapgen/kit/grammar.py` holds it, both engines run its audit last, the
  checker warns with `composition.grammar_*`): a floor light stands by a wall in a corner or beside what it lights,
  never free, on a carpet, at a bed's foot, side by side or in a row; a table set stands by a wall, on a carpet or by the
  hearth, never floating, at a bed's foot or square before the fire; chairs are drawn up to something; barrels, crates
  and chests join a group (Westwood leaves 15% of its stock and 2% of its chests alone in the open or on a front wall);
  no even gaps along a wall (or of hangings), no stepped rows, no piece one to a corner, no rings (four chairs at a
  table's quarter points); no table or bench square before the hearth; no bench or column alone in the open; no plants
  but in a gallery; no face on a front wall; no twin knots or table sets; beds and tombs of one kind.
- **One palette per building** (seats, tables, carpets, hangings, plants), one hanging theme per room, one door family
  per building; candelabras indoors, never open torches.

## How a room is made and checked

1. The building gives each room a kind (`kit/identity.py BUILDINGS`); the kind maps to a type (`kit/roomtypes.py
   KIND_TYPE`).
2. The furnisher composes the kind's recipe (`ROOMS[kind]["compose"]`, then `fill`), toward its type's coverage target
   and never past its limit, holding the type's caps (`ROOMS[kind]["repeat"]`, written from the profile).
3. `py review/roomscore.py <map>` judges each room against its type: coverage, open floor, pieces per tile, variety,
   repeats and caps, the must and never pieces, the focal piece and where it stands, walls used and lined, what the
   room reads as, and the checker's warnings in it. It reports by type.
4. `py review/rooms.py <map> --each` shows each room; look at one or two of every type by eye.
