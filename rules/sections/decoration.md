# Decoration and furniture placement rules

Mined by `rules/decoration.py` from the reference corpus. Style figures use the 107 campaign maps weighted so each distinct layout counts once (54 layouts); `observed_types` uses all 157 maps and marks the types never placed in a campaign map (`campaign: false`).

## JSON schema (`rules/out/decoration.json`)

```
observed_types[type] = {category, count, maps, campaign}  # every decoration type seen (all maps); campaign: placed in a campaign map
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

- **Density by terrain** (decoration objects per 100 floor tiles): grass 21.04, dirt 19.08, cave 15.55, swamp 13.23, interior 13.0, town paving 8.44, dungeon 4.78, lava 6.78, ice 5.2. Grass = small plants (Plant4/Plant5/PlantForest1), flowers, mushrooms and trees; dirt and cave = rocks, pebbles, rock pillars and mushrooms; dungeon = bones, webs, columns.
- **Scenery hugs walls**: within 1 cell of a wall - plants 54%, rocks 55%, trees 54%, furniture 50%, clutter 64%, webs 91%; wall decorations sit on the wall cell (96% within 1 cell).
- **Trees line the edges of outdoor areas**: trees per 100 grass tiles by distance from the bounding wall: 0-2 cells: 4.06, 2-4 cells: 3.33, 4-8 cells: 1.1, 8-16 cells: 1.66. Only 5% of trees stand within 1 cell of a path tile (median 5 cells away). Median tree spacing 63.1 px (~2.7 cells).
- **Small scenery is close-packed**: median nearest neighbour - plants 22.0 px, flowers/tufts/mushrooms 22.6 px, rocks 27.0 px. Mushrooms clump (p75 cluster 3, p90 6, mostly one type); flowers are almost always single (90% singletons).
- **Furniture sets**: chairs with tables and desks (about half of tables/desks have a chair within 60 px), nightstands with beds (68% of nightstands beside a bed, median 35 px), bellows with fireplaces, stools with Urchin/Ogre tables, straw with ogre beds; barrels and crates in small groups (p75 2, p90 3).
- **Directional variants follow the wall they back onto** (table below): one variant per wall side with 80-100% consistency for beds, nightstands, desks, benches, chests, sconces, lanterns and DunMir torches. Furniture is placed mostly against the walls on the BR side of '/' walls and the BL side of '\' walls.
- **Extent\* blockers** are invisible collision shapes: on town paving/dungeon floors, often on wall cells or alone (stairs, ledges, fountains, tower bases), and under scenery such as swamp Plant3 and Galava trees.

## Palettes by floor family (decoration objects per 100 tiles)

| family | tiles (weighted) | maps | per 100 tiles | category densities | top types |
|---|---|---|---|---|---|
| dungeon | 70379 | 73 | 4.78 | structure 1.96, clutter 0.71, furniture 0.6, bones 0.52, web 0.39 | FireGrate 5%, Crypt3 4%, SpiderWebEast 4%, Brick 3%, LOTDColumn1 3%, LegBone 3%, ArmBone 3%, SpiderWebNorth 2% |
| dirt | 62615 | 72 | 19.08 | rock 7.54, furniture 2.88, flower_tuft 2.11, bones 1.76, clutter 1.65 | CaveRocksPebbles 12%, Mushroom3 6%, CaveRocksSmall 6%, CaveRockPillarTall1 3%, CaveRocksTiny 3%, LegBone 3%, Mushroom4 3%, CaveRocksHuge 2% |
| town_paving | 44468 | 76 | 8.44 | furniture 2.5, structure 1.33, clutter 1.17, plant 0.91, bones 0.51 | Plant5 4%, Plant4 4%, Barrel 2%, Column5 2%, LegBone 2%, FlowersYellowSparse 2%, Barrel2 2%, Straw2 2% |
| grass | 43479 | 50 | 21.04 | plant 9.47, flower_tuft 3.87, tree 3.19, rock 1.94, clutter 0.77 | Plant4 15%, Plant5 12%, FlowersYellowSparse 5%, PlantForest1 3%, Mushroom3 3%, FlowersPurpleSparse 2%, Plant2Flowered 2%, PlantBarren1 2% |
| cave | 38452 | 61 | 15.55 | rock 6.84, flower_tuft 3.13, structure 1.73, clutter 1.46, web 0.67 | CaveRocksPebbles 9%, Mushroom3 8%, MineBeam1 5%, CaveRocksMedium 4%, Mushroom4 4%, CaveRocksSmall 4%, CaveRocksHuge 4%, CaveRockPillarTall1 4% |
| interior | 23508 | 82 | 13.0 | furniture 6.07, structure 3.09, clutter 1.41, web 0.72, bones 0.68 | ArmBone 3%, Statue2c 2%, SpiderWebNorthEast 2%, CathedralColumn3Cracked 2%, DarkWoodenChair3 2%, DarkWoodenChair1 2%, Column6 2%, Column8 2% |
| lava | 20203 | 15 | 6.78 | rock 2.65, water_decor 2.15, bones 1.57, structure 0.17, furniture 0.1 | LegBone 11%, LavaBubble6 7%, Skull 6%, LavaBubble9 6%, LavaBubble4 6%, LavaBubble5 5%, LavaBubble8 5%, ArmBone 4% |
| swamp | 13937 | 11 | 13.23 | plant 6.77, flower_tuft 2.8, tree 0.87, rock 0.86, structure 0.57 | Plant3 24%, Plant4 14%, Plant5 10%, Mushroom3 5%, Mushroom2 3%, GrassTuft2 3%, Plant2 3%, Plant2Flowered 3% |
| water | 11762 | 50 | 11.08 | water_decor 4.69, plant 4.03, rock 1.65, structure 0.31, clutter 0.15 | Plant3 21%, Plant1 11%, WaterBubbles 5%, WaterRipplesDrip02 5%, WaterRipplesMedium03 3%, CaveRockPillarTall1 3%, SmallStalagmite 3%, WaterRipplesDrip01 2% |
| ice | 7531 | 4 | 5.2 | tree 4.51, furniture 0.28, other 0.21, wall_decor 0.08, clutter 0.08 | TreeSnowCovered3 24%, TreeSnowCovered6 18%, TreeSnowCovered5 17%, TreeSnowCovered4 12%, TreeSnowCovered2 11%, TreeSnowCovered1 5%, IceCrack2 2%, LOTDBanner1 1% |
| other | 127 | 13 | 31.5 | furniture 16.08, clutter 15.42 | Barrel2 15%, Fireplace4 13%, WaterBarrel 10%, Barrel 7%, Stove03 5%, WoodenChair3 5%, WoodenChair1 5%, RoundTableWithFood 5% |

## Palettes by floor material (largest 25)

| material | family | tiles | per 100 tiles | top types |
|---|---|---|---|---|
| DirtDark2 | dirt | 39747 | 20.69 | CaveRocksPebbles 14%, CaveRocksSmall 6%, Mushroom3 6%, LegBone 3%, CaveRocksHuge 3%, Mushroom4 3%, UrchinStool1 2% |
| GreenBrick | dungeon | 30920 | 7.26 | Crypt3 6%, FireGrate 6%, SpiderWebEast 5%, Brick 5%, SpiderWebNorth 3%, Barrel 3%, Statue2g 3% |
| CaveHardBrown | cave | 24009 | 14.44 | Mushroom3 12%, CaveRocksPebbles 8%, Mushroom4 7%, CaveRocksMedium 6%, Mushroom1 5%, CaveRocksHuge 5%, CaveRockPillarTall1 4% |
| GrassNorm | grass | 24005 | 25.27 | Plant4 17%, Plant5 14%, FlowersYellowSparse 7%, PlantForest1 4%, Plant2Flowered 3%, FlowersPurpleSparse 3%, Plant2 2% |
| LOTDPitted | dungeon | 19164 | 1.94 | LOTDColumn1 20%, LOTDTapestry2 16%, LOTDTapestry1 10%, StoneBlock 5%, LOTDTombstone1 4%, Coffin4 4%, ArmBone 3% |
| Lava | lava | 11901 | 5.81 | LavaBubble6 12%, LavaBubble9 11%, LavaBubble4 10%, LavaBubble5 10%, LavaBubble8 8%, LavaHardened5 6%, LavaBubble7 5% |
| GrassSparse2 | grass | 9383 | 13.47 | Plant4 14%, Plant5 9%, CaveRocksSmall 4%, GrassTuft3 4%, PlantBarren1 3%, Mushroom3 2%, FlowersYellowSparse 2% |
| SwampGrass | swamp | 9350 | 15.1 | Plant4 18%, Plant5 13%, Mushroom3 7%, Plant3 5%, Mushroom2 4%, GrassTuft2 4%, Plant2 3% |
| GalavaBrick3 | town_paving | 8596 | 8.15 | Gargoyle8 5%, Gargoyle3 4%, Barrel2 3%, BlueTapestry2 3%, Gargoyle6 3%, DunMirAltar1 2%, Nightstand4 2% |
| DirtLight2 | dirt | 8485 | 15.73 | CaveRockPillarTall1 7%, CaveRocksPebbles 7%, Plant4 5%, Column5 4%, Mushroom3 4%, Mushroom4 4%, Barrel 3% |
| ManaMineDirt | cave | 8411 | 21.19 | MineBeam1 15%, MineBeam2 11%, CaveRocksPebbles 9%, BarrelSteel1 4%, MudBubble3 4%, CaveRocksSmall 3%, Barrel 3% |
| VolcanicCraggy | lava | 8302 | 8.16 | LegBone 22%, Skull 13%, ArmBone 8%, Rock8 7%, SmallStalagmite 4%, LargeStalagmite 4%, Rock6 4% |
| WeedsSparse | grass | 6773 | 14.36 | PlantBarren1 8%, OgreStraw1 5%, CaveRockPillarShort1 4%, CaveRockPillarTall1 3%, Barrel 3%, CaveRockPillarShort2 3%, CaveRocksPebbles 3% |
| Black | dungeon | 6761 | 0.01 | GrassTuft3 50%, Aspen2 50% |
| LOTDBlackMarble | dungeon | 6756 | 4.47 | Coffin1 9%, LOTDColumn1 5%, LOTDTapestry1 5%, StatueVictory3SW 4%, BarrelLOTD 4%, LOTDTapestry2 4%, StatueVictory3NW 4% |
| TileDark | interior | 6434 | 7.74 | CathedralColumn3Cracked 12%, ArmBone 10%, SpiderWebNorthEast 7%, Column8 7%, SpiderWebNorth 6%, SpiderWebEast 6%, Stool2 4% |
| GalavaTowerFacade | town_paving | 5651 | 5.08 | Plant5 42%, Plant4 22%, FlowersYellowSparse 8%, TreeGalava07 5%, TreeGalava03 4%, Bush6 3%, TreeGalava02 3% |
| DirtHard | dirt | 4998 | 25.82 | CaveRocksPebbles 12%, Mushroom3 9%, CaveRockPillarShort1 4%, CaveRockPillarTall1 4%, CaveRockPillarShort2 4%, CaveRocksTiny 4%, CaveRockPillarTall2 3% |
| GalavaGateFacade | town_paving | 4969 | 5.94 | WaterBubbles 14%, FlowersYellowSparse 13%, Plant3 8%, Plant5 6%, FoliageDense1 6%, FlowersBlueSparse 5%, TreeGalava06 4% |
| Water | water | 4601 | 6.91 | WaterBubbles 14%, WaterRipplesDrip02 14%, WaterRipplesDrip01 6%, SewerPipe06 4%, CaveRocksPebbles 4%, Brick 3%, CaveRockPillarTall1 2% |
| DunMirBrick1 | town_paving | 4513 | 9.27 | DunMirChest4 6%, Bed3 6%, DunMirColumn1 4%, Column7 3%, DunMirChest3 3%, Cot1 3%, OldDarkWoodenChair3 3% |
| WaterDeep | water | 4062 | 13.29 | Plant3 33%, Plant1 15%, WaterRipplesMedium03 6%, WaterRipplesPatchBig06 5%, SmallStalagmite 4%, WaterRipplesDrip02 3%, WaterRipplesMedium05 3% |
| GalavaBrick | town_paving | 4010 | 20.31 | LegBone 8%, Skull 4%, IronFenceDebris 4%, ArmBone 4%, Barrel 4%, WaterBarrel 3%, Rock8 2% |
| DirtBlue | dirt | 3906 | 2.41 | CaveRockPillarTall1 22%, CaveRocksPebbles 19%, CaveRockPillarShort2 11%, DunMirChest4 9%, CaveRockPillarTall2 8%, CaveRocksSmall 5%, CaveRocksMedium 3% |
| CaveHardTan | cave | 3505 | 10.68 | CaveRocksPebbles 10%, Mushroom3 8%, CaveRocksSmall 8%, CaveRockPillarShort1 6%, CaveRockPillarTall1 5%, ArmBone 5%, CaveRockPillarShort2 5% |

## Spacing and distance from walls

| category | nearest same-category object px (p25 / p50 / p75) | isolated (>230 px) | wall distance cells (p25/p50/p75) | within 1 cell of wall |
|---|---|---|---|---|
| tree | 41.0 / 63.1 / 107.7 | 5% | 1 / 1 / 2 | 54% |
| plant | 15.5 / 22.0 / 35.9 | 1% | 1 / 1 / 3 | 54% |
| flower_tuft | 13.6 / 22.6 / 48.6 | 2% | 1 / 2 / 3 | 45% |
| rock | 16.8 / 27.0 / 42.1 | 2% | 1 / 1 / 2 | 55% |
| log | 196.5 / 999.0 / 999.0 | 66% | 1 / 2 / 3 | 34% |
| bones | 9.4 / 13.6 / 21.3 | 1% | 1 / 2 / 3 | 40% |
| web | 33.6 / 59.2 / 111.3 | 7% | 1 / 1 / 1 | 91% |
| furniture | 29.2 / 38.9 / 63.1 | 5% | 1 / 1 / 3 | 50% |
| clutter | 26.4 / 33.2 / 49.5 | 3% | 1 / 1 / 2 | 64% |
| wall_decor | 56.6 / 87.0 / 161.2 | 14% | 0 / 0 / 1 | 96% |
| structure | 31.9 / 43.8 / 90.4 | 3% | 1 / 1 / 2 | 65% |
| water_decor | 25.1 / 58.8 / 112.4 | 11% | 1 / 2 / 4 | 26% |
| other | 21.8 / 32.5 / 91.2 | 12% | 1 / 2 / 3 | 50% |

## Trees outdoors

- Floor under trees: grass 67%, ice 16%, swamp 6%, dirt 6%, town_paving 5%, water 0%
- Trees on grass: distance to nearest path tile (dirt/paving) p25 3 / median 5 / p75 8 cells; 5% stand within 1 cell of a path.
- Tree density per 100 grass tiles by distance from the nearest wall (cells): 0-2: 4.06, 2-4: 3.33, 4-8: 1.1, 8-16: 1.66

## Clumping (single-linkage clusters, 35 px)

| kind | cluster size p50 / p75 / p90 | singletons | same type within a clump |
|---|---|---|---|
| flowers | 1 / 1 / 2 | 90% | 82% |
| mushrooms | 2 / 3 / 6 | 46% | 77% |
| plants | 1 / 3 / 4 | 56% | 81% |
| rocks | 1 / 2 / 4 | 66% | 59% |
| barrels_crates | 1 / 2 / 3 | 72% | 86% |
| grass_tufts | 1 / 1 / 3 | 76% | 85% |

## Co-occurrence (furniture, clutter, lights, structures within 60 px; top 40)

| a | b | share of a with b nearby | weighted | maps | median distance px | median offset b-a (dx,dy) |
|---|---|---|---|---|---|---|
| LOTDCandleLarge | LOTDCandleGroupSmall | 100% | 29.0 | 7 | 34.8 | [-11, -7] |
| UrchinTableLarge | UrchinStool | 98% | 66.0 | 8 | 27.9 | [-15, -23] |
| MinePost | MineBeam | 97% | 52.0 | 10 | 34.6 | [-27, -14] |
| LOTDCandleSmall | LOTDCandleGroupSmall | 97% | 35.0 | 6 | 44.8 | [-26, -4] |
| UrchinTableSmall | UrchinStool | 97% | 33.0 | 5 | 27.3 | [-21, -17] |
| BarrelLOTD | ColorLight | 85% | 22.0 | 3 | 29.2 | [0, 0] |
| LOTDCandleGroupSmall | LOTDCandleSmall | 83% | 35.0 | 6 | 31.9 | [-9, -10] |
| LOTDCandleSmall | LOTDCandleGroupLarge | 83% | 30.0 | 6 | 37.4 | [-14, -15] |
| OgreBed | OgreStraw | 80% | 31.0 | 10 | 38.0 | [-8, 16] |
| Flame | SmallFlame | 76% | 230.5 | 23 | 35.6 | [-10, -1] |
| Bellows | Fireplace | 76% | 33.2 | 24 | 42.4 | [11, -27] |
| MediumFlame | SmallFlame | 75% | 470.5 | 27 | 26.8 | [-6, -3] |
| LOTDCandleLarge | LOTDCandleSmall | 72% | 21.0 | 6 | 47.0 | [-8, -16] |
| UrchinStool | UrchinTableLarge | 70% | 310.0 | 8 | 25.7 | [-1, 6] |
| LightBench | Table | 70% | 97.0 | 20 | 32.5 | [-18, -17] |
| LOTDCandleGroupSmall | LOTDCandleGroupLarge | 69% | 29.0 | 6 | 47.0 | [-19, 1] |
| Nightstand | Bed | 68% | 85.2 | 33 | 35.4 | [0, -1] |
| Statue2g | TorchPole | 67% | 78.0 | 13 | 16.3 | [11, -12] |
| Statue2e | TorchPole | 66% | 65.0 | 13 | 15.6 | [11, 11] |
| OgreTable | OgreStool | 66% | 20.7 | 14 | 48.8 | [-34, -2] |
| Statue2g | Statue | 66% | 76.0 | 13 | 23.0 | [23, 0] |
| Fireplace | Bellows | 65% | 33.2 | 24 | 42.4 | [-11, 27] |
| Statue | TorchPole | 63% | 153.0 | 13 | 16.3 | [-12, -12] |
| LOTDCandleLarge | LOTDCandleGroupLarge | 66% | 19.0 | 6 | 44.6 | [5, -2] |
| LOTDCandleGroupSmall | LOTDCandleLarge | 62% | 26.0 | 7 | 34.8 | [-14, 17] |
| TraderTentPoleUP | TraderTentShadowUP | 100% | 12.3 | 11 | 50.6 | [8, 48] |
| VandegrafLarge | Gargoyle | 76% | 16.0 | 3 | 47.1 | [11, 13] |
| OvalTable | DarkWoodenChair | 60% | 25.3 | 17 | 41.1 | [-29, -15] |
| Statue2e | Statue2g | 60% | 59.0 | 13 | 23.0 | [0, 23] |
| Statue2e | Statue | 60% | 59.0 | 13 | 23.0 | [23, 0] |
| StatueVictory4 | DunMirScaleTorch | 100% | 12.0 | 3 | 32.5 | [23, 23] |
| GalavaStairsDownSidePiece | GalavaStairsDownEndPiece | 100% | 12.0 | 10 | 44.3 | [-2, 40] |
| Desk | DarkWoodenChair | 60% | 58.3 | 26 | 23.0 | [13, 14] |
| ClothSign | DunMirWarPole | 73% | 16.0 | 4 | 26.9 | [-13, 25] |
| CushionedStool | RoundTable | 58% | 22.0 | 4 | 35.1 | [2, -1] |
| SmallFlame | MediumFlame | 58% | 893.0 | 27 | 24.7 | [-3, -2] |
| TraderTentShadowUP | TraderTentPurple&OrangeTop | 82% | 14.0 | 11 | 39.8 | [7, 35] |
| PulleyGear | Gear | 61% | 18.8 | 14 | 51.4 | [-23, 23] |
| RoundTable | DarkWoodenChair | 57% | 43.5 | 26 | 30.1 | [-22, -17] |
| RoundTableWithFood | DarkWoodenChair | 57% | 31.5 | 17 | 41.1 | [-32, -3] |

## Directional variants against walls

line '/' = wall run along constant u (facing 0, T 3/5); side BR = towards +u (down-right on screen), TL = other side. line '\' = run along constant v (facing 1, T 4/6); side TR = towards +v (up-right), BL = other side. Nearest straight wall within 3 cells; otherwise counted free-standing.

| group | wall side -> variant (share, weighted) |
|---|---|
| MineBeam | /|BR: MineBeam1 (62%, 146.0); /|TL: MineBeam1 (100%, 142.0); \|BL: MineBeam1 (51%, 161.0); \|TR: MineBeam2 (96%, 102.0) |
| Candleabra | /|BR: Candleabra1 (34%, 135.7); /|TL: Candleabra1 (44%, 107.3); \|BL: Candleabra1 (52%, 154.1); \|TR: Candleabra1 (46%, 142.3) |
| Column | /|BR: Column6 (47%, 130.2); /|TL: Column6 (46%, 114.8); \|BL: Column6 (44%, 89.2); \|TR: Column5 (30%, 50.2) |
| UrchinStool | /|BR: UrchinStool1 (62%, 26.0); /|TL: UrchinStool1 (62%, 39.0); \|BL: UrchinStool2 (63%, 38.0); \|TR: UrchinStool2 (53%, 30.0) |
| DarkWoodenChair | /|BR: DarkWoodenChair1 (31%, 76.3); /|TL: DarkWoodenChair1 (26%, 57.0); \|BL: DarkWoodenChair6 (27%, 79.8); \|TR: DarkWoodenChair3 (28%, 68.5) |
| OgreStraw | /|BR: OgreStraw1 (69%, 61.3); /|TL: OgreStraw1 (68%, 40.5); \|BL: OgreStraw1 (63%, 83.7); \|TR: OgreStraw5 (43%, 33.3) |
| VictorianLantern | /|BR: VictorianLantern2 (97%, 116.2); /|TL: VictorianLantern4 (98%, 54.0); \|BL: VictorianLantern1 (95%, 118.7); \|TR: VictorianLantern3 (95%, 84.0) |
| Straw | /|BR: Straw2 (59%, 78.2); /|TL: Straw2 (58%, 35.0); \|BL: Straw2 (56%, 99.2); \|TR: Straw2 (68%, 65.5) |
| Tombstone | /|BR: Tombstone1 (27%, 52.7); /|TL: Tombstone1 (35%, 58.9); \|BL: Tombstone12 (30%, 46.0); \|TR: Tombstone9 (19%, 35.7) |
| Crypt | /|BR: Crypt3 (35%, 57.3); /|TL: Crypt3 (33%, 61.0); \|BL: Crypt3 (63%, 41.3); \|TR: Crypt3 (47%, 68.0) |
| UrchinShelvesFull | /|BR: UrchinShelvesFull2 (99%, 80.0); /|TL: UrchinShelvesFull2 (90%, 57.0); \|BL: UrchinShelvesFull1 (100%, 45.0); \|TR: UrchinShelvesFull1 (92%, 59.0) |
| Gargoyle | /|BR: Gargoyle8 (63%, 73.2); /|TL: Gargoyle4 (38%, 20.7); \|BL: Gargoyle6 (57%, 71.5); \|TR: Gargoyle3 (60%, 38.0) |
| Statue | /|BR: Statue2a (48%, 88.2); /|TL: Statue2c (80%, 30.0); \|BL: Statue2a (81%, 36.0); \|TR: Statue2a (53%, 48.7) |
| DunMirChest | /|BR: DunMirChest4 (98%, 124.7); /|TL: DunMirChest3 (50%, 6.0); \|BL: DunMirChest3 (97%, 77.1); \|TR: DunMirChest2 (83%, 6.0) |
| Gear | /|BR: Gear4 (36%, 80.7); /|TL: Gear3 (29%, 39.5); \|BL: Gear5 (36%, 50.3); \|TR: Gear5 (53%, 22.3) |
| LOTDWallSconse | /|BR: LOTDWallSconse1 (100%, 71.7); /|TL: LOTDWallSconse3 (97%, 35.7); \|BL: LOTDWallSconse2 (99%, 72.0); \|TR: LOTDWallSconse4 (100%, 33.0) |
| Chest | /|BR: Chest4 (48%, 66.3); /|TL: Chest1 (53%, 7.5); \|BL: Chest3 (63%, 84.2); \|TR: Chest4 (71%, 3.5) |
| DunMirTorch | /|BR: DunMirTorchNorth (64%, 72.5); /|TL: DunMirTorch2 (48%, 8.3); \|BL: DunMirTorchEast (75%, 63.0); \|TR: DunMirTorchWest (78%, 27.0) |
| WizardWorkstation | /|BR: WizardWorkstation3a (29%, 25.5); /|TL: WizardWorkstation3d (28%, 32.0); \|BL: WizardWorkstation3b (43%, 33.5); \|TR: WizardWorkstation3c (40%, 19.5) |
| Bench | /|BR: Bench1 (86%, 25.7); /|TL: Bench5 (100%, 8.0); \|BL: Bench2 (90%, 20.7); \|TR: Bench4 (80%, 25.5) |
| CrateSteel | /|BR: CrateSteel4 (48%, 25.0); /|TL: CrateSteel4 (47%, 23.5); \|BL: CrateSteel3 (41%, 31.5); \|TR: CrateSteel3 (48%, 25.0) |
| WoodenChair | /|BR: WoodenChair4 (30%, 23.3); /|TL: WoodenChair1 (29%, 14.0); \|BL: WoodenChair3 (22%, 19.8); \|TR: WoodenChair2 (32%, 32.5) |
| LightBench | /|BR: LightBench2 (100%, 16.5); /|TL: LightBench2 (100%, 11.0); \|BL: LightBench2 (54%, 26.0); \|TR: LightBench1 (85%, 13.0) |
| LogShelvesFull | /|BR: LogShelvesFull3 (92%, 40.0); /|TL: LogShelvesFull2 (55%, 20.0); \|BL: LogShelvesFull4 (96%, 48.0); \|TR: LogShelvesFull2 (33%, 12.0) |
| Coffin | /|BR: Coffin3 (36%, 37.3); /|TL: Coffin3 (48%, 7.0); \|BL: Coffin1 (37%, 33.7); \|TR: Coffin3 (48%, 20.7) |
| Table | /|BR: Table1 (54%, 8.7); /|TL: Table3 (55%, 11.0); \|BL: Table1 (43%, 23.5); \|TR: Table1 (83%, 6.0) |
| UrchinPainting | /|BR: UrchinPainting1 (95%, 56.0); /|TL: UrchinPainting1 (80%, 10.0); \|BL: UrchinPainting2 (93%, 60.0); \|TR: UrchinPainting1 (75%, 4.0) |
| BarrelSteel | /|BR: BarrelSteel1 (54%, 37.0); /|TL: BarrelSteel1 (62%, 21.0); \|BL: BarrelSteel1 (70%, 30.0); \|TR: BarrelSteel1 (54%, 35.0) |
| LOTDTapestry | /|BR: LOTDTapestry2 (100%, 62.0); /|TL: LOTDTapestry2 (78%, 9.0); \|BL: LOTDTapestry1 (100%, 48.0) |
| Nightstand | /|BR: Nightstand4 (98%, 45.5); /|TL: Nightstand1 (100%, 8.5); \|BL: Nightstand3 (99%, 47.0); \|TR: Nightstand2 (100%, 23.2) |
| UrchinBed | /|BR: UrchinBed1 (100%, 27.0); /|TL: UrchinBed3 (100%, 30.0); \|BL: UrchinBed2 (100%, 39.0); \|TR: UrchinBed4 (92%, 26.0) |
| CryptChest | /|BR: CryptChest4 (69%, 29.0); /|TL: CryptChest2 (60%, 8.3); \|BL: CryptChest1 (56%, 37.0); \|TR: CryptChest3 (61%, 11.0) |
| DunMirHangingShield | /|BR: DunMirHangingShield13 (23%, 55.5); \|BL: DunMirHangingShield14 (38%, 53.0) |
| TeepeeShelvesFull | /|BR: TeepeeShelvesFull1 (52%, 13.5); /|TL: TeepeeShelvesFull2 (67%, 15.0); \|BL: TeepeeShelvesFull2 (52%, 31.0); \|TR: TeepeeShelvesFull1 (67%, 9.0) |
| StatueVictory3 | /|BR: StatueVictory3SE (100%, 28.5); /|TL: StatueVictory3NW (100%, 24.0); \|BL: StatueVictory3SW (92%, 24.0); \|TR: StatueVictory3NE (82%, 17.0) |
| DarkCrate | /|BR: DarkCrate2 (92%, 12.3); /|TL: DarkCrate2 (100%, 20.7); \|BL: DarkCrate1 (66%, 32.3); \|TR: DarkCrate2 (53%, 20.7) |
| Desk | /|BR: Desk1 (100%, 37.8); /|TL: Desk3 (100%, 7.0); \|BL: Desk2 (100%, 42.5); \|TR: Desk4 (100%, 6.3) |
| Bed | /|BR: Bed4 (97%, 29.2); /|TL: Bed1 (75%, 4.0); \|BL: Bed3 (93%, 42.8); \|TR: Bed2 (100%, 11.8) |
| Cot | /|BR: Cot1 (57%, 30.3); /|TL: Cot2 (56%, 9.0); \|BL: Cot1 (49%, 31.3); \|TR: Cot4 (59%, 15.3) |
| Stool | /|BR: Stool2 (64%, 20.3); /|TL: Stool2 (60%, 5.0); \|BL: Stool1 (63%, 19.0); \|TR: Stool1 (45%, 6.7) |
| Brick | /|BR: Brick1 (50%, 6.7); /|TL: Brick0 (56%, 5.3); \|BL: Brick2 (50%, 13.3); \|TR: Brick3 (33%, 12.0) |
| SewerPipe | /|BR: SewerPipe01 (81%, 48.0); \|BL: SewerPipe04 (65%, 34.0) |
| RoundTable | /|BR: RoundTable2 (53%, 9.5); /|TL: RoundTable2 (68%, 10.3); \|BL: RoundTable1 (50%, 10.0); \|TR: RoundTable1 (79%, 14.0) |
| OldDarkWoodenChair | /|BR: OldDarkWoodenChair8 (38%, 12.0); /|TL: OldDarkWoodenChair2 (56%, 9.0); \|BL: OldDarkWoodenChair3 (42%, 16.5); \|TR: OldDarkWoodenChair5 (50%, 6.0) |
| UrchinShelvesEmpty | /|BR: UrchinShelvesEmpty2 (100%, 28.0); /|TL: UrchinShelvesEmpty2 (67%, 9.0); \|BL: UrchinShelvesEmpty1 (100%, 19.0); \|TR: UrchinShelvesEmpty1 (100%, 9.0) |
| PiledBarrels | /|BR: PiledBarrels1 (92%, 23.7); /|TL: PiledBarrels1 (89%, 9.0); \|BL: PiledBarrels2 (83%, 28.0); \|TR: PiledBarrels2 (100%, 11.0) |
| AlchemistDesk | /|BR: AlchemistDesk4 (100%, 14.5); \|BL: AlchemistDesk3 (62%, 16.0); \|TR: AlchemistDesk1 (75%, 8.0) |
| BarrelWithTools | /|BR: BarrelWithTools2 (70%, 21.3); /|TL: BarrelWithTools2 (55%, 11.0); \|BL: BarrelWithTools1 (55%, 22.0); \|TR: BarrelWithTools1 (65%, 5.7) |
| Crate | /|BR: Crate2 (86%, 18.5); /|TL: Crate2 (79%, 12.0); \|BL: Crate1 (61%, 16.8); \|TR: Crate1 (63%, 8.1) |
| OgreStool | /|BR: OgreStool2 (67%, 4.0); /|TL: OgreStool1 (61%, 9.3); \|BL: OgreStool1 (75%, 5.3); \|TR: OgreStool2 (63%, 6.3) |
| BlueTapestry | /|BR: BlueTapestry2 (100%, 26.0); \|BL: BlueTapestry4 (100%, 31.0); \|TR: BlueTapestry1 (100%, 2.0) |
| Painting | /|BR: Painting1 (100%, 31.3); \|BL: Painting2 (100%, 23.5) |
| MinePost | /|BR: MinePost4 (62%, 10.5); /|TL: MinePost3 (55%, 7.2); \|BL: MinePost3 (63%, 20.8); \|TR: MinePost4 (67%, 6.0) |
| ChestLOTD | /|BR: ChestLOTD4 (86%, 16.7); /|TL: ChestLOTD1 (100%, 3.0); \|BL: ChestLOTD3 (90%, 17.0); \|TR: ChestLOTD2 (100%, 6.7) |
| SquareTable | /|BR: SquareTable1 (52%, 15.5); /|TL: SquareTable1 (100%, 6.7); \|BL: SquareTable1 (59%, 21.8); \|TR: SquareTable1 (100%, 3.0) |
| Fireplace | /|BR: Fireplace4 (100%, 20.5); /|TL: Fireplace1 (100%, 2.0); \|BL: Fireplace3 (100%, 26.5); \|TR: Fireplace2 (100%, 2.0) |
| LOTDTombstone | /|BR: LOTDTombstone1 (62%, 13.0); /|TL: LOTDTombstone4 (67%, 6.0); \|BL: LOTDTombstone1 (54%, 13.0); \|TR: LOTDTombstone2 (57%, 7.0) |
| LargeBarrel | /|BR: LargeBarrel2 (58%, 14.3); /|TL: LargeBarrel2 (91%, 11.7); \|BL: LargeBarrel1 (54%, 13.8); \|TR: LargeBarrel1 (68%, 7.3) |
| DunMirWarPole | /|BR: DunMirWarPole3 (40%, 10.0); \|BL: DunMirWarPole6 (40%, 15.0) |
| TraderPoleArm | /|BR: TraderPoleArm3 (83%, 15.0); /|TL: TraderPoleArm1 (50%, 4.0); \|BL: TraderPoleArm2 (57%, 17.5); \|TR: TraderPoleArm4 (36%, 5.5) |
| Bellows | /|BR: Bellows4 (36%, 23.5); /|TL: Bellows4 (100%, 2.0); \|BL: Bellows3 (38%, 13.0) |
| TraderShieldWallHanging | /|BR: TraderShieldWallHanging4 (51%, 23.5); \|BL: TraderShieldWallHanging3 (42%, 20.0) |
| ChestUrchin | /|BR: ChestUrchin4 (92%, 12.0); \|BL: ChestUrchin3 (96%, 24.0) |
| DarkWoodenChairFallen | /|BR: DarkWoodenChairFallen3 (69%, 4.3); /|TL: DarkWoodenChairFallen2 (54%, 4.3); \|BL: DarkWoodenChairFallen1 (30%, 10.0) |
| WoodBed | /|BR: WoodBed1 (55%, 11.0); /|TL: WoodBed3 (75%, 4.0); \|BL: WoodBed2 (75%, 20.3); \|TR: WoodBed1 (64%, 7.0) |
| LOTDCandleGroupSmall | /|BR: LOTDCandleGroupSmall2 (67%, 6.0); /|TL: LOTDCandleGroupSmall2 (58%, 12.0); \|BL: LOTDCandleGroupSmall1 (80%, 5.0) |
| OvalTable | /|BR: OvalTable2 (100%, 2.3); /|TL: OvalTable2 (100%, 6.2) |
| GreenTapestry | /|BR: GreenTapestry2 (100%, 12.5); \|BL: GreenTapestry4 (100%, 22.0); \|TR: GreenTapestry1 (100%, 5.0) |
| OgreBed | /|BR: OgreBed2 (86%, 21.0); /|TL: OgreBed1 (67%, 3.0); \|BL: OgreBed1 (93%, 15.0) |
| CushionedStool | /|BR: CushionedStool1 (50%, 4.0); /|TL: CushionedStool4 (67%, 6.0); \|BL: CushionedStool2 (100%, 2.0); \|TR: CushionedStool1 (100%, 4.0) |
| CushionedBench | /|BR: CushionedBench1 (100%, 6.0); /|TL: CushionedBench2 (57%, 4.7); \|BL: CushionedBench2 (90%, 10.5); \|TR: CushionedBench1 (50%, 2.0) |
| Stove | /|BR: Stove05 (90%, 12.3); \|BL: Stove03 (58%, 19.0) |
| RedTapestry | /|BR: RedTapestry1 (100%, 14.0); \|BL: RedTapestry2 (100%, 14.0); \|TR: RedTapestry4 (100%, 3.0) |
| TraderDesk | /|BR: TraderDesk1 (56%, 9.0); \|BL: TraderDesk3 (67%, 9.0) |
| OgreBench | /|BR: OgreBench2 (100%, 4.0); /|TL: OgreBench2 (33%, 3.0); \|BL: OgreBench1 (83%, 6.0); \|TR: OgreBench4 (50%, 4.0) |
| PulleyGear | /|BR: PulleyGear3 (56%, 5.3); /|TL: PulleyGear6 (71%, 8.5); \|BL: PulleyGear3 (43%, 7.0); \|TR: PulleyGear1 (57%, 7.0) |
| WhiteTapestry | /|BR: WhiteTapestry2 (100%, 15.5); \|BL: WhiteTapestry4 (100%, 13.5) |
| TeepeeShelvesEmpty | /|BR: TeepeeShelvesEmpty2 (80%, 5.0); \|BL: TeepeeShelvesEmpty1 (50%, 8.0); \|TR: TeepeeShelvesEmpty2 (100%, 3.0) |
| MovableStatueVictory3 | /|BR: MovableStatueVictory3SE (75%, 8.0); /|TL: MovableStatueVictory3NW (100%, 6.0); \|BL: MovableStatueVictory3SW (86%, 7.0); \|TR: MovableStatueVictory3NE (86%, 7.0) |
| DunMirScaleTorch | /|BR: DunMirScaleTorch1 (100%, 2.0); \|BL: DunMirScaleTorch2 (100%, 6.5); \|TR: DunMirScaleTorch2 (100%, 6.0) |
| MineOreCart | /|BR: MineOreCart2 (62%, 8.0); /|TL: MineOreCart2 (100%, 2.0); \|BL: MineOreCart1 (83%, 6.0); \|TR: MineOreCart1 (100%, 6.0) |
| LogShelvesEmpty | /|BR: LogShelvesEmpty3 (100%, 10.0); /|TL: LogShelvesEmpty3 (80%, 5.0); \|BL: LogShelvesEmpty4 (100%, 3.0) |
| StreetLampOrnate | /|BR: StreetLampOrnate3 (50%, 6.0); /|TL: StreetLampOrnate2 (75%, 6.7); \|BL: StreetLampOrnate4 (67%, 6.0); \|TR: StreetLampOrnate1 (90%, 3.3) |
| TraderHangingSwords | /|BR: TraderHangingSwords2 (100%, 9.0); \|BL: TraderHangingSwords1 (100%, 15.0) |
| TraderArmorRack | /|BR: TraderArmorRack2 (100%, 2.3); \|BL: TraderArmorRack1 (81%, 10.5) |
| ClothSign | /|BR: ClothSign2 (67%, 3.0); \|BL: ClothSign1 (100%, 4.0) |
| TraderClothesRack | /|BR: TraderClothesRack1 (64%, 11.0); /|TL: TraderClothesRack1 (100%, 3.0); \|BL: TraderClothesRack2 (50%, 4.0) |
| DunMirAltar | /|BR: DunMirAltar1 (80%, 5.0); /|TL: DunMirAltar1 (80%, 5.0); \|BL: DunMirAltar1 (100%, 4.0); \|TR: DunMirAltar1 (100%, 4.0) |
| StreetLamp | /|BR: StreetLamp3 (60%, 5.0); /|TL: StreetLamp2 (75%, 8.0); \|BL: StreetLamp3 (100%, 2.0); \|TR: StreetLamp1 (100%, 3.0) |
| TraderBowRack | /|BR: TraderBowRack2 (100%, 10.0); \|BL: TraderBowRack1 (100%, 3.0) |
| TraderShelves | /|TL: TraderShelves2 (100%, 2.0); \|BL: TraderShelves1 (100%, 5.0); \|TR: TraderShelves1 (100%, 2.0) |
| TraderTentShadowUP | \|TR: TraderTentShadowUP1 (100%, 2.0) |
| CathedralColumn | \|BL: CathedralColumn1 (100%, 3.5); \|TR: CathedralColumn3 (50%, 8.0) |
| RedRug | /|BR: RedRug4 (33%, 6.0); /|TL: RedRug1 (33%, 3.0) |
| TraderCrossedWeapons | /|BR: TraderCrossedWeapons6 (56%, 4.5); /|TL: TraderCrossedWeapons5 (50%, 4.0); \|BL: TraderCrossedWeapons3 (100%, 8.0) |
| StatueVase1 | /|BR: StatueVase1SE (100%, 2.7); \|BL: StatueVase1SW (93%, 9.7); \|TR: StatueVase1NE (100%, 3.0) |
| TraderHangingCrossbow | /|BR: TraderHangingCrossbow2 (100%, 3.0); \|BL: TraderHangingCrossbow1 (100%, 12.0) |
| SmallMirror | /|BR: SmallMirror2 (100%, 8.5); \|BL: SmallMirror1 (100%, 4.5) |
| StatueVictory1 | /|BR: StatueVictory1SE (100%, 7.0); \|BL: StatueVictory1SW (100%, 4.0) |
| StatueVictory2 | /|BR: StatueVictory2SE (100%, 2.0); /|TL: StatueVictory2NW (100%, 2.0); \|BL: StatueVictory2SW (100%, 4.0); \|TR: StatueVictory2NE (60%, 5.0) |
| SackChestLarge | /|BR: SackChestLarge1 (73%, 3.7); \|BL: SackChestLarge2 (58%, 4.0) |
| MiningTools | /|BR: MiningTools2 (64%, 2.8); \|BL: MiningTools1 (50%, 4.0) |
| MineOreCartBroken | /|BR: MineOreCartBroken2 (67%, 3.0); \|BL: MineOreCartBroken1 (50%, 2.0) |
| TraderHelmShelf | /|BR: TraderHelmShelf2 (100%, 3.0); \|BL: TraderHelmShelf1 (100%, 6.0); \|TR: TraderHelmShelf1 (100%, 2.0) |
| LOTDBanner | /|BR: LOTDBanner1 (100%, 4.0) |
| SackChestMedium | /|BR: SackChestMedium2 (70%, 6.7); \|BL: SackChestMedium2 (67%, 2.0) |
| Anvil | \|TR: Anvil4 (55%, 3.7) |
| ChestOgre | /|BR: ChestOgre4 (100%, 4.0); \|BL: ChestOgre3 (100%, 4.7) |
| SmallTable | /|TL: SmallTable2 (100%, 3.0) |
| TortureRack | /|BR: TortureRack6 (57%, 3.5); \|TR: TortureRack6 (100%, 3.0) |
| MiningPickAxeInGround | \|BL: MiningPickAxeInGround1 (50%, 2.0) |
| OpenChest | /|BR: OpenChest4 (100%, 2.0); \|BL: OpenChest3 (100%, 4.0) |
| SackChestSmall | /|BR: SackChestSmall2 (50%, 2.0) |
| StatueVase4 | \|TR: StatueVase4NE (100%, 2.0) |
| MovableStatueVictory1 | \|BL: MovableStatueVictory1SW (100%, 3.0); \|TR: MovableStatueVictory1NE (100%, 2.0) |
| StatueVictory5 | /|BR: StatueVictory5SE (100%, 3.0) |
| MovableStatueVictory4 | \|BL: MovableStatueVictory4NE (50%, 2.0) |
| WallTrophyBear | \|BL: WallTrophyBear2 (100%, 3.0) |
| WallTrophyMountainLion | /|BR: WallTrophyMountainLion1 (100%, 4.0) |
| LOTDLichThrone | \|BL: LOTDLichThrone2 (100%, 3.0) |
| WallTrophyMoose | /|BR: WallTrophyMoose1 (100%, 3.0) |

Per-variant detail (dominant side, share free-standing, perpendicular distance from the wall centre line) is in the JSON.

## Invisible blockers (Extent*)

| type | weighted | maps | on a wall cell | floor | nearest object within 40 px |
|---|---|---|---|---|---|
| ExtentBoxSmall | 246.7 | 42 | 42% | town_paving 45%, dungeon 34%, interior 12% | (nothing within 40px) 59%, ColorLight 5%, Brick 4%, LOTDStairsDown4 4% |
| ExtentShortBoxSmall | 243.7 | 18 | 64% | dungeon 37%, interior 35%, lava 26% | ColorLight 53%, (nothing within 40px) 20%, DunMirStairsDownSidePiece 10%, LOTDStairsDown3 7% |
| ExtentStoneCylinderLarge | 128.3 | 9 | 59% | town_paving 100% | (nothing within 40px) 88%, Plant5 6%, Plant4 3%, Bush6 2% |
| ExtentShortCylinderSmall | 90.3 | 14 | 8% | swamp 79%, grass 12%, water 6% | (nothing within 40px) 52%, Plant3 23%, ColorLight 12%, CaveRockPillarShort1 3% |
| ExtentShortCylinderMedium | 59.0 | 8 | 77% | swamp 97%, water 2%, dirt 2% | Plant3 51%, (nothing within 40px) 44%, WaterRipplesLarge03 2%, WaterRipplesMedium08 2% |
| ExtentCylinderLarge | 57.3 | 23 | 20% | town_paving 84%, grass 7%, dungeon 5% | (nothing within 40px) 84%, GrassTuft3 6%, Plant5 4%, VandegrafSmall 2% |
| ExtentBoxLarge | 53.0 | 15 | 33% | town_paving 35%, water 32%, dungeon 17% | (nothing within 40px) 52%, Plant4 14%, WaterRipplesEdge08 4%, WaterRipplesEdge15 4% |
| ExtentCylinderSmallStone | 32.7 | 8 | 38% | dungeon 67%, town_paving 33% | (nothing within 40px) 98%, WaterRipplesEdge15 2% |
| ExtentShortCylinderLarge | 30.0 | 14 | 49% | swamp 53%, town_paving 41%, grass 3% | (nothing within 40px) 51%, Plant3 31%, GalavaGateChain 11%, WaterBubbles 7% |
| ExtentCylinderSmall | 22.3 | 10 | 42% | town_paving 87%, swamp 9%, interior 4% | (nothing within 40px) 22%, TreeGalava07 18%, Bush6 9%, Plant5 9% |
| ExtentBoxMedium | 18.3 | 5 | 49% | town_paving 100% | (nothing within 40px) 46%, Column5 16%, WaterRipplesEdge03 11%, WaterRipplesEdge11 11% |
| ExtentStoneBoxLarge | 14.3 | 9 | 0% | town_paving 65%, dungeon 35% | (nothing within 40px) 67%, LOTDColumn1 26%, Crypt6 7% |
| ExtentStoneCylinderSmall | 13.7 | 8 | 40% | town_paving 71%, dungeon 22%, interior 7% | (nothing within 40px) 63%, Monument1 15%, Torch 11%, WaterRipplesEdge15 7% |
| ExtentStoneCylinderMedium | 11.0 | 3 | 0% | dirt 82%, dungeon 18% | (nothing within 40px) 88%, ColorLight 12% |
| ExtentStoneBoxSmall | 4.3 | 4 | 46% | interior 46%, town_paving 31%, dungeon 23% | DunMirStairsUp 69%, (nothing within 40px) 23%, Plant4 8% |
| ExtentCylinderMedium | 4.0 | 2 | 75% | town_paving 75%, cave 25% | PlantBarren1 75%, CaveRockPillarTall1 25% |
| ExtentShortBoxMedium | 4.0 | 3 | 50% | town_paving 100% | (nothing within 40px) 75%, Plant3 25% |
| ExtentShortBoxLarge | 0.7 | 1 | 50% | town_paving 100% | (nothing within 40px) 100% |

## Ambient sound emitters by floor family

Ambient sound emitters (Amb*) per 100 tiles of the floor they sit on; `no_floor` = placed over void (off the walkable area, common for area-wide sounds).

- water: 2.864 per 100 tiles - AmbBrook3 30%, AmbDripCave1 21%, AmbDripCave2 17%, AmbBrook1 14%, AmbDripRoom 6%
- lava: 1.709 per 100 tiles - AmbLavaFlow 56%, AmbLavaBubbles 44%
- grass: 0.756 per 100 tiles - AmbBird1 25%, AmbBird2 15%, AmbRodentForest2 8%, AmbRodentForest1 6%, AmbCricket1 5%
- ice: 0.713 per 100 tiles - AmbWindWL1 67%, AmbWindWL2 28%, AmbCrowWL 4%, AmbHowls 1%
- cave: 0.702 per 100 tiles - AmbMineCreaks 50%, AmbWindCave3 14%, AmbWindCave1 9%, AmbWindCave2 5%, AmbDripCave2 4%
- swamp: 0.701 per 100 tiles - AmbFrogSwamp1 14%, AmbFrogSwamp4 13%, AmbFrogSwamp5 11%, AmbFliesSwamp 10%, AmbFrogSwamp2 9%
- dirt: 0.622 per 100 tiles - AmbWindCave3 19%, AmbWindCave1 19%, AmbIxTemple 19%, AmbSpiritsFOV 14%, AmbBeachBirds 4%
- dungeon: 0.358 per 100 tiles - AmbSpiritsFOV 22%, AmbWindLOTD 20%, AmbSpiritsLOTD 18%, AmbDripCave2 10%, AmbDripCave1 10%
- town_paving: 0.216 per 100 tiles - AmbIxTemple 31%, AmbWindCave1 23%, AmbWindCave3 9%, AmbBird2 6%, AmbCrowdBig 5%
- interior: 0.105 per 100 tiles - AmbSpiritsFOV 36%, AmbCrowdBig 18%, AmbWindCave1 10%, AmbWindCave3 8%, AmbMineCreaks 4%
- no_floor: 110.5 emitters (weighted) - AmbSpiritsLOTD 33%, AmbWindLOTD 14%, AmbHowls 7%, AmbLeaves 4%, AmbBird7 4%
