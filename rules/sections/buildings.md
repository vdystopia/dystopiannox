# Buildings

Source: `rules/buildings.py`, buildings from `rules/out/rooms.json` (rooms sharing a wall or door) in the 120 single-player maps, at most 900 floor tiles and 14 rooms (larger complexes are dungeons). Weighted by 1 / layout group size. Sizes are in lattice units along the wall axes (one wall segment = 2 in u or v, about one cell along the wall). Quartiles are [25%, median, 75%]. A building is *freestanding* when at least half of what lies outside its outer walls is open floor (towns, villages), as opposed to rooms inside larger structures.

## JSON schema (`rules/out/buildings.json`)

```
{schema_version, units, shape_definitions{shape: text},
 all|freestanding|styles{name}: {buildings, weighted, shapes{shape: share}, size_units{W (long side), H (short)}: quartiles,
   tiles, rooms{n: share}, area_units_per_room, room_long_short_units{long, short}, hall_share (largest room / building),
   corridor_share, interior_doors_per_extra_room, entrances{n: share}, entrance_sides{u_min|u_max|v_min|v_max: share},
   room_floors, exterior_door_types, interior_door_types, interior_wall_materials, outside_floors{material: share},
   nearest_gap_units (to the next freestanding building),
   styles only: exterior_wall, freestanding_share, source (freestanding|all: which buildings the style was measured on),
   wall_pieces_complete, missing_wall_facings}}
```

## All buildings

- 917 buildings (438.33 weighted). Shapes: rect 48%, T 18%, L 12%, Z 9%, irregular 7%, cross 3%, U 2%, courtyard 0%.
- Long side [7, 12, 22] units, short side [5, 8, 15]; floor tiles [22, 64, 171].
- Rooms: 1 54%, 2 16%, 3 10%, 4 5%, 5 4%, 10 4%, 6 3%, 8 2%; lattice units per room in multi-room buildings [40.33, 66.0, 97.0].
- Rooms measure long [5.0, 8.0, 13.0] x short [4.0, 6.0, 9.0] units; the largest room holds [0.42, 0.57, 0.74] of a multi-room building; 12% of multi-room buildings have a corridor.
- Interior doors per additional room [0.0, 0.86, 1.0] (below 1 means some rooms join through archways or each other).
- Entrances: 0 52%, 2 20%, 1 17%, 4 4%, 3 4%, 5 1%; sides: u_max 33%, u_min 25%, v_max 21%, v_min 21%.

## Freestanding buildings (towns and villages)

- 421 buildings (202.42 weighted). Shapes: rect 55%, L 16%, T 10%, irregular 9%, Z 5%, U 3%, courtyard 1%, cross 0%.
- Long side [6, 10, 17] units, short side [5, 8, 12]; floor tiles [19, 51, 111]; rooms 1 53%, 2 18%, 3 11%, 4 6%, 5 4%, 6 2%.
- Entrances 0 32%, 2 26%, 1 24%, 3 8%, 4 6%, 5 2%; sides u_max 32%, u_min 25%, v_min 22%, v_max 21%.
- Gap to the nearest neighbouring building [3.0, 5.0, 15.0] units (0 = sharing walls / touching).
- Outside them: GrassNorm 18%, GreenBrick 14%, GrassSparse2 7%, CaveHardBrown 7%, GalavaBrick2 6%, SwampGrass 5%.

## Styles (by exterior wall material)

| style | wall | buildings (w) | freestanding | shapes | long x short (median) | rooms | room floors | doors (ext) | partition walls | pieces complete |
|---|---|---|---|---|---|---|---|---|---|---|
| dungeon_block | DungeonStone | 69 (28.67) | 37% | rect 65%, L 21%, Z 7% | 9 x 6 | 1 69%, 2 21%, 3 7% | GreenBrick 83%, GalavaBrownMarble 7%, DirtDark2 5% | CryptDoor 73%, JailDoor 13% | DungeonStone 85%, DilapidatedShort 9% | yes |
| lotd_crypt | LOTDBrick | 23 (8.67) | 12% | rect 88%, Z 12% | 5 x 3 | 1 88%, 4 12% | LOTDPitted 65%, DungeonStoneDark 26%, LOTDDark2 3% | CryptDoor 100% | LOTDBrick 100% | yes |
| log_cabin | Log | 50 (24.0) | 66% | rect 65%, irregular 12%, L 8% | 10 x 5 | 1 60%, 3 21%, 2 6% | OakWoodFloor 32%, WoodGray 12%, DirtHard 10% | BandedPlankDoor 43%, WoodenDoor 13% | Log 78%, Cobblestone 6% | yes |
| galava_townhouse | GalavaTownWall | 30 (17.67) | 52% | rect 51%, L 32%, Z 11% | 16 x 12 | 1 49%, 5 17%, 3 11% | GalavaBrick 33%, GalavaBrick2 26%, RugBlueNorm 15% | ArchedHalfDoor 33%, CryptDoor 20% | GalavaTownWall 85%, LOTDMagicOrnate 15% | yes |
| cobble_house | Cobblestone | 20 (9.0) | 38% | L 33%, irregular 33%, rect 22% | 9 x 7 | 1 47%, 2 19%, 10 11% | GreenBrick 44%, BlueBrick7 22%, BrokenCobbleDirtWebs 11% | WoodAndSteelHalfDoor 67%, ArchedHalfDoor 19% | Cobblestone 91%, StoneGray 9% | yes |
| lotd_ornate | LOTDOrnate | 34 (16.33) | 73% | rect 33%, T 31%, irregular 18% | 17 x 11 | 1 45%, 2 24%, 5 12% | LOTDPitted 43%, LOTDBlackMarble 22%, LOTDDark2 19% | LOTDHalfDoor 57%, LOTDSingleDoor 29% | LOTDOrnate 90%, IronFence 8% | yes |
| blue_brick_house | BrickBlue | 3 (3.0) | 16% | rect 100% | 5 x 5 | 1 100% | TileDark 33%, TileStarBlack 33%, RugBlueNorm 33% | GalavaHalfDoor 100% | - | yes |
| stucco_house | StuccoLightWood | 45 (17.0) | 94% | rect 74%, T 14%, Z 6% | 9 x 7 | 2 47%, 1 28%, 3 14% | RugTanLightNorm 31%, OakWoodFloor 22%, RedwoodFloor 12% | WoodenDoor 47%, ArchedHalfDoor 38% | StuccoLightWood 98%, StuccoLightWoodDamaged 1% | yes |
| dunmir_hall | DunMirCathedral | 28 (14.5) | 85% | rect 45%, irregular 28%, L 14% | 19 x 11 | 2 34%, 1 31%, 4 14% | GreenBrick 60%, DunMirBrick1 30%, DunMirBrick2 7% | DunMirDoor 57%, DunMirHalfDoor 30% | DunMirCathedral 100% | yes |
| ix_temple | IxTempleWall | 8 (3.0) | 20% | L 33%, rect 33%, Z 33% | 9 x 5 | 2 67%, 1 33% | IxBrickFancy 100% | - | IxTempleWall 100% | yes |
| sewer | SewerWall | 2 (2.0) | 15% | rect 100% | 6 x 6 | 1 100% | GreenBrick 100% | BandedWoodenDoor 100% | - | yes |
| ogre_hut | OgreWall | 20 (13.0) | 100% | rect 46%, L 31%, courtyard 8% | 10 x 8 | 1 54%, 2 23%, 3 15% | DirtDark2 63%, GalavaBrick 15%, AncientRuin 8% | SpikedDoor 100% | OgreWall 82%, OgreCage 18% | yes |
| ruined_shack | Dilapidated | 24 (12.25) | 100% | rect 80%, L 8%, Z 8% | 6 x 5 | 1 80%, 3 16%, 2 4% | WoodGray 33%, WoodGray2 14%, WoodSlatFloor 12% | BandedPlankDoor 46%, Dilapidated 27% | Dilapidated 94%, DecidiousWallGreen 6% | yes |
| ancient_ruin | AncientRuin | 14 (7.0) | 64% | rect 29%, T 29%, irregular 14% | 8 x 6 | 1 71%, 6 14%, 7 14% | AncientRuinRough 87%, AncientRuin 6%, DirtLight2 2% | AncientRuinDoor 100% | AncientRuin 98%, AncientRuinShort 2% | yes |
| stone_house | StoneGray | 14 (7.33) | 76% | T 41%, rect 32%, L 27% | 14 x 11 | 1 32%, 10 27%, 2 27% | WoodGray2 39%, GreenBrick 14%, GalavaBrownMarble 14% | Gate 32%, ArchedHalfDoor 21% | StoneGray 100% | yes |
| galava_tower | GalavaTowerWall | 12 (8.0) | 19% | T 31%, rect 25%, cross 25% | 17 x 14 | 1 38%, 3 19%, 10 12% | GalavaBrick3 29%, GalavaBrownMarble 22%, LOTDDark2 12% | GalavaDoor 40%, ArchedHalfDoor 40% | GalavaTowerWall 87%, IronFence 9% | yes |
| blue_stone_house | StoneBlue | 9 (4.5) | 82% | Z 44%, rect 33%, U 22% | 16 x 13 | 1 33%, 6 22%, 2 22% | WoodLight 37%, DungeonStoneMuddy 30%, DungeonStoneDark 15% | BarredGate 40%, GalavaHalfDoor 40% | StoneBlue 48%, Dilapidated 22% | yes |
| stucco_dark_house | StuccoDarkWood | 9 (4.0) | 100% | L 50%, rect 50% | 20 x 16 | 4 50%, 2 25%, 6 25% | RugTanLightNorm 75%, RedwoodFloor 8%, Water 4% | ArchedHalfDoor 50%, Gate 25% | StuccoDarkWood 84%, InvisibleWallSet 11% | yes |
| red_brick_house | BrickRed | 4 (2.0) | 100% | rect 50%, irregular 50% | 18 x 15 | 3 50%, 5 50% | TileRed 53%, DirtRed 27%, DunMirBrick2 20% | DunMirDoor 100% | BrickRed 82%, DunMirCathedral 18% | yes |
| brick_house | BrickPlain | 3 (2.0) | 0% | rect 50%, Z 50% | 14 x 12 | 1 50%, 6 50% | TileStarBlack 50%, IxBrickSmall 25%, IxBrickSmallRev 17% | CryptDoor 100% | BrickPlain 77%, IronFence 23% | yes |

## Notes for generation

- Footprints are unions of rectangles on the u/v wall lattice; rectangles dominate, then L and T/U shapes.
- A style is only safe for multi-room interiors when its wall material has valid pieces for T-junctions and corners (`wall_pieces_complete`); otherwise use a different partition material (the style's `interior_wall_materials`) or keep the building single-roomed.
- Freestanding buildings mostly have one entrance; place it on the side facing the street or square.
