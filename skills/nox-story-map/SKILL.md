---
name: nox-story-map
description: Make a complete, playable Nox single-player map with a story - a start, quests, fights, rewards, shops, talking NPCs and an exit - using the dystopiannox generator (mapgen/kit). Use when asked to create a new Nox map, a campaign chapter, a quest map or a town for OpenNox.
---

# Making a Nox story map

You are building a single-player map for Nox (OpenNox v1.9.0-alpha13, GOG install at `C:\GOG Games\Nox`) with the
dystopiannox generator. A finished map is a story the player walks through; every creature, chest and sign is
there for a reason. The process is in `PROCESS.md` (read its "Story" section and the house rules); the examples
are `mapgen/designs/thornwick.py` (a forest market town, chapter one) and `mapgen/designs/rimehold.py` (a snow
outpost, chapter two). Start a new map by copying the one closest in kind.

## 1. Write the story first (in the design's docstring)

Decide, in this order:
1. **Theme and environment** (town, forest, cave, ice, lava, swamp...) and the biome palette (`kit/biome.py BIOMES`:
   cave, ice, lava, swamp; or the green world's `FORESTS`; `mapgen/designs/swamplab.py` shows a swamp's pools). A town in snow is judged as a town (`environment="town"`) with the ice palette.
2. **The start and the hook**: where the player arrives, what is wrong, who tells them where to go.
3. **The main quest, which locks the exit**: a gate across the road out (`StoryMap.gate_across`, Mechanism lock)
   opened by the quest's end (`A.unlock`), and the exit area beyond (`StoryMap.exit_to`) leading to the next map,
   which must exist (make a small closing map like `tnorth.py` or `rimepass.py`).
4. **Two or three side quests**, each with its own place, giver and reward, chosen to send the player across the
   whole map. Good shapes: fetch an heirloom from a guarded place; find what happened to someone; a bounty on a beast
   or a pack; a choice between two givers who want the same item.
5. **Fights with a reason**: an ambush off a road (`q.near` + `A.hunt`), a camp with a sentry, a pack at its den, a
   room's keepers (`StoryMap.keepers`), a boss who drops the quest item (`q.on_death` + `A.drop`).
6. **Rewards**: givers pay in items first (armour, a weapon, potions) and some gold; chests hold loot (`items=`);
   2-3 caches hidden by the forest's edge (`StoryMap.hidden_spot` + `camps.cache`); one or two shops that buy and
   sell (`StoryMap.shops`). Keep a map's gold, chests and rewards together, near Westwood's 500-1500
   (`rules/QUESTS.md`: a chest holds about 40 gold, rarely over 130). Item names must exist in the game: look them
   up with `py review/catalog.py <name or regex>` or in `corpus/out/nox_corpus.db` table `things`.
7. **Everyone talks**: givers, guards, every townsperson (a rumour pointing at a quest, and a line once the main
   quest is done), each with a Westwood portrait.

Then the map plan: areas and links (roads between settled places, forest paths to the wild ones). Units: the map
is 256 x 256 squares as seen on screen (X right, Y down); `land.area(name, uv(X, Y), radius_uv)` takes its centre in
uv (`uv(X, Y) = (X + Y, X - Y)`) and its radius in uv units, two to a square: radius 20 is 10 squares. The area's
centre (`land.areas[name]["c"]`) and everything else in the kit are in squares (i, j) = uv / 2. An area must stay
12 + radius squares inside the edges (the examples assert it).

Quest shapes that worked: an heirloom from a guarded ruin (Thornwick's greatsword); what happened to someone (Rimehold's
trapper); a bounty (wolves, a bear); a choice between two givers (the Varn emerald, the Ember Eye); a rescue where the
rescued walks home (`A.walk`); a count of things done in any order (`A.advance` per vent, `q.when_true` on the
total: Emberhollow's three vents).

## 2. Build it, in this order (see the examples)

1. `Land` areas and links; the palette (`Dresser` for a biome; `land.blends` for the green world); water planned
   with its crossings (`land.plan_crossing`, `reserve_band`); structures that the land grows round
   (`Dresser.structure`).
2. The centre: the square, then the roads.
3. `StoryMap.place_buildings(no_build={wild places})`, `connect_and_furnish(path_material=...)`.
4. Yards; `land.carve`; `StoryMap.keep_open({story places})`; thickets avoiding the lanes; `land.open_links()`;
   `land.apply`; water dug and bridged; the gate; the exit.
5. The story's places (`kit/camps.py`: bandit camp, wreck, wolf den, ruined tower, stone ring (a shrine, a vent),
   cache, signpost), and the woods' small scenes (`Planter.forest_floor`, `rock_piles`).
6. Planting, rocks (`rock_piles`), lights; the PlayerStart.
7. People: givers cloned from Westwood's townsfolk in their clothes (`StoryMap.person`, immortal), shops, townsfolk
   with rumours, the fights, the wood's creatures (`StoryMap.wild` with your own mix). A biome structure's garrison
   (`Dresser.garrison`) joins the map's script when you set `d.population = sm.pop` first. Signs over the doors:
   `Village.SIGN_TEXT` by role, with keys from `q.text`. A different house style for a role:
   `BuildingIdentity(..., style="stone_house")`.
   Last, after the people: `kit/dressing.Exterior(m, land, biome).dress()` fills the empty outdoor ground with
   composed prop groups (PROCESS.md step 6.7).
8. The story in `QuestBook` (`kit/quests.py`): talkers (later stages first), events (`q.on_death`, `q.on_all_dead`,
   `q.near`, `q.on_pickup`, `q.when_true`), `q.start` (lock the gate, disable the exit, the first journal entry),
   portraits. Conditions read the world where possible (`q.dead`, `has=`): the script's stages and flags (and so
   `advance` counts) do not survive a saved game being loaded.
   Objects a script names must be ones the game registers by name: creatures, doors, exits, `ColorLight`, crystals,
   chests and signs work; a `FireGrate` did not. The server's quest self-check lists any it cannot find.

## 3. Check, fix, repeat

```
py mapgen/designs/<map>.py                                   # builds; prints CHECK errors/warnings
py tests/check_scripts.py mapgen/out/<map>/<Name>_scripts --go <portable go.exe>
py mapgen/install.py mapgen/out/<map> <Name>                 # map, scripts, text; rebuilds nox.csf.json
py tests/server_smoke.py mapgen/designs/<map>.py             # loads in the server; self-checks find everything
py review/spots.py mapgen/out/<map>/<Name>.map <names...>    # close-ups of the story's places: look at them
py review/rooms.py mapgen/out/<map>/<Name>.map --each        # one picture per room
py review/roomscore.py mapgen/out/<map>/<Name>.map
py tests/campaign.py                                         # the whole chain, end first: build, compile, install, load
```

Aim for 0 errors and 0 warnings. The checker also proves the story gates seal the exit (`check_story_gates`). Look
at every story place in close-up: is the camp open ground and secluded, can the player reach it, is the boss's
chest where the boss is? `py review/storymap.py <map>` draws the whole map with every named object labelled.

Results depend on the seed: when a build has errors the kit does not explain, try two or three seeds
(`py mapgen/designs/<map>.py <seed>`; `NOX_NOCHECK=1` skips the 30-second check while trying), then fix the cause
in the kit if it recurs. Commit and push at checkpoints when the task is yours to finish; when someone will review
the work first, leave it uncommitted and report.

## Techniques (from the test builds)

- A boss that appears only when summoned: `A.disable(name)` in `q.start`, then `A.hunt(name)` when the moment comes
  (Deepvault's brood mother wakes when the vault's lamp is lit).
- More than one gate: `gate_across` works on any link made with `road=True`; give each its own prefix (Deepvault
  opens a gallery gate early and the exit gate last).
- After planting, `StoryMap.open_ways([...story targets in px])` takes out the fewest pillars, trees or rocks that
  wall a target off.
- A lake belongs in its own dead-end area, its radius well under the area's: lanes run to an area's centre, so a pool
  centred where links meet walls the way off, and a pool bigger than its area hangs into the void.
- In a cave or other biome, house floors (WoodGray2...) meet the cave floor under the walls: `m.blending(mat, -1)`
  on the house floors lets the ground spill over them, as Westwood's edges do.
- The mine kit lays its own cart track: pass `track=` your road material, or its DirtHard meets the yard's cobble.
- `camps.Scene.put` returns None and places nothing on a road, water, a building or against a wall: check what
  matters (a quest object) and move it.
- Cloned people are not drawn by the editor's render: `review/spots.py` shows their spot but not them; the server's
  self-check proves they exist.

- A castle: `StoryMap.Curtain` lays a curtain wall with corner towers and gatehouses round a courtyard, named locked
  gates, and keeps the land outside its closed faces so the gates seal the exit; `place_buildings(square_area=)`
  makes the public buildings face a courtyard; roles `keep` and `barracks`; `camps.training_ground`
  (`mapgen/designs/greywatch.py`).
- A person who turns on the player: a cloned person cannot be made hostile, so place a creature disabled at the same
  spot and swap them with `A.turn(person, foe)`: Greywatch's traitor.
- Fights in turn (an arena, cells): open one door at a time with `A.unlock` as each bout's foes die (`q.dead`); a
  jail yard's cell doors are `yard.cells`.
- A toll, a bribe, a ransom: `q.when(gold=n)` holds while the player carries n gold; `A.gold(-n)` takes it.

## Geometry, in short

- The square grid's axes run along the screen's diagonals: a rectangle in squares (i, j) is a diamond on screen.
  Building sizes are in uv units (two to a square) at the kit's scale (1.25 Westwood's); a role's footprint in
  squares is about `size * 1.25 / 2` each way. Leave room for that when you plan a courtyard or a lot.
- The land grows only round what is placed in it (areas, buildings, yards, links): open ground far from anything
  becomes forest. Fill a courtyard or a field yourself (`land.squares |= ...`), and use `land.forbidden` for ground
  that must never become land (the outside of a castle wall, the rock behind a cliff).

## Gotchas (each cost an evening once)

- Never place a `Zombie`: OpenNox cannot read the map back (the server stops at "cannot read next section: EOF").
- OpenNox alpha13 leaves TellStoryStr, quest status, JournalEntryStr/Edit, MakeFriendly and GiveXp unimplemented:
  the kit uses TellStory and JournalEntry by key with the map's own string table.
- String keys are at most 31 characters (the dialogue message's field).
- Trees lining both edges of a narrow forest path close it: the Planter keeps forest paths clear; keep story places
  open with `keep_open` before thickets, and buildings off them with `no_build`.
- A wall across a road must be measured on screen (`gate_across` does it): the square grid's axes are not the
  screen's.
- Long water running to the map's edge drags thin strips of land with it: end streams inside the forest near the
  settled land.
- An exit drops the player at its ExitX/ExitY in the next map: `exit_to` reads the next map's PlayerStart, so build
  the chain from its end (the next map first). 0, 0 is the map's corner: the player would arrive in the void.
- Map names are at most 9 characters. Builds are reproducible: never Python `hash()` on strings.
