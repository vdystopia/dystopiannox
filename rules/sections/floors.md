# Floors and edge blending

Schema of `rules/out/floors.json`:
- `blend[]`: one entry per pair of materials that touch as side neighbours (>= 10 contacts in all maps): `a`, `b`, `contacts_all`, `maps_all`, `contacts_sp_weighted`, `maps_sp`, `edge_share_sp` (share of single-player contacts with an edge overlay on the touching side), `edge_share_all`, `overlay`/`base` (which material is drawn over which), `overlay_direction_share`, `edge_types` (share), `preferred_edge_type`.
- `priority{material: {score, evidence}}`: score -1..1, higher = drawn over neighbours (single-player weighted); evidence = weighted blended contacts.
- `material_family{}`, `families{family: materials (area share), unused_in_sp, sp_maps_using, median_share_when_used, neighbour_families}`.
- `never_touch[]`: common materials that co-occur in single-player maps but never touch; `buffer_materials` seen between them.
- `edge_pieces{}`: piece rule, match rate, deviations, side-variant shares, piece ids.
- `variation_rule{}`: share of tiles/edges whose variation equals the editor's automatic formula.
- `edge_types{}`: usage counts and piece count (`nvar`).

## Variation rule

- Tile variation equals the editor's position formula for 80% of all tiles; edge variation equals the overlay material's formula for 89% of edges.
- Lowest-matching materials: DunMirFacade 0%, GalavaGateFacade 0%, GalavaTowerFacade 0%, IxExteriorFacade 0%, IxTempleInteriorFacade 0%, LOTDTempleFacade 0%, RugBlueLight 20%, WoodDark2 26%

## Edge pieces

- Rule: side neighbour of overlay material -> side piece (3 variants, random); two adjacent sides -> corner 'Sides' piece; tip neighbour with neither adjacent side -> tip piece.
- Exact match with the rule: 76% of (tile, overlay) groups (single-player weighted).
- Piece kinds: {'tip': 0.285, 'side': 0.562, 'corner': 0.154}. Deviations per group: {'missing_side': 0.037, 'extra_corner': 0.043, 'extra_tip': 0.069, 'extra_side': 0.133, 'missing_tip': 0.012, 'missing_corner': 0.056}.
- Side variants are used about equally: {'S': {'5': 0.369, '7': 0.301, '9': 0.33}, 'W': {'1': 0.382, '2': 0.298, '3': 0.319}, 'N': {'6': 0.374, '8': 0.3, '10': 0.325}, 'E': {'12': 0.382, '13': 0.294, '14': 0.324}}.

## Most common blends (single-player)

| a | b | contacts (all) | maps | blended | overlay on base | edge type |
|---|---|---|---|---|---|---|
| LOTDBlackMarble | LOTDPitted | 14884 | 29 | 86% | LOTDBlackMarble over LOTDPitted (83%) | MetalSteel |
| DirtDark2 | GreenBrick | 13102 | 37 | 96% | DirtDark2 over GreenBrick (73%) | BlendEdge |
| GrassNorm | GrassSparse2 | 11757 | 47 | 93% | GrassSparse2 over GrassNorm (90%) | BlendEdge |
| CaveHardBrown | CaveHardTan | 11754 | 35 | 99% | CaveHardTan over CaveHardBrown (96%) | BlendEdge |
| DirtDark2 | GrassNorm | 8629 | 45 | 96% | DirtDark2 over GrassNorm (100%) | BlendEdge |
| CaveHardBrown | DirtDark2 | 8591 | 36 | 97% | DirtDark2 over CaveHardBrown (77%) | BlendEdge |
| SwampGrass | WeedsSparse | 7126 | 12 | 100% | WeedsSparse over SwampGrass (97%) | BlendEdge |
| DirtDark2 | DirtHard | 6699 | 54 | 97% | DirtHard over DirtDark2 (65%) | BlendEdge |
| DirtDark2 | GrassSparse2 | 6307 | 39 | 99% | DirtDark2 over GrassSparse2 (87%) | BlendEdge |
| SwampGrass | WaterSwampShallow | 6142 | 12 | 100% | WaterSwampShallow over SwampGrass (100%) | SwampEdge |
| IceFloorDeepBlue | IceFloorRough | 5488 | 8 | 99% | IceFloorRough over IceFloorDeepBlue (66%) | BlendEdge |
| Lava | VolcanicCraggy | 5480 | 18 | 96% | Lava over VolcanicCraggy (100%) | LavaEdgeBlackDirt |
| GalavaBrick3 | GalavaBrownMarble | 4852 | 16 | 9% | GalavaBrownMarble over GalavaBrick3 (100%) | MetalBrass |
| DirtDark2 | DirtLight2 | 4727 | 41 | 99% | DirtLight2 over DirtDark2 (94%) | BlendEdge |
| LOTDDark2 | LOTDPitted | 4332 | 14 | 73% | LOTDPitted over LOTDDark2 (62%) | BrickEdgeBrown |
| DirtLight2 | WeedsSparse | 4135 | 15 | 100% | DirtLight2 over WeedsSparse (94%) | BlendEdge |
| WaterDeep | WaterShallow | 4046 | 26 | 99% | WaterDeep over WaterShallow (91%) | BlendEdge |
| IceFloorDark | IceFloorRough | 3608 | 6 | 100% | IceFloorRough over IceFloorDark (100%) | BlendEdge |
| CaveHardBrown | DirtHard | 3112 | 30 | 95% | DirtHard over CaveHardBrown (54%) | BlendEdge |
| GrassNorm | GrassNormYellow | 2994 | 26 | 80% | GrassNormYellow over GrassNorm (99%) | BlendEdge |
| GrassDense | GrassNorm | 2874 | 29 | 96% | GrassDense over GrassNorm (99%) | BlendEdge |
| DirtLight2 | IxBrickFancy | 2781 | 9 | 98% | DirtLight2 over IxBrickFancy (91%) | BlendEdge |
| CaveHardBrown | Water | 2768 | 23 | 100% | Water over CaveHardBrown (100%) | DirtRidge |
| CaveHardBrown | GreenBrick | 2717 | 18 | 75% | GreenBrick over CaveHardBrown (82%) | BlendEdge |
| DungeonStoneDark | DungeonStoneMuddy | 2684 | 9 | 98% | DungeonStoneDark over DungeonStoneMuddy (100%) | BlendEdge |
| LOTDDark | LOTDPitted | 2456 | 7 | 62% | LOTDDark over LOTDPitted (60%) | BrickEdgeBrown |
| DirtDark | GreenBrick | 2406 | 7 | 99% | GreenBrick over DirtDark (100%) | BlendEdge |
| DirtCrackedDark | DirtCrackedLight | 2319 | 4 | 99% | DirtCrackedLight over DirtCrackedDark (63%) | BlendEdge |
| CaveHardBrown | CaveHardDark | 2301 | 27 | 99% | CaveHardDark over CaveHardBrown (96%) | BlendEdge |
| WaterSwampDeep | WaterSwampShallow | 2087 | 11 | 100% | WaterSwampDeep over WaterSwampShallow (100%) | BlendEdge |
| LOTDPitted | TileDark | 2083 | 7 | 99% | LOTDPitted over TileDark (100%) | BlendEdge |
| TileDark | TileStarBlack | 2009 | 8 | 47% | TileStarBlack over TileDark (82%) | MetalBrass |
| DirtLight2 | IxBrick | 1953 | 9 | 97% | DirtLight2 over IxBrick (98%) | BlendEdge |
| LOTDBlackMarble | StoneLight | 1951 | 22 | 89% | StoneLight over LOTDBlackMarble (74%) | MetalSteel |
| DirtBlue | DirtLight2 | 1934 | 8 | 100% | DirtLight2 over DirtBlue (99%) | BlendEdge |
| DirtBlue | DirtDark2 | 1894 | 9 | 100% | DirtBlue over DirtDark2 (90%) | BlendEdge |
| GrassSparseYellow | WeedsSparse | 1814 | 9 | 100% | GrassSparseYellow over WeedsSparse (100%) | BlendEdge |
| GreenBrick | Water | 1774 | 7 | 99% | Water over GreenBrick (99%) | DirtRidge |
| GrassNorm | GrassSparseYellow | 1770 | 30 | 94% | GrassSparseYellow over GrassNorm (96%) | BlendEdge |
| DirtDark2 | RedBrick6 | 1687 | 6 | 99% | DirtDark2 over RedBrick6 (100%) | BlendEdge |
| DunMirBrick1 | RugRed | 1648 | 5 | 100% | RugRed over DunMirBrick1 (100%) | RugTanLightEdge |
| AncientRuin | AncientRuinRough | 1508 | 5 | 96% | AncientRuin over AncientRuinRough (61%) | BlendEdge |
| CobbleStone | DirtDark2 | 1458 | 11 | 99% | DirtDark2 over CobbleStone (86%) | BlendEdge |
| CryptFloor | DirtDark2 | 1437 | 3 | 98% | DirtDark2 over CryptFloor (96%) | BlendEdge |
| GrassSparse2 | WeedsSparse | 1421 | 14 | 90% | GrassSparse2 over WeedsSparse (75%) | BlendEdge |

## Families

- **dirt**: in 100 single-player maps, median 10% of a map's floor when used. Palette: DirtDark2 52%, DirtLight2 10%, ManaMineDirt 9%, DirtHard 8%, DirtCrackedLight 6%, DirtBlue 4%. Borders: brick 30%, grass 26%, cave 15%, dungeon_stone 7%, water 7%.
- **brick**: in 96 single-player maps, median 20% of a map's floor when used. Palette: GreenBrick 52%, GalavaBrick3 12%, GalavaBrick 7%, DunMirBrick1 6%, GalavaBrick2 6%, IxBrickFancy 6%. Borders: dirt 38%, dungeon_stone 17%, interior_rug 13%, cave 7%, water 6%.
- **interior_rug**: in 70 single-player maps, median 2% of a map's floor when used. Palette: RugBlueNorm 28%, RugRed 20%, RugGreen 19%, RugTanLightDark 9%, RugTanLightNorm 7%, RugTan 4%. Borders: brick 51%, interior_wood 25%, tile 16%, dungeon_stone 5%, cobble 2%.
- **interior_wood**: in 69 single-player maps, median 1% of a map's floor when used. Palette: OakWoodFloor 20%, WoodGray2 16%, RedwoodFloor 15%, WoodLight 12%, WoodLight2 10%, WoodGray 9%. Borders: interior_rug 30%, grass 23%, brick 11%, dirt 9%, dungeon_stone 9%.
- **cave**: in 66 single-player maps, median 8% of a map's floor when used. Palette: CaveHardBrown 81%, CaveHardTan 12%, CaveHardDark 6%, RockDark 1%, RockRed 0%. Borders: dirt 48%, brick 18%, water 12%, lava 10%, dungeon_stone 3%.
- **dungeon_stone**: in 66 single-player maps, median 15% of a map's floor when used. Palette: LOTDPitted 41%, LOTDBlackMarble 18%, LOTDDark2 9%, GalavaBrownMarble 6%, DungeonStoneMuddy 4%, DungeonStoneDark 4%. Borders: brick 36%, dirt 18%, lava 14%, tile 13%, interior_wood 4%.
- **cobble**: in 64 single-player maps, median 3% of a map's floor when used. Palette: CobbleStone 24%, CobblestoneGrayLight 18%, RoughCobble 14%, BrokenCobbleDirtWebs 10%, CobblestoneBlack 7%, CobbleDirt 7%. Borders: dirt 30%, tile 23%, brick 12%, grass 12%, lava 8%.
- **grass**: in 61 single-player maps, median 14% of a map's floor when used. Palette: GrassNorm 59%, GrassSparse2 20%, WeedsSparse 13%, GrassSparseYellow 3%, GrassNormYellow 2%, GrassDense 1%. Borders: dirt 53%, swamp 13%, brick 9%, interior_wood 8%, water 6%.
- **water**: in 60 single-player maps, median 7% of a map's floor when used. Palette: Water 25%, WaterDeep 19%, WaterShallow 15%, WaterSwampShallow 15%, WaterSwampShallowNoTeleport 11%, WaterSwampDeep 7%. Borders: swamp 29%, dirt 24%, brick 18%, cave 13%, grass 11%.
- **void**: in 48 single-player maps, median 0% of a map's floor when used. Palette: Black 100%. Borders: facade 70%, grass 7%, lava 6%, cave 5%, dirt 4%.
- **tile**: in 45 single-player maps, median 1% of a map's floor when used. Palette: TileDark 74%, TileStarBlack 21%, TileRed 4%, BusyBlue 1%, CrystalCyan 0%, CrystalBlue 0%. Borders: dungeon_stone 31%, cobble 24%, interior_rug 20%, brick 12%, lava 5%.
- **facade**: in 22 single-player maps, median 16% of a map's floor when used. Palette: GalavaTowerFacade 36%, GalavaGateFacade 32%, LOTDTempleFacade 11%, DunMirFacade 8%, IxTempleInteriorFacade 7%, IxExteriorFacade 6%. Borders: dirt 37%, grass 28%, void 15%, dungeon_stone 8%, ice 6%.
- **lava**: in 21 single-player maps, median 7% of a map's floor when used. Palette: Lava 58%, VolcanicCraggy 42%. Borders: dungeon_stone 35%, brick 28%, cave 22%, cobble 8%, tile 5%.
- **swamp**: in 11 single-player maps, median 45% of a map's floor when used. Palette: SwampGrass 100%. Borders: water 39%, grass 30%, dirt 27%, interior_wood 3%, cobble 0%.
- **ice**: in 6 single-player maps, median 39% of a map's floor when used. Palette: IceFloorRough 42%, IceFloorDeepBlue 37%, IceFloorDark 16%, IceFloorLight 4%. Borders: dungeon_stone 64%, dirt 16%, facade 12%, cave 6%, void 1%.

## Priority (who overlays whom, materials with >= 100 weighted blended contacts)

RugRed +1.00, RugGreen +1.00, RedBrick +1.00, RugBlueLight +1.00, RugTan +0.98, DirtSand +0.97, IceFloorLight +0.96, RugBrown +0.92, RugTanLightLight +0.90, GrassDenseYellow +0.86, RugBlueNorm +0.84, DirtLight +0.83, DungeonStoneLight +0.80, Water +0.80, StoneLight +0.77, WaterShallow +0.76, WaterDeepNoTeleport +0.75, WoodSlatFloor +0.71, RugTanLightNorm +0.60, WoodGray +0.58, DungeonStoneDark +0.57, RugBlueDark +0.49, CobblestoneBlack +0.49, Lava +0.49, GalavaBrownMarble +0.46, RugTanLightDark +0.44, LOTDDark +0.35, RoughCobble +0.31, TileStarBlack +0.30, CobblestoneGrayLight +0.30, DirtRed +0.28, VolcanicCraggy +0.25, DirtHard +0.24, CobbleDirt +0.24, WoodSlatFloor2 +0.20, DirtLight2 +0.17, CaveHardTan +0.17, DirtDark2 +0.16, IxBrickSmall +0.16, LOTDBlackMarble +0.15, WoodGray2 +0.15, WaterShallowNoTeleport +0.09, GrassDense +0.08, GrassSparseYellow +0.08, DirtDark +0.06, BrokenCobbleDirtWebs +0.04, CaveHardDark +0.03, WaterSwampShallow +0.01, LOTDPitted -0.03, TileRed -0.08, IxBrickRev -0.10, DirtLighter -0.12, DungeonStoneMuddy -0.18, GrassSparse2 -0.18, CobbleStone -0.20, IxBrickSmallRev -0.20, IxBrick -0.21, GalavaBrick2 -0.23, GrassNormYellow -0.24, RedBrick6 -0.24, LOTDDark2 -0.27, WeedsSparse -0.29, GalavaBrick -0.30, RockDark -0.31, AncientRuin -0.33, AncientRuinRough -0.33, ManaMineDirt -0.40, CaveHardBrown -0.44, DirtBlue -0.44, GreenBrick -0.48, IceFloorRough -0.50, TileDark -0.54, RedwoodFloor -0.57, DirtCrackedLight -0.59, BlueBrick7 -0.60, IceFloorDeepBlue -0.63, CryptFloor -0.64, DunMirBrick1 -0.65, DirtCrackedDark -0.77, GrassNorm -0.83, IxBrickFancy -0.84, WoodLight -0.87, WoodLight2 -0.88, OakWoodFloor -0.92, GalavaBrick3 -0.97, SwampGrass -0.99, IceFloorDark -1.00, GalavaGateFacade -1.00, IxExteriorFacade -1.00

## Materials that never touch (need a buffer)

- CaveHardBrown / WaterShallow (both in 24 maps): between them GalavaBrick2 96%, DunMirBrick1 4%
- CaveHardTan / DirtLight2 (both in 24 maps): between them GrassSparse2 67%, GrassNorm 33%
- Water / WeedsSparse (both in 19 maps): between them DirtDark2 100%
- DirtLight2 / LOTDPitted (both in 19 maps): between them AncientRuinRough 100%
- GreenBrick / WaterDeep (both in 17 maps): between them WaterShallow 100%
- DirtHard / TileStarBlack (both in 17 maps): between them TileDark 100%
- DirtLight2 / RugBlueNorm (both in 16 maps): between them GalavaBrick 100%
- GrassNorm / RugGreen (both in 14 maps): between them WoodLight2 72%, RedwoodFloor 26%, OakWoodFloor 2%
- GrassSparse2 / RugGreen (both in 14 maps): between them RedwoodFloor 100%
- DirtLight2 / RugGreen (both in 14 maps): between them WoodLight 100%
- DirtDark2 / RugRed (both in 14 maps): between them DunMirBrick1 71%, DirtHard 29%
- DirtLight2 / RedwoodFloor (both in 13 maps): between them GalavaBrick2 100%
- DunMirBrick1 / Water (both in 12 maps): between them DirtCrackedLight 100%
- GrassNorm / StoneLight (both in 12 maps): between them RedwoodFloor 100%
- GrassNorm / RugBlueNorm (both in 11 maps): between them BlueBrick7 75%, GalavaBrick3 25%
- DirtLight2 / OakWoodFloor (both in 11 maps): between them GreenBrick 100%
- GrassNorm / TileStarBlack (both in 11 maps): between them GreenBrick 100%
- DirtLight2 / RugRed (both in 10 maps): between them GalavaBrick 100%
- WaterSwampShallow / WeedsSparse (both in 10 maps): between them SwampGrass 100%
- CobblestoneGrayLight / Lava (both in 10 maps): between them VolcanicCraggy 100%
- RoughCobble / RugGreen (both in 9 maps): between them WoodLight2 100%
- GrassSparseYellow / WoodLight2 (both in 9 maps): between them GrassSparse2 100%
- RedwoodFloor / RoughCobble (both in 9 maps): between them DirtDark2 67%, WeedsSparse 33%
- DirtHard / RedBrick6 (both in 9 maps): between them DirtLight2 100%
- DirtBlue / IxBrick (both in 9 maps): between them DirtLight2 100%
- WaterDeep / WeedsSparse (both in 8 maps): between them WaterShallow 100%
- DirtDark / GrassNormYellow (both in 8 maps): between them CryptFloor 100%
- GrassNorm / RugRed (both in 8 maps): between them RedwoodFloor 100%
- GreenBrick / SwampGrass (both in 8 maps): between them WeedsSparse 100%
- DunMirBrick1 / Lava (both in 8 maps): between them VolcanicCraggy 100%
