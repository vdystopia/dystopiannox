# Water and crossings

Schema of `rules/out/water.json`:
- `water_materials{material: tiles_all, sp_weighted, maps, categories}`
- `shore_structure{kind: distance_from_land_weighted percentiles, mean}`: kind = deep / shallow / plain / swamp_*; distance 1 = water tile touching land, counted in tile steps.
- `bodies{}`: campaign water bodies; size, stream width (tiles and cells), lake depth, composition.
- `walls_on_water{}`: walls whose cell is covered by water tiles; invisible vs visible; distance from land; shore fencing share.
- `crossings{bridge|ford: count_sp, length_tiles, width_tiles, materials, end_materials, edges_on_crossing, water_beside, examples}`
- `kits{kit: chains, maps, units_per_chain, sequences, step_offsets_px, front_back_offset_px, floor_under, walls_near}` and `kit_examples[]`.

## Water materials

- Water: 11563 tiles in 51 maps, categories {'multiplayer': 238, 'campaign': 7313, 'quest': 840, 'social': 3172}
- WaterDeep: 9029 tiles in 26 maps, categories {'campaign': 8771, 'social': 258}
- WaterSwampShallow: 7847 tiles in 12 maps, categories {'multiplayer': 158, 'campaign': 7610, 'social': 79}
- WaterShallow: 7599 tiles in 32 maps, categories {'campaign': 7510, 'social': 89}
- WaterSwampDeep: 3140 tiles in 11 maps, categories {'campaign': 3131, 'social': 9}
- WaterDeepNoTeleport: 2414 tiles in 4 maps, categories {'quest': 1599, 'multiplayer': 815}
- WaterSwampShallowNoTeleport: 2361 tiles in 1 maps, categories {'quest': 2361}
- WaterShallowNoTeleport: 2133 tiles in 4 maps, categories {'quest': 1499, 'multiplayer': 634}
- WaterNoTeleport: 207 tiles in 1 maps, categories {'multiplayer': 207}

## Shore structure (campaign maps, distance from land in tile steps)

- plain: {'p10': 1, 'p25': 1, 'p50': 1, 'p75': 2, 'p90': 3} (mean 1.46)
- shallow: {'p10': 1, 'p25': 1, 'p50': 1, 'p75': 2, 'p90': 3} (mean 1.66)
- deep: {'p10': 1, 'p25': 2, 'p50': 3, 'p75': 5, 'p90': 8} (mean 3.83)
- swamp_shallow: {'p10': 1, 'p25': 1, 'p50': 1, 'p75': 2, 'p90': 2} (mean 1.47)
- swamp_deep: {'p10': 1, 'p25': 2, 'p50': 3, 'p75': 4, 'p90': 5} (mean 2.99)

## Water bodies

- 534 campaign bodies: 17 streams, 517 pools/lakes. Size (tiles): {'p10': 5, 'p25': 7, 'p50': 17, 'p75': 45, 'p90': 167}.
- Stream width: typical {'p10': 1.0, 'p25': 1.0, 'p50': 1.0, 'p75': 1.0, 'p90': 3.0} tiles = {'p10': 1.4, 'p25': 1.4, 'p50': 1.4, 'p75': 1.4, 'p90': 4.2} cells; widest point {'p10': 3, 'p25': 3, 'p50': 5, 'p75': 5, 'p90': 9} tiles; size {'p10': 88, 'p25': 91, 'p50': 162, 'p75': 200, 'p90': 1507} tiles.
- Lake depth (max distance from shore, tiles): {'p10': 1, 'p25': 1, 'p50': 2, 'p75': 3, 'p90': 4}.

## Walls on water

- Counts (all maps): {'visible:water_by_void': 4618, 'invisible:on_water': 3801, 'invisible:shore_edge': 2860, 'visible:on_water': 2536, 'visible:shore_edge': 684, 'invisible:water_by_void': 68}.
- Distance of wall from land: {'visible': {'p10': 1, 'p25': 1, 'p50': 1, 'p75': 1, 'p90': 1}, 'invisible': {'p10': 1, 'p25': 1, 'p50': 1, 'p75': 2, 'p90': 2}}.
- Wall materials on water (weighted): {'InvisibleWallSet': 1715.8, 'RootLight': 892.0, 'CaveWall2': 460.0, 'Shard': 397.0, 'DecidiousWallGreen': 242.5, 'Coni-Wall1': 202.0, 'SewerWall': 188.7, 'Rock': 139.0}.
- Share of shore tiles fenced by a wall: 58%.

## Crossings (floor)

### bridge (106 in campaign maps)

- Length {'p10': 1, 'p25': 2, 'p50': 4, 'p75': 5, 'p90': 6} tiles, width {'p10': 2, 'p25': 2, 'p50': 3, 'p75': 4, 'p90': 5} tiles.
- Materials: {'GreenBrick': 0.326, 'GalavaBrick3': 0.276, 'WoodDark2': 0.08, 'WoodDark': 0.08, 'WoodGray': 0.053, 'DunMirBrick1': 0.048, 'DirtDark2': 0.024, 'WoodSlatFloor2': 0.023}.
- Land at the ends: {'GreenBrick': 0.272, 'GalavaBrick3': 0.268, 'DunMirBrick1': 0.094, 'GalavaBrick2': 0.067, 'DirtDark2': 0.064, 'WoodDark': 0.044}.
- Edges on the crossing (overlay|type): {'Water|DirtRidge': 0.418, 'WaterShallow|BrickEdgeBrown': 0.341, 'WaterDeep|BlendEdge': 0.059, 'DirtDark2|BlendEdge': 0.032, 'Water|BrickEdgeBrown': 0.031, 'WaterShallow|BlendEdge': 0.031}.
- Water beside: {'WaterShallow': 0.439, 'Water': 0.363, 'WaterDeep': 0.107, 'WaterSwampShallow': 0.073}.
- Examples: Con08e 13x2 ['WoodDark2', 'DirtDark2']; War08e 13x2 ['WoodDark2', 'DirtDark2']; Wiz08e 13x2 ['WoodDark2', 'DirtDark2']; Con06a 5x5 ['GalavaBrick3']; Con06a 5x5 ['GalavaBrick3']; Con06a 5x5 ['GalavaBrick3']

### ford (512 in campaign maps)

- Length {'p10': 1, 'p25': 1, 'p50': 2, 'p75': 2, 'p90': 4} tiles, width {'p10': 2, 'p25': 2, 'p50': 3, 'p75': 5, 'p90': 6} tiles.
- Materials: {'SwampGrass': 0.572, 'DirtDark2': 0.149, 'CaveHardBrown': 0.101, 'DirtBlue': 0.047, 'DirtCrackedLight': 0.031, 'GrassSparse2': 0.022, 'GreenBrick': 0.021, 'ManaMineDirt': 0.019}.
- Land at the ends: {'SwampGrass': 0.413, 'DirtDark2': 0.177, 'CaveHardBrown': 0.124, 'DirtBlue': 0.075, 'GreenBrick': 0.034, 'GrassNormYellow': 0.033}.
- Edges on the crossing (overlay|type): {'WaterSwampShallow|SwampEdge': 0.533, 'Water|DirtRidge': 0.195, 'WaterShallow|GrassEdge': 0.051, 'WaterShallow|ShallowWaterAndGrass': 0.046, 'Water|BlendEdge': 0.043, 'GreenBrick|BlendEdge': 0.039}.
- Water beside: {'WaterSwampShallow': 0.584, 'Water': 0.277, 'WaterShallow': 0.138, 'WaterDeep': 0.001}.
- Examples: Con09a 14x3 ['SwampGrass']; War09a 14x3 ['SwampGrass']; Wiz09a 14x3 ['SwampGrass']; Con08e 13x3 ['DirtDark2', 'GreenBrick']; War08e 13x3 ['DirtDark2', 'GreenBrick']; Wiz08e 13x3 ['DirtDark2', 'GreenBrick']

## Crossing kits (objects)

### DockDown: 45 chains in 5 maps

- Units per chain: {1: 36, 2: 9}. Sequences: {'FarRamp': 15, 'Center1': 15, 'Center1 > NearEnd': 9, 'NearRamp': 6}.
- Step between units (px): {'36.0,42.0': 8, '35.0,41.0': 1}. Front->Back offset (px): {}.
- Floor under: {'WoodGray': 54}. Walls near: {'InvisibleWallSet': 263, 'Coni-Wall1': 1}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {}.

### DockUp: 9 chains in 4 maps

- Units per chain: {1: 7, 2: 1, 3: 1}. Sequences: {'Center1': 2, 'FarRamp': 2, 'NearRamp': 2, 'FarEnd > Center1': 1, 'FarCenter2': 1, 'FarEnd > Center1 > NearEnd': 1}.
- Step between units (px): {'-42.0,44.0': 2, '-45.0,47.0': 1}. Front->Back offset (px): {}.
- Floor under: {'WoodGray2': 9, 'DirtDark2': 2, 'GrassSparse2': 1}. Walls near: {'InvisibleWallSet': 55}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {'0.7,-0.7': 1}.

### LavaBridge1: 10 chains in 7 maps

- Units per chain: {3: 7, 4: 3}. Sequences: {'FarEnd > Center > NearEnd': 7, 'FarEnd > Center > Center > NearEnd': 3}.
- Step between units (px): {'61.0,61.0': 8, '28.0,28.0': 7, '44.0,44.0': 2, '26.0,29.0': 1, '60.0,61.0': 1, '27.0,28.0': 1}. Front->Back offset (px): {'-1.0,-28.0': 12, '0.0,-30.0': 7, '0.0,-29.0': 6, '-2.0,-29.0': 2}.
- Floor under: {'VolcanicCraggy': 34, 'CaveHardBrown': 14, 'Lava': 14, 'GalavaBrick': 4}. Walls near: {'InvisibleWallSet': 677, 'InvisibleBlockingWallSet': 23, 'IronFenceDamaged': 2}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {'-0.7,-0.7': 10}.

### LavaBridge2: 5 chains in 5 maps

- Units per chain: {4: 4, 3: 1}. Sequences: {'NearEnd > Center > Center > FarEnd': 3, 'FarEnd > Center > Center > NearEnd': 1, 'NearEnd > Center > FarEnd': 1}.
- Step between units (px): {'28.0,-27.0': 3, '62.0,-60.0': 2, '42.0,-45.0': 2, '-28.0,28.0': 1, '-43.0,45.0': 1, '-60.0,62.0': 1}. Front->Back offset (px): {'1.0,-29.0': 5, '1.0,-28.0': 3, '2.0,-27.0': 3, '0.0,-30.0': 3}.
- Floor under: {'VolcanicCraggy': 14, 'GreenBrick': 10, 'GalavaBrick': 8, 'CaveHardBrown': 5, 'Lava': 1}. Walls near: {'InvisibleWallSet': 295, 'LOTDMagicOrnate': 13, 'IronFence': 5, 'Volcano': 1}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {'0.7,-0.7': 5}.

### RopeBridge1: 24 chains in 14 maps

- Units per chain: {4: 7, 6: 7, 5: 4, 8: 2, 16: 1, 3: 1, 1: 1, 2: 1}. Sequences: {'FarEnd > Center2 > Center > NearEnd': 5, 'FarEnd > Center2 > Center > Center2 > Center > NearEnd': 4, 'FarEnd > Center > Center > Center > NearEnd': 4, 'FarEndBack > CenterBack > CenterBack > NearEndBack': 2, 'FarEnd > Center > Center2 > Center > Center2 > NearEnd': 2, 'Center2 > Center > Center2 > Center > Center2 > Center > Center2 > Center': 2}.
- Step between units (px): {'46.0,46.0': 11, '45.0,45.0': 8, '45.0,53.0': 7, '46.0,45.0': 5, '45.0,40.0': 5, '36.0,37.0': 5}. Front->Back offset (px): {'0.0,-30.0': 43, '0.0,-30.7': 18, '-1.0,-31.0': 7, '0.0,-29.3': 6}.
- Floor under: {'WoodDark': 165, 'SwampGrass': 25, 'WoodDark2': 15, 'DirtDark2': 14, 'GrassNorm': 6}. Walls near: {'InvisibleWallSet': 1242, 'DecidiousWallGreen': 30, 'Log': 18, 'DilapidatedShort': 8}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {'-0.7,-0.7': 19, '0.7,-0.7': 1}.

### RopeBridge2: 45 chains in 26 maps

- Units per chain: {4: 19, 1: 6, 6: 5, 5: 5, 3: 4, 8: 4, 10: 1, 2: 1}. Sequences: {'FarEnd > Center > Center > NearEnd': 6, 'NearEndBack': 5, 'FarEnd > Center2 > Center2 > NearEnd': 5, 'FarEnd > Center > Center > Center > Center > NearEnd': 3, 'Center > Center2 > Center > FarEnd': 3, 'FarEnd > Center > Center > Center2 > Center2 > Center > Center2 > NearEnd': 3}.
- Step between units (px): {'-46.0,46.0': 28, '-45.0,39.0': 12, '-44.0,56.0': 8, '-45.0,38.0': 8, '-44.0,44.0': 6, '-47.0,47.0': 6}. Front->Back offset (px): {'0.0,-30.0': 86, '-1.0,-29.0': 20, '0.0,-31.0': 13, '-2.0,-28.0': 10}.
- Floor under: {'WoodDark2': 180, 'WoodDark': 65, 'SwampGrass': 37, 'WoodThinSlatDarkREV': 27, 'DirtDark2': 21}. Walls near: {'InvisibleWallSet': 1916, 'DecidiousWallGreen': 32, 'Dilapidated': 8, 'RootLight': 7}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {'0.7,-0.7': 30}.

### RopeBridgeBroken1: 12 chains in 6 maps

- Units per chain: {1: 12}. Sequences: {'NearEnd': 6, 'FarEnd': 6}.
- Step between units (px): {}. Front->Back offset (px): {'0.0,-30.0': 12}.
- Floor under: {'GrassSparse2': 18, 'GrassNormYellow': 6}. Walls near: {'InvisibleWallSet': 144}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {}.

### RopeBridgeBroken2: 5 chains in 3 maps

- Units per chain: {1: 5}. Sequences: {'NearEnd': 2, 'FarEnd': 2, 'NearEndBack': 1}.
- Step between units (px): {}. Front->Back offset (px): {'0.0,-30.0': 4}.
- Floor under: {'SwampGrass': 6, 'DirtDark2': 2, 'WaterSwampShallow': 1}. Walls near: {'InvisibleWallSet': 39}.
- Direction NearEnd -> FarEnd (unit vector, screen x/y): {}.

