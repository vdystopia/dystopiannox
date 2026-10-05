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

The numbers come from Westwood's single-player maps, each building room classified by its contents and measured
exactly as our rooms are (`py rules/rooms/westwood.py` writes `westwood.json`; rooms the three campaigns share counted
once: 363 rooms), from the playtester's verdicts, and from our own praised rooms. Westwood's figures below are
p10-p50-p90.

## The types, by family

Ranked within each family by how often they occur (Westwood's building rooms / our 11 designs' rooms, 2026-10-05).

| Family | Type | Westwood | Ours | Kit kinds | What makes it good |
|---|---|---|---|---|---|
| private | [bedroom](bedroom.md) | 50 | 36 | bedroom | the bed headboard to a back wall with its nightstand, the chest snug with a rug before it, shelves end to end; cosy and full, one sleeper's things |
| private | [living room](living_room.md) | 22 | 32 | living_room, dwelling | the hearth centred on a back wall flanked by shelves, the table and chairs before it on a carpet: the household gathers here |
| private | [study](study.md) | 2 | 8 | study | the desk centred on a back wall among bookcases, a meeting table on a carpet, a curio, statues: everything a scholar needs, in the right places |
| work | [laboratory](laboratory.md) | 29 | 2 | laboratory | used in zones: the study end, the work wall of workstations, the alchemist's table and a conjuring circle in the middle; one of each showpiece |
| work | [kitchen](kitchen.md) | 18 | 9 | kitchen | the hearth with the cauldron a step off, provisions lining a back wall, a work table with its food, stores heaped by the front walls |
| work | [library](library.md) | 9 | 3 | library | books end to end on both back walls, stacks in rows in a big one, a reading table on a carpet |
| work | [smithy](smithy.md) | 3 | 7 | smithy | the forge's coals, the bellows beside them, the anvil before them, water to quench; the smith behind his counter |
| work | [herbalist](herbalist.md) | 2 | 3 | herbalist | the cauldron bubbling, one pair of potion shelves, books of remedies end to end, herbs in sacks and pots |
| stores | [storeroom](storeroom.md) | 28 | 21 | storeroom, ore_store, ogre_hoard, granary | supplies in good order: stocked shelves, heaps in the corners, crates side by side, an aisle to walk |
| martial | [barracks](barracks.md) | 26 | 5 | barracks, ogre_den | bunks of one kind in a row, a chest at each foot, gear shelves end to end, a table: orderly |
| martial | [armoury](armoury.md) | 29 | 4 | gear_store | racks in rows of one kind each with aisles between, shelves on the back wall, the stock by the front walls |
| public | [shop](shop.md) | 25 | 8 | shop | the counter out from a back wall with the keeper behind it, goods lining the walls, racks for show three to a row, open floor before the counter |
| public | [tavern](tavern.md) | 5 | 8 | tavern | the bar with kegs behind it, the hearth, tables of three kinds of set with open floor between, lively but not packed |
| public | [dining hall](dining_hall.md) | 6 | 4 | dining_hall, mess_hall, ogre_hall | long tables in rows seated both sides, the hearth on a back wall flanked by crockery |
| ceremonial | [hall](hall.md) | 41 | 2 | hall | a colonnade in pairs either side of a clear aisle, statues facing across it, hangings: open and stately |
| ceremonial | [chapel](chapel.md) | 4 | 5 | chapel, dark_chapel | the altar across from the door in line with it, a carpeted aisle, a few rows of pews nearest the altar, open floor toward the door |
| ceremonial | [great hall](great_hall.md) | 2 | 3 | great_hall | the house's heart: the hearth, a few long tables on a great carpet, banners, and a lot of open floor |
| ceremonial | [throne room](throne_room.md) | 1 | 2 | throne_room | the throne facing the door down a runner, statues and braziers about it, a few pairs of columns, tapestries of one colour: open, processional, with character |
| dead | [crypt](crypt.md) | 28 | 5 | crypt, dark_crypt | sarcophagi in rows with aisles between, statues of the dead, a chest, quiet and sparse |

Westwood also has 33 **passages** (bare halls under 40 tiles, a statue or two): we build those as corridors, not rooms.

Merged and split: the dwelling is a one-room living room with a bed (a variant); mess halls and the ogres' feasting halls
are dining halls; ore stores and the ogres' hoards are storerooms; the ogres' den is a barracks of straw; the Land of the
Dead's chapel and crypt are variants of the chapel and the crypt. The **armoury** is split from the storeroom: a store
keeps supplies, an armoury shows arms on racks (Westwood: 29 rooms of racks with no counter or keeper, against 28 of
supplies). The **throne room** is split from the hall: a hall has no seat to face.

## The families

- **Private** (bedroom, living room, study): cosy and full. Every wall has a purpose, the back walls are lined, one
  group in the middle shows the use. Coverage 0.10-0.30, open floor 0.30-0.80.
- **Work** (laboratory, kitchen, library, smithy, herbalist): the work station is the focus; tools and stock along the
  walls; a long room is used in zones along its length. Balanced to full.
- **Stores** (storeroom): full by nature: stocked walls, tidy rows, heaps in the corners, an aisle. Coverage up to 0.42.
- **Martial** (barracks, armoury): rows of one kind, orderly; the gear on show.
- **Public** (shop, tavern, dining hall): sets of furniture with open floor between them to move about; the counter or
  bar is the focus.
- **Ceremonial** (hall, chapel, great hall, throne room): open and processional. A way from the door to the focus, kept
  clear; few pieces, each placed for effect, in pairs; character from the walls (tapestries, banners) and from variety,
  never from more of one piece. Coverage 0.02-0.18, open floor 0.55-0.97.
- **The dead** (crypt): rows of tombs with aisles; sparse and quiet.

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
- **Single and repeatable pieces**: bookcases, log shelves, trader's shelves, workstations, racks, beds in a bunk room,
  pews, columns, coffins and stores repeat and may line a wall end to end. Showpieces stand once (an alchemist's desk, a
  generator pair, a telescope, an orrery, a crystal ball, a desk; twice, 10 units apart, in a room of 120 tiles or
  more); potion shelves once, as a pair. "The shelves on the NE wall in this room are more of a single instance object.
  These are not repeatable shelves that should line a whole wall" (Starwell, 2026-10-05).
- **Whole walls, not single pieces**: a lined wall is lined end to end ("put bookshelves end to end for the entire
  length of the wall", TreePlace v0.3), but nothing lines a wall from corner to corner unless it is a store.
- **Large rooms mix their pieces**: a repeated set stops at the type's cap ("way too many benches and not enough object
  diversity ... too many of the same object (chapel benches, tavern tables and chairs)", Greywatch, 2026-10-05). The
  floor left takes other groups of the type, or stays open.
- **Each wall has a purpose; one group in the middle shows the use; the pieces keep to one theme** ("This room has no
  sense of identity or purpose. No continuity of theme or real feel", the Starwell laboratory). The room reads as its
  type and no other.
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
