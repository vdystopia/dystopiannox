---
name: nox-story-map
description: Make a complete, playable Nox single-player map with a story - a start, quests, fights, rewards, shops, talking NPCs and an exit - using the dystopiannox generator (mapgen/kit). Use when asked to create a new Nox map, a campaign chapter, a quest map or a town for OpenNox.
---

# Making a Nox story map

You are building a single-player map for Nox (OpenNox v1.9.0-alpha13, GOG install at `C:\GOG Games\Nox`) with the
dystopiannox generator. A finished map is a story the player walks through; every creature, chest and sign is there
for a reason.

**Read first:** `PROCESS.md` (the rules, by topic: what a good result is, each rule tagged with the playtest that set
it), `rules/rooms/README.md` (each room type's own rules: there is no one-size-fits-all room) and
`review/FEEDBACK.md` (every piece of the user's feedback and the check that now enforces it). Westwood's style means its campaign
maps only (Con/War/Wiz): never copy a piece, a number or a layout from the quest maps (G_*) or the multiplayer maps;
the kit decorates only with types the campaign places (`nox.campaign_types()`). This file is the
recipe: what to call, in which order.

**Template:** copy `mapgen/designs/starwell.py` (the newest town: sections, yards, a camp in zones with posts, a sealed
building, a bribe-or-law choice, a culture's scenes) or `mapgen/designs/ambermere.py` (a lake town: `camp_site`,
`urchin_camp`, a journey home, `doorside`). `greywatch.py` shows a castle (`Curtain`), `deepvault.py` a cave town,
`emberhollow.py` a lava biome, `mirefen.py` a swamp; `tnorth.py` and `rimepass.py` are small linking maps.
`harrowby.py` shows a farming town with an ogre culture (`ogre_camp`, an `ogre_keep` lair, two cultures' scenes, a
law-or-mercy choice ending in a journey home). `thornwick.py` and `rimehold.py` are the oldest and predate several rules: do not copy their camps or movement.

## 1. Write the story first (in the design's docstring)

1. **Theme and environment** (town, forest, cave, ice, lava, swamp, castle...) and the palette (`kit/biome.py BIOMES`
   for cave, ice, lava, swamp; `kit/vegetation.py FORESTS` for the green world). A town in snow is
   `environment="town"` with the ice palette.
2. **The start and the hook**: where the player arrives, what is wrong, who tells them where to go.
3. **The main quest, which locks the exit**: a gate across the road out (`sm.gate_across`), opened by the quest's end
   (`A.unlock`), the exit beyond (`sm.exit_to`) to the next map, which must already be built (an exit reads the next
   map's PlayerStart; build a chain from its end; a small closing map like `tnorth.py` is enough).
4. **Two or three side quests**, each with its own place, giver and reward, sending the player across the whole map.
   Shapes that worked: an heirloom from a guarded ruin; what happened to someone; a bounty; a choice between two givers;
   a rescue where the rescued walks home (`sm.journey` + `A.walk`); a count of things done in any order (`A.advance`,
   `q.when_true`); a bribe or the law (`q.when(gold=)`, `A.gold(-n)`, `A.turn`).
5. **Fights with a reason**, **rewards** (items first, gold within about 500-1500 per map, `rules/QUESTS.md`), **shops**,
   and **everyone talks** (a rumour each, a line after the main quest, a portrait). Item names must exist:
   `py review/catalog.py <name or regex>`.
6. **Write every line from a Westwood frame, then check it by `rules/DIALOGUE.md`.** Deal the map its frames with
   `py tests/storylab.py frames --seed <MapName>` (a Westwood quest for each quest, a Westwood line for each guard,
   shopkeeper, townsperson, reminder and journal entry) and rewrite each line for line: same size, punctuation,
   register and quirks, new matter and names, nothing added (no explanation, joke, backstory or closing sentiment
   the frame lacks), then rework whatever the originality check flags so the lines are our own. This is what the story lab's blind judges could not tell from Westwood (`rules/DIALOGUE.md`
   "Write from Westwood's own lines"); rules and imitation alone were told apart every time. Then the guide's
   checks (no semicolons, the player never addressed by class, journal entries as short orders) and each side quest
   by `rules/QUESTS.md`'s five beats (offer with a yes/no
   question, refusal, reminder, completion with the reward handed over, afterwards; `q.errand`). Score the story with
   `py tests/storylab.py --check mapgen/designs/<map>.py` (aim: 8 or more, no line below 6; its Originality section must pass: the lines are our own writing, never Westwood's with the nouns changed).

Then the map plan: areas and links. Units: the map is 256 x 256 squares on screen (X right, Y down);
`land.area(name, uv(X, Y), radius_uv)` takes its centre in uv (`uv(X, Y) = (X + Y, X - Y)`) and its radius in uv
units, two to a square. Everything else in the kit is in squares (i, j) = uv / 2 (`land.areas[name]["c"]`). An area
must stay 12 + radius squares inside the edges.

## 2. Build it, in this order (as `starwell.py` does)

```python
SEED = int(sys.argv[1]) if len(sys.argv) > 1 else 4; rng = random.Random(SEED)
ID = MapIdentity(name=NAME, theme=..., environment="town", areas=[AreaIdentity(...)], buildings=[BuildingIdentity(role, area, name, occupant, style=)])
m = Spec(NAME, ..., type=SOLO, minPlayers=1, maxPlayers=1); m.d["nxz"] = False; q = QuestBook(NAME)
```
1. **Plan**: `land = Land(rng, u_range=, v_range=)`; `land.area(..., region=)`; `land.link(a, b, width, road=)`;
   `land.blends(m)`; water with its crossings (`land.plan_crossing`, `land.reserve_band`, `Waterworks`); structures the
   land grows round (`MineEntrance.plan()`, `Dresser.structure`).
2. **Centre**: `land.paint_square`, `land.paint_roads`.
3. **Buildings**: `sm = StoryMap(m, rng, land, ID)`; `placed = sm.place_buildings(no_build={area: r}, first=, centred=,
   square_area=)`; `sm.connect_and_furnish(path_material=)`. Yards: `Y.plan_any(land, rng, kind, candidates, toward=)`.
4. **The land**: `land.carve(margin=)`; `lane = sm.keep_open({area: r})`; `land.assign_regions()`;
   `land.thickets(n, avoid=lane)`; `land.open_links()`; `land.apply(m, wall=f(region), floor=f(region))`;
   `Y.build(m, rng, land, yard)`; water dug and bridged; `sm.gate_across(link, prefix=)`.
5. **Town life**: `vil = Village(m, rng, land)`; door scenes `vil.scene(b, sc, role=)` and gardens per
   `BUILDINGS[role]`; the square (`vil.square_piece` or `vil.fountain_square`); `land.ground_variety(...)`.
6. **Story places** (`kit/camps.py`): `camp_site` then `bandit_camp(..., trade=, finds=)`, `urchin_camp` or `ogre_camp`;
   `stone_ring`, `ruined_tower`, `wolf_den`, `wagon_wreck`, `training_ground`; caches (`sm.hidden_spot` +
   `camps.cache`); signposts (`camps.signpost` with `q.text`).
7. **Planting and the start**: `vil.ground_bits`; `Planter(m, rng, land, forest, keep_clear=, settled=,
   forest_of=)`; `plant_all(profile=TOWN_PLANTING)`; `rock_piles`; `forest_floor`; the `PlayerStart`;
   `sm.exit_to(area, NEXT_MAP, prefix=)`.
8. **People** (`pop, B = sm.pop, sm.B`): givers cloned in their clothes (`sm.person(donor_map, donor_scr, x, y,
   name, face=)`, immortal), shops (`sm.shops(WARES, GREET, keeper=)`: keepers stand behind their counters),
   `sm.keep_folk_away(centre, r)` round foes' ground, then `sm.townsfolk(FOLK, centre, q=, rumours=, after=, pics=)`
   and the watch (`sm.person(...)` + `sm.beat(name, centre, radius=, stops=)`). A person waiting at a door:
   `sm.doorside(role or building=, toward=)`. A camp's people: `posts.camp_posts(m, camp, toward, sit=, tents=,
   watch=, work=)` returns `leader`, `sit`, `tent`, `watch`, `work` spots; a cloned person's hidden fighter twin
   stands exactly on his spot (`pop.creature(..., spread=False)`).
9. **Fights**: `pop.creature(type, x, y, action=, scr=, aggr=, face=)`, `B.sentry(name, face, rouse=)`,
   `sm.keepers(room, types, prefix)`, `sm.wild({type: n}, away_from=, avoid=)`; a biome structure's garrison
   (`d.garrison(sm.pop)` on the biome's `Dresser`, so its keepers join the map's script); then `sm.open_ways(story_xy)`.
10. **The story** (`kit/quests.py`): `q.talker(name, [q.say(text, when=, do=, ask=, else_=)])` (later stages first),
    events (`q.on_death`, `q.on_all_dead`, `q.near`, `q.on_pickup`, `q.when_true`), `q.start([...])` (lock the gate,
    disable the exit, the first journal entry), `q.portrait`. Conditions read the world (`q.dead`, `has=`).
    A side quest's five beats in one call: `q.talker(giver, q.errand(giver, quest, offer, reminder, thanks, after,
    objective, done=q.when(has=item), reward=[A.give(...)], refusal=...) + other_lines)`; a quest's done entry is
    `q.done(objective)` (the same words, COMPLETED), news is `q.note(text)`. The text by `rules/DIALOGUE.md`.
    Every line said in a dialogue window is voiced by the build: a sulk after "no" is `else_=[q.tell(giver, text)]`
    (a window of its own, voiced), never `A.chat` (over the head, silent). Voices are cast from the body, portrait and
    title; pin one for a character who speaks on two maps: `q.talker(name, lines, voice="bm_george")`.
    `m.scripts.update(B.files(m.d["name"])); m.scripts.update(q.files())`.
11. **Last, the outdoor dressing**: `Exterior(m, land, biome, placed=placed, culture=, martial=).dress()` (`culture` may
    be a tuple: Harrowby's `("farm", "ogre")`). Add a theme
    to `kit/scenes.py` when a map needs one; never lay loose props by hand.
12. **Write**: `rooms_sidecar(placed, path, yards=)`, `q.write_strings(OUT)` (before the build: the voices read it),
    `m.build(OUT)`, which voices the spoken lines (`VOICE <Name>: n of n lines voiced`; `NOX_NOVOICE=1` skips it while
    trying seeds). The TTS is installed once per PC with `py mapgen/voice.py fetch` (PROCESS.md "Voices").

## 3. Check, fix, repeat

While building: `py mapgen/designs/<map>.py [seed]` builds and prints `CHECK <Name>: N error(s), M warning(s)`
(`NOX_NOCHECK=1` skips the check while trying seeds). Useful on the way:

```
py validate/validate.py mapgen/out/<map>/<Name>.map --image   # the report with markers on a picture
py review/storymap.py mapgen/out/<map>/<Name>.map --routes    # who walks where, which way each stop faces
py review/spots.py mapgen/out/<map>/<Name>.map <names...>     # close-ups of the story's places
py review/rooms.py mapgen/out/<map>/<Name>.map --each         # one picture per room
py review/roomscore.py mapgen/out/<map>/<Name>.map            # each room scored for its type (rules/rooms/)
py review/exteriors.py mapgen/out/<map>/<Name>.map --holes    # empty outdoor ground
py tests/storylab.py --check mapgen/designs/<map>.py          # the story's lines against Westwood's (no build needed)
py mapgen/voice.py cast mapgen/out/<map> <Name>               # who speaks with which voice
py mapgen/voice.py say "Well met, stranger." --voice elder    # hear a voice before casting it
```

**The last step before handing a map over** is the QA gate:

```
py tests/qa.py <design> [seed]
```

It builds the design, runs the checker (0 errors; every warning listed as accepted or not), compiles the scripts,
checks the story's strings and loot and that every spoken line is voiced, runs the room score and the exterior-holes measure, renders the review pictures
(story map with routes, every named story place, every room, the empty-ground map) into `review/out/<Name>/qa/` with
an `index.md`/`index.html` to walk through, and prints a PASS/FAIL summary. `--no-render` skips the pictures while
fixing; `--no-build` re-checks the map already built. Look at every picture it lists (PROCESS.md
section 9 says what to look for in each). A warning is accepted only by listing it in the design, with the reason:

```python
QA_ACCEPT = [("density", r"Few creatures", "a waystation: Westwood's waystations are empty too")]
```

The gate never installs or starts the server. After it passes, the **main session** (not a building agent, since the
user may be playing on this PC) installs the map (`py mapgen/install.py mapgen/out/<map> <Name>`, which also copies its
waves into `Dialog\` and rebuilds `nox.csf.json`) and runs `py tests/server_smoke.py mapgen/designs/<map>.py` (the map loads; the self-checks find every
creature, waypoint and story object). Report the gate's summary and leave the work uncommitted unless told otherwise;
never push.

Results depend on the seed: when a build has errors the kit does not explain, try two or three seeds, then fix the
cause in the kit if it recurs.

## Techniques

- A boss that appears only when summoned: `A.disable(name)` in `q.start`, then `A.enable`/`A.hunt` (Deepvault).
- More than one gate: `gate_across` works on any link made with `road=True`; give each its own prefix.
- A castle: `kit.story.Curtain(land, centre, half, gates=)` (curtain wall, corner towers, gatehouses, named locked gates; keeps the land outside
  its closed faces) with `place_buildings(square_area=)`; roles `keep`, `barracks`; `camps.training_ground`.
- A person who turns on the player: a cloned person cannot be made hostile, so place a disabled creature on the same
  spot (`spread=False`) and swap them with `A.turn(person, foe)`.
- Fights in turn: open one door at a time with `A.unlock` as each bout's foes die; a jail yard's cell doors are
  `yard.cells`.
- A sealed building: `sm.seal_entrance(building, prefix)` locks its entrance to a mechanism; `A.unlock` breaks it.
- A light the story relights: a named `ColorLight` disabled in `q.start` and enabled by the story.
- A culture's own scenes and roles: `culture=` themes in `kit/scenes.py` with `Exterior(..., culture=)`; roles
  `college`, `apothecary`, `observatory`.
- In a cave or other biome, house floors meet the cave floor under the walls: `m.blending(mat, -1)` on the house floors.
- The mine kit lays its own cart track: pass `track=` your road material.
- `camps.Scene.put` places nothing on a road, water, a building or against a wall and returns None: check what matters.
- Done by the kit, nothing to write: dialogue titles (`NPC:<script name>`), the minimap polygon, container loot,
  gifts picked up a few frames after they are made, clones without their donor's script hooks, throne rooms entered
  through their SE wall, every stop's facing.

## Geometry

- The square grid's axes run along the screen's diagonals: a rectangle in squares is a diamond on screen. Building
  sizes are in uv units at the kit's scale (1.25 Westwood's); a role's footprint in squares is about
  `size * 1.25 / 2` each way.
- The land grows only round what is placed (areas, buildings, yards, links): open ground far from anything becomes
  forest. Fill a courtyard yourself (`land.squares |= ...`); use `land.forbidden` for ground that must never be land.
- A wall across a road must be measured on screen (`gate_across` does it).

## Gotchas (each cost an evening once)

- Never place a `Zombie`; map names at most 9 characters; string keys at most 31.
- Never send anyone far with a single Move: use `sm.journey` and `A.walk`.
- Trees lining both edges of a narrow forest path close it: keep story places open with `keep_open` before thickets,
  and buildings off them with `no_build`.
- Long water running to the map's edge drags thin strips of land with it: end streams inside the forest.
- Objects a script names must be ones the game registers by name (creatures, doors, exits, `ColorLight`, crystals,
  chests, signs; not a `FireGrate`).
- Cloned people are not drawn by the editor's render: `review/spots.py` shows their spot; the server's self-check
  proves they exist.
- Builds are reproducible: never Python `hash()` on strings; run builds one at a time.
