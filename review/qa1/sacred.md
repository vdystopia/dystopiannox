# QA round 1: sacred and dark rooms (chapel, mana room, coven, crypt)

Ledger rows for the user's QA round 1 notes on the chapel and crypt sets and the in-game screenshot nox14
(review/reviews/QA-round1.md), in the columns of review/FEEDBACK.md. *Before* is master at b005f84; *after* is the
qa1-sacred branch. The rule's home is PROCESS.md §3 "Sacred and dark rooms are symmetric set pieces" (P§3) and the
type's brief in rules/rooms/; the kit is mapgen/kit/sacred.py; the checks are validate/checks.py check_sacred and
doors.lotd, each with its planted case in validate/selftest.py.

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| Q1C-1 | "Generally, chapels should have a much more symmetric layout. The carpet that runs down the middle with benches and / or pillars and pews evenly and symmetrically placed on either side and an altar at the end, centered." | P§3 sacred set pieces; `rules/rooms/chapel.md` (kit/sacred.py chapel: mirrored pairs about the door's line) | `sacred.symmetry` (STsSym) | none | check |
| Q1C-2 | "Chapels should always be aligned with the main door. The character should walk in and be on the main path facing the altar." RM-CHAPEL-03: "The carpet and altar should be centered in the room and be aligned with the door." RM-CHAPEL-09: "Center the door, altar, benches and pillars in the room." | P§3; `chapel.md` (building.CENTRE_DOOR_ROOMS: the main door in its wall's middle; the altar on its line; the lab enters through a front wall) | `sacred.axis` (STsAxis) | review | check |
| Q1C-3 | "They all need to have the carpet underneath them made even and symmetrical." RM-CHAPEL-02: "The southwest side of the carpet extends further than the other sides." RM-CHAPEL-08/09: "a carpet or path from the door to the altar" | P§3; `chapel.md`, `mana_room.md` (carpets' edges on the squares' seams, as far out either side; a runner from the door to the altar; a ring has its carpet or none) | `sacred.carpet` (STsCarp) | none | check |
| Q1C-4 | "all rooms use the same altar - try different objects"; nox14: "it seems like the altar in this chapel is the only altar being used. Try some other objects as altars" | `chapel.md`, `coven.md`, `mana_room.md` (CHAPEL_ALTARS, COVEN_ALTARS, MANA_CENTRES spread over a map's rooms by deficit) | `sacred.altar_kind` (STsAltr) | none | check |
| Q1C-5 | "separate these rooms into their own category - mana rooms. define them by 1-4 arrangements of mana crystals evenly and symmetrically placed and a wide selection of other arcane objects" | `rules/rooms/mana_room.md`; kit/roomtypes.py TYPES["mana_room"]; the chapel's sanctum archetype removed | `sacred.symmetry`, `sacred.carpet`; the variety: look:rooms (RM-MANAROOM) | none | check |
| Q1C-6 | RM-CHAPEL-02: "Center the mana obelisks on the carpet ... Fill the southeast side of the room a little bit more, and move the treasure chest away from the corner just a little bit." | `mana_room.md` (rings on whole units, carpets centred under them; the chest centred on a back wall; pieces mirrored on the front walls) | `sacred.carpet`; look:rooms | none | check |
| Q1C-7 | RM-CHAPEL-06: "The room is way too big and empty. Add a second mana obelisk arrangement and orient them in the southwest and southeast of the room so they're balanced. Fill the room with many more objects." | `mana_room.md` (rings by size, the most that fit first; crystals flanking each ring, wall pieces) | `sacred.symmetry`; look:rooms (fullness: room score cover) | none | review |
| Q1C-8 | RM-CHAPEL-07: "Center the mana obelisk arrangement in the room. Improve the layout of the benches and add more objects." | `mana_room.md` (one ring in the room's middle; no benches) | `sacred.symmetry`; look:rooms | none | review |
| Q1C-9 | "Create an additional separate chapel category for necromancy. call them Covens. Use coffins and sarcophagi and bones, as well as altars, pews, monuments, statues, cauldrons, etc. ... many Mana obelisks lining the walls. All of the rules regarding balance and centering of normal chapels should apply to covens as well. RM-CHAPEL-10 will serve as the basis" | `rules/rooms/coven.md`; TYPES["coven"] (kinds coven, dark_chapel); the coven building role | `sacred.axis`, `sacred.symmetry`, `sacred.dead` | none | check |
| Q1C-10 | RM-CHAPEL-01: "Barely recognizable as a chapel"; 04: "Scattered mess"; 05: "Needs better centering and alignment ... The benches also seem to be randomly placed." | `chapel.md` (the set piece: pews in rows either side of the runner) | `sacred.symmetry`, `sacred.axis` | none | check |
| Q1C-11 | nox14: "It's just a little bit sparse and needs more pillars, benches, and statues." | `chapel.md` (a pew per 10 tiles to 20 in rows spread down the nave; a few column pairs at one pitch lined up with the rows; statues in the side aisles and by the door) | room score (cover, types); look:rooms | review | review |
| Q1C-12 | nox14: "Give the priest a better location instead of being behind a random pillar. Have the priest stand closer to the altar." | `chapel.md`, `coven.md` "Where people stand" (the priest's spot beside the altar, STANDS ("spot", "priest") first: kit/story.py stand_px) | look:routes, the playtest | none | review |
| Q1C-13 | crypts: "The objects in these rooms need better organization, arrangement, and balance." | P§3; `rules/rooms/crypt.md` (kit/sacred.py crypt: rows mirrored about the door's line; crypts off the motif engine) | `sacred.symmetry` | none | check |
| Q1C-14 | "Add more object diversity, like bones." RM-CRYPT-09: "Worst one in the set, very empty." | `crypt.md` (bones at the rows' heads, graves, statues, tombstones, obelisks; small crypts' fallbacks: tombs along the walls, a bier on the axis) | `sacred.dead` (4+ kinds; STsDead) | none | check |
| Q1C-15 | "Use the breakable coffin objects sometimes." | `crypt.md` (coffin rows in 4 crypts of 10, or nearest the door) | look:rooms (RM-CRYPT) | none | review |
| Q1C-16 | "Add a high chance for these rooms to contain mana obelisks." | `crypt.md` (obelisks flank the centrepiece in 4 crypts of 5, a pair by the door in a big one) | look:rooms | none | review |
| Q1C-17 | RM-CRYPT-10: "This room also needs coffins or graves or something to give it a crypt identity." | `crypt.md` (the Land of the Dead's crypts lie in coffins and sarcophagi, LOTD gravestones at their heads) | `sacred.dead` (LOTD gravestones alone are no graves; STsDead) | none | check |
| Q1C-18 | RM-CRYPT-10: "The wooden doors mismatch with the double doors. Generally, the double door style should be used for all doors with this tile set." | P§3; building.DOUBLE_DOOR_STYLES (the LOTD styles' every door their double door) | `doors.lotd` (STdLotd) | none | check |

Totals: 18 items; after: 13 check, 5 review only (the fullness and variety a room score or the eye judges, the priest's
place the playtest shows), 0 not covered.

## Pictures

Before: review/out/qa/round1/rooms/chapel/RM-CHAPEL-NN.png and .../crypt/RM-CRYPT-NN.png (round 1, iteration qa1).
After: the room lab's iteration qa1b, seed 11 (`py tests/roomlab.py <type> --n 10 --seed 11 --iter qa1b`):
review/out/roomlab/{chapel,coven,mana_room,crypt}/qa1b/renders/NN.png, and the before/after contact sheets in
review/out/qa/qa1-sacred/.
