# Rulebook (phase 2)

Map-making rules learned from Westwood's maps: style from the 107 campaign maps only (Con, War, Wiz; 54 layouts),
validity from all 157 stock maps. Read [RULEBOOK.md](RULEBOOK.md); the
generator and the validator use the machine-readable versions in `out/`.

```
py corpus\build_corpus.py --skip-images   # once: the corpus the rules are mined from
py rules\build_rulebook.py                # run every miner and rebuild RULEBOOK.md (~2 min)
py rules\build_rulebook.py --assemble     # only reassemble RULEBOOK.md from sections/
```

| Miner | Output | Covers |
|---|---|---|
| `walls.py` | `out/walls.json` | valid wall pieces (material x facing x variation), natural variation mix, material contexts and joins, windows/breakable/secret walls, outer-boundary construction, invisible-wall usage, door types and placement, minimap groups |
| `floors.py` | `out/floors.json` | material adjacency and blend table (edge type, which material draws over which), priorities, materials that must never touch, edge piece rules, tile/edge variation rule, floor families |
| `water.py` | `out/water.json` | shoreline structure, stream and lake sizes, shore walls, floor bridges, fords, rope/lava bridge and dock kit assembly |
| `lighting.py` | `out/lighting.json` | ColorLight presets with complete settings, density and spacing by context, visible light sources and wall-mounted variants, ambient colours, polygons |
| `decoration.py` | `out/decoration.json` | palettes and density per floor, spacing, relation to walls and paths, clusters, furniture sets, directional variants, Extent blockers, ambient sounds |
| `life.py` | `out/life.json` | townsfolk counts, behaviour, clothing, shops, waypoint networks, roaming |
| `rooms.py` | `out/rooms.json` | room and building statistics, and an index of every room for building pieces (phase 3) |

`common.py` holds the shared geometry facts and database access. Style statistics weight
campaign maps only (`common.campaign_weights()`: Con/War/Wiz, never the quest maps G_* nor the multiplayer and
social maps, which are other games' noise for the campaign maps we make), so layouts shared by the class campaigns
count once; validity tables (what object, wall and floor types exist, how kit pieces join) use all maps, and
`decoration.json observed_types` marks the types never placed in a campaign map (`campaign: false`). `py rules/spacing.py`
measures the outdoor gaps (`kit/spacing.py`) and grouped creatures (`kit/posts.py`) on the campaign maps.

Spot checks against independent measurements: the valid-wall table rejects exactly the 56 walls that
rendered black in Mossford v0.1; outer boundaries are visible walls 98-99% of the time; every light
preset carries all 70 settings of a real ColorLight.

## Biomes

`py rules/biomes.py` and `py rules/biome_places.py` measure what sets Westwood's cave, ice and lava maps apart
(floors, walls, signature objects and where they stand, light, ambient, creatures). The findings and the way the kit
builds each biome are in `BIOMES.md`.

## Towns

`py rules/town_walls.py` sorts every wall of Westwood's town maps by what it bounds (the map's edge, islands of
forest and rock, buildings, gated yards, free-standing fences) and measures the islands and the yards. The findings,
the yards Westwood builds and how the kit plants a town are in `TOWNS.md`.
