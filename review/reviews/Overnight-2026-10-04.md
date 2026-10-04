# Overnight run, 3-4 October 2026

You asked me to work through the night on a list of tasks without stopping for questions. This is what I did for each
task, where the work lives, what you can try in the game, and what still needs your eyes. Every change is committed
and pushed to GitHub (`master`, from `b7a88bd` to the latest commit).

## What to look at first

1. **The town lab overview** I sent (`review/out/TownLab/overview.png` and `centre.png`): the bigger-scale village.
2. **Three biome maps, version 0.2**, installed in `C:\GOG Games\Nox\maps\` and loaded without errors in the OpenNox
   server: **Darkdelve** (cave), **Frostfang** (ice) and **Emberdeep** (lava). Each now has a building in its own
   culture's style, furnished the way Westwood furnishes that culture, and guarded by creatures with scripted
   behaviour. Open them the same way you opened TreePlace.
3. **The numbered room pictures** I sent: three per biome map (`review/out/<map>/rooms/01.png` to `03.png`).
4. **TreePlace v0.4** is still the installed version and still waits for your numbered room review. I did not change
   the installed map. The design in the repository has kept improving: all 11 of its rooms now pass the room score,
   and its doors get their signs and barrels. Your review notes will go into v0.5 with these.

## Task 1: generate and evaluate rooms and structures

- **Room lab** (`mapgen/designs/roomlab.py`, scored by `review/roomscore.py`): every room kind (21 of them) at three
  sizes, now at Westwood's true sizes over two lab maps (`RoomLab` and `RoomLab2`). It went from 23 of 42 rooms
  passing to 59-61 of 63 over three seeds.
- **Building lab** (`mapgen/designs/buildinglab.py`, scored by `review/buildingscore.py`): every building role,
  generated and furnished, scored on room sizes, reachability and the room scores. 16 roles now, including a manor
  and the three culture buildings; 13 of 16 pass at the kit's scale (1.25 times Westwood's).
- **Bigger buildings**: an 8-room **manor**. Westwood's multi-room buildings give their largest room half or more of
  the floor and reach the other rooms through it (few have corridors), so large buildings now use a **hub plan**: a
  great hall down the middle with the other rooms along both sides, every door opening onto the hall. The great hall
  has hearths, long tables with benches, statues and trophies, with the doorways kept clear.
- **Town lab** (`mapgen/designs/townlab.py`, installed as `maps/TownLab`): the whole village pipeline at the
  bigger scale. A market town of 13 buildings round a cobbled square, with the manor, inn, store and smithy
  facing it and homes along the streets.
  - The square follows Westwood's own, measured round its 12 town wells and fountains: a fountain ringed by potted
    plants and flowers, benches facing in, ornate street lamps at the edge.
  - Thirteen villagers walk between the square and the doorsteps and run for a doorstep when a wolf comes near;
    wolves, bats and urchins keep to the woods round the town, as in Westwood's towns. The server's self-check
    finds all 39 scripted creatures.
  - The store has a shopkeeper behind its counter (potions, food, travel gear) and the inn a barkeeper behind its
    bar (apples, meat, cider), set up the way Westwood sets its traders. Please try buying from them: I could only
    check that the map loads. They greet you with lines from the game's own text file that fit any town ("Welcome,
    Wanderer! We carry the finest wares in all of Nox!", "I bet it's been a long day for you, aye mate?"). All 13 buildings place at every scale tried, with 0 errors and 23-28 of
  29-30 rooms passing. It found:
  - a U-shaped house whose living room came out as two closed-off halves;
  - a round cauldron in a corner crowded by shelves;
  - small rooms that lost their only table because no chairs fit round it.
- Fixes found along the way, among them:
  - rooms too small for their kind;
  - L- and T-shaped rooms where nothing could be placed;
  - wall lining that skipped whole walls;
  - big rooms that stopped filling;
  - beds without nightstands;
  - halls without hearths;
  - dirt floors in a manor;
  - hard floor seams at doorways;
  - props meant to stand beside a door (signs, water barrels, goods on display) were never placed in any map,
    TreePlace included. Signs now read what the building is ("Tavern", "General Store").

## Task 2: maps of different styles and what sets them apart

- `rules/BIOMES.md` describes caves, ice and lava as Westwood builds them: floors, walls, signature objects, light,
  ambient colour, creatures, and their built parts.
- `rules/CULTURES.md` is new tonight. It measures how Westwood furnishes ogre lairs, the Land of the Dead and Dun Mir,
  room by room: which pieces stand where, how often and how densely.
- From that, new room kinds:
  - ogre den, feasting hall and hoard: straw heaps, crude beds, a fire pit ringed by stools, meat, carcasses;
  - dark chapel and dark crypt: the lich god's statue, mana obelisks, judgement balances, tombstones in rows, wall
    sconces, bones.
- Three culture buildings: the **ogres' keep** (dungeon stone, in Darkdelve), the **dark temple** (Land of the Dead,
  in Frostfang) and the **demon forge** (Dun Mir hall, in Emberdeep).

- Late in the night I calibrated the biome maps against Westwood's own densities: Frostfang is now an open
  snowfield like Westwood's ice maps (4.9 decorations per 100 tiles, from 16.7; fewer coloured lights, more torches
  by the walls). Emberdeep is thinned to Westwood's lava range.
- Then the ground: the snow's patches of other floors had formed rings round each other, where Westwood's ground is a
  patchwork (about two spots per 100 tiles where three floors meet). Each floor now has a pattern of its own, rock
  shows through the snow, and Frostfang has 81 rock outcrops. The checker: Darkdelve and Emberdeep have no errors or
  warnings; Frostfang has one warning (fewer cliff walls than Westwood's ice maps, which are cut by narrow passages).

## The town lab's outskirts (toward morning)

- I measured where the walls of Westwood's towns stand (`rules/town_walls.py`, `rules/TOWNS.md`). Only a seventh are
  houses. Most ring blocks of forest that the paths loop round, and fenced plots with a purpose: graveyards,
  orchards, parks, quarries, jail cells, monuments.
- Westwood's towns also have far fewer tree objects than I planted: about 2 per 100 floor tiles against the town
  lab's 11. The forest wall is itself drawn as trees.
- The town lab now has outskirts: a glade between each pair of roads, reached by forest paths that loop round four
  blocks of forest, and 26 small clumps of forest in the meadows.
- New `kit/yards.py` builds nine yards, each fenced and gated the way Westwood does it: a graveyard, a quarry, two
  orchards, a monument, a park of benches, two jail cells by the town gate, and fields by the mill and the southern
  homes.
- The checker now gives the town lab 0 errors and 0 warnings, the first time. Walls are 26.4 per 100 tiles (Westwood's
  towns 25.9-49.2); decorations 20.4 (Westwood 7.9-23.7, typical 19). It loads in the server with all 41 creatures
  and 21 waypoints found. It is installed as TownLab, and the new overview picture is in `review/out/TownLab/`.

## Tasks 3-5: NPCs

- `rules/NPCS.md` covers where Westwood places its creatures, how many, how they stand and how they move (routes,
  patrols, guards).
- Behaviour sets written in Go for OpenNox (`mapgen/kit/behaviours/`):
  - a sentry that rouses the others;
  - a patrol along waypoints;
  - a pack following its leader;
  - skittish creatures that flee;
  - an ambush that springs when you come near;
  - townsfolk wandering between spots;
  - villagers who run for their doorstep when a wolf comes into town, then go back to their rounds (new, used by
    the town lab).
- **NpcLab** is the test map with the first six; the town lab has the villagers.
- The culture buildings use them:
  - the ogre warlord, the skeleton lord and the demon are sentries;
  - grunts, ghosts and ember demons patrol through the rooms;
  - skeletons lie in ambush in the crypt;
  - imps flee when hit.
- The server's self-check finds every scripted creature and waypoint in every map: Darkdelve 45 of 45, Frostfang
  79 of 79, Emberdeep 5 of 5, NpcLab 25 of 25, TownLab 39 of 39.

## Task 6: a fireball staff that shoots a harpoon

- `rules/WEAPONS.md` explains how each weapon fires its projectile (from the game's `thing.bin`) and how the
  warrior's harpoon works inside OpenNox.
- The **Harpoon** test map holds a fireball staff whose fireballs are turned into harpoon bolts by a map script: they
  strike the first creature they meet and reel it in. It loads in the server; I could not play it, so please try it:
  pick up the staff and cast at the zombies.

## Known weak spots (worth a look when you review)

- The dark chapel's colonnade of glowing obelisks is dense; you may like it or not.
- Three of the building lab's 16 buildings still miss the bar on details: a back wall 31% lined against 35%,
  coverage a point under target. Odd-shaped smithies with short back walls are the most frequent case.
- The town lab's yards are new and simple: the field's crops and the monument's torches are sparser than I meant, and
  there is no trader's stall or flower garden yet.

## What I would do next, with your go-ahead

- Your numbered review of TreePlace v0.4 and of the three biome structures.
- A large town map using the manor and the hub plan at the bigger scale.
- Phase 6: package the process as a skill.
