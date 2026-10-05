# Storeroom

Family: stores. Feel: **full, in good order**. Kit kinds: `storeroom` (a house's, a manor's, a keep's stores),
`ore_store` (a mine's ore shed: carts of mana ore), `ogre_hoard` (the ogres' heap). Profile:
`kit/roomtypes.py TYPES["storeroom"]`.

## Purpose and feel

Supplies kept in good order: the fullest room of a building, but tidy, with an aisle to walk. Clusters (heaps in the
corners) and spaced pieces, not an even spread.

## Focal point

None: the stocked walls themselves. An ore store's loaded carts.

## Pieces

- Must: stores (4+: barrels, sacks, crates, piled barrels, tool barrels).
- May: stocked log shelves end to end, a row of racks (hunting gear) with aisles, a stack in the middle; an ore store's
  carts and trader's shelves of tools and helmets.
- Never: bookcases, beds, desks, tables, chairs, an altar, a throne, tombs, lab pieces, bars, counters, hearths,
  stoves, statues, black-powder barrels in a dwelling.

## Composition

- **A back wall:** stocked log shelves end to end.
- **The other back wall:** crates side by side.
- **Front walls and corners:** heaps of barrels and sacks.
- **The middle:** clear, or one row of racks (at most 5 to a row, 1.2 apart, aisles of 2.2), or a stack.

## Density and openness

| | Westwood (28) | Profile |
|---|---|---|
| coverage | 0.02-0.13-0.19 | 0.15-0.42 (target 0.30) |
| open floor | 0.32-0.67-0.91 | 0.15-0.65 |
| pieces per tile | 0.06-0.31-0.50 | 0.30-1.1 |
| distinct types | 2-3-5 | 4+ |
| caps | | racks 1 per 10 tiles, at most 6 (an ore store 1 per 8, at most 12) |

The user wants stores fuller than Westwood's ("a store room holds more than any other room", TreePlace reviews).

## Size

15-90 tiles.

## Culture variants

- `ore_store`: mana and ore carts with room to move them, racks of mining gear, dark crates.
- `ogre_hoard`: barrels, sacks and crates heaped along the walls, carcasses hung to cure, bones about; torch poles.

## Common mistakes

- A mill's grain store with a row of axe racks down its middle (Harrowby): the `granary` kind (a storeroom of sacks,
  barrels, crates and provisions shelves, heaps in the corners, never racks) for a mill or a farm.

- "Storeroom: almost empty; a bookshelf, a crate, an explosive barrel and a barrel scattered at random" (TreePlace).
- "Bunkhouse storeroom: too evenly spaced; balance clusters and spaced objects" (TreePlace).
- "Storeroom racks a little too dense and numerous: spread out, fewer" (2026-10-04 review).
- Nothing lines a wall corner to corner but a store, and even a store keeps its aisle.

## Examples

- Westwood: Con05C, cell 154,100 (42 tiles, coverage 0.17); Con06a, cell 153,212 (36 tiles, 0.19).
- Ours: Starwell seed 4, room 20, iron and coal (25 tiles, coverage 0.22).
