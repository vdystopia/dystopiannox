# Buildings

Source: `rules/buildings.py`, buildings from `rules/out/rooms.json` (rooms sharing a wall or door) in the 107 campaign maps, at most 900 floor tiles and 14 rooms (larger complexes are dungeons). Weighted by 1 / layout group size. Sizes are in lattice units along the wall axes (one wall segment = 2 in u or v, about one cell along the wall). Quartiles are [25%, median, 75%]. A building is *freestanding* when at least half of what lies outside its outer walls is open floor (towns, villages), as opposed to rooms inside larger structures.

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

- 678 buildings (301.33 weighted). Shapes: rect 52%, T 16%, L 11%, irregular 8%, Z 6%, cross 3%, U 2%, courtyard 1%.
- Long side [7, 12, 20] units, short side [5, 8, 15]; floor tiles [24, 56, 162].
- Rooms: 1 54%, 2 18%, 3 11%, 5 5%, 4 4%, 10 3%, 8 2%, 6 2%; lattice units per room in multi-room buildings [39.0, 63.5, 97.0].
- Rooms measure long [5.0, 8.0, 13.0] x short [4.0, 6.0, 8.0] units; the largest room holds [0.44, 0.61, 0.76] of a multi-room building; 8% of multi-room buildings have a corridor.
- Interior doors per additional room [0.0, 1.0, 1.25] (below 1 means some rooms join through archways or each other).
- Entrances: 0 47%, 2 21%, 1 20%, 3 5%, 4 4%, 5 1%; sides: u_max 31%, u_min 26%, v_min 22%, v_max 21%.

## Freestanding buildings (towns and villages)

- 299 buildings (133.42 weighted). Shapes: rect 60%, L 15%, irregular 9%, T 8%, U 4%, courtyard 2%, Z 2%, cross 1%.
- Long side [7, 10, 17] units, short side [5, 7, 11]; floor tiles [24, 48, 99]; rooms 1 49%, 2 20%, 3 14%, 4 5%, 5 4%, 10 2%.
- Entrances 1 28%, 2 26%, 0 23%, 3 10%, 4 7%, 5 2%; sides u_max 32%, v_min 24%, u_min 23%, v_max 21%.
- Gap to the nearest neighbouring building [3.0, 5.0, 20.0] units (0 = sharing walls / touching).
- Outside them: GrassNorm 18%, GreenBrick 16%, GrassSparse2 11%, CaveHardBrown 11%, GalavaBrick2 7%, GalavaBrick 7%.

## Styles (by exterior wall material)

| style | wall | buildings (w) | freestanding | shapes | long x short (median) | rooms | room floors | doors (ext) | partition walls | pieces complete |
|---|---|---|---|---|---|---|---|---|---|---|
| lotd_crypt | LOTDBrick | 17 (5.67) | 10% | rect 100% | 5 x 3 | 1 100% | LOTDPitted 100% | - | - | yes |
| dungeon_block | DungeonStone | 43 (15.67) | 37% | rect 81%, L 6%, courtyard 6% | 9 x 8 | 1 62%, 2 26%, 3 13% | GreenBrick 95%, TileDark 3%, DirtDark2 2% | CryptDoor 68%, JailDoor 16% | DungeonStone 100% | yes |
| log_cabin | Log | 34 (16.0) | 60% | rect 59%, L 12%, irregular 12% | 11 x 5 | 1 53%, 3 31%, 2 9% | WoodGray 19%, DirtHard 15%, DirtDark2 13% | WoodenDoor 24%, BandedPlankDoor 24% | Log 88%, InvisibleBlockingWallSet 8% | yes |
| cobble_house | Cobblestone | 20 (9.0) | 42% | L 33%, irregular 33%, rect 22% | 9 x 7 | 1 47%, 2 19%, 10 11% | GreenBrick 44%, BlueBrick7 22%, BrokenCobbleDirtWebs 11% | WoodAndSteelHalfDoor 67%, ArchedHalfDoor 19% | Cobblestone 91%, StoneGray 9% | yes |
| blue_brick_house | BrickBlue | 3 (3.0) | 17% | rect 100% | 5 x 5 | 1 100% | TileDark 33%, TileStarBlack 33%, RugBlueNorm 33% | GalavaHalfDoor 100% | - | yes |
| stucco_house | StuccoLightWood | 45 (17.0) | 94% | rect 74%, T 14%, Z 6% | 9 x 7 | 2 47%, 1 28%, 3 14% | RugTanLightNorm 31%, OakWoodFloor 22%, RedwoodFloor 12% | WoodenDoor 47%, ArchedHalfDoor 38% | StuccoLightWood 98%, StuccoLightWoodDamaged 1% | yes |
| dunmir_hall | DunMirCathedral | 28 (14.5) | 85% | rect 45%, irregular 28%, L 14% | 19 x 11 | 2 34%, 1 31%, 4 14% | GreenBrick 60%, DunMirBrick1 30%, DunMirBrick2 7% | DunMirDoor 57%, DunMirHalfDoor 30% | DunMirCathedral 100% | yes |
| galava_townhouse | GalavaTownWall | 23 (11.67) | 70% | rect 51%, L 49% | 14 x 11 | 1 49%, 5 17%, 3 17% | GalavaBrick 39%, RugBlueNorm 23%, GalavaBrick2 18% | ArchedHalfDoor 37%, ArchedDoor 26% | GalavaTownWall 100% | yes |
| sewer | SewerWall | 2 (2.0) | 15% | rect 100% | 6 x 6 | 1 100% | GreenBrick 100% | BandedWoodenDoor 100% | - | yes |
| lotd_ornate | LOTDOrnate | 16 (7.33) | 59% | rect 32%, T 27%, U 27% | 10 x 6 | 1 59%, 3 27%, 2 14% | LOTDPitted 50%, LOTDBlackMarble 50% | LOTDHalfDoor 67%, LOTDSingleDoor 33% | LOTDOrnate 86%, LOTDBrick 14% | yes |
| ruined_shack | Dilapidated | 21 (10.25) | 100% | rect 85%, L 10%, T 5% | 6 x 5 | 1 85%, 3 10%, 2 5% | WoodGray 39%, WoodGray2 16%, WoodSlatFloor 15% | BandedPlankDoor 33%, Dilapidated 33% | Dilapidated 100% | yes |
| ix_temple | IxTempleWall | 6 (2.0) | 20% | L 50%, rect 50% | 5 x 5 | 1 50%, 2 50% | IxBrickFancy 100% | - | IxTempleWall 100% | yes |
| galava_tower | GalavaTowerWall | 12 (8.0) | 19% | T 31%, rect 25%, cross 25% | 17 x 14 | 1 38%, 3 19%, 10 12% | GalavaBrick3 29%, GalavaBrownMarble 22%, LOTDDark2 12% | GalavaDoor 40%, ArchedHalfDoor 40% | GalavaTowerWall 87%, IronFence 9% | yes |
| stone_house | StoneGray | 10 (5.33) | 70% | T 56%, L 38%, rect 6% | 14 x 11 | 10 38%, 2 38%, 4 19% | WoodGray2 53%, LOTDBlackMarble 19%, GalavaBrick2 7% | Gate 37%, ArchedHalfDoor 25% | StoneGray 100% | yes |
| stucco_dark_house | StuccoDarkWood | 9 (4.0) | 100% | L 50%, rect 50% | 20 x 16 | 4 50%, 2 25%, 6 25% | RugTanLightNorm 75%, RedwoodFloor 8%, Water 4% | ArchedHalfDoor 50%, Gate 25% | StuccoDarkWood 84%, InvisibleWallSet 11% | yes |
| ogre_hut | OgreWall | 9 (3.0) | 100% | courtyard 33%, rect 33%, irregular 33% | 10 x 7 | 1 67%, 3 33% | GalavaBrick 67%, WoodGray2 22%, WeedsSparse 11% | SpikedDoor 100% | OgreWall 100% | yes |
| red_brick_house | BrickRed | 4 (2.0) | 100% | rect 50%, irregular 50% | 18 x 15 | 3 50%, 5 50% | TileRed 53%, DirtRed 27%, DunMirBrick2 20% | DunMirDoor 100% | BrickRed 82%, DunMirCathedral 18% | yes |

## Notes for generation

- Footprints are unions of rectangles on the u/v wall lattice; rectangles dominate, then L and T/U shapes.
- A style is only safe for multi-room interiors when its wall material has valid pieces for T-junctions and corners (`wall_pieces_complete`); otherwise use a different partition material (the style's `interior_wall_materials`) or keep the building single-roomed.
- Freestanding buildings mostly have one entrance; place it on the side facing the street or square.
