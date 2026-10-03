## Lighting

Source: `rules/lighting.py` -> `rules/out/lighting.json`. Style figures are single-player maps weighted by 1/layout-group size; validity facts use all 157 maps. Quartiles are written as [25%, median, 75%].

**JSON schema (`lighting.json`)**: `floor_context_rules` (ordered regex -> context used everywhere below); `colorlight` {`constant_fields`, `varying_fields` (field -> distinct values), `radius_by_intensity`, `unknown7_by_intensity`, `presets[]` {id, family, animation, intensity_class, weighted_share, count, maps, rgb_median, intensity_median, radius_median, contexts, `xfer` = complete field set of the most common real light in the preset}}; `density` {by_context{ctx: tiles_weighted, colorlights/sources/all_lights_per_100_tiles}, per_map quartiles}; `spacing` {ctx: nearest-neighbour px quartiles}; `pairing`; `visible_sources` {type: kind, weighted_count, maps, contexts, dangerous, wall_mounted, share_with_colorlight_within_46px, paired_colorlight_presets, paired_offset_px_median, wall_relation[], distance_to_wall_centre_px_median}; `ambient` {map_by_kind, polygon_by_context, polygon_minimap_groups, maps[]}.

### ColorLight (invisible light) settings

- Fields that never vary across 13,145 lights in all maps (copy as-is): B2, B3, ChangeColors, ChangeRadius, ColorChangeIndex, G2, G3, IntensityChangeIndex, IsAntiLight, MaxRadius10, MaxRadius6, MaxRadius7, MaxRadius8, MinRadius10, MinRadius6, MinRadius7, MinRadius8, MinRadius9, NumOfColors, R2, R3, RadiusChangeIndex, Unknown11, Unknown30, Unknown4, Unknown5, Unknown6, Unknown9, UnknownB, UnknownB2, UnknownG, UnknownG2, UnknownR, UnknownR2.
- R,G,B are the light colour; Color1 equals R,G,B in 90% of lights (set both). `ChangeIntensitySingle` equals `LightIntensity` in 90% of lights.
- `LightRadius` and `Unknown7` are tied to `LightIntensity` (most common radius per intensity: 63->181, 50->144, 49->141, 45->129, 40->115, 25->66). The standard light is intensity 63 / radius 181-182 (about 90% of all lights); to make a light, copy a preset's `xfer` and change only the colour (R,G,B and Color1).

| preset | share | maps | median RGB | intensity / radius | main contexts |
|---|---|---|---|---|---|
| white_steady_full | 30.9% | 69 | [127, 126, 126] | 63 / 182 | dungeon 26%, outdoor 25%, lava 22% |
| red_steady_full | 17.2% | 29 | [114, 4, 0] | 63 / 181 | lava 70%, masonry 9%, cave 7% |
| blue_steady_full | 11.9% | 74 | [76, 92, 216] | 63 / 181 | outdoor 22%, water 21%, dungeon 15% |
| orange_steady_full | 10.2% | 44 | [140, 108, 74] | 63 / 181 | outdoor 44%, cave 26%, masonry 16% |
| yellow_steady_full | 7.4% | 34 | [132, 123, 70] | 63 / 181 | outdoor 50%, masonry 30%, cave 14% |
| white_animated_full | 4.0% | 54 | [255, 255, 255] | 63 / 181 | outdoor 34%, dungeon 25%, cave 12% |
| cyan_steady_full | 3.2% | 35 | [85, 138, 142] | 63 / 181 | outdoor 34%, dungeon 30%, water 14% |
| blue_steady_dim | 2.6% | 28 | [66, 71, 255] | 47 / 135 | swamp 45%, outdoor 25%, water 13% |
| green_steady_full | 2.1% | 40 | [16, 255, 59] | 63 / 181 | outdoor 39%, masonry 30%, water 15% |
| red_animated_full | 1.6% | 5 | [239, 147, 127] | 63 / 181 | lava 94%, masonry 6%, outdoor 1% |
| green_animated_full | 1.5% | 15 | [20, 203, 69] | 63 / 181 | outdoor 67%, water 23%, masonry 7% |
| purple_animated_full | 1.4% | 9 | [115, 20, 203] | 63 / 181 | outdoor 93%, masonry 7% |
| purple_steady_dim | 1.0% | 22 | [131, 0, 255] | 50 / 144 | masonry 49%, dungeon 17%, cave 17% |
| purple_steady_full | 0.9% | 20 | [190, 99, 255] | 63 / 182 | dungeon 48%, outdoor 25%, masonry 18% |
| green_steady_dim | 0.6% | 23 | [41, 211, 68] | 40 / 115 | cave 32%, outdoor 23%, masonry 15% |
| red_steady_dim | 0.5% | 7 | [244, 103, 68] | 45 / 129 | lava 68%, masonry 21%, cave 5% |

### Density and spacing

- Per map, all light sources per 100 tiles: [2.0, 4.3, 5.7]; ColorLights alone: [0.4, 1.3, 2.1].

| floor context | weighted tiles | ColorLights /100 tiles | visible sources /100 tiles | all /100 tiles | ColorLight nearest-neighbour px |
|---|---|---|---|---|---|
| outdoor | 137778 | 1.37 | 1.26 | 2.63 | [98.1, 131.6, 179.6] |
| masonry | 79168 | 1.25 | 3.45 | 4.70 | [83.4, 121.5, 186.5] |
| dungeon | 64275 | 1.48 | 3.27 | 4.75 | [105.4, 140.1, 198.7] |
| interior | 48188 | 0.70 | 2.03 | 2.72 | [103.7, 149.4, 206.8] |
| cave | 45659 | 1.50 | 1.69 | 3.19 | [92.3, 118.4, 161.4] |
| lava | 25399 | 5.82 | 9.97 | 15.79 | [74.5, 90.1, 109.4] |
| water | 21154 | 1.61 | 0.06 | 1.67 | [87.0, 111.0, 143.2] |
| swamp | 15048 | 1.45 | 0.70 | 2.14 | [88.3, 123.8, 184.0] |
| ice | 10744 | 0.39 | 0.41 | 0.80 | [134.6, 166.4, 250.4] |
| other | 130 | 0.00 | 7.02 | 7.02 |  |

- ColorLights near water (3 cells): 9%; near lava: 26%.
- Distance from a ColorLight to the nearest visible light source: [90.0, 159.3, 321.8] px; 9% sit within 46 px (2 cells) of one, i.e. most ColorLights are free-standing area lights, not just glows on torches.

### Visible light sources

| type | kind | weighted uses | maps | main contexts | wall-mounted | has ColorLight within 46 px | usual placement |
|---|---|---|---|---|---|---|---|
| SmallFlame | fire (hurts) | 1546.5 | 29 | lava 82%, masonry 6% |  | 33% |  |
| Torch | fire | 1530.5 | 82 | outdoor 41%, masonry 38% | yes | 2% | junction/corner  (35%), 11.5 px from wall centre |
| ObeliskPrimitive | magic | 830.0 | 54 | outdoor 29%, masonry 28% |  | 1% |  |
| TorchPole | fire | 632.8 | 62 | outdoor 34%, masonry 28% |  | 3% |  |
| MediumFlame | fire (hurts) | 630.3 | 34 | lava 77%, masonry 8% |  | 31% |  |
| LOTDManaObelisk | magic | 443.0 | 20 | dungeon 94%, ice 4% |  | 0% |  |
| Obelisk | magic | 308.2 | 38 | dungeon 34%, masonry 32% |  | 6% |  |
| Flame | fire (hurts) | 302.0 | 28 | lava 83%, outdoor 8% |  | 30% |  |
| Candleabra1 | fire | 265.9 | 29 | masonry 52%, interior 46% |  | 1% |  |
| SmallFlameImmobile | fire (hurts) | 263.5 | 12 | lava 71%, dungeon 11% |  | 17% |  |
| LOTDWallSconse1 | fire | 197.7 | 18 | dungeon 86%, interior 13% | yes | 1% | '/' wall SE side (91%), 11.5 px from wall centre |
| LOTDWallSconse2 | fire | 189.3 | 18 | dungeon 91%, interior 9% | yes | 3% | '\' wall SW side (89%), 11.5 px from wall centre |
| MediumFlameImmobile | fire (hurts) | 157.0 | 10 | lava 57%, dungeon 31% |  | 9% |  |
| Candleabra3 | fire | 149.7 | 18 | masonry 48%, interior 48% |  | 1% |  |
| LOTDCandleabra1 | fire | 124.3 | 16 | dungeon 98%, ice 2% |  | 0% |  |
| DunMirFlameBasinLit | fire | 124.0 | 12 | cave 59%, masonry 34% |  | 0% |  |
| Candleabra2 | fire | 123.3 | 17 | masonry 78%, interior 22% |  | 5% |  |
| VictorianLantern1 | fire | 120.2 | 23 | masonry 85%, interior 15% | yes | 0% | '\' wall SW side (90%), 8.9 px from wall centre |
| VictorianLantern2 | fire | 113.7 | 19 | masonry 88%, interior 12% | yes | 0% | '/' wall SE side (89%), 8.9 px from wall centre |
| LargeFlame | fire (hurts) | 108.3 | 9 | lava 86%, masonry 10% |  | 22% |  |
| DunMirTorchNorth | fire | 108.0 | 16 | masonry 76%, outdoor 10% | yes | 10% | '/' wall SE side (87%), 11.5 px from wall centre |
| FlameImmobile | fire (hurts) | 97.0 | 10 | lava 68%, dungeon 27% |  | 12% |  |
| DunMirTorchEast | fire | 94.8 | 16 | masonry 76%, outdoor 13% | yes | 6% | '\' wall SW side (80%), 11.5 px from wall centre |
| ForceOrb | magic | 89.0 | 9 | dungeon 99%, none 1% |  | 0% |  |
| MineCrystal03 | magic | 85.5 | 32 | cave 34%, outdoor 21% |  | 7% |  |
| VictorianLantern3 | fire | 84.0 | 15 | masonry 83%, interior 17% | yes | 0% | '\' wall NE side (63%), 11.5 px from wall centre |
| MineCrystal04 | magic | 82.0 | 34 | cave 36%, outdoor 34% |  | 8% |  |
| MineCrystal01 | magic | 80.3 | 30 | cave 36%, lava 22% |  | 12% |  |

### Ambient colour and polygons

| map kind | maps | median ambient RGB | brightness [25/50/75] | lights /100 tiles | polygons per map | polygon coverage | examples |
|---|---|---|---|---|---|---|---|
| cave | 5 | [37, 67, 94] | [1.0, 66.0, 96.7] | [1.7, 3.3, 5.8] | [12, 12, 21] | [1.0, 1.0, 1.0] | Con01A, Con03B, Con09c, War09c |
| dungeon/castle | 36 | [82, 104, 81] | [19.3, 101.7, 105.7] | [3.4, 5.0, 6.3] | [1, 6, 11] | [1.0, 1.0, 1.0] | Wiz02C, Wiz07D, Wiz07E, Con07D |
| ice | 6 | [70, 70, 140] | [88.0, 93.3, 93.3] | [0.9, 2.0, 4.3] | [9, 14, 91] | [1.0, 1.0, 1.0] | Wiz11A, G_LOTD, G_LOTDD, Con09d |
| lava | 10 | [125, 133, 94] | [25.3, 138.3, 253.0] | [5.0, 5.9, 10.0] | [6, 8, 11] | [1.0, 1.0, 1.0] | G_Lava, War02A, War02b, War11a |
| outdoor | 26 | [98, 98, 81] | [36.0, 98.3, 109.3] | [1.6, 3.9, 4.4] | [6, 7, 27] | [1.0, 1.0, 1.0] | G_Mines, War03c, War03d, Wiz01A |
| swamp | 11 | [48, 117, 63] | [76.0, 76.0, 98.3] | [2.0, 2.5, 2.9] | [9, 20, 21] | [1.0, 1.0, 1.0] | Con11a, G_Swamp, Con08e, Con09a |
| town | 26 | [156, 147, 99] | [107.0, 141.3, 253.0] | [1.5, 2.7, 4.7] | [3, 10, 12] | [1.0, 1.0, 1.0] | Con02a, War07A, Wiz02B, Wiz06b |

| polygon dominant floor context | polygons | median ambient RGB | brightness [25/50/75] |
|---|---|---|---|
| outdoor | 665 | [99, 86, 100] | [37.7, 91.0, 114.3] |
| dungeon | 371 | [58, 49, 45] | [21.0, 63.3, 88.0] |
| cave | 334 | [86, 103, 109] | [53.0, 102.3, 129.7] |
| masonry | 331 | [89, 63, 44] | [37.0, 65.3, 106.3] |
| swamp | 118 | [48, 117, 63] | [58.3, 76.0, 98.3] |
| interior | 113 | [126, 87, 81] | [51.0, 105.7, 137.7] |
| water | 102 | [20, 62, 101] | [61.0, 61.0, 61.0] |
| ice | 43 | [63, 70, 127] | [21.0, 88.0, 93.3] |
| lava | 41 | [127, 14, 12] | [51.0, 51.0, 51.0] |
| none | 32 | [63, 79, 63] | [25.0, 77.7, 141.7] |

- Polygon minimap groups (weighted share): 100: 32%, 80: 15%, 90: 13%, 110: 6%, 70: 6%, 50: 6%, 95: 3%, 60: 3%.
- Polygons with a player-enter script: 16%.
- Polygons tile essentially the whole floor: 92 of 120 maps have >= 99% of floor tiles inside a polygon (minimum 0.40). Every area needs a polygon carrying its ambient colour and minimap group.
- Flames of type SmallFlame/MediumFlame/Flame/LargeFlame are DANGEROUS (they burn players); Westwood uses them mostly in lava areas. Use torches, TorchPole, candelabra, lanterns, basins and fireplaces as safe light.
