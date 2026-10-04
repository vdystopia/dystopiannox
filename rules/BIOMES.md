# Biomes: caves, snow and ice, lava

This file says what sets Westwood's cave, ice and lava maps apart, and how the kit builds them.

**Sources.**
- `py rules/biomes.py` profiles each biome: its floors, walls, signature objects, light, ambient colour and creatures, against all of Westwood's other single-player maps. It counts each layout once. It writes `rules/out/biomes.json`.
- `py rules/biome_places.py` measures where each signature object stands: on the liquid, against a wall (within 1.5 cells of one), or in the open. Densities are per 100 floor tiles of that context. It writes `rules/out/biome_places.json`.
- `rules/environments.py` types every map: 11 cave maps (5 layouts), 4 ice maps (2 layouts: the Wastelands and the Wizard finale) and 10 lava maps (9 layouts).

**Building.**
- `mapgen/kit/biome.py` holds the palettes and the Dresser.
- `mapgen/designs/darkdelve.py` (cave), `frostfang.py` (ice) and `emberdeep.py` (lava) are the first maps.

## What all three share, and what sets them apart from the green world

**What they share.**
- **Natural walls.** Every walkable area is ringed by a cliff material instead of a forest wall, with black void beyond.
- **Wall-hugging fringe.** Pillars, rocks or snow-laden trees thicken in front of the walls and thin toward the middle. The planter's "forest" for each biome does this.
- **Liquid behind cliffs.** The lava lake and the underground lake sit below the cliffs, out of reach, and their tiles run under the wall line. `Dresser.reserve_pool` keeps the land out of them before `carve()`.
- **Islands.** Ice and lava break their open ground with cliff-ringed outcrops (`Land.thickets`). The outcrops' tops take a floor (`cap_islands`) so they read as the top of the rock, not as a pit into the void.

**How they differ.**

| | Cave | Ice | Lava |
|---|---|---|---|
| Ambient | dark blue-grey (29, 34, 45); regions (32, 48, 48) | cold blue (70, 70, 140); regions (64, 64, 128) | dark red (45, 16, 15); regions (16-112, 0, 0) |
| Lights per 100 tiles | 4.0, amber (128, 96, 32) | 1.1, dim and cold | 7.9, red (96-224, 0, 0) and white |
| Creatures per 100 tiles | 1.0: bats, grunts, scorpions, zombies, spiders, urchins | 0.7: wolves (packs), undead, ghosts | 0.6: imps, ember and melee demons, skeletons, zombies |

## Cave

**Floors.** CaveHardBrown 0.28, then patches:
- CaveHardTan 0.06;
- CaveHardDark;
- DirtDark2 0.11;
- ManaMineDirt in mines.

They blend with BlendEdge, or DirtRidge where dirt meets rock.

**Water.** Underground water (Water) spills over cave floor with a DirtRidge edge (82%).

**Walls.** CaveWall2 0.36, CaveWall 0.19, ManaMineWall in mines.

**Along walls,** per 100 tiles:
- rock pillars: CaveRockPillarShort1 1.75, Short2 1.5, Tall1 1.6, Tall2 1.2;
- boulders 0.9;
- spider webs about 0.7 of each of 3 facings;
- torches 1.6.

**In the open,** per 100 tiles:
- Mushroom3 4.1, in patches;
- pebbles 2.0;
- crumbling pits 2.0 (traps);
- bones 0.9;
- stalagmites 0.25-0.3 (they stand free, not at the walls);
- flame basins 0.5.

**Lights.** Amber coloured lights: 4.5 per 100 open tiles and 3.0 along walls.

## Ice

**Floors.** In the game's art the names mislead:
- IceFloorDeepBlue is the pale snowfield (0.22), where Westwood's snow trees stand (3 per 100 tiles);
- IceFloorRough is blue speckled ice (0.14);
- IceFloorDark is dark slate ice (0.12), used for a frozen lake;
- IceFloorLight is a bright accent.

They blend with BlendEdge. Rock (CaveHardBrown or Tan) meets ice with an IceRidge edge.

**Walls.** IceWall 0.42 (bright blue cliffs), CaveWall 0.27.

**Signature objects.**
- Snow trees (TreeSnowCovered 1-6) are 40-75 times denser than elsewhere. They mix bare white trees with snow-laden pines, grow in clusters, and line the cliffs.
- Ice cracks (IceCrack2/4/6) lie on the ice.
- Blue crystals (MineCrystal05) stand against the walls.
- Bones are scattered about.

**Lights.** Few, about 0.3 coloured lights per 100 tiles, plus torches by the walls. The cold ambient does most of the work.

**Walls per 100 tiles.** 28-33. The plateaus are cut by many cliffs, so an ice map needs outcrops: Frostfang has 81
and reaches 22 wall pieces per 100 tiles. The rest of the gap would take Westwood's layout of narrow passages
between the cliffs, not more islands (bigger outcrops left room for fewer of them: 54).

**Floor junctions.** 1.85-2.65 spots per 100 floor tiles where three floors meet: a patchwork, not bands. Rock
(CaveHardBrown, Tan) shows through the snow in patches.

## Lava

**Floors.** Lava 0.20, VolcanicCraggy 0.14 (the black ground) and CaveHardBrown 0.12, plus brick and marble in the built parts.
- Lava spills over craggy ground with a LavaEdgeBlackDirt edge (80%), and over brown cave floor with LavaEdgeBrownDirt.
- Lava never touches brick or cobble directly: VolcanicCraggy buffers it.

**Walls.** Volcano 0.31 (black cliffs veined red), CaveWall2 0.19, plus town and sewer walls in the built parts.

**On the lava,** per 100 lava tiles:
- SmallFlame 11.2, MediumFlame 4.3, Flame 2.2, LargeFlame 0.85, burning flames 2-3;
- LavaBubble 4-9, about 0.6-0.95 each;
- LavaFountain3 0.5;
- cooled crusts (LavaHardened5/7) 0.4.

Cooled crusts away from the lava read as puddles of lava, so keep them on it.

**On the ground,** per 100 tiles:
- bones 1.2, skulls 0.7;
- FireGrate vents 0.6;
- rocks 0.5;
- rubble (Brick) 0.8 at the walls;
- dark obelisks 1.3 at the walls (shrines).

**Lights.** The most lit biome: 9 coloured lights per 100 lava tiles, 6 per 100 open tiles, about half of them red or orange.

## How to build one (the kit)

```python
d = Dresser(spec, rng, land, "lava")            # palette, ambient and blends
d.reserve_pool(centre_uv, radius_uv)            # before land.carve(): the liquid behind cliffs
d.structure("ogre_keep", "den", toward="heart") # before land.carve(): a building the cavern grows round
land.carve(); outcrops = land.thickets(...)     # islands break up big open ground
land.apply(spec, wall=d.wall, floor=d.base); d.cap_islands(outcrops)
d.ground(); d.paint_pools()                     # patches of the other floors, then the liquid's tiles
d.clusters(types, squares, n, ...)              # landmarks and scenes: crystal formations, crate stacks, bone heaps
d.furnish_structures(); d.garrison()            # the building's rooms in its culture; its keepers' behaviours
d.dress_liquid(); d.vegetate(); d.scatter_open(); d.rim(); d.lights(); d.creatures()
d.declare_rooms(path)                           # <map>.rooms.json for the room review and scores
```

## Built parts

Westwood's biome maps hold buildings in their own styles (rules/out/buildings.json styles; rules/CULTURES.md for how
their rooms are furnished):
- **Caves:** dungeon stone (DungeonStone walls 0.12 of the caves' walls, GreenBrick floors 0.19 of their floors), Dun
  Mir's cathedral walls, mine walls. The kit's structure: the ogres' keep (`dungeon_block`), its feasting hall, straw
  beds and hoard furnished as Westwood's ogre lairs; the ogre warlord a sentry who rouses the rest, brutes on
  guard in the den, grunts patrolling a loop through the rooms.
- **Ice:** the Land of the Dead's temples (LOTDOrnate walls 0.19 of the ice maps' walls; LOTDTempleFacade, LOTDPitted
  and LOTDDark floors; the style's outside floor is blue ice, 0.39). The kit's structure: the dark temple
  (`lotd_ornate`), its lich god's chapel, crypt and library; the skeleton lord a sentry, skeletons lying in
  ambush in the crypt until the player comes near, ghosts patrolling the rooms.
- **Lava:** halls and town walls (GalavaTownWall 0.12, DunMirCathedral 0.06; GreenBrick, LOTDBlackMarble, GalavaBrick2
  and DunMirBrick1 floors; the `dunmir_hall` style's outside floors include VolcanicCraggy, 0.10). The kit's
  structure: the demon forge (`dunmir_hall`), its forge, hall of arms and store; a demon sentry, ember demons
  patrolling, imps that flee when hit.

Lessons from the first three maps:
- **Group everything.** Props spread evenly over an area read as a grid; group them (`clusters`). Crystals form formations around a tall one; crates stack in threes to fives; mushrooms grow in patches.
- **Keep props out of walls.** Placement checks the cell and its neighbours (`wall_clear`).
- **Stay inside the grid.** Every area stays inside the map with room for its walls: centre plus radius within cells 12-243.
- **Nothing on the rock.** An island's capped top is not land: no pillar or prop stands there (the checker reads a capped
  top holding pillars as a room of columns).
- **Nothing in a building.** The planter, the props and the creatures keep off a structure's squares (`land.taken`).
- **Patches overlap.** Each patch floor has a noise field of its own (`Dresser.ground`), so patches of different floors
  meet and overlap as Westwood's do. One shared field nested them in bands round each other: Frostfang had 1.0
  junctions per 100 tiles against Westwood's 1.85-2.65, and a floor whose threshold lay beyond an earlier one's was
  never laid at all. Now 1.94. A palette's `patch_scale` sets how small the patches are (ice 1.35).
- **As sparse as Westwood's.** Westwood's ice maps are open snowfields: 3.4-5.2 decorations per 100 floor tiles (about 2.3 snow trees), 0.09-0.23 coloured lights and torches by the walls; its lava maps carry 2.9-13.6 decorations. The palettes' `tree_depth` and `undergrowth` keep the biome maps in those ranges (Frostfang went from 16.7 decorations per 100 tiles to 4.9).
