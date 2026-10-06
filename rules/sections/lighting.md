## Lighting

Source: `rules/lighting.py` -> `rules/out/lighting.json`. Style figures are campaign maps weighted by 1/layout-group size; validity facts use all 157 maps. Quartiles are written as [25%, median, 75%].

**JSON schema (`lighting.json`)**: `floor_context_rules` (ordered regex -> context used everywhere below); `colorlight` {`constant_fields`, `varying_fields` (field -> distinct values), `radius_by_intensity`, `unknown7_by_intensity`, `presets[]` {id, family, animation, intensity_class, weighted_share, count, maps, rgb_median, intensity_median, radius_median, contexts, `xfer` = complete field set of the most common real light in the preset}}; `density` {by_context{ctx: tiles_weighted, colorlights/sources/all_lights_per_100_tiles}, per_map quartiles}; `spacing` {ctx: nearest-neighbour px quartiles}; `pairing`; `visible_sources` {type: kind, weighted_count, maps, contexts, dangerous, wall_mounted, share_with_colorlight_within_46px, paired_colorlight_presets, paired_offset_px_median, wall_relation[], distance_to_wall_centre_px_median}; `ambient` {map_by_kind, polygon_by_context, polygon_minimap_groups, maps[]}.

### ColorLight (invisible light) settings

- Fields that never vary across 13,145 lights in all maps (copy as-is): B2, B3, ChangeColors, ChangeRadius, ColorChangeIndex, G2, G3, IntensityChangeIndex, IsAntiLight, MaxRadius10, MaxRadius6, MaxRadius7, MaxRadius8, MinRadius10, MinRadius6, MinRadius7, MinRadius8, MinRadius9, NumOfColors, R2, R3, RadiusChangeIndex, Unknown11, Unknown30, Unknown4, Unknown5, Unknown6, Unknown9, UnknownB, UnknownB2, UnknownG, UnknownG2, UnknownR, UnknownR2.
- R,G,B are the light colour; Color1 equals R,G,B in 90% of lights (set both). `ChangeIntensitySingle` equals `LightIntensity` in 90% of lights.
- `LightRadius` and `Unknown7` are tied to `LightIntensity` (most common radius per intensity: 63->181, 50->144, 49->141, 45->129, 40->115, 25->66). The standard light is intensity 63 / radius 181-182 (about 90% of all lights); to make a light, copy a preset's `xfer` and change only the colour (R,G,B and Color1).

| preset | share | maps | median RGB | intensity / radius | main contexts |
|---|---|---|---|---|---|
| red_steady_full | 22.2% | 28 | [114, 4, 0] | 63 / 181 | lava 70%, masonry 9%, cave 7% |
| white_steady_full | 19.9% | 56 | [84, 85, 85] | 63 / 181 | lava 35%, dungeon 25%, outdoor 18% |
| orange_steady_full | 12.5% | 37 | [140, 108, 74] | 63 / 181 | outdoor 45%, cave 27%, masonry 17% |
| blue_steady_full | 11.5% | 67 | [51, 71, 216] | 63 / 181 | water 24%, dungeon 16%, outdoor 15% |
| yellow_steady_full | 9.6% | 33 | [132, 123, 70] | 63 / 181 | outdoor 50%, masonry 30%, cave 14% |
| white_animated_full | 4.1% | 49 | [255, 255, 255] | 63 / 181 | dungeon 32%, outdoor 28%, none 13% |
| cyan_steady_full | 3.8% | 33 | [82, 138, 142] | 63 / 181 | dungeon 32%, outdoor 32%, water 15% |
| blue_steady_dim | 2.9% | 22 | [68, 71, 255] | 49 / 141 | swamp 50%, outdoor 23%, water 15% |
| green_steady_full | 2.4% | 34 | [0, 255, 59] | 63 / 181 | outdoor 44%, masonry 30%, water 16% |
| red_animated_full | 2.1% | 5 | [239, 147, 127] | 63 / 181 | lava 94%, masonry 6%, outdoor 1% |
| green_animated_full | 1.9% | 15 | [20, 203, 69] | 63 / 181 | outdoor 67%, water 23%, masonry 7% |
| purple_animated_full | 1.9% | 9 | [115, 20, 203] | 63 / 181 | outdoor 93%, masonry 7% |
| purple_steady_dim | 0.9% | 15 | [131, 0, 255] | 50 / 144 | masonry 59%, cave 17%, dungeon 17% |
| red_steady_dim | 0.7% | 7 | [244, 103, 68] | 45 / 129 | lava 68%, masonry 21%, cave 5% |
| white_animated_dim | 0.6% | 14 | [255, 252, 252] | 28 / 78 | masonry 60%, outdoor 37%, interior 3% |
| green_steady_dim | 0.6% | 17 | [34, 255, 68] | 40 / 115 | cave 24%, outdoor 22%, swamp 21% |

### Density and spacing

- Per map, all light sources per 100 tiles: [2.0, 4.2, 5.9]; ColorLights alone: [0.4, 0.9, 2.2].

| floor context | weighted tiles | ColorLights /100 tiles | visible sources /100 tiles | all /100 tiles | ColorLight nearest-neighbour px |
|---|---|---|---|---|---|
| outdoor | 104862 | 1.30 | 1.05 | 2.35 | [93.2, 117.5, 148.3] |
| masonry | 63521 | 1.24 | 3.56 | 4.80 | [78.6, 106.0, 154.0] |
| interior | 39198 | 0.54 | 1.98 | 2.52 | [94.8, 138.0, 190.1] |
| cave | 38454 | 1.43 | 1.75 | 3.17 | [89.3, 111.4, 143.0] |
| dungeon | 36864 | 1.57 | 2.82 | 4.39 | [89.5, 124.0, 162.6] |
| lava | 20203 | 6.81 | 10.84 | 17.65 | [73.4, 87.9, 103.6] |
| water | 16347 | 1.87 | 0.04 | 1.91 | [84.6, 105.1, 135.9] |
| swamp | 9350 | 1.84 | 0.29 | 2.12 | [77.1, 108.5, 142.5] |
| ice | 7531 | 0.03 | 0.19 | 0.21 |  |
| other | 130 | 0.00 | 7.02 | 7.02 |  |

- ColorLights near water (3 cells): 10%; near lava: 31%.
- Distance from a ColorLight to the nearest visible light source: [83.2, 149.0, 343.2] px; 10% sit within 46 px (2 cells) of one, i.e. most ColorLights are free-standing area lights, not just glows on torches.

### Visible light sources

| type | kind | weighted uses | maps | main contexts | wall-mounted | has ColorLight within 46 px | usual placement |
|---|---|---|---|---|---|---|---|
| SmallFlame | fire (hurts) | 1546.5 | 29 | lava 82%, masonry 6% |  | 33% |  |
| Torch | fire | 1101.5 | 71 | outdoor 43%, masonry 41% | yes | 2% | junction/corner  (39%), 11.4 px from wall centre |
| TorchPole | fire | 632.8 | 62 | outdoor 34%, masonry 28% |  | 3% |  |
| MediumFlame | fire (hurts) | 625.3 | 33 | lava 77%, masonry 8% |  | 31% |  |
| Flame | fire (hurts) | 302.0 | 28 | lava 83%, outdoor 8% |  | 30% |  |
| LOTDManaObelisk | magic | 265.0 | 18 | dungeon 97%, interior 2% |  | 0% |  |
| Candleabra1 | fire | 263.9 | 27 | masonry 52%, interior 46% |  | 1% |  |
| ObeliskPrimitive | magic | 211.0 | 43 | outdoor 56%, masonry 22% |  | 2% |  |
| Obelisk | magic | 205.2 | 36 | masonry 48%, interior 34% |  | 10% |  |
| Candleabra3 | fire | 149.7 | 18 | masonry 48%, interior 48% |  | 1% |  |
| DunMirFlameBasinLit | fire | 124.0 | 12 | cave 59%, masonry 34% |  | 0% |  |
| Candleabra2 | fire | 123.3 | 17 | masonry 78%, interior 22% |  | 5% |  |
| VictorianLantern1 | fire | 120.2 | 23 | masonry 85%, interior 15% | yes | 0% | '\' wall SW side (90%), 8.9 px from wall centre |
| VictorianLantern2 | fire | 113.7 | 19 | masonry 88%, interior 12% | yes | 0% | '/' wall SE side (89%), 8.9 px from wall centre |
| LargeFlame | fire (hurts) | 108.3 | 9 | lava 86%, masonry 10% |  | 22% |  |
| ForceOrb | magic | 89.0 | 9 | dungeon 99%, none 1% |  | 0% |  |
| VictorianLantern3 | fire | 84.0 | 15 | masonry 83%, interior 17% | yes | 0% | '\' wall NE side (63%), 11.5 px from wall centre |
| BlueFlame | fire (hurts) | 77.0 | 15 | dungeon 67%, masonry 33% |  | 3% |  |
| MineCrystal03 | magic | 75.5 | 29 | cave 38%, lava 22% |  | 8% |  |
| MineCrystal01 | magic | 73.3 | 29 | cave 40%, lava 24% |  | 13% |  |
| LOTDWallSconse1 | fire | 72.7 | 14 | dungeon 100% | yes | 0% | '/' wall SE side (92%), 11.5 px from wall centre |
| LOTDWallSconse2 | fire | 71.3 | 14 | dungeon 100%, none 0% | yes | 3% | '\' wall SW side (94%), 11.5 px from wall centre |
| MineCrystal02 | magic | 68.5 | 28 | cave 47%, lava 25% |  | 9% |  |
| MineCrystal04 | magic | 63.0 | 29 | cave 45%, dungeon 25% |  | 10% |  |
| VictorianLantern4 | fire | 55.0 | 15 | masonry 78%, interior 22% | yes | 0% | '/' wall NW side (86%), 10.3 px from wall centre |
| DunMirTorchNorth | fire | 52.0 | 8 | masonry 88%, cave 10% | yes | 21% | '/' wall SE side (84%), 6.4 px from wall centre |
| Candleabra5 | fire | 49.5 | 14 | masonry 86%, dungeon 12% |  | 6% |  |
| LOTDCandleabra1 | fire | 49.3 | 14 | dungeon 100% |  | 0% |  |

### Ambient colour and polygons

| map kind | maps | median ambient RGB | brightness [25/50/75] | lights /100 tiles | polygons per map | polygon coverage | examples |
|---|---|---|---|---|---|---|---|
| cave | 5 | [37, 67, 94] | [1.0, 66.0, 96.7] | [1.7, 3.3, 5.8] | [12, 12, 21] | [1.0, 1.0, 1.0] | Con01A, Con03B, Con09c, War09c |
| dungeon/castle | 30 | [82, 104, 81] | [2.0, 101.7, 105.7] | [3.4, 5.3, 6.5] | [1, 3, 6] | [0.9, 1.0, 1.0] | Wiz02C, Wiz07D, Wiz07E, Con07D |
| ice | 4 | [70, 70, 140] | [93.3, 93.3, 93.3] | [0.8, 0.9, 2.0] | [9, 9, 14] | [1.0, 1.0, 1.0] | Wiz11A, Con09d, War09d, Wiz09d |
| lava | 9 | [45, 34, 45] | [25.0, 36.0, 253.0] | [5.9, 6.2, 13.2] | [4, 6, 10] | [1.0, 1.0, 1.0] | War02A, War02b, War11a, Wiz06a |
| outdoor | 23 | [99, 98, 81] | [25.0, 98.3, 105.7] | [1.6, 3.9, 4.4] | [5, 7, 23] | [1.0, 1.0, 1.0] | War03c, War03d, Wiz01A, Wiz03a |
| swamp | 10 | [48, 117, 63] | [40.0, 76.0, 76.0] | [1.9, 2.7, 2.9] | [7, 20, 20] | [1.0, 1.0, 1.0] | Con11a, Con08e, Con09a, Con09b |
| town | 26 | [156, 147, 99] | [107.0, 141.3, 253.0] | [1.5, 2.7, 4.7] | [3, 10, 12] | [1.0, 1.0, 1.0] | Con02a, War07A, Wiz02B, Wiz06b |

| polygon dominant floor context | polygons | median ambient RGB | brightness [25/50/75] |
|---|---|---|---|
| outdoor | 415 | [101, 100, 100] | [100.3, 100.3, 149.3] |
| cave | 234 | [86, 117, 111] | [73.0, 111.0, 143.7] |
| masonry | 147 | [118, 122, 106] | [100.3, 111.0, 143.7] |
| dungeon | 111 | [54, 65, 71] | [54.0, 63.3, 70.0] |
| swamp | 99 | [48, 117, 63] | [40.3, 76.0, 76.0] |
| interior | 58 | [140, 134, 106] | [105.7, 132.7, 151.3] |
| water | 29 | [100, 100, 101] | [68.0, 100.3, 137.3] |
| ice | 21 | [70, 70, 140] | [93.3, 93.3, 94.0] |
| lava | 13 | [35, 12, 8] | [16.7, 20.0, 106.7] |
| none | 12 | [101, 100, 69] | [25.0, 100.3, 173.7] |

- Polygon minimap groups (weighted share): 100: 50%, 90: 15%, 80: 14%, 70: 5%, 110: 4%, 0: 2%, 1: 1%, 60: 1%.
- Polygons with a player-enter script: 22%.
- Polygons tile essentially the whole floor: 80 of 107 maps have >= 99% of floor tiles inside a polygon (minimum 0.40). Every area needs a polygon carrying its ambient colour and minimap group.
- Flames of type SmallFlame/MediumFlame/Flame/LargeFlame are DANGEROUS (they burn players); Westwood uses them mostly in lava areas. Use torches, TorchPole, candelabra, lanterns, basins and fireplaces as safe light.
