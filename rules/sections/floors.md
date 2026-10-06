# Floors and edge blending

Schema of `rules/out/floors.json`:
- `blend[]`: one entry per pair of materials that touch as side neighbours (>= 10 contacts in all maps): `a`, `b`, `contacts_all`, `maps_all`, `contacts_sp_weighted`, `maps_sp`, `edge_share_sp` (share of campaign contacts with an edge overlay on the touching side), `edge_share_all`, `overlay`/`base` (which material is drawn over which), `overlay_direction_share`, `edge_types` (share), `preferred_edge_type`.
- `priority{material: {score, evidence}}`: score -1..1, higher = drawn over neighbours (campaign maps, weighted); evidence = weighted blended contacts.
- `material_family{}`, `families{family: materials (area share), unused_in_sp, sp_maps_using, median_share_when_used, neighbour_families}`.
- `never_touch[]`: common materials that co-occur in campaign maps but never touch; `buffer_materials` seen between them.
- `edge_pieces{}`: piece rule, match rate, deviations, side-variant shares, piece ids.
- `variation_rule{}`: share of tiles/edges whose variation equals the editor's automatic formula.
- `edge_types{}`: usage counts and piece count (`nvar`).

## Variation rule

- Tile variation equals the editor's position formula for 80% of all tiles; edge variation equals the overlay material's formula for 89% of edges.
- Lowest-matching materials: DunMirFacade 0%, GalavaGateFacade 0%, GalavaTowerFacade 0%, IxExteriorFacade 0%, IxTempleInteriorFacade 0%, LOTDTempleFacade 0%, RugBlueLight 20%, WoodDark2 26%

## Edge pieces

- Rule: side neighbour of overlay material -> side piece (3 variants, random); two adjacent sides -> corner 'Sides' piece; tip neighbour with neither adjacent side -> tip piece.
- Exact match with the rule: 71% of (tile, overlay) groups (campaign maps, weighted).
- Piece kinds: {'tip': 0.294, 'side': 0.546, 'corner': 0.16}. Deviations per group: {'missing_side': 0.043, 'extra_corner': 0.054, 'extra_tip': 0.088, 'extra_side': 0.152, 'missing_tip': 0.012, 'missing_corner': 0.072}.
- Side variants are used about equally: {'S': {'5': 0.376, '7': 0.297, '9': 0.327}, 'W': {'1': 0.394, '2': 0.293, '3': 0.313}, 'N': {'6': 0.381, '8': 0.295, '10': 0.323}, 'E': {'12': 0.39, '13': 0.287, '14': 0.323}}.

## Most common blends (campaign maps)

| a | b | contacts (all) | maps | blended | overlay on base | edge type |
|---|---|---|---|---|---|---|
| LOTDBlackMarble | LOTDPitted | 14884 | 29 | 82% | LOTDBlackMarble over LOTDPitted (94%) | MetalSteel |
| DirtDark2 | GreenBrick | 13102 | 37 | 94% | DirtDark2 over GreenBrick (63%) | BlendEdge |
| GrassNorm | GrassSparse2 | 11757 | 47 | 92% | GrassSparse2 over GrassNorm (90%) | BlendEdge |
| CaveHardBrown | CaveHardTan | 11754 | 35 | 100% | CaveHardTan over CaveHardBrown (94%) | BlendEdge |
| DirtDark2 | GrassNorm | 8629 | 45 | 95% | DirtDark2 over GrassNorm (100%) | BlendEdge |
| CaveHardBrown | DirtDark2 | 8591 | 36 | 97% | DirtDark2 over CaveHardBrown (75%) | BlendEdge |
| SwampGrass | WeedsSparse | 7126 | 12 | 100% | WeedsSparse over SwampGrass (97%) | BlendEdge |
| DirtDark2 | DirtHard | 6699 | 54 | 96% | DirtHard over DirtDark2 (76%) | BlendEdge |
| DirtDark2 | GrassSparse2 | 6307 | 39 | 99% | DirtDark2 over GrassSparse2 (89%) | BlendEdge |
| SwampGrass | WaterSwampShallow | 6142 | 12 | 100% | WaterSwampShallow over SwampGrass (100%) | SwampEdge |
| IceFloorDeepBlue | IceFloorRough | 5488 | 8 | 99% | IceFloorRough over IceFloorDeepBlue (100%) | BlendEdge |
| Lava | VolcanicCraggy | 5480 | 18 | 98% | Lava over VolcanicCraggy (100%) | LavaEdgeBlackDirt |
| GalavaBrick3 | GalavaBrownMarble | 4852 | 16 | 9% | GalavaBrownMarble over GalavaBrick3 (100%) | MetalBrass |
| DirtDark2 | DirtLight2 | 4727 | 41 | 99% | DirtLight2 over DirtDark2 (92%) | BlendEdge |
| LOTDDark2 | LOTDPitted | 4332 | 14 | 50% | LOTDDark2 over LOTDPitted (94%) | BrickEdgeBrown |
| DirtLight2 | WeedsSparse | 4135 | 15 | 100% | DirtLight2 over WeedsSparse (94%) | BlendEdge |
| WaterDeep | WaterShallow | 4046 | 26 | 99% | WaterDeep over WaterShallow (91%) | BlendEdge |
| IceFloorDark | IceFloorRough | 3608 | 6 | 100% | IceFloorRough over IceFloorDark (100%) | BlendEdge |
| CaveHardBrown | DirtHard | 3112 | 30 | 95% | DirtHard over CaveHardBrown (54%) | BlendEdge |
| GrassNorm | GrassNormYellow | 2994 | 26 | 80% | GrassNormYellow over GrassNorm (99%) | BlendEdge |
| GrassDense | GrassNorm | 2874 | 29 | 96% | GrassDense over GrassNorm (99%) | BlendEdge |
| DirtLight2 | IxBrickFancy | 2781 | 9 | 98% | DirtLight2 over IxBrickFancy (91%) | BlendEdge |
| CaveHardBrown | Water | 2768 | 23 | 100% | Water over CaveHardBrown (100%) | DirtRidge |
| CaveHardBrown | GreenBrick | 2717 | 18 | 75% | GreenBrick over CaveHardBrown (82%) | BlendEdge |
| LOTDDark | LOTDPitted | 2456 | 7 | 39% | LOTDDark over LOTDPitted (84%) | BrickEdgeBrown |
| DirtDark | GreenBrick | 2406 | 7 | 99% | GreenBrick over DirtDark (100%) | BlendEdge |
| CaveHardBrown | CaveHardDark | 2301 | 27 | 99% | CaveHardDark over CaveHardBrown (98%) | BlendEdge |
| WaterSwampDeep | WaterSwampShallow | 2087 | 11 | 100% | WaterSwampDeep over WaterSwampShallow (100%) | BlendEdge |
| LOTDPitted | TileDark | 2083 | 7 | 99% | LOTDPitted over TileDark (100%) | BlendEdge |
| DirtLight2 | IxBrick | 1953 | 9 | 97% | DirtLight2 over IxBrick (98%) | BlendEdge |
| LOTDBlackMarble | StoneLight | 1951 | 22 | 86% | StoneLight over LOTDBlackMarble (62%) | MetalSteel |
| DirtBlue | DirtLight2 | 1934 | 8 | 100% | DirtLight2 over DirtBlue (99%) | BlendEdge |
| DirtBlue | DirtDark2 | 1894 | 9 | 100% | DirtBlue over DirtDark2 (90%) | BlendEdge |
| GrassSparseYellow | WeedsSparse | 1814 | 9 | 100% | GrassSparseYellow over WeedsSparse (100%) | BlendEdge |
| GreenBrick | Water | 1774 | 7 | 99% | Water over GreenBrick (99%) | DirtRidge |
| GrassNorm | GrassSparseYellow | 1770 | 30 | 94% | GrassSparseYellow over GrassNorm (96%) | BlendEdge |
| DunMirBrick1 | RugRed | 1648 | 5 | 100% | RugRed over DunMirBrick1 (100%) | RugTanLightEdge |
| CobbleStone | DirtDark2 | 1458 | 11 | 70% | CobbleStone over DirtDark2 (50%) | BlendEdge |
| GrassSparse2 | WeedsSparse | 1421 | 14 | 90% | GrassSparse2 over WeedsSparse (75%) | BlendEdge |
| GrassNorm | OakWoodFloor | 1389 | 13 | 0% | GrassNorm over OakWoodFloor (0%) | BrickEdgeBrown |
| LOTDBlackMarble | LOTDDark2 | 1367 | 11 | 96% | LOTDDark2 over LOTDBlackMarble (67%) | BrickEdgeBrown |
| GreenBrick | TileStarBlack | 1352 | 13 | 90% | TileStarBlack over GreenBrick (100%) | BrickEdgeBrown |
| CaveHardTan | DirtDark2 | 1303 | 10 | 100% | CaveHardTan over DirtDark2 (64%) | DirtRidge |
| GrassDense | GrassSparseYellow | 1267 | 8 | 100% | GrassDense over GrassSparseYellow (0%) | BlendEdge |
| GalavaBrick3 | RugGreen | 1254 | 5 | 10% | RugGreen over GalavaBrick3 (100%) | RugTanLightEdge |

## Families

- **dirt**: in 87 campaign maps, median 10% of a map's floor when used. Palette: DirtDark2 57%, DirtLight2 12%, ManaMineDirt 12%, DirtHard 7%, DirtBlue 6%, DirtDark 3%. Borders: brick 32%, grass 30%, cave 17%, water 9%, cobble 4%.
- **brick**: in 85 campaign maps, median 20% of a map's floor when used. Palette: GreenBrick 55%, GalavaBrick3 15%, DunMirBrick1 8%, GalavaBrick 7%, GalavaBrick2 4%, IxBrickFancy 3%. Borders: dirt 33%, interior_rug 16%, dungeon_stone 15%, cave 8%, water 7%.
- **cave**: in 60 campaign maps, median 8% of a map's floor when used. Palette: CaveHardBrown 80%, CaveHardTan 12%, CaveHardDark 7%, RockDark 2%, RockRed 0%. Borders: dirt 46%, brick 22%, lava 11%, water 9%, dungeon_stone 3%.
- **interior_rug**: in 60 campaign maps, median 2% of a map's floor when used. Palette: RugBlueNorm 30%, RugRed 21%, RugGreen 19%, RugTanLightNorm 7%, RugTanLightDark 6%, RugTan 5%. Borders: brick 57%, interior_wood 18%, tile 18%, dungeon_stone 4%, cobble 1%.
- **interior_wood**: in 58 campaign maps, median 2% of a map's floor when used. Palette: WoodGray2 27%, RedwoodFloor 14%, WoodGray 13%, OakWoodFloor 12%, WoodDark2 11%, WoodLight 5%. Borders: interior_rug 31%, grass 26%, brick 17%, dirt 10%, cave 6%.
- **cobble**: in 58 campaign maps, median 3% of a map's floor when used. Palette: CobblestoneGrayLight 24%, RoughCobble 18%, BrokenCobbleDirtWebs 14%, CobblestoneBlack 9%, CobbleDirt 8%, BrokenCobbleWeedy 7%. Borders: tile 30%, dirt 22%, brick 16%, lava 10%, grass 9%.
- **dungeon_stone**: in 53 campaign maps, median 12% of a map's floor when used. Palette: LOTDPitted 58%, LOTDBlackMarble 20%, GalavaBrownMarble 8%, StoneLight 6%, LOTDDark 4%, LOTDDark2 3%. Borders: brick 52%, tile 13%, lava 13%, dirt 9%, interior_rug 4%.
- **water**: in 52 campaign maps, median 7% of a map's floor when used. Palette: Water 28%, WaterDeep 25%, WaterShallow 19%, WaterSwampShallow 19%, WaterSwampDeep 9%. Borders: dirt 29%, swamp 26%, brick 24%, cave 11%, grass 8%.
- **grass**: in 50 campaign maps, median 15% of a map's floor when used. Palette: GrassNorm 55%, GrassSparse2 22%, WeedsSparse 16%, GrassSparseYellow 4%, GrassNormYellow 2%, GrassDense 1%. Borders: dirt 54%, swamp 16%, brick 12%, interior_wood 7%, water 4%.
- **void**: in 46 campaign maps, median 0% of a map's floor when used. Palette: Black 100%. Borders: facade 68%, grass 7%, lava 6%, cave 6%, dirt 5%.
- **tile**: in 39 campaign maps, median 2% of a map's floor when used. Palette: TileDark 71%, TileStarBlack 23%, TileRed 5%, BusyBlue 1%, CrystalCyan 0%, CrystalBlue 0%. Borders: cobble 28%, interior_rug 24%, dungeon_stone 20%, brick 14%, lava 6%.
- **facade**: in 20 campaign maps, median 16% of a map's floor when used. Palette: GalavaTowerFacade 38%, GalavaGateFacade 34%, LOTDTempleFacade 12%, DunMirFacade 9%, IxTempleInteriorFacade 4%, IxExteriorFacade 3%. Borders: dirt 39%, grass 26%, void 14%, ice 7%, dungeon_stone 6%.
- **lava**: in 16 campaign maps, median 8% of a map's floor when used. Palette: Lava 59%, VolcanicCraggy 41%. Borders: brick 30%, cave 25%, dungeon_stone 24%, cobble 12%, tile 7%.
- **swamp**: in 10 campaign maps, median 45% of a map's floor when used. Palette: SwampGrass 100%. Borders: grass 51%, water 44%, interior_wood 3%, dirt 2%, cobble 0%.
- **ice**: in 4 campaign maps, median 59% of a map's floor when used. Palette: IceFloorDeepBlue 43%, IceFloorRough 28%, IceFloorDark 24%, IceFloorLight 5%. Borders: facade 44%, dungeon_stone 29%, cave 23%, void 3%.

## Priority (who overlays whom, materials with >= 100 weighted blended contacts)

RugRed +1.00, RugGreen +1.00, RedBrick +1.00, RugTan +0.98, DirtSand +0.97, RugBrown +0.92, IceFloorRough +0.92, RugBlueNorm +0.83, DirtLight +0.83, CobbleStone +0.78, WaterShallow +0.76, DirtRed +0.76, Water +0.74, LOTDDark +0.70, WoodGray +0.67, RugTanLightNorm +0.66, LOTDDark2 +0.59, StoneLight +0.57, RedBrick6 +0.53, CobblestoneBlack +0.49, RugTanLightDark +0.49, Lava +0.46, TileStarBlack +0.43, RoughCobble +0.30, CobblestoneGrayLight +0.30, CaveHardTan +0.27, DirtHard +0.21, GalavaBrick2 +0.21, GrassDense +0.18, GalavaBrownMarble +0.18, VolcanicCraggy +0.18, DirtLight2 +0.13, IxBrickSmallRev +0.12, LOTDBlackMarble +0.07, DirtDark +0.06, BrokenCobbleDirtWebs +0.04, CaveHardDark +0.04, WaterSwampShallow +0.01, TileRed -0.08, GrassSparseYellow -0.08, DirtDark2 -0.09, DirtLighter -0.12, GalavaBrick -0.14, GrassNormYellow -0.15, CobbleDirt -0.18, WoodSlatFloor2 -0.19, GrassSparse2 -0.21, WoodGray2 -0.24, IxBrickRev -0.25, WeedsSparse -0.29, RockDark -0.31, ManaMineDirt -0.40, DirtBlue -0.44, GreenBrick -0.44, LOTDPitted -0.52, TileDark -0.52, DirtCrackedLight -0.55, BlueBrick7 -0.60, CaveHardBrown -0.65, DunMirBrick1 -0.71, IceFloorDeepBlue -0.74, GrassNorm -0.77, IxBrickFancy -0.78, WoodLight -0.87, OakWoodFloor -0.95, GalavaBrick3 -0.97, SwampGrass -0.98, IceFloorDark -1.00, WoodLight2 -1.00, RedwoodFloor -1.00, GalavaGateFacade -1.00

## Materials that never touch (need a buffer)

- CaveHardBrown / WaterShallow (both in 24 maps): between them GalavaBrick2 96%, DunMirBrick1 4%
- DirtDark2 / RugTan (both in 19 maps): between them RedwoodFloor 67%, WoodLight 22%, WoodLight2 11%
- Water / WeedsSparse (both in 18 maps): between them DirtDark2 100%
- CaveHardTan / DirtLight2 (both in 18 maps): between them GrassSparse2 67%, GrassNorm 33%
- GreenBrick / WaterDeep (both in 17 maps): between them WaterShallow 100%
- GrassNorm / RugTan (both in 17 maps): between them OakWoodFloor 50%, RedwoodFloor 50%
- GrassSparse2 / RugTan (both in 17 maps): between them WoodLight2 78%, WoodThinSlatLightREV 22%
- DirtHard / RugTanLightNorm (both in 15 maps): between them WoodLight 100%
- DirtLight2 / RugBlueNorm (both in 14 maps): between them GalavaBrick 100%
- GrassNorm / RugTanLightNorm (both in 13 maps): between them OakWoodFloor 58%, RedwoodFloor 42%
- GrassSparse2 / RugTanLightNorm (both in 13 maps): between them RedwoodFloor 50%, WoodLight 38%, RedBrickDesign 12%
- GrassNormYellow / RugTanLightNorm (both in 13 maps): between them RedwoodFloor 100%
- CaveHardBrown / RugTan (both in 13 maps): between them GreenBrick 100%
- DirtDark2 / RugRed (both in 13 maps): between them DunMirBrick1 71%, DirtHard 29%
- GrassNorm / RugGreen (both in 12 maps): between them WoodLight2 74%, RedwoodFloor 26%
- GrassSparse2 / RugGreen (both in 12 maps): between them RedwoodFloor 100%
- DirtLight2 / RugGreen (both in 12 maps): between them WoodLight 100%
- GrassNorm / RugBlueNorm (both in 11 maps): between them BlueBrick7 75%, GalavaBrick3 25%
- BlueBrick7 / GrassSparse2 (both in 11 maps): between them GrassNorm 67%, WoodLight 33%
- DirtHard / TileStarBlack (both in 11 maps): between them TileDark 100%
- DirtLight2 / RedwoodFloor (both in 10 maps): between them GalavaBrick2 100%
- DirtLight2 / TileRed (both in 10 maps): between them CaveHardBrown 100%
- RugTan / TileDark (both in 10 maps): between them RedwoodFloor 86%, WoodLight 14%
- GrassSparse2 / RugTanLightDark (both in 10 maps): between them WoodLight2 91%, DirtLight 9%
- WaterSwampShallow / WeedsSparse (both in 10 maps): between them SwampGrass 100%
- CobblestoneGrayLight / Lava (both in 10 maps): between them VolcanicCraggy 100%
- DirtLight2 / OakWoodFloor (both in 9 maps): between them GreenBrick 100%
- RoughCobble / RugGreen (both in 9 maps): between them WoodLight2 100%
- RedwoodFloor / RoughCobble (both in 9 maps): between them DirtDark2 67%, WeedsSparse 33%
- DunMirBrick1 / Water (both in 9 maps): between them DirtCrackedLight 100%
