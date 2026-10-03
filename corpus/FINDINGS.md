# What professional Nox maps look like (phase 1 findings)

From a visual review of all 62 distinct single-player layouts (whole-map renders, contact sheets
in `out\sheets\`) and measurements over the 54 distinct campaign layouts (`nox_corpus.db`,
near-duplicate class variants counted once).

## Composition

1. **Organic footprints.** Outdoor areas follow the terrain: their edges are irregular tree lines,
   cliffs and cave walls, never a large geometric shape. Everything outside is black void.
   (Mossford's diamond-shaped town wall reads as artificial.)
2. **Several zones per map.** A typical map combines a town or hub, wilderness paths, and caves or
   dungeons, joined by narrow passages, elevators or teleports. Building interiors and secret areas
   are often separate "islands" placed elsewhere on the 256x256 grid.
3. **Corridors, not fields.** Wilderness is mostly winding paths 6-15 cells wide, lined with dense
   trees, opening into clearings. Large open areas are rare.
4. **Towns are dense and compact.** Buildings sit close together and share walls, around a paved
   square or fountain; roads are cobbled; many towns are walled; gardens are fenced. Buildings vary
   in size and shape (L-shapes, multi-room, courtyards) and their interiors are subdivided rooms
   with distinct floors (rugs, tiles) and lots of furniture.
5. **Water is narrow.** Streams and rivers are 3-6 tiles wide, in ravines lined by trees; lakes have
   docks built from dock objects. Crossings are short square plank bridges or fords (Con05A).
6. **Dungeons** are grids of rooms and corridors on the diagonal axes; lava, ice and swamp appear as
   themed regions with their own floors and walls.

## Measurements (25th percentile / median / 75th percentile per map)

| Measure | Westwood campaign | Mossford v0.1 |
|---|---|---|
| Floor tiles | 4,523 / 6,234 / 8,173 | 5,184 |
| Objects (top level) | 852 / 1,414 / 1,757 | 903 |
| Objects per 100 tiles | 16.8 / 20.9 / 26.8 | 17.4 |
| Share of tiles with edge blends | 0.29 / 0.36 / 0.41 | 0.24 |
| Distinct floor materials | 10 / 14 / 20 | 10 |
| Distinct wall materials | 4 / 7 / 9 | 4 |
| Light sources per 100 tiles | 3.1 / 4.75 / 6.7 | **0.56** |

Lighting is the largest measurable gap: Westwood places roughly 8x more light sources (mostly
invisible `ColorLight` objects with tuned colour and radius, plus torches and candles).

## Defects found in Mossford v0.1 and their causes

| Defect | Cause | Rule to learn in phase 2 |
|---|---|---|
| Black wall sections | Wall variation chosen per material, but valid variations depend on facing (corners: usually only 0) | Use only (material, facing, variation) combinations that occur in the corpus |
| See-through hole in the boundary | Invisible bank walls overwrote boundary walls | Boundaries must be sight-blocking; invisible walls only inside |
| Abrupt bridges | Plank floor laid directly on a wide river | Narrow streams with short bridges or fords; bridge/dock kits; edge blending at both ends |

## Implications for phase 2 (rulebook)

- Mine valid wall combinations, material adjacency and edge styles, water/shore structure, bridge
  and dock assemblies, boundary construction, and lighting (ColorLight settings and density by area).
- Extract buildings and rooms as reusable pieces (walls, floors, doors, furniture, lights).
- Learn decoration density and placement per terrain, and how paths are lined with trees.
- Layout generation should produce organic footprints and multi-zone compositions, not geometric
  outlines.
