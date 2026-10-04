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
   the installed map. The design in the repository has kept improving: all 11 of its rooms now pass the room score.

## Task 1: generate and evaluate rooms and structures

- **Room lab** (`mapgen/designs/roomlab.py`, scored by `review/roomscore.py`): every room kind (21 of them) at three
  sizes, now at Westwood's true sizes over two lab maps (`RoomLab` and `RoomLab2`). It went from 23 of 42 rooms
  passing to 59-61 of 63 over three seeds.
- **Building lab** (`mapgen/designs/buildinglab.py`, scored by `review/buildingscore.py`): every building role,
  generated and furnished, scored on room sizes, reachability and the room scores. 16 roles now, including a manor
  and the three culture buildings; 8-10 of 16 pass at Westwood's size and the kit's.
- **Bigger buildings**: an 8-room **manor**. Westwood's multi-room buildings give their largest room half or more of
  the floor and reach the other rooms through it (few have corridors), so large buildings now use a **hub plan**: a
  great hall down the middle with the other rooms along both sides, every door opening onto the hall. The great hall
  has hearths, long tables with benches, statues and trophies, with the doorways kept clear.
- **Town lab** (`mapgen/designs/townlab.py`, installed as `maps/TownLab`): the whole village pipeline at the
  bigger scale. A market town of 13 buildings round a cobbled square, with the manor, inn, store and smithy
  facing it and homes along the streets.
  - The square follows Westwood's own, measured round its 12 town wells and fountains: a fountain ringed by potted
    plants and flowers, benches facing in, ornate street lamps at the edge.
  - Thirteen townsfolk walk between the square and the doorsteps, and wolves, bats and urchins keep to the woods
    round the town, as in Westwood's towns. The server's self-check finds all 28 scripted creatures. All 13 buildings place at every scale tried, with 0 errors and 23-28 of
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
  - hard floor seams at doorways.

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
- **NpcLab** is the test map with all of these.
- The culture buildings use them:
  - the ogre warlord, the skeleton lord and the demon are sentries;
  - grunts, ghosts and ember demons patrol through the rooms;
  - skeletons lie in ambush in the crypt;
  - imps flee when hit.
- The server's self-check finds every scripted creature and waypoint in every map: Darkdelve 46 of 46, Frostfang
  74 of 74, Emberdeep 5 of 5, NpcLab 25 of 25, TownLab 39 of 39.

## Task 6: a fireball staff that shoots a harpoon

- `rules/WEAPONS.md` explains how each weapon fires its projectile (from the game's `thing.bin`) and how the
  warrior's harpoon works inside OpenNox.
- The **Harpoon** test map holds a fireball staff whose fireballs are turned into harpoon bolts by a map script: they
  strike the first creature they meet and reel it in. It loads in the server; I could not play it, so please try it:
  pick up the staff and cast at the zombies.

## Known weak spots (worth a look when you review)

- Frostfang's temple library is a little sparse.
- The dark chapel's colonnade of glowing obelisks is dense; you may like it or not.
- About half the building-lab buildings still miss the bar on details: a back wall 31% lined against 35%, coverage a
  point under target.

## What I would do next, with your go-ahead

- Your numbered review of TreePlace v0.4 and of the three biome structures.
- A large town map using the manor and the hub plan at the bigger scale.
- Phase 6: package the process as a skill.
