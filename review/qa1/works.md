# QA round 1, applied themes: the unrated works, stores, sacred and dead rooms

The user rated only part of the room types in QA round 1 (2026-10-13: armoury .. great hall) and asked that the
high-level feedback and recurring themes be applied to the room types they did not rate. "Much of the feedback boiled
down to" two themes (review/reviews/QA-round1.md; memory `qa-round1-themes`):

1. **Too empty, not enough object diversity.**
2. **No balance or symmetry: things placed randomly, not lined up with each other.**

This ledger covers the types the works helper took on: guardroom, laboratory, observatory, mausoleum, ossuary,
powder_store, shrine (shrine, dark_shrine), smithy, storeroom (storeroom, granary, ogre_hoard, ore_store),
torture_chamber, treasury, winch_room, workshop. The user's words are quoted from the theme statement or from the rated
room's note the lesson came from; none of these types was rated, so every row is an *applied theme*.

How: `mapgen/kit/finish.py` (the furnishing engines' last step, after the placement grammar's audit) takes up the
loose pieces a recipe scattered and composes each of these rooms as a whole: the type's programme (rows, lined walls,
corner heaps, the ceremonial axis), lights in mirrored pairs, the walls topped up to the type's share with its own units,
the middle's groups on the room's long axis. Each type's rules are in `rules/rooms/<type>.md`, section *QA round 1*.

Status: **check** (a checker rule warns on it, with a planted case in `validate/selftest.py`), **review** (a picture or
the lab's measures). *Before* is master at aef0678 (the round-1 pictures); *after* is branch `qa1-works`.

| ID | The user's words | Applied to | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|---|
| Q1B-1 | "Too empty, not enough object diversity" (theme 1); "Too much empty space" (RM-ARMOURY-07, -08) | all 13 types | every wall used to the type's share (`walls.fill`), a big room's middle holds the type's groups on its long axis (`middle`) | lab: `finish` log `reach`, wall shares (NOX_QA1_DEBUG); look: the lab sheets | none | review |
| Q1B-2 | "Dead spaces in the south corner are too common" (bedroom set); "Add an object or two to the south corner area" (RM-BARRACKS-10) | all but the ceremonial types | a heap or group in the S corner and on the front walls (`corner_heap S`, front `heap` units) | `composition.qa1_s_corner` (STq1scr) | none | check |
| Q1B-3 | "Many of these include only barrels. Improve the diversity. Add metal barrels and tools. Use crates more often alongside the barrels" (cellar set) | storeroom, granary, ore_store, powder_store, treasury, smithy, workshop, winch_room, guardroom | heaps mix kinds and variants (wood and steel barrels, crates, sacks, tool barrels), never the same piece twice in a row (`pick_seq`) | `composition.qa1_store_variety` (STq1sto) | none | check |
| Q1B-4 | "Larger rooms need to have things like weapon racks along their walls" (armoury set) | guardroom, smithy | a centred, evenly spaced row of weapon racks on a back wall (both in a room of 90 tiles), armour stands closing it | look: guardroom and smithy sheets | none | review |
| Q1B-5 | "more wall objects (banners, trophies, bookshelves, etc) are needed" (bedroom set); "Add more bookshelves to the northwest wall" (nox20) | guardroom, laboratory, observatory, treasury, shrine, mausoleum | hangings on the bare back walls (`hang`), bookcases lining the desk's wall end to end (`line`), star charts in an observatory | look; `composition.shelves_gap` (existing) | review | review |
| Q1B-6 | "When placing two mana obelisks, place them with symmetry. For example, in the corners" (RM-BARRACKS-04) | all 13 types | the same piece or heap in matching corners (`corner_pair`), lights in mirrored pairs (`light_pairs`), the grammar's irregularity rules waived for these types (`roomtypes symmetry_ok`) | `composition.qa1_axis` for the ceremonial types (STq1axs) | none | check |
| Q1B-7 | "Chapels should always be aligned with the main door. The character should walk in and be on the main path facing the altar"; "Generally, chapels should have a much more symmetric layout ... an altar at the end, centered" (chapel set) | shrine, dark_shrine, mausoleum, ossuary, treasury | composed on the axis from the main door (`step_axis`): the centrepiece on it, a runner down it, avenues and flanking pairs, coffins and basins mirrored | `composition.qa1_axis` (STq1axs) | none | check |
| Q1B-8 | "place furnaces on a small brick square" (nox17); "The brick hearth around the stove is not properly bordered" (nox21) | smithy | the forge on a bordered square of brick (`brick_square`) | `composition.qa1_forge_floor` (STq1frg) | none | check |
| Q1B-9 | "They all need to have the carpet underneath them made even and symmetrical" (chapel set); "The six tables on the carpet look good. They just need to be centered more" (RM-GREATHALL-01) | guardroom, treasury, shrine, mausoleum | a table group centred on its carpet (snapped to the floor squares), the runner centred on the axis | look | none | review |
| Q1B-10 | "Large crates overall are too close to other objects" (wagon set); "Giant wine barrels need more space" (RM-CELLAR-09) | stores, workshop, winch_room | big pieces through the furnisher's clearances; heaps of touching small pieces only | look | review | review |
| Q1B-11 | "Ogre barracks are completely different than regular barracks ... Separate these two categories out"; "The ogre straw looks better when it's in a corner or end of the room" (barracks, cell sets) | ogre_hoard | its own programme: minimal but balanced, heaps in matching corners and the S corner, the hoard's chest centred on a back wall | look | none | review |
| Q1B-12 | "Add more object diversity, like bones. Use the breakable coffin objects sometimes. Add a high chance for these rooms to contain mana obelisks" (crypt set) | mausoleum, ossuary, dark_shrine | breakable coffins first in the palettes, bone heaps mirrored, obelisk pairs in the far corners | look | none | review |
| Q1B-13 | "the chest in the north corner looks out of place. Center the chest on the northwest wall" (RM-BEDROOM-03) | all with chests | chests centred on a back wall's bare stretch, the space before them kept clear (`claim_front`); a chest the recipe left on a front wall taken up | `composition.anchor_blocked` (existing) | review | review |
| Q1B-14 | "No balance or symmetry: things placed randomly, not lined up with each other" (theme 2) | all 13 types | the recipe's loose pieces taken up (`keep`), rows centred and evenly spaced with mirrored kinds (A B A), the middle's groups on the long axis mirrored about its centre, no group at a random bare spot outside the ceremonial rooms | look; `composition.qa1_axis` | none | review |
| Q1B-15 | "Use crates more often alongside the barrels" (cellar); "Ogre encampment should be very heavy on barrels (including explosives) and sacks" (ogre camp) | powder_store | the powder kegs in heaps in the corners with steel crates and barrels among them, never one kind alone | `composition.qa1_store_variety` (STq1sto) | none | check |
