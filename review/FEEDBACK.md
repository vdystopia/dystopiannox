# Feedback ledger

Every numbered piece of the user's feedback, from every playtest and review, with the rule that answers it and how it
is enforced. Use the IDs in PROCESS.md tags (`[SW-3]`) and in commit messages. When new feedback comes in, add its
lines here first, then the rule (PROCESS.md, or the room type's file in `rules/rooms/`), then the check.

- **Rule**: where the rule lives. `P§n` is PROCESS.md section n; room items point to the room type's file in
  `rules/rooms/` (the per-type room knowledge base; `rules/rooms/README.md` indexes it).
- **Enforced by**: the checker rule (`checks.RULES`, run on every build and by `tests/qa.py`) with its planted case in
  `validate/selftest.py`, a QA-gate step (`qa:story`, `qa:exterior`), or the gate's picture to look at (`look:<picture>`,
  with what to look for in `review/out/<Name>/qa/index.html`).
- **Status**: **check** (an automatic check fails or warns on it), **review** (only a picture or a measure a reviewer
  reads), **none** (not covered). *Before* is the kit as of commit 1a92130, before this QA pass; *after* is now.
- **Recurring** marks a fault that came back after a fix.

Sources: the user's messages of 2026-10-05 (verbatim quotes below), the ROADMAP playtest log for the rounds of
2026-10-03/04 (paraphrased there), and the dated history of PROCESS.md (`review/history/PROCESS-2026-10-05.md`).

## DysVale v0.1 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| DV1-1 | mismatched dock planks | P§2 Water: kit pieces at Westwood's steps (`KIT_STEPS`) | `kits.step` (STdock) | check | check |
| DV1-2 | a sight gap at a corner beside a door | P§3 Buildings 6: jambs shaped as if the opening were wall | `wall_shapes.jamb` (STjamb) | check | check |
| DV1-3 | a gap beside a door frame (half doors) | P§3 Buildings 6: half doors in pairs in 2-cell openings | `doors.half_single`, `doors.no_half` (SThalf) | check | check |
| DV1-4 | a cluttered tavern | P§3 Buildings 3-4; `rules/rooms/tavern.md` | `rooms.crammed` (STcram), `rooms.count` (STclutr) | check | check |
| DV1-5 | no flow or coherent design | P§2 centre first, the land grows round what was placed | look:storymap; `review/review.py` path measures | review | review |
| DV1-6 | trees and shrubs look random | P§4 planting (`Planter`, `TOWN_PLANTING`) | `review/review.py` tree clustering; RUBRIC 4 | review | review |

## Mossford v0.1 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| MF-1 | black walls | wall styles with artwork only | `wall_pieces.black` (STwall) | check | check |
| MF-2 | a see-through hole in the boundary | no invisible walls on the boundary | `boundary.hole` (SThole, STinvis) | check | check |
| MF-3 | abrupt bridges | P§2 Water and its crossings | `composition.bridge_*` (STbridg, STwideb), `floors.never_touch` | check | check |

## DysVale v0.3 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| DV3-1 | the square off-centre, a building on it | P§2 the centre first | look:storymap | review | review |
| DV3-2 | paths near the river hard to read (stacked blends) | P§2 Water: bands reserved, roads 2 tiles off water | `review/review.py` roads crowding water; `floors.hard_seam` | review | review |
| DV3-3 | exterior objects felt random | P§4 scenes with a purpose | `exterior.pile` (STheap); look:spots | review | check |
| DV3-4 | interiors incoherent (four table sets in a back room) | P§1 Rooms; `rules/rooms/` | `rooms.stray` (declared rooms), `identity.tables` (STtabl) | check | check |
| DV3-5 | swamp densities averaged with towns | P§1 Environment | `density.range` by environment | check | check |
| DV3-6 | the map needs an identity step | P§1 | the recipe (SKILL.md); RUBRIC 8 | review | review |

## DysVale v0.4 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| DV4-1 | a dock across a puddle. **Recurring** (AM-2) | P§2 Docks | `composition.dock_puddle` (STpuddl), `exterior.dock` (STdockb) | check | check |
| DV4-2 | a path led to the side of a building; the door had no path | P§4 Ground, paths | `composition.path_to_wall` (STspur) | check | check |
| DV4-3 | random benches and torches round the square | P§2 the square is a set piece | look:spots, look:storymap | review | review |
| DV4-4 | the inn's only door faced away from the square | P§3 Buildings 1 (`place_buildings` rejects it) | look:storymap (the kit builds it so) | review | review |
| DV4-5 | two candelabras side by side | P§3 Rooms: lights | `composition.lights_pair` (STlites) | check | check |
| DV4-6 | the bar did not meet the walls; the flap read as a window | `rules/rooms/tavern.md` | `composition.bar_gap` (no planted case) | check | check |

## DysVale v0.5 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| DV5-1 | the bedroom's chests and rugs not centred | `rules/rooms/bedroom.md` | look:rooms | review | review |
| DV5-2 | the kitchen lacked any purpose | `rules/rooms/kitchen.md` | look:rooms; room score | review | review |
| DV5-3 | the bridge ended against the forest wall | P§2 Water: crossings planned with the road | `composition.bridge_landing` (STbridg) | check | check |
| DV5-4 | the chest behind a table and a lamp; everything bunched in a corner | P§3 Rooms: the clear way in, spacing | `composition.anchor_blocked` (STchest), `composition.bunched`, `composition.chairs_no_table` | check | check |

## DysVale v0.6 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| DV6-1 | a chest perpendicular to its wall | P§3 Rooms: pieces along their wall | `composition.across_wall` (STchacr) | check | check |
| DV6-2 | the candelabra beside the chest belonged in the other corner | P§3 Rooms: lights | look:rooms (`composition.lights_pair` covers two lights only) | review | review |
| DV6-3 | stumps clustered in one spot | P§4 props spread out (`vegetation.scatter`) | `composition.props_bunched` (STstump) | check | check |
| DV6-4 | door halves slightly out of line | P§3 Buildings 6 | `doors.pair_line` (STpairl) | check | check |
| DV6-5 | the bridge too wide for the stream, on a bend | P§2 Water | `composition.bridge_wide`, `bridge_slant`, `bridge_bend` (STwideb) | check | check |

## TreePlace v0.1 (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TP1-1 | kitchen: everything clustered round the chimney, meat on the floor | `rules/rooms/kitchen.md`; P§3 no loose food | `composition.food` (STfood), `composition.short_span` (STlopsd) | check | check |
| TP1-2 | mess hall: chairs pulled up to the ends of the tables; barrels sitting there | `rules/rooms/dining_hall.md` | `composition.ends_only` (STends), `rooms.stray` | check | check |
| TP1-3 | bunkhouse: two cots and two beds in random places, a table with no chairs | `rules/rooms/barracks.md` | `composition.mixed_beds` (STbunks), `scattered_beds` (STscbed), `table_no_seats` (STnoset) | check | check |
| TP1-4 | storeroom: almost empty; a bookshelf, an explosive barrel at random | `rules/rooms/storeroom.md` | `rooms.stray`, `composition.sparse` (STsparse) | check | check |
| TP1-5 | torches indoors do not look attached; an open flame is unrealistic | P§3 Rooms: lights | `composition.torch_indoors` (STtorch; a house rule Westwood breaks) | check | check |

## TreePlace v0.2 room review (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TP2-1 | living room very empty, lights uneven, the table half on a rug | `rules/rooms/living_room.md` | `composition.sparse` (STsparse), `table_on_rug` (STrugtb) | check | check |
| TP2-2 | herbalist: table on a rug; line whole walls with potion shelves, not every wall | `rules/rooms/herbalist.md` | `composition.table_on_rug`; look:rooms | check | check |
| TP2-3 | bedroom very empty; nightstand too close to the bed | `rules/rooms/bedroom.md` | `composition.sparse`; look:rooms for the nightstand | check | check |
| TP2-4 | storeroom too empty; a shelf in a corner looked wrong | `rules/rooms/storeroom.md` | `composition.sparse`; look:rooms | check | check |
| TP2-5 | ore shed: clusters and open spaces; spread things out | `rules/rooms/storeroom.md` | look:rooms | review | review |
| TP2-6 | bunk room: beds too close; more shelves and bigger rugs | `rules/rooms/barracks.md` | `composition.beds_close` (STbeds) | check | check |
| TP2-7 | bunkhouse storeroom too evenly spaced | `rules/rooms/storeroom.md` | look:rooms | review | review |
| TP2-8 | mess hall good, needs more | `rules/rooms/dining_hall.md` | `composition.sparse` | check | check |
| TP2-9 | kitchen: cauldron too close to the hearth; apples crowding it | `rules/rooms/kitchen.md`; P§3 spacing | `composition.hearth_crowded` (SThearth) | check | check |
| TP2-10 | study small and empty; a double door into a bedroom; three kinds of door | P§3 Buildings 6; `rules/rooms/study.md` | `doors.double_inside` (STddoor), `doors.kinds` (STdkind) | check | check |
| TP2-11 | foreman's bedroom could use more | `rules/rooms/bedroom.md` | `composition.sparse` | check | check |

## TreePlace v0.3 room review (2026-10-03)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TP3-a | very high priority: shelves and hangings on the NE and NW walls; free pieces toward the S and W | P§3 Rooms: what the camera sees | `composition.front_wall` (STfront) | check | check |
| TP3-b | put bookshelves end to end for the entire length of the wall | `rules/rooms/` (lined walls) | `composition.shelves_gap` (STscatr) | check | check |
| TP3-c | use more of the game's objects | `rules/rooms/` | room score (types); look:rooms | review | review |
| TP3-d | study Con07B; use carpet floor tiles sometimes | `rules/rooms/` | look:rooms | review | review |
| TP3-e | bigger rooms and structures than Westwood's | P§3 Buildings 3 (`BUILDING_SCALE`) | the kit's scale; `rooms.small` | check | check |
| TP3-3 | the chest should be closer to the NW wall; it sits in the middle | P§3 Rooms: pieces along their wall (`SNUG_GAP`) | `composition.off_wall` (STfloat) | check | check |
| TP3-4 | a store room holds racks of gear in the middle (rooms 4, 5, 7) | `rules/rooms/storeroom.md`, `gear_store.md` | look:rooms | review | review |
| TP3-6 | carpets weirdly spaced; chests too close to the beds | `rules/rooms/bedroom.md` | look:rooms | review | review |
| TP3-8 | shelves along the wall with the hearth | `rules/rooms/living_room.md` | look:rooms | review | review |
| TP3-9 | still too empty | `rules/rooms/` (cover by type) | `composition.sparse` | check | check |
| TP3-10 | more shelves, banners and trophies along the NE wall | `rules/rooms/` (lined back walls) | room score (lined); look:rooms | review | review |

## Room and exterior review (2026-10-04, TownLab and the labs)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TL-1 | storeroom racks a little too dense and numerous | `rules/rooms/storeroom.md` (`RACKS_PER_ROW`) | look:rooms | review | review |
| TL-2 | a wall with one bookcase should usually be full of bookcases; shelves tight into corners | `rules/rooms/` (`complete_bookcase_walls`, `CORNER_CLEAR`) | `composition.shelves_gap` | check | check |
| TL-3 | great hall: fewer table sets; a large floor-tile carpet | `rules/rooms/great_hall.md` | `identity.monotony` (STmono), `identity.tables` | review | check |
| TL-4 | more exterior variety (rock piles); fewer aspens on the map edge | P§4 planting | look:empty, look:spots | review | review |

## First campaign playtest (2026-10-05: Thornwick, with Greywatch's chapel)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TW-1 | "npc trying to walk through the door but getting stuck on the frame" | P§6 doorways square-on | `routes.waypoint` (STwpjmb), `routes.leg` (STwpcut); look:routes | check | check |
| TW-2 | "the game crashes when an urchin or bandit archer projectiles hit them" | P§8 gifts (believed the same freeze) | in the game only (look:ingame); `qa:story` gift timer | none | none |
| TW-3 | "when player dies, the game doesn't respond" | P§8 gifts (believed the same freeze) | in the game only (look:ingame) | none | none |
| TW-4 | "lots of random crashes while running around ... near monsters" | P§8 gifts (believed the same freeze) | in the game only (look:ingame) | none | none |
| TW-5 | "The minimap is either not rendering or doesn't exist". **Recurring** (GW-3; Rimehold) | P§8 the minimap | `minimap.start` (STmmap) | none | check |
| TW-6 | "NPC names are showing up as missing:NPC..." | P§8 dialogue titles | `qa:story` every talker titled | none | check |
| TW-7 | "containers are all empty ... every chest should have loot" | P§7 rewards (`kit/loot.py`) | `qa:story` chests filled, gold in budget | none | check |
| TW-8 | "The Greywatch Chapel has way too many benches ... (chapel benches, tavern tables and chairs)" | `rules/rooms/chapel.md`, `tavern.md`; P§3 a room reads as what it is | `identity.monotony` (STmono), `identity.tables` (STtabl) | none | check |
| TW-9 | "npcs wander around too sporadically ... they look like ants ... stand still for longer (20 seconds)" | P§6 tours | `routes.leg`, `routes.tour` (STtour); look:routes | check | check |
| TW-10 | "exterior areas are way too empty ... use more object diversity" | P§4 scenes; empty ground | `qa:exterior` (fails over Westwood's p90); look:empty | review | check |
| TW-11 | "when NPC interactions place items in the player inventory ... the game immediately crashes" | P§8 gifts | `qa:story` gift picked up on a timer | none | check |

## Greywatch playtest (2026-10-05)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| GW-1 | "Will gets stuck on the wall when trying to return to town ... hand-draw NPC routes along paths" | P§6 long walks are journeys | `routes.leg` (journeys in routes.json); look:routes | check | check |
| GW-2 | "exterior objects are very random and purposeless ... instead of 3 crates and 2 barrels, try a cart ..." | P§4 scenes with a purpose | `exterior.pile` (STheap); look:spots | review | check |
| GW-3 | "still no minimap on greywatch". **Recurring** (TW-5) | P§8 the minimap | `minimap.start` (STmmap) | none | check |
| GW-4 | "The bandit camp looks terrible. It's a scattered mess. Beds randomly strewn". **Recurring** (SW-1) | P§5 camps | `exterior.bedroll` (STroll), `exterior.camp_seat`; look:spots | review | check |
| GW-5 | "groups of hostile npcs ... cluster too tightly on a central point like a swarm" | P§6 hostile groups stand apart | `exterior.swarm` (STswarm), `exterior.two_bodies` | check | check |
| GW-6 | "a pair of NPCs converging on the same point and endlessly pushing each other off of it" | P§6 nobody shares a spot | `routes.shared_stop` (STshare) | check | check |
| GW-7 | "osric's keep ... The throne ... facing sideways ... pillars in the dead center ... statues ... face directly against the wall" | `rules/rooms/throne_room.md`; P§3 the clear way in | `identity.throne` (STthron), `composition.way_in` (STwayin), `composition.statue_wall` (STstatw) | check | check |

## Starwell playtest (2026-10-05)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| SW-1 | "The bandit camp in Starwell is another absolute mess ... NPCs are all on top of each other like a swarm". **Recurring** (GW-4) | P§5 camps (zones, posts) | `exterior.swarm`, `exterior.bedroll`, `exterior.camp_seat`; look:spots | check | check |
| SW-2 | "NPCs seem to face random directions ... have them face away from the building" | P§6 facing | `routes.facing` (STface); look:routes | check | check |
| SW-3 | "the stumps around the fires in bandit camps arent the right object" | P§5 seats round a fire | `exterior.camp_seat` (STseat) | none | check |
| SW-4 | "Tile blending on the inside of doors seems consistently off" | P§3 thresholds | `floors.threshold` (STthrsh; its "lies on" half had been dead) | check | check |
| SW-5 | "Many object clusters like these crates are simply too close to each other" | P§4 spacing outdoors | `exterior.overlap` (STbarrl) | check | check |
| SW-6 | "the room in the fourth screenshot ... no sense of identity or purpose ... The throne room is also kind of empty and barren ... tons of the same exact pillars" | `rules/rooms/laboratory.md`, `throne_room.md`; P§3 a room reads as what it is | `identity.repeat_wall` (STrepw), `identity.monotony`, `identity.showpiece`; look:rooms | review | check |
| SW-7 | "The room in the fifth screenshot is exceptional ... a very, very good room" | `rules/rooms/study.md` (the good example of a study, not every room's yardstick) | look:rooms | review | review |
| SW-8 | "candle objects are not appropriate ... these items can actually be picked up" | P§4 outdoor lights | `exterior.pickable` (STcandl) | check | check |
| SW-9 | "it would look better if there were actually some graves. Maybe a bucket of tools" | P§2 yards: a graveyard has graves | `exterior.graveyard` (STgrave); look:spots | none | check |

## Starwell rooms (2026-10-05)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| SWR-1 | "The shelves on the NE wall ... are more of a single instance object ... The shelving on the northwest wall ... can be repeated" | `rules/rooms/laboratory.md`, `herbalist.md`; P§3 | `identity.showpiece` (STshow), `identity.repeat_wall` | review | check |
| SWR-2 | "The shopkeeper is standing in the middle of the shop ... like behind a desk. Instead of six armor racks, use three armor racks and three weapon racks" | `rules/rooms/shop.md`, `smithy.md` | `identity.keeper` (STkeep); racks: look:rooms | none | check |

## Ambermere screenshot (2026-10-05)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| AM-1 | "The northeast stretch of fence overlaps with the row of crops" | P§2 yards: nothing on a fence line | `exterior.on_fence` (STcrop) | check | check |
| AM-2 | "Another example of a doc problem that I thought we fixed ... does not extend out into the middle of the pond". **Recurring** (DV4-1) | P§2 docks | `exterior.dock` (STdockb, a planted case added now) | check | check |

## Internal reviews (agents, not the user; Ambermere, 2026-10-05)

| ID | Finding | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| AMR-1 | the diggers' camp squeezed against a fence and the forest | P§5 the site (`camp_site`) | look:storymap, look:spots | review | review |
| AMR-2 | the pit urchins' beds strewn at random angles | P§5 urchins (`urchin_camp`) | `exterior.bedroll` | review | check |
| AMR-3 | the chapel's crypt door where the altar belonged | `rules/rooms/chapel.md` | look:rooms | review | review |
| AMR-4 | 17 piled barrels end to end along the Amber Eel's wall | P§3 a room reads as what it is (`stock_walls(per_wall=)`) | `identity.supplies_wall` (STsupw) | none | check |
| AMR-5 | fishers' houses, the herbwife's hut and the moot hall called for no scenes | P§4 every role calls for its scenes (`ROLE_SCENES`) | look:empty | review | review |
| AMR-6 | a flower patch grew in the west gate | P§4 gardens keep off doors | look:spots | review | review |
| AMR-7 | Morwen at her door stood in Pip's walk home | P§6 a person waiting at a door; routes keep clear of people standing still by construction (`Ground.add_people`) | `routes.through_person` (STpers) | none | check |

## Harrowby playtest (2026-10-05)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| HB-1 | "Why are there two cauldrons? There should only be a maximum of one cauldron per room. bed is way too close to one of the cauldrons. The bench is too close to the bed. Chest is way too close to the other cauldron. Do a pass over all objects ... a tendency to line walls with things like sacks and barrels ... try a cluster of sacks (three different sizes), and then a barrel, and then something else" | P§3 every piece by Westwood's measure (`rules/objects.py`, `kit/objects.py`); `rules/rooms/living_room.md`, `storeroom.md` | `pieces.cauldrons` (STcauld), `pieces.clearance` (SThclr), `pieces.showpiece` (STshw2), `pieces.run`; supplies in clusters: look:rooms | none | check |
| HB-2 | "On the northwest wall, there are trophies on the wall with statues right on top of them. Double-placed objects. The two treasure chests are both too close to the hearth. It's also a little bit too empty" | P§3 hangings on bare wall, chests 3 units off a hearth; `rules/rooms/great_hall.md` | `pieces.hung` (SThung), `pieces.chests`, `pieces.clearance`; the hall's south corner: look:rooms | none | check |
| HB-3 | "Why are there four treasure chests? For a bedroom, this room has way too many table and chair sets. Hard rule: A bedroom should never have more than one table and chair set." | P§3 chests by the type's p90, a bedroom one set; `rules/rooms/bedroom.md` | `pieces.chests` (STchst4), `pieces.sets` (STsets) | none | check |
| HB-4 | "two statues way too close to each other ... Too many candelabras. The treasure chest should be centered between the end of the bookcase and the door. The shelves lining the northwest and northeast walls are the kind of objects that can be used to span an entire wall" | P§3 statues apart, candelabras by size, the chest by a door centred (`centre_by_doors`); `rules/rooms/study.md`, `library.md` | `pieces.clearance`, `pieces.lights` (STcand); the chest's place: look:rooms | none | check |
| HB-5 | "The entire northwest wall is lined with countless duplicates of that one object ... some objects are suitable for lining an entire wall, and some are not." | P§3 only fabric lines walls (`kit/objects.py` role, max_run, wall_cap); `rules/rooms/storeroom.md` | `pieces.run` (STlogw) | none | check |

## Voiced dialogue (2026-10-08, a request)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| VO-1 | "investigate and implement a method for turning generated NPC dialogue into voiced audio that can be added to the game, so that new maps have fully voiced NPCs and quests" | P§7 Voices, P§8 Dialogue voices (`mapgen/voice.py`, run by `Spec.build`; `q.tell` for refusals) | `qa:voice` (every spoken line has a good wave from its present text; `tests/voice_test.py`); hearing it: the playtest | none | check |
| VO-2 | "Breeze TTS 2 is exceptional, massive improvement! implement it." (after an audition of Kokoro, Breeze TTS 2, Qwen3-TTS, Maya1 and VoxCPM2 on six Thornwick characters) | P§7 Voices (Breeze the default engine; a description and seed per speaker, a design take as its reference, lines by voice direction, vocal events, the quality gate, the GPU only while not gaming; licence: non-commercial) | `qa:voice` (every line passed the gate: Whisper transcript, pitch band, pace; `tests/voice_test.py`); hearing it: the playtest | none | check |
| VO-3 | "run the Nox renders on pc1 unless im gaming - same rules as our previous processes. this should be the default for all work we do. when im gaming, reserve the 4090 and run it on the 2080ti" | P§7 Voices "Where it renders" (the pc1 AI guard's state file decides; registered in gpu-jobs; Talk's model yielded to; pc2's GPU service while gaming, back to pc1 after; replaces the idle-only rule of 5651dea) | `tests/voice_test.py` (state file, registration, policies, a whole pc1 -> pc2 -> pc1 run against stand-in services) | none | check |
| VO-4 | (a default pc1 Claude chose, 2026-10-08; the user may override it) Talk's model loaded on pc1 and the user not gaming: render on pc2 rather than wait (pc1 is serving the user, pc2 is free) | P§7 Voices "Where it renders" (`voice.choose_gpu`: `auto` goes to pc2 while pc1 is busy; the pc1 worker stops at a line when Talk's model loads and the run continues on pc2) | `tests/voice_test.py` (the policies; the switching run: Talk's model at the start and mid-run, on pc2 both times, back to pc1 after) | none | check |
| VO-5 | (a default pc1 Claude chose, 2026-10-08; the user may override it) a line that fails the pace gate (Thornwick:Mirela5, 4.8-5.1 words a second against 4.8): keep the gate strict and give the line a slower delivery, then `--retry` it | P§7 Voices "Delivery" and "The quality gate" (a `mood` pinned in the design, e.g. "Measured and deliberate, unhurried."; never a looser gate) | `qa:voice` (the line must pass the unchanged gate) | none | check |

## Thornwick screenshot (2026-10-08)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TW-12 | "We've had some issues with blending tiles in the transition between interior and exterior. ... There does not need to be blending on a wall. The wall cuts off vision from the inside out and from the outside in. It's also a natural transition point in itself. Therefore, this kind of transition must never be used." (a soft grass edge along the outside of a building's wall) | P§3 No blending at a wall (`nox.wall_seams`, `Spec._edges`) | `floors.wall_blend` (STwallb) | none | check |

## Iron fences (2026-10-08, a request)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| FN-1 | "Try iron fences with and without blending. If no blending is used, then must be put precisely on the line between two tiles." Then, of FenceCut and FenceBlnd side by side: "In every single case, blend is the right choice. Additionally, I must say each of these blends looks very good." (decision: `blend` is the default, `cut` an option) | P§3 Iron fences: cut or blend (`Spec.fence_policy`, `nox.fence_line_tiles`, `Spec._fence_line_floors`); `rules/fences.py`; comparison map `mapgen/designs/fencelab.py` | `floors.fence_line` (STfence), `floors.wall_blend` (STfncbl) | none | check |

## Transporters (2026-10-08, a request)

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| TR-1 | "The next feature we need to add is elevators, lifts, stairs and portals. They all function the exact same way. They basically teleport the player from one location to another. The second location is often an isolated part of the map (but not always)." | P§2 Transporters (`kit/transport.py`, one call for lift, stairs, portal, passage); `rules/TRANSPORTERS.md`; `skills/nox-transporters/SKILL.md` | `transport.link` (STtpLnk), `transport.landing` (STtpWal), `transport.bounce` (STtpBnc), `transport.serves` (STtpSrv), `transport.stranded` (STtpStr), `transport.wall`, `transport.pocket`, `transport.missing`, `transport.unreached`; look:spots (every named end) | none | check |

## Totals

| | Items | Check | Review only | Not covered |
|---|---|---|---|---|
| User feedback, before this pass | 92 | 52 | 28 | 12 |
| User feedback, after | 92 | 68 | 21 | 3 |
| Harrowby playtest (HB), after | 5 | 5 | 0 | 0 |
| Voiced dialogue (VO), after | 5 | 5 | 0 | 0 |
| Thornwick screenshot (TW-12), after | 1 | 1 | 0 | 0 |
| Transporters (TR), after | 1 | 1 | 0 | 0 |
| Iron fences (FN), after | 1 | 1 | 0 | 0 |
| Internal reviews, before | 7 | 0 | 5 | 2 |
| Internal reviews, after | 7 | 3 | 4 | 0 |

What only an eye can judge is listed with its picture in `tests/qa.py` (LOOK) and in each map's
`review/out/<Name>/qa/index.html`. The three not covered (TW-2, TW-3, TW-4) are crashes in the game that were believed
to be the gift freeze (TW-11, fixed and now checked); only a playtest can confirm them gone.
