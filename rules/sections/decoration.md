# Decoration and furniture placement rules

Mined by `rules/decoration.py` from the reference corpus. Style figures use the 120 single-player maps weighted so each distinct layout counts once (62 layouts); `observed_types` uses all 157 maps.

## JSON schema (`rules/out/decoration.json`)

```
observed_types[type] = {category, count, maps}            # every decoration type seen (all maps)
family_of_material[material] = family                     # grass/dirt/cave/dungeon/town_paving/interior/swamp/ice/lava/water/other
palettes_by_material[material] / palettes_by_family[family] = {
    tiles_weighted, maps, objects_per_100_tiles, top_types[[type, share]...],
    category_density_per_100_tiles{category: value}       # family palettes only
}
spacing_px[category] = {nearest_same_category{p10..p90}, share_isolated_over_230px, n_weighted, maps}
wall_distance_cells[category] = {quantiles{p10..p90}, share_within_1_cell, share_within_2_cells}
trees = {floor_family_share, on_grass_distance_to_path_tile_cells{..}, on_grass_share_within_1_cell_of_path,
         density_per_100_grass_tiles_by_wall_distance{band: value}}
clusters_35px[kind] = {cluster_size{p10..p90}, share_singletons, mean_same_type_share}
co_occurrence[] = {a, b, weighted, maps, share_of_a_with_b_within_60px, distance_px{..}, median_offset_px[dx,dy]}
directional_variants[base] = {variants[type] = {weighted, maps, share_free_standing, wall_side_shares{"line|side": share},
                              dominant, dominant_share, perpendicular_distance_px{..}},
                              use_variant_for_wall_side{"line|side": {variant, share, weighted}}}
directional_convention = text  (line '/' sides BR/TL, line '\' sides TR/BL)
blockers[type] = {weighted, maps, floor_family_share, share_on_wall_cell, nearest_object_within_40px}
ambient_sounds_by_family[family] = {per_100_tiles, top_types}
```
Quantiles are weighted p10/p25/p50/p75/p90. Distances: px = world pixels (23 per cell).

## Key rules

- **Density by terrain** (decoration objects per 100 floor tiles): grass 21.25, dirt 18.03, cave 15.68, swamp 11.56, interior 11.5, town paving 8.05, dungeon 6.1, lava 6.06, ice 5.98. Grass = small plants (Plant4/Plant5/PlantForest1), flowers, mushrooms and trees; dirt and cave = rocks, pebbles, rock pillars and mushrooms; dungeon = bones, webs, columns.
- **Scenery hugs walls**: within 1 cell of a wall - plants 56%, rocks 56%, trees 57%, furniture 52%, clutter 64%, webs 92%; wall decorations sit on the wall cell (95% within 1 cell).
- **Trees line the edges of outdoor areas**: trees per 100 grass tiles by distance from the bounding wall: 0-2 cells: 3.9, 2-4 cells: 3.27, 4-8 cells: 1.03, 8-16 cells: 1.62. Only 6% of trees stand within 1 cell of a path tile (median 5 cells away). Median tree spacing 65.2 px (~2.8 cells).
- **Small scenery is close-packed**: median nearest neighbour - plants 23.9 px, flowers/tufts/mushrooms 24.3 px, rocks 28.9 px. Mushrooms clump (p75 cluster 3, p90 5, mostly one type); flowers are almost always single (91% singletons).
- **Furniture sets**: chairs with tables and desks (about half of tables/desks have a chair within 60 px), nightstands with beds (68% of nightstands beside a bed, median 35 px), bellows with fireplaces, stools with Urchin/Ogre tables, straw with ogre beds; barrels and crates in small groups (p75 2, p90 3).
- **Directional variants follow the wall they back onto** (table below): one variant per wall side with 80-100% consistency for beds, nightstands, desks, benches, chests, sconces, lanterns and DunMir torches. Furniture is placed mostly against the walls on the BR side of '/' walls and the BL side of '\' walls.
- **Extent\* blockers** are invisible collision shapes: on town paving/dungeon floors, often on wall cells or alone (stairs, ledges, fountains, tower bases), and under scenery such as swamp Plant3 and Galava trees.

## Palettes by floor family (decoration objects per 100 tiles)

| family | tiles (weighted) | maps | per 100 tiles | category densities | top types |
|---|---|---|---|---|---|
| dungeon | 104170 | 86 | 6.1 | bones 2.08, structure 1.69, furniture 0.53, clutter 0.5, rock 0.48 | ArmBoneImmobile 16%, SkullImmobile 11%, FireGrate 3%, SpiderWebEast 3%, SpiderWebNorth 3%, LOTDColumn1 2%, Crypt3 2%, Brick 2% |
| dirt | 87237 | 85 | 18.03 | rock 8.53, furniture 2.12, flower_tuft 1.92, bones 1.63, clutter 1.24 | CaveRocksPebbles 9%, CaveRocksPebblesImmobile 6%, Mushroom3 5%, CaveRocksSmall 4%, CaveRocksSmallImmobile 3%, Mushroom4 3%, CaveRockPillarTall1 3%, CaveRocksTinyImmobile 2% |
| town_paving | 55242 | 86 | 8.05 | furniture 2.11, structure 1.29, clutter 0.95, plant 0.82, rock 0.71 | Plant5 4%, Plant4 3%, Column5 3%, Barrel 2%, LegBone 2%, FlowersYellowSparse 2%, Barrel2 2%, Straw2 2% |
| grass | 51959 | 61 | 21.25 | plant 9.95, flower_tuft 3.85, tree 3.13, rock 1.95, clutter 0.65 | Plant4 15%, Plant5 11%, PlantForest1 5%, FlowersYellowSparse 4%, Mushroom3 3%, PlantFern1 3%, FlowersPurpleSparse 2%, PlantBarren1 2% |
| cave | 45657 | 67 | 15.68 | rock 7.57, flower_tuft 3.28, structure 1.48, clutter 1.23, bones 0.58 | CaveRocksPebbles 8%, Mushroom3 8%, Mushroom4 5%, MineBeam1 4%, Mushroom1 4%, CaveRocksMedium 4%, CaveRockPillarTall1 4%, CaveRocksSmall 4% |
| interior | 30804 | 93 | 11.5 | furniture 5.01, structure 3.11, clutter 1.08, bones 0.71, web 0.55 | ArmBone 2%, Statue2c 2%, SpiderWebNorthEast 2%, CathedralColumn3Cracked 2%, DarkWoodenChair3 2%, DarkWoodenChair1 2%, Column6 2%, Column8 2% |
| lava | 25399 | 20 | 6.06 | rock 2.35, water_decor 2.11, bones 1.25, structure 0.16, furniture 0.08 | LegBone 10%, LavaBubble6 8%, LavaBubble5 6%, LavaBubble9 6%, Skull 6%, LavaBubble4 6%, LavaBubble8 5%, LavaBubble7 4% |
| swamp | 21996 | 12 | 11.56 | plant 6.5, flower_tuft 1.81, tree 0.76, rock 0.63, structure 0.61 | Plant3 18%, Plant4 11%, Plant5 7%, PlantFern1 7%, PlantForest1 4%, Mushroom3 4%, Mushroom2 2%, GrassTuft2 2% |
| water | 14208 | 56 | 10.41 | water_decor 4.95, plant 3.34, rock 1.52, structure 0.27, clutter 0.13 | Plant3 19%, Plant1 9%, WaterRipplesDrip02 7%, WaterBubbles 5%, WaterRipplesDrip01 4%, WaterRipplesMedium03 3%, CaveRockPillarTall1 3%, SmallStalagmite 3% |
| ice | 10744 | 6 | 5.98 | tree 5.3, furniture 0.2, other 0.15, wall_decor 0.12, rock 0.12 | TreeSnowCovered3 22%, TreeSnowCovered5 17%, TreeSnowCovered6 15%, TreeSnowCovered4 15%, TreeSnowCovered2 14%, TreeSnowCovered1 6%, LOTDBanner1 2%, IceCrack2 1% |
| other | 127 | 13 | 31.5 | furniture 16.08, clutter 15.42 | Barrel2 15%, Fireplace4 13%, WaterBarrel 10%, Barrel 7%, Stove03 5%, WoodenChair3 5%, WoodenChair1 5%, RoundTableWithFood 5% |

## Palettes by floor material (largest 25)

| material | family | tiles | per 100 tiles | top types |
|---|---|---|---|---|
| DirtDark2 | dirt | 49259 | 19.49 | CaveRocksPebbles 12%, CaveRocksSmall 6%, Mushroom3 5%, Mushroom4 3%, LegBone 3%, CaveRocksHuge 2%, CaveRocksPebblesImmobile 2% |
| GreenBrick | dungeon | 36677 | 8.13 | ArmBoneImmobile 11%, SkullImmobile 6%, SpiderWebEast 6%, Crypt3 5%, FireGrate 4%, SpiderWebNorth 4%, Brick 4% |
| GrassNorm | grass | 30410 | 24.8 | Plant4 16%, Plant5 12%, PlantForest1 6%, FlowersYellowSparse 5%, PlantFern1 3%, Mushroom3 3%, Plant2Flowered 3% |
| CaveHardBrown | cave | 30032 | 14.89 | Mushroom3 11%, Mushroom4 7%, CaveRocksPebbles 7%, Mushroom1 5%, CaveRocksMedium 5%, CaveRockPillarTall1 4%, CaveRockPillarShort2 4% |
| LOTDPitted | dungeon | 25046 | 3.66 | ArmBoneImmobile 25%, SkullImmobile 17%, LOTDColumn1 10%, LOTDTapestry2 6%, LOTDTapestry1 4%, LOTDTombstone1 2%, FireGrate 2% |
| SwampGrass | swamp | 15048 | 13.52 | Plant4 13%, Plant5 9%, PlantFern1 9%, PlantForest1 5%, Mushroom3 5%, Plant3 4%, Mushroom2 3% |
| Lava | lava | 14757 | 5.66 | LavaBubble6 12%, LavaBubble5 10%, LavaBubble9 10%, LavaBubble4 10%, LavaBubble8 8%, LavaBubble7 6%, LavaHardened5 6% |
| LOTDBlackMarble | dungeon | 11208 | 4.55 | ArmBoneImmobile 13%, SkullImmobile 12%, Coffin1 5%, LOTDColumn1 4%, LOTDTapestry1 4%, LOTDTapestry2 4%, SpiderWebNorth 2% |
| VolcanicCraggy | lava | 10642 | 6.6 | LegBone 21%, Skull 13%, ArmBone 8%, Rock8 7%, SmallStalagmite 4%, LargeStalagmite 4%, Rock6 4% |
| GrassSparse2 | grass | 10590 | 14.02 | Plant4 14%, Plant5 9%, CaveRocksSmall 3%, GrassTuft3 3%, PlantBarren1 3%, Mushroom3 3%, PlantFern1 2% |
| DirtLight2 | dirt | 9418 | 15.03 | CaveRockPillarTall1 7%, CaveRocksPebbles 6%, Plant4 5%, Column5 4%, Mushroom4 4%, Mushroom3 3%, Barrel 3% |
| GalavaBrick3 | town_paving | 8596 | 8.15 | Gargoyle8 5%, Gargoyle3 4%, Barrel2 3%, BlueTapestry2 3%, Gargoyle6 3%, DunMirAltar1 2%, Nightstand4 2% |
| ManaMineDirt | cave | 8411 | 21.19 | MineBeam1 15%, MineBeam2 11%, CaveRocksPebbles 9%, BarrelSteel1 4%, MudBubble3 4%, CaveRocksSmall 3%, Barrel 3% |
| TileDark | interior | 8354 | 6.74 | CathedralColumn3Cracked 11%, ArmBone 9%, SpiderWebNorthEast 6%, Column8 6%, SpiderWebNorth 5%, SpiderWebEast 5%, SkullImmobile 4% |
| DirtHard | dirt | 7049 | 24.4 | CaveRocksPebbles 9%, Mushroom3 8%, CaveRockPillarShort1 5%, CaveRockPillarTall1 5%, CaveRockPillarShort2 4%, CaveRockPillarTall2 4%, CaveRocksPebblesImmobile 3% |
| WeedsSparse | grass | 6793 | 14.35 | PlantBarren1 8%, OgreStraw1 5%, CaveRockPillarShort1 4%, CaveRockPillarTall1 3%, Barrel 3%, CaveRockPillarShort2 3%, CaveRocksPebbles 3% |
| Black | dungeon | 6782 | 0.01 | GrassTuft3 50%, Aspen2 50% |
| GalavaTowerFacade | town_paving | 5651 | 5.08 | Plant5 42%, Plant4 22%, FlowersYellowSparse 8%, TreeGalava07 5%, TreeGalava03 4%, Bush6 3%, TreeGalava02 3% |
| DirtCrackedLight | dirt | 5642 | 18.2 | CaveRocksPebblesImmobile 32%, CaveRocksSmallImmobile 11%, CaveRocksTinyImmobile 9%, CaveRocksMediumImmobile 9%, CaveRocksTiny 6%, CaveRocksLargeImmobile 5%, CaveRocksSmall 4% |
| LOTDDark2 | dungeon | 5299 | 3.92 | ArmBoneImmobile 29%, SkullImmobile 19%, LOTDTapestry1 8%, LOTDColumn1 8%, LOTDTapestry2 4%, LegBoneImmobile 2%, Column6 2% |
| Water | water | 5257 | 7.13 | WaterRipplesDrip02 17%, WaterBubbles 12%, WaterRipplesDrip01 8%, SewerPipe06 3%, CaveRocksPebbles 3%, CaveRockPillarTall1 3%, WaterRipplesEdge07 2% |
| GalavaBrick | town_paving | 5166 | 16.62 | LegBone 7%, Skull 4%, IronFenceDebris 4%, ArmBone 4%, Barrel 3%, WaterBarrel 3%, Rock8 2% |
| GalavaGateFacade | town_paving | 4969 | 5.94 | WaterBubbles 14%, FlowersYellowSparse 13%, Plant3 8%, Plant5 6%, FoliageDense1 6%, FlowersBlueSparse 5%, TreeGalava06 4% |
| CaveHardTan | cave | 4551 | 10.85 | Mushroom3 9%, CaveRocksPebbles 7%, CaveRocksSmall 6%, CaveRockPillarShort1 6%, CaveRocksSmallImmobile 5%, CaveRockPillarTall1 5%, CaveRocksPebblesImmobile 4% |
| IceFloorRough | ice | 4549 | 5.87 | TreeSnowCovered5 20%, TreeSnowCovered3 19%, TreeSnowCovered2 17%, TreeSnowCovered4 16%, TreeSnowCovered6 13%, TreeSnowCovered1 6%, CaveRocksPebblesImmobile 2% |

## Spacing and distance from walls

| category | nearest same-category object px (p25 / p50 / p75) | isolated (>230 px) | wall distance cells (p25/p50/p75) | within 1 cell of wall |
|---|---|---|---|---|
| tree | 41.9 / 65.2 / 117.3 | 7% | 1 / 1 / 2 | 57% |
| plant | 16.3 / 23.9 / 40.2 | 1% | 1 / 1 / 2 | 56% |
| flower_tuft | 14.4 / 24.3 / 52.8 | 2% | 1 / 2 / 2 | 45% |
| rock | 18.4 / 28.9 / 46.0 | 1% | 1 / 1 / 2 | 56% |
| log | 182.5 / 999.0 / 999.0 | 64% | 1 / 2 / 3 | 33% |
| bones | 11.7 / 18.0 / 30.1 | 0% | 1 / 2 / 3 | 35% |
| web | 35.6 / 66.6 / 119.5 | 6% | 1 / 1 / 1 | 92% |
| furniture | 29.7 / 39.6 / 66.6 | 6% | 1 / 1 / 3 | 52% |
| clutter | 26.6 / 33.3 / 50.4 | 3% | 1 / 1 / 2 | 64% |
| wall_decor | 60.8 / 94.8 / 164.0 | 15% | 0 / 0 / 1 | 95% |
| structure | 31.0 / 45.0 / 95.5 | 3% | 1 / 1 / 2 | 65% |
| water_decor | 31.9 / 73.2 / 138.9 | 12% | 1 / 2 / 3 | 32% |
| other | 23.3 / 32.5 / 112.8 | 18% | 1 / 2 / 3 | 49% |

## Trees outdoors

- Floor under trees: grass 62%, ice 22%, swamp 6%, dirt 5%, town_paving 5%, interior 1%
- Trees on grass: distance to nearest path tile (dirt/paving) p25 3 / median 5 / p75 8 cells; 6% stand within 1 cell of a path.
- Tree density per 100 grass tiles by distance from the nearest wall (cells): 0-2: 3.9, 2-4: 3.27, 4-8: 1.03, 8-16: 1.62

## Clumping (single-linkage clusters, 35 px)

| kind | cluster size p50 / p75 / p90 | singletons | same type within a clump |
|---|---|---|---|
| flowers | 1 / 1 / 1 | 91% | 82% |
| mushrooms | 1 / 3 / 5 | 55% | 75% |
| plants | 1 / 2 / 4 | 60% | 80% |
| rocks | 1 / 2 / 4 | 65% | 58% |
| barrels_crates | 1 / 2 / 3 | 72% | 86% |
| grass_tufts | 1 / 1 / 3 | 78% | 85% |

## Co-occurrence (furniture, clutter, lights, structures within 60 px; top 40)

| a | b | share of a with b nearby | weighted | maps | median distance px | median offset b-a (dx,dy) |
|---|---|---|---|---|---|---|
| RopeBridge1CenterFront | RopeBridge1CenterBack | 100% | 26.0 | 10 | 30.0 | [0, -30] |
| RopeBridge1Center2Front | RopeBridge1Center2Back | 100% | 21.0 | 6 | 30.0 | [0, -30] |
| UrchinTableLarge | UrchinStool | 98% | 66.0 | 8 | 27.9 | [-15, -23] |
| MinePost | MineBeam | 97% | 54.0 | 11 | 34.3 | [-27, -11] |
| UrchinTableSmall | UrchinStool | 97% | 33.0 | 5 | 27.3 | [-21, -17] |
| RopeBridge1Center2Back | RopeBridge1Center2Front | 96% | 21.0 | 6 | 30.0 | [0, 30] |
| RopeBridge2CenterFront | RopeBridge2CenterBack | 94% | 33.0 | 17 | 30.0 | [-1, -29] |
| RopeBridge2CenterBack | RopeBridge2CenterFront | 93% | 31.0 | 17 | 30.0 | [0, 30] |
| RopeBridge1CenterBack | RopeBridge1CenterFront | 92% | 24.0 | 10 | 30.0 | [0, 29] |
| RopeBridge2Center2Front | RopeBridge2Center2Back | 91% | 20.5 | 8 | 29.0 | [-1, -29] |
| RopeBridge1Center2Front | RopeBridge1CenterBack | 90% | 19.0 | 6 | 47.8 | [46, 16] |
| RopeBridge2Center2Back | RopeBridge2CenterFront | 85% | 21.0 | 14 | 50.0 | [47, -17] |
| BarrelLOTD | ColorLight | 85% | 22.0 | 3 | 29.2 | [0, 0] |
| RopeBridge2Center2Back | RopeBridge2Center2Front | 83% | 20.5 | 8 | 29.0 | [1, 29] |
| OgreBed | OgreStraw | 80% | 31.0 | 10 | 38.0 | [-8, 16] |
| RopeBridge2FarEndFront | RopeBridge2FarEndBack | 94% | 16.3 | 17 | 30.0 | [0, -30] |
| RopeBridge2NearEndFront | RopeBridge2NearEndBack | 100% | 15.3 | 14 | 30.0 | [0, -30] |
| Flame | SmallFlame | 76% | 230.5 | 23 | 35.6 | [-10, -1] |
| Bellows | Fireplace | 76% | 33.2 | 24 | 42.4 | [11, -27] |
| LOTDCandleLarge | LOTDCandleSmall | 75% | 42.5 | 10 | 36.4 | [-12, -3] |
| LOTDTombstone1Shadow | LOTDTombstone | 100% | 15.0 | 5 | 0.0 | [0, 0] |
| MediumFlame | SmallFlame | 75% | 470.5 | 27 | 26.8 | [-6, -3] |
| RopeBridge2FarEndBack | RopeBridge2FarEndFront | 90% | 16.3 | 17 | 30.0 | [0, 30] |
| TraderTentShadowUP | TraderTentPurple&OrangeTop | 85% | 17.0 | 13 | 39.8 | [7, 35] |
| LOTDCandleGroupSmall | LOTDCandleSmall | 72% | 46.0 | 10 | 31.9 | [-9, -9] |
| RopeBridge2FarEndBack | RopeBridge2CenterBack | 89% | 16.0 | 17 | 58.9 | [-45, 38] |
| UrchinStool | UrchinTableLarge | 70% | 310.0 | 8 | 25.7 | [-1, 6] |
| LightBench | Table | 70% | 97.0 | 20 | 32.5 | [-18, -17] |
| RopeBridge1CenterBack | RopeBridge1Center2Front | 73% | 19.0 | 6 | 47.8 | [-46, -15] |
| RopeBridge2CenterFront | RopeBridge2Center2Back | 69% | 24.0 | 14 | 50.0 | [-46, 17] |
| LOTDCandleLarge | LOTDCandleGroupSmall | 68% | 38.5 | 11 | 34.8 | [-11, -8] |
| Nightstand | Bed | 68% | 85.2 | 33 | 35.4 | [0, -1] |
| Statue2g | TorchPole | 67% | 78.0 | 13 | 16.3 | [11, -12] |
| Statue2e | TorchPole | 66% | 65.0 | 13 | 15.6 | [11, 11] |
| OgreTable | OgreStool | 66% | 20.7 | 14 | 48.8 | [-34, -2] |
| Statue2g | Statue | 66% | 76.0 | 13 | 23.0 | [23, 0] |
| RopeBridge2FarEndFront | RopeBridge2CenterBack | 87% | 15.0 | 16 | 45.7 | [-45, 8] |
| RopeBridge2NearEndBack | RopeBridge2NearEndFront | 85% | 15.3 | 14 | 30.0 | [0, 30] |
| Statue | TorchPole | 63% | 153.0 | 13 | 16.3 | [-12, -12] |
| TraderTentPoleUP | TraderTentShadowUP | 100% | 12.3 | 11 | 50.6 | [8, 48] |

## Directional variants against walls

line '/' = wall run along constant u (facing 0, T 3/5); side BR = towards +u (down-right on screen), TL = other side. line '\' = run along constant v (facing 1, T 4/6); side TR = towards +v (up-right), BL = other side. Nearest straight wall within 3 cells; otherwise counted free-standing.

| group | wall side -> variant (share, weighted) |
|---|---|
| MineBeam | /|BR: MineBeam1 (62%, 146.0); /|TL: MineBeam1 (100%, 142.0); \|BL: MineBeam1 (51%, 162.0); \|TR: MineBeam2 (96%, 105.0) |
| Candleabra | /|BR: Candleabra1 (34%, 135.7); /|TL: Candleabra1 (44%, 107.3); \|BL: Candleabra1 (52%, 156.1); \|TR: Candleabra1 (46%, 142.3) |
| Column | /|BR: Column6 (48%, 176.2); /|TL: Column6 (44%, 124.8); \|BL: Column6 (50%, 113.2); \|TR: Column6 (39%, 68.2) |
| LOTDWallSconse | /|BR: LOTDWallSconse1 (100%, 196.7); /|TL: LOTDWallSconse3 (98%, 64.7); \|BL: LOTDWallSconse2 (100%, 190.0); \|TR: LOTDWallSconse4 (100%, 64.0) |
| UrchinStool | /|BR: UrchinStool1 (62%, 26.0); /|TL: UrchinStool1 (62%, 39.0); \|BL: UrchinStool2 (63%, 38.0); \|TR: UrchinStool2 (53%, 30.0) |
| DarkWoodenChair | /|BR: DarkWoodenChair1 (31%, 76.3); /|TL: DarkWoodenChair1 (26%, 57.0); \|BL: DarkWoodenChair6 (27%, 79.8); \|TR: DarkWoodenChair3 (29%, 69.5) |
| OgreStraw | /|BR: OgreStraw1 (69%, 61.3); /|TL: OgreStraw1 (68%, 40.5); \|BL: OgreStraw1 (63%, 83.7); \|TR: OgreStraw5 (43%, 33.3) |
| VictorianLantern | /|BR: VictorianLantern2 (97%, 116.2); /|TL: VictorianLantern4 (98%, 54.0); \|BL: VictorianLantern1 (95%, 118.7); \|TR: VictorianLantern3 (95%, 84.0) |
| Straw | /|BR: Straw2 (59%, 78.2); /|TL: Straw2 (58%, 35.0); \|BL: Straw2 (56%, 99.2); \|TR: Straw2 (68%, 65.5) |
| Tombstone | /|BR: Tombstone1 (21%, 67.7); /|TL: Tombstone1 (34%, 60.9); \|BL: Tombstone12 (33%, 55.0); \|TR: Tombstone9 (17%, 38.7) |
| Gargoyle | /|BR: Gargoyle8 (63%, 109.2); /|TL: Gargoyle1 (51%, 29.7); \|BL: Gargoyle6 (63%, 92.5); \|TR: Gargoyle3 (57%, 47.0) |
| DunMirTorch | /|BR: DunMirTorchNorth (79%, 128.5); /|TL: DunMirTorchSouth (79%, 29.8); \|BL: DunMirTorchEast (84%, 111.0); \|TR: DunMirTorchWest (86%, 44.0) |
| DunMirChest | /|BR: DunMirChest4 (97%, 154.8); /|TL: DunMirChest1 (57%, 7.0); \|BL: DunMirChest3 (98%, 110.6); \|TR: DunMirChest2 (73%, 11.0) |
| Crypt | /|BR: Crypt3 (34%, 58.3); /|TL: Crypt3 (33%, 61.0); \|BL: Crypt3 (63%, 41.3); \|TR: Crypt3 (47%, 68.0) |
| UrchinShelvesFull | /|BR: UrchinShelvesFull2 (99%, 80.0); /|TL: UrchinShelvesFull2 (90%, 57.0); \|BL: UrchinShelvesFull1 (100%, 45.0); \|TR: UrchinShelvesFull1 (92%, 59.0) |
| Gear | /|BR: Gear4 (37%, 95.7); /|TL: Gear3 (29%, 43.5); \|BL: Gear3 (38%, 56.3); \|TR: Gear5 (52%, 26.3) |
| Statue | /|BR: Statue2a (48%, 88.2); /|TL: Statue2c (80%, 30.0); \|BL: Statue2a (81%, 36.0); \|TR: Statue2a (52%, 49.7) |
| Chest | /|BR: Chest4 (48%, 66.3); /|TL: Chest1 (53%, 7.5); \|BL: Chest3 (63%, 84.2); \|TR: Chest4 (71%, 3.5) |
| LOTDTapestry | /|BR: LOTDTapestry2 (100%, 86.0); /|TL: LOTDTapestry2 (78%, 9.0); \|BL: LOTDTapestry1 (100%, 71.0) |
| WizardWorkstation | /|BR: WizardWorkstation3a (29%, 25.5); /|TL: WizardWorkstation3d (28%, 32.0); \|BL: WizardWorkstation3b (43%, 33.5); \|TR: WizardWorkstation3c (40%, 19.5) |
| Bench | /|BR: Bench1 (86%, 25.7); /|TL: Bench5 (100%, 8.0); \|BL: Bench2 (90%, 20.7); \|TR: Bench4 (80%, 25.5) |
| CryptChest | /|BR: CryptChest4 (63%, 38.0); /|TL: CryptChest2 (60%, 13.3); \|BL: CryptChest1 (63%, 47.0); \|TR: CryptChest3 (69%, 14.0) |
| CrateSteel | /|BR: CrateSteel4 (48%, 25.0); /|TL: CrateSteel4 (47%, 23.5); \|BL: CrateSteel3 (41%, 31.5); \|TR: CrateSteel3 (48%, 25.0) |
| WoodenChair | /|BR: WoodenChair4 (30%, 23.3); /|TL: WoodenChair1 (29%, 14.0); \|BL: WoodenChair3 (22%, 19.8); \|TR: WoodenChair2 (32%, 32.5) |
| LightBench | /|BR: LightBench2 (100%, 16.5); /|TL: LightBench2 (100%, 11.0); \|BL: LightBench2 (54%, 26.0); \|TR: LightBench1 (85%, 13.0) |
| LogShelvesFull | /|BR: LogShelvesFull3 (92%, 40.0); /|TL: LogShelvesFull2 (55%, 20.0); \|BL: LogShelvesFull4 (96%, 48.0); \|TR: LogShelvesFull3 (33%, 12.0) |
| DunMirHangingShield | /|BR: DunMirHangingShield13 (24%, 62.5); \|BL: DunMirHangingShield14 (32%, 68.5) |
| Coffin | /|BR: Coffin3 (36%, 37.3); /|TL: Coffin3 (48%, 7.0); \|BL: Coffin1 (37%, 33.7); \|TR: Coffin3 (48%, 20.7) |
| Table | /|BR: Table1 (54%, 8.7); /|TL: Table3 (55%, 11.0); \|BL: Table2 (43%, 23.5); \|TR: Table1 (83%, 6.0) |
| UrchinPainting | /|BR: UrchinPainting1 (95%, 56.0); /|TL: UrchinPainting1 (80%, 10.0); \|BL: UrchinPainting2 (93%, 60.0); \|TR: UrchinPainting1 (75%, 4.0) |
| BarrelSteel | /|BR: BarrelSteel1 (54%, 37.0); /|TL: BarrelSteel1 (62%, 21.0); \|BL: BarrelSteel1 (70%, 30.0); \|TR: BarrelSteel1 (54%, 35.0) |
| Nightstand | /|BR: Nightstand4 (98%, 46.5); /|TL: Nightstand1 (100%, 8.5); \|BL: Nightstand3 (99%, 47.0); \|TR: Nightstand2 (100%, 23.2) |
| UrchinBed | /|BR: UrchinBed1 (100%, 27.0); /|TL: UrchinBed3 (100%, 30.0); \|BL: UrchinBed2 (100%, 39.0); \|TR: UrchinBed4 (92%, 26.0) |
| Desk | /|BR: Desk1 (100%, 38.8); /|TL: Desk3 (100%, 9.0); \|BL: Desk2 (100%, 42.5); \|TR: Desk4 (100%, 6.3) |
| DarkCrate | /|BR: DarkCrate2 (85%, 13.3); /|TL: DarkCrate2 (100%, 20.7); \|BL: DarkCrate1 (67%, 33.3); \|TR: DarkCrate2 (53%, 20.7) |
| TeepeeShelvesFull | /|BR: TeepeeShelvesFull1 (52%, 13.5); /|TL: TeepeeShelvesFull2 (67%, 15.0); \|BL: TeepeeShelvesFull2 (52%, 31.0); \|TR: TeepeeShelvesFull1 (67%, 9.0) |
| StatueVictory3 | /|BR: StatueVictory3SE (100%, 28.5); /|TL: StatueVictory3NW (100%, 24.0); \|BL: StatueVictory3SW (92%, 24.0); \|TR: StatueVictory3NE (82%, 17.0) |
| Bed | /|BR: Bed4 (97%, 29.2); /|TL: Bed1 (75%, 4.0); \|BL: Bed3 (93%, 42.8); \|TR: Bed2 (100%, 11.8) |
| Cot | /|BR: Cot1 (57%, 30.3); /|TL: Cot2 (56%, 9.0); \|BL: Cot1 (49%, 31.3); \|TR: Cot4 (59%, 15.3) |
| Stool | /|BR: Stool2 (64%, 20.3); /|TL: Stool2 (60%, 5.0); \|BL: Stool1 (63%, 19.0); \|TR: Stool1 (45%, 6.7) |
| Brick | /|BR: Brick1 (50%, 6.7); /|TL: Brick0 (56%, 5.3); \|BL: Brick2 (50%, 13.3); \|TR: Brick3 (33%, 12.0) |
| LOTDTombstone | /|BR: LOTDTombstone1 (67%, 30.0); /|TL: LOTDTombstone1 (40%, 10.0); \|BL: LOTDTombstone1 (53%, 17.0); \|TR: LOTDTombstone2 (42%, 12.0) |
| SewerPipe | /|BR: SewerPipe01 (81%, 48.0); \|BL: SewerPipe04 (65%, 34.0) |
| RoundTable | /|BR: RoundTable2 (53%, 9.5); /|TL: RoundTable2 (68%, 10.3); \|BL: RoundTable1 (50%, 10.0); \|TR: RoundTable1 (79%, 14.0) |
| OldDarkWoodenChair | /|BR: OldDarkWoodenChair8 (38%, 12.0); /|TL: OldDarkWoodenChair2 (56%, 9.0); \|BL: OldDarkWoodenChair3 (42%, 16.5); \|TR: OldDarkWoodenChair5 (50%, 6.0) |
| UrchinShelvesEmpty | /|BR: UrchinShelvesEmpty2 (100%, 28.0); /|TL: UrchinShelvesEmpty2 (67%, 9.0); \|BL: UrchinShelvesEmpty1 (100%, 19.0); \|TR: UrchinShelvesEmpty1 (100%, 9.0) |
| PiledBarrels | /|BR: PiledBarrels1 (92%, 23.7); /|TL: PiledBarrels1 (89%, 9.0); \|BL: PiledBarrels2 (83%, 28.0); \|TR: PiledBarrels2 (100%, 11.0) |
| TraderPoleArm | /|BR: TraderPoleArm3 (66%, 31.0); /|TL: TraderPoleArm2 (50%, 4.0); \|BL: TraderPoleArm2 (59%, 30.5); \|TR: TraderPoleArm3 (36%, 5.5) |
| AlchemistDesk | /|BR: AlchemistDesk4 (100%, 16.5); \|BL: AlchemistDesk3 (62%, 16.0); \|TR: AlchemistDesk1 (75%, 8.0) |
| BarrelWithTools | /|BR: BarrelWithTools2 (67%, 22.3); /|TL: BarrelWithTools2 (55%, 11.0); \|BL: BarrelWithTools1 (55%, 22.0); \|TR: BarrelWithTools1 (65%, 5.7) |
| Crate | /|BR: Crate2 (86%, 18.5); /|TL: Crate2 (79%, 12.0); \|BL: Crate1 (61%, 16.8); \|TR: Crate1 (63%, 8.1) |
| LOTDCandleGroupSmall | /|BR: LOTDCandleGroupSmall2 (50%, 10.0); /|TL: LOTDCandleGroupSmall2 (58%, 12.0); \|BL: LOTDCandleGroupSmall1 (61%, 11.5); \|TR: LOTDCandleGroupSmall1 (60%, 7.5) |
| TraderShieldWallHanging | /|BR: TraderShieldWallHanging4 (46%, 34.5); \|BL: TraderShieldWallHanging2 (40%, 29.0) |
| OgreStool | /|BR: OgreStool2 (67%, 4.0); /|TL: OgreStool1 (61%, 9.3); \|BL: OgreStool1 (75%, 5.3); \|TR: OgreStool2 (63%, 6.3) |
| Fireplace | /|BR: Fireplace4 (100%, 25.5); /|TL: Fireplace1 (100%, 2.0); \|BL: Fireplace3 (100%, 31.5); \|TR: Fireplace2 (100%, 2.0) |
| BlueTapestry | /|BR: BlueTapestry2 (100%, 26.0); \|BL: BlueTapestry4 (100%, 31.0); \|TR: BlueTapestry1 (100%, 2.0) |
| RuinsColumnIndoor | /|BR: RuinsColumnIndoor01 (35%, 20.0); /|TL: RuinsColumnIndoor02 (35%, 17.0); \|BL: RuinsColumnIndoor01 (25%, 8.0); \|TR: RuinsColumnIndoor03 (43%, 7.0) |
| Painting | /|BR: Painting1 (100%, 31.3); \|BL: Painting2 (100%, 23.5) |
| MinePost | /|BR: MinePost4 (62%, 10.5); /|TL: MinePost3 (55%, 7.2); \|BL: MinePost3 (60%, 21.8); \|TR: MinePost4 (57%, 7.0) |
| WoodBed | /|BR: WoodBed1 (58%, 12.0); /|TL: WoodBed3 (88%, 8.0); \|BL: WoodBed2 (78%, 22.3); \|TR: WoodBed1 (46%, 12.0) |
| ChestLOTD | /|BR: ChestLOTD4 (86%, 16.7); /|TL: ChestLOTD1 (100%, 3.0); \|BL: ChestLOTD3 (90%, 17.0); \|TR: ChestLOTD2 (100%, 6.7) |
| RuinsColumnOutdoor | /|BR: RuinsColumnOutdoor02 (23%, 13.0); /|TL: RuinsColumnOutdoor01 (30%, 10.0); \|BL: RuinsColumnOutdoor04 (14%, 14.0); \|TR: RuinsColumnOutdoor08 (25%, 8.0) |
| SquareTable | /|BR: SquareTable1 (52%, 15.5); /|TL: SquareTable1 (100%, 6.7); \|BL: SquareTable1 (59%, 21.8); \|TR: SquareTable1 (100%, 3.0) |
| LargeBarrel | /|BR: LargeBarrel2 (58%, 14.3); /|TL: LargeBarrel2 (91%, 11.7); \|BL: LargeBarrel1 (54%, 13.8); \|TR: LargeBarrel1 (68%, 7.3) |
| DunMirWarPole | /|BR: DunMirWarPole1 (40%, 10.0); \|BL: DunMirWarPole6 (40%, 15.0) |
| Bellows | /|BR: Bellows4 (36%, 23.5); /|TL: Bellows4 (100%, 2.0); \|BL: Bellows3 (38%, 13.0) |
| ChestUrchin | /|BR: ChestUrchin4 (92%, 12.0); \|BL: ChestUrchin3 (96%, 24.0) |
| DarkWoodenChairFallen | /|BR: DarkWoodenChairFallen3 (69%, 4.3); /|TL: DarkWoodenChairFallen2 (54%, 4.3); \|BL: DarkWoodenChairFallen1 (30%, 10.0) |
| OvalTable | /|BR: OvalTable2 (100%, 2.3); /|TL: OvalTable2 (100%, 6.2) |
| StatueDragon | /|BR: StatueDragon7 (92%, 24.0); /|TL: StatueDragon3 (100%, 4.0); \|BL: StatueDragon1 (100%, 9.0); \|TR: StatueDragon5 (100%, 4.0) |
| GreenTapestry | /|BR: GreenTapestry2 (100%, 12.5); \|BL: GreenTapestry4 (100%, 22.0); \|TR: GreenTapestry1 (100%, 5.0) |
| Stove | /|BR: Stove05 (91%, 14.3); \|BL: Stove03 (65%, 23.0) |
| OgreBed | /|BR: OgreBed2 (86%, 21.0); /|TL: OgreBed1 (67%, 3.0); \|BL: OgreBed1 (93%, 15.0) |
| MineOreCart | /|BR: MineOreCart2 (64%, 11.0); /|TL: MineOreCart2 (100%, 3.0); \|BL: MineOreCart1 (78%, 9.0); \|TR: MineOreCart1 (70%, 10.0) |
| CushionedStool | /|BR: CushionedStool2 (50%, 4.0); /|TL: CushionedStool4 (67%, 6.0); \|BL: CushionedStool2 (100%, 2.0); \|TR: CushionedStool1 (100%, 4.0) |
| CushionedBench | /|BR: CushionedBench1 (100%, 6.0); /|TL: CushionedBench2 (57%, 4.7); \|BL: CushionedBench2 (90%, 10.5); \|TR: CushionedBench1 (50%, 2.0) |
| TraderShelves | /|TL: TraderShelves2 (100%, 16.0); \|BL: TraderShelves1 (100%, 8.0); \|TR: TraderShelves1 (100%, 3.0) |
| TraderDesk | /|BR: TraderDesk1 (56%, 9.0); \|BL: TraderDesk3 (67%, 9.0) |
| RedTapestry | /|BR: RedTapestry1 (100%, 14.0); \|BL: RedTapestry2 (100%, 14.0); \|TR: RedTapestry4 (100%, 3.0) |
| OgreBench | /|BR: OgreBench2 (100%, 4.0); /|TL: OgreBench4 (33%, 3.0); \|BL: OgreBench1 (83%, 6.0); \|TR: OgreBench4 (50%, 4.0) |
| PulleyGear | /|BR: PulleyGear3 (56%, 5.3); /|TL: PulleyGear6 (71%, 8.5); \|BL: PulleyGear3 (43%, 7.0); \|TR: PulleyGear1 (57%, 7.0) |
| WhiteTapestry | /|BR: WhiteTapestry2 (100%, 15.5); \|BL: WhiteTapestry4 (100%, 13.5) |
| TeepeeShelvesEmpty | /|BR: TeepeeShelvesEmpty2 (80%, 5.0); \|BL: TeepeeShelvesEmpty2 (50%, 8.0); \|TR: TeepeeShelvesEmpty2 (100%, 3.0) |
| MovableStatueVictory3 | /|BR: MovableStatueVictory3SE (75%, 8.0); /|TL: MovableStatueVictory3NW (100%, 6.0); \|BL: MovableStatueVictory3SW (86%, 7.0); \|TR: MovableStatueVictory3NE (86%, 7.0) |
| TraderHangingSwords | /|BR: TraderHangingSwords2 (100%, 12.0); \|BL: TraderHangingSwords1 (100%, 15.0) |
| DunMirScaleTorch | /|BR: DunMirScaleTorch1 (100%, 2.0); \|BL: DunMirScaleTorch2 (100%, 6.5); \|TR: DunMirScaleTorch2 (100%, 6.0) |
| TraderArmorRack | /|BR: TraderArmorRack2 (100%, 4.3); \|BL: TraderArmorRack1 (81%, 10.5) |
| LogShelvesEmpty | /|BR: LogShelvesEmpty3 (100%, 10.0); /|TL: LogShelvesEmpty3 (80%, 5.0); \|BL: LogShelvesEmpty4 (100%, 3.0) |
| StreetLampOrnate | /|BR: StreetLampOrnate3 (50%, 6.0); /|TL: StreetLampOrnate2 (75%, 6.7); \|BL: StreetLampOrnate4 (67%, 6.0); \|TR: StreetLampOrnate1 (90%, 3.3) |
| MineOreCartBroken | /|BR: MineOreCartBroken2 (60%, 5.0); /|TL: MineOreCartBroken2 (67%, 3.0); \|BL: MineOreCartBroken1 (67%, 6.0); \|TR: MineOreCartBroken1 (100%, 2.0) |
| StatueRuin | /|BR: StatueRuin7 (60%, 5.0); \|BL: StatueRuin1 (100%, 12.0); \|TR: StatueRuin5 (75%, 4.0) |
| TraderClothesRack | /|BR: TraderClothesRack1 (58%, 12.0); /|TL: TraderClothesRack1 (100%, 3.0); \|BL: TraderClothesRack2 (60%, 5.0) |
| ClothSign | /|BR: ClothSign2 (67%, 3.0); \|BL: ClothSign1 (100%, 4.0) |
| TraderBowRack | /|BR: TraderBowRack2 (100%, 12.0); \|BL: TraderBowRack1 (100%, 5.0) |
| StatueVictory1 | /|BR: StatueVictory1SE (100%, 12.0); /|TL: StatueVictory1NW (100%, 4.0); \|BL: StatueVictory1SW (100%, 4.0) |
| TraderTentShadowUP | /|BR: TraderTentShadowUP2 (33%, 3.0); \|TR: TraderTentShadowUP1 (100%, 2.0) |
| LOTDCandleGroupLarge | /|BR: LOTDCandleGroupLarge2 (100%, 3.0) |
| DunMirAltar | /|BR: DunMirAltar1 (80%, 5.0); /|TL: DunMirAltar1 (80%, 5.0); \|BL: DunMirAltar1 (100%, 4.0); \|TR: DunMirAltar1 (100%, 4.0) |
| StreetLamp | /|BR: StreetLamp3 (60%, 5.0); /|TL: StreetLamp2 (75%, 8.0); \|BL: StreetLamp3 (100%, 2.0); \|TR: StreetLamp1 (100%, 3.0) |
| CathedralColumn | \|BL: CathedralColumn1 (100%, 3.5); \|TR: CathedralColumn3 (50%, 8.0) |
| LOTDBanner | /|BR: LOTDBanner1 (100%, 6.0) |
| LOTDLichGodStatue | /|BR: LOTDLichGodStatue1 (50%, 6.0); \|BL: LOTDLichGodStatue2 (60%, 5.0); \|TR: LOTDLichGodStatue1 (100%, 3.0) |
| RedRug | /|BR: RedRug3 (33%, 6.0); /|TL: RedRug2 (33%, 3.0) |
| MovableStatueVictory4 | \|BL: MovableStatueVictory4SE (50%, 2.0) |
| TraderCrossedWeapons | /|BR: TraderCrossedWeapons6 (56%, 4.5); /|TL: TraderCrossedWeapons6 (50%, 4.0); \|BL: TraderCrossedWeapons3 (100%, 8.0) |
| StatueVase1 | /|BR: StatueVase1SE (100%, 2.7); \|BL: StatueVase1SW (93%, 9.7); \|TR: StatueVase1NE (100%, 3.0) |
| StatueVictory4 | /|TL: StatueVictory4NW (50%, 2.0) |
| TraderHangingCrossbow | /|BR: TraderHangingCrossbow2 (100%, 3.0); \|BL: TraderHangingCrossbow1 (100%, 13.0) |
| MiningTools | /|BR: MiningTools2 (58%, 4.8); \|BL: MiningTools2 (50%, 4.0) |
| WallTrophyBear | /|BR: WallTrophyBear1 (100%, 5.5); \|BL: WallTrophyBear2 (100%, 9.0) |
| SackChestLarge | /|BR: SackChestLarge1 (65%, 5.7); \|BL: SackChestLarge2 (58%, 4.0) |
| TraderHelmShelf | /|BR: TraderHelmShelf2 (100%, 4.0); \|BL: TraderHelmShelf1 (100%, 8.0); \|TR: TraderHelmShelf1 (100%, 2.0) |
| RuinsColumnOutdoorShort | /|BR: RuinsColumnOutdoorShort02 (33%, 3.0); \|BL: RuinsColumnOutdoorShort02 (50%, 4.0) |
| SmallMirror | /|BR: SmallMirror2 (100%, 8.5); \|BL: SmallMirror1 (100%, 4.5) |
| StatueVictory2 | /|BR: StatueVictory2SE (100%, 2.0); /|TL: StatueVictory2NW (100%, 2.0); \|BL: StatueVictory2SW (100%, 4.0); \|TR: StatueVictory2NE (60%, 5.0) |
| SackChestMedium | /|BR: SackChestMedium2 (54%, 8.7); \|BL: SackChestMedium2 (67%, 2.0) |
| WallTrophyMountainLion | /|BR: WallTrophyMountainLion1 (100%, 9.0) |
| MiningPickAxeInGround | \|BL: MiningPickAxeInGround1 (50%, 4.0) |
| Anvil | \|TR: Anvil4 (55%, 3.7) |
| ChestOgre | /|BR: ChestOgre4 (100%, 4.0); \|BL: ChestOgre3 (100%, 4.7) |
| SmallTable | /|TL: SmallTable2 (100%, 3.0) |
| LOTDLichThrone | \|BL: LOTDLichThrone2 (100%, 4.0) |
| TortureRack | /|BR: TortureRack6 (57%, 3.5); \|TR: TortureRack6 (100%, 3.0) |
| OpenChest | /|BR: OpenChest4 (100%, 2.0); \|BL: OpenChest3 (100%, 4.0) |
| SackChestSmall | /|BR: SackChestSmall2 (50%, 2.0) |
| StatueVase4 | \|TR: StatueVase4NE (100%, 2.0) |
| WallTrophyMoose | /|BR: WallTrophyMoose1 (100%, 3.0); \|BL: WallTrophyMoose2 (100%, 3.0) |
| MovableStatueVictory1 | \|BL: MovableStatueVictory1SW (100%, 3.0); \|TR: MovableStatueVictory1NE (100%, 2.0) |
| StatueVictory5 | /|BR: StatueVictory5SE (100%, 3.0) |
| WallTrophyBull | /|BR: WallTrophyBull1 (100%, 2.0); \|BL: WallTrophyBull2 (100%, 3.0) |

Per-variant detail (dominant side, share free-standing, perpendicular distance from the wall centre line) is in the JSON.

## Invisible blockers (Extent*)

| type | weighted | maps | on a wall cell | floor | nearest object within 40 px |
|---|---|---|---|---|---|
| ExtentBoxSmall | 268.7 | 45 | 42% | town_paving 41%, dungeon 32%, interior 12% | (nothing within 40px) 60%, ColorLight 5%, Brick 3%, LOTDStairsDown4 3% |
| ExtentShortBoxSmall | 262.7 | 20 | 61% | dungeon 34%, interior 33%, lava 24% | ColorLight 50%, (nothing within 40px) 23%, DunMirStairsDownSidePiece 9%, LOTDStairsDown3 6% |
| ExtentStoneCylinderLarge | 167.3 | 11 | 47% | town_paving 99%, grass 1%, dirt 1% | (nothing within 40px) 90%, Plant5 5%, Plant4 2%, Bush6 2% |
| ExtentShortCylinderSmall | 90.3 | 14 | 8% | swamp 79%, grass 12%, water 6% | (nothing within 40px) 52%, Plant3 23%, ColorLight 12%, CaveRockPillarShort1 3% |
| ExtentCylinderLarge | 64.3 | 31 | 18% | town_paving 75%, dungeon 8%, grass 8% | (nothing within 40px) 78%, ColorLight 8%, GrassTuft3 5%, Plant5 3% |
| ExtentShortCylinderMedium | 59.0 | 8 | 77% | swamp 97%, water 2%, dirt 2% | Plant3 51%, (nothing within 40px) 44%, WaterRipplesLarge03 2%, WaterRipplesMedium08 2% |
| ExtentBoxLarge | 53.0 | 15 | 33% | town_paving 35%, water 32%, dungeon 17% | (nothing within 40px) 52%, Plant4 14%, WaterRipplesEdge08 4%, WaterRipplesEdge15 4% |
| ExtentBoxMedium | 39.3 | 6 | 25% | town_paving 64%, cave 23%, lava 13% | (nothing within 40px) 29%, SmallFlameImmobile 20%, LavaBridge2CenterFront 10%, Column5 8% |
| ExtentShortCylinderLarge | 39.0 | 16 | 61% | town_paving 55%, swamp 41%, grass 3% | (nothing within 40px) 62%, Plant3 24%, GalavaGateChain 8%, WaterBubbles 5% |
| ExtentCylinderSmallStone | 32.7 | 8 | 38% | dungeon 67%, town_paving 33% | (nothing within 40px) 98%, WaterRipplesEdge15 2% |
| ExtentCylinderSmall | 22.3 | 10 | 42% | town_paving 87%, swamp 9%, interior 4% | (nothing within 40px) 22%, TreeGalava07 18%, Bush6 9%, Plant5 9% |
| ExtentStoneBoxLarge | 20.3 | 11 | 5% | town_paving 75%, dungeon 25% | (nothing within 40px) 77%, LOTDColumn1 18%, Crypt6 5% |
| ExtentStoneCylinderSmall | 13.7 | 8 | 40% | town_paving 71%, dungeon 22%, interior 7% | (nothing within 40px) 63%, Monument1 15%, Torch 11%, WaterRipplesEdge15 7% |
| ExtentStoneCylinderMedium | 11.0 | 3 | 0% | dirt 82%, dungeon 18% | (nothing within 40px) 88%, ColorLight 12% |
| ExtentCylinderMedium | 7.0 | 6 | 43% | town_paving 43%, cave 14%, water 14% | PlantBarren1 43%, (nothing within 40px) 29%, CaveRockPillarTall1 14%, ColorLight 14% |
| ExtentStoneBoxSmall | 4.3 | 4 | 46% | interior 46%, town_paving 31%, dungeon 23% | DunMirStairsUp 69%, (nothing within 40px) 23%, Plant4 8% |
| ExtentShortBoxMedium | 4.0 | 3 | 50% | town_paving 100% | (nothing within 40px) 75%, Plant3 25% |
| ExtentShortBoxLarge | 0.7 | 1 | 50% | town_paving 100% | (nothing within 40px) 100% |

## Ambient sound emitters by floor family

Ambient sound emitters (Amb*) per 100 tiles of the floor they sit on; `no_floor` = placed over void (off the walkable area, common for area-wide sounds).

- water: 2.899 per 100 tiles - AmbBrook3 28%, AmbDripCave1 19%, AmbDripCave2 17%, AmbBrook1 16%, AmbBrook2 8%
- lava: 1.588 per 100 tiles - AmbLavaFlow 55%, AmbLavaBubbles 45%, AmbSpiritsLOTD 0%
- grass: 0.814 per 100 tiles - AmbBird1 20%, AmbBird2 12%, AmbCricket1 7%, AmbRodentForest2 7%, AmbLeaves 6%
- ice: 0.797 per 100 tiles - AmbWindWL1 42%, AmbWindLOTD 23%, AmbWindWL2 18%, AmbHowls 14%, AmbCrowWL 2%
- swamp: 0.78 per 100 tiles - AmbFliesSwamp 20%, AmbFrogSwamp1 14%, AmbFrogSwamp4 11%, AmbFrogSwamp5 10%, AmbFrogSwamp2 8%
- cave: 0.743 per 100 tiles - AmbMineCreaks 42%, AmbWindCave3 11%, AmbCaveRumble 8%, AmbDripCave1 8%, AmbWindCave1 8%
- dirt: 0.716 per 100 tiles - AmbWindCave1 13%, AmbIxTemple 13%, AmbWindCave3 13%, AmbCaveRumble 12%, AmbSpiritsFOV 9%
- dungeon: 0.436 per 100 tiles - AmbSpiritsLOTD 30%, AmbSpiritsFOV 15%, AmbWindLOTD 11%, AmbIxTemple 8%, AmbDripCave2 6%
- town_paving: 0.302 per 100 tiles - AmbIxTemple 30%, AmbWindCave1 17%, AmbMineCreaks 10%, AmbSpiritsFOV 7%, AmbWindCave3 5%
- interior: 0.249 per 100 tiles - AmbLeaves 13%, AmbWindCave3 12%, AmbSpiritsFOV 12%, AmbWindCave1 11%, AmbMineCreaks 10%
- no_floor: 174.5 emitters (weighted) - AmbSpiritsLOTD 22%, AmbWindLOTD 9%, AmbHowls 6%, AmbMineCreaks 5%, AmbWindCave2 4%
