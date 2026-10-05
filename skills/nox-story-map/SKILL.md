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
1. **Theme and environment** (town, forest, cave, ice, lava...) and the biome palette (`kit/biome.py BIOMES`, or
   the green world's `FORESTS`). A town in snow is judged as a town (`environment="town"`) with the ice palette.
2. **The start and the hook**: where the player arrives, what is wrong, who tells them where to go.
3. **The main quest, which locks the exit**: a gate across the road out (`StoryMap.gate_across`, Mechanism lock)
   opened by the quest's end (`A.unlock`), and the exit area beyond (`StoryMap.exit_to`) leading to the next map,
   which must exist (make a small closing map like `tnorth.py` or `rimepass.py`).
4. **Two or three side quests**, each with its own place, giver and reward, chosen to send the player across the
   whole map. Good shapes: fetch an heirloom from a guarded place; find what happened to someone; a bounty on a beast
   or a pack; a choice between two givers who want the same item.
5. **Fights with a reason**: an ambush off a road (`q.near` + `A.hunt`), a camp with a sentry, a pack at its den, a
   room's keepers (`StoryMap.keepers`), a boss who drops the quest item (`q.on_death` + `A.drop`).
6. **Rewards**: givers pay gold and items; chests hold loot (`items=`); 2-3 caches hidden by the forest's edge
   (`StoryMap.hidden_spot` + `camps.cache`); one or two shops that buy and sell (`StoryMap.shops`).
7. **Everyone talks**: givers, guards, every townsperson (a rumour pointing at a quest, and a line once the main
   quest is done), each with a Westwood portrait.

Then the map plan: areas (screen squares X, Y in 0..255; `uv(X, Y) = (X + Y, X - Y)`), with radius, and links
(roads between settled places, forest paths to the wild ones).

## 2. Build it, in this order (see the examples)

1. `Land` areas and links; the palette (`Dresser` for a biome; `land.blends` for the green world); water planned
   with its crossings (`land.plan_crossing`, `reserve_band`); structures that the land grows round
   (`Dresser.structure`).
2. The centre: the square, then the roads.
3. `StoryMap.place_buildings(no_build={wild places})`, `connect_and_furnish(path_material=...)`.
4. Yards; `land.carve`; `StoryMap.keep_open({story places})`; thickets avoiding the lanes; `land.open_links()`;
   `land.apply`; water dug and bridged; the gate; the exit.
5. The story's places (`kit/camps.py`: bandit camp, wreck, wolf den, ruined tower, cache, signpost).
6. Planting, rocks (`rock_piles`), lights; the PlayerStart.
7. People: givers cloned from Westwood's townsfolk in their clothes (`StoryMap.person`), shops, townsfolk with
   rumours, the fights, the wood's creatures (`StoryMap.wild`).
8. The story in `QuestBook` (`kit/quests.py`): talkers (later stages first), events, `q.start` (lock the gate,
   disable the exit, the first journal entry), portraits. Conditions read the world where possible (`q.dead`,
   `has=`).

## 3. Check, fix, repeat

```
py mapgen/designs/<map>.py                                   # builds; prints CHECK errors/warnings
py tests/check_scripts.py mapgen/out/<map>/<Name>_scripts --go <portable go.exe>
py mapgen/install.py mapgen/out/<map> <Name>                 # map, scripts, text; rebuilds nox.csf.json
py tests/server_smoke.py mapgen/designs/<map>.py             # loads in the server; self-checks find everything
py review/spots.py mapgen/out/<map>/<Name>.map <names...>    # close-ups of the story's places: look at them
py review/rooms.py mapgen/out/<map>/<Name>.map --each        # one picture per room
py review/roomscore.py mapgen/out/<map>/<Name>.map
```

Aim for 0 errors and 0 warnings. Look at every story place in close-up: is the camp open ground and secluded, can
the player reach it, does the gate cross the road, is the boss's chest where the boss is? Commit and push at each
checkpoint (the repo's git workflow).

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
- Map names are at most 9 characters. Builds are reproducible: never Python `hash()` on strings.
