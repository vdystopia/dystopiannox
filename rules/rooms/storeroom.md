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

The room lab (2026-10-05, review/roomlab/LOG_tuneC.md) read Westwood's 22 campaign storerooms again: no shelves and no
racks in any of them; 1-5 types (median 3), the commonest kind over half the pieces (barrels in 17); stores against two
walls (p90 three), the rest bare. The recipe follows them (`slot="heaps"`, kit/furnish.py `store_heaps`):

- **A palette:** one lead kind (barrels mostly; a granary's sacks in three sizes; an ore store's crates), a second kind,
  sometimes one odd piece (a piled barrel, a great cask, a water barrel). One stem of crate, one or two types of barrel.
- **The home corner:** the lead kind heaped two deep in a corner clear of the doors, on walls Westwood stands it against
  (barrels: the back walls, 77% of Westwood's), sometimes spilling round the corner.
- **Along the same walls:** the second kind side by side toward the far end of the long wall, stopping short of the far
  corner so the other walls stay bare.
- **The middle:** a stack of crates standing free, or a knot of three or four barrels (Con06a, Con05C); never one alone.
- **More**, while under the target: heaps on the free stretch furthest from the stores so far (the room must not read
  as bunched), 1.6 units apart; a third wall only to balance the room.
- **Lights:** three a hundred tiles (one candelabra in a store of 40 tiles).


## Archetypes

Westwood's 7 curated campaign storeroom rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| corner heaps | 57% | Con01A@95,121, Con02a@58,154, Con06a@12,149, War03d@88,216 | a small store: a heap of barrels in one corner, a crate or an apple crate by another wall, the middle an aisle (recipe engine: the kind's own recipe) |
| shelved store | 14% | Con05A@52,18 | shelves of stores on both back walls, water barrels free before them (recipe engine: the kind's own recipe) |
| hall of stock | 29% | Con03B@203,115, Con07B@121,219 | a big store: crates and casks heaped free over the floor in knots, a desk, odd things put away (statues, telescopes, bookcases) (recipe engine: the kind's own recipe) |

## Density and openness

| | Westwood's campaign (22 rooms, 17 maps) | Profile |
|---|---|---|
| coverage | 0.02-0.07-0.19 | 0.06-0.26 (target 0.13) |
| open floor | 0.32-0.75-0.91 | 0.30-0.92 |
| pieces per tile | 0.06-0.25-0.44 | 0.10-0.8 |
| distinct types | 1-3-5 | 2+ |
| walls with a purpose | 1-2-3 | 2+ |

The user wants stores fuller than Westwood's ("a store room holds more than any other room", TreePlace reviews): the
target sits at Westwood's p75, the limit past its p90. The old target (0.30, shelves and racks to reach it) made the
stores read as generated at once (the lab's AUC 0.96).

## Size

15-90 tiles.

## Culture variants

- `ore_store`: mana and ore carts with room to move them, racks of mining gear, dark crates.
- `ogre_hoard`: barrels, sacks and crates heaped along the walls, carcasses hung to cure, bones about; torch poles.

## Where people stand

The storekeeper by his shelves, else at a back wall clear of the stock; never in the aisle. (`STANDS["storeroom"]`: beside the log shelves, a back wall.)

## Common mistakes

- A mill's grain store with a row of axe racks down its middle (Harrowby): the `granary` kind (a storeroom of sacks,
  barrels, crates and provisions shelves, heaps in the corners, never racks) for a mill or a farm.

- "Storeroom: almost empty; a bookshelf, a crate, an explosive barrel and a barrel scattered at random" (TreePlace).
- "Bunkhouse storeroom: too evenly spaced; balance clusters and spaced objects" (TreePlace).
- "Storeroom racks a little too dense and numerous: spread out, fewer" (2026-10-04 review).
- Nothing lines a wall corner to corner but a store, and even a store keeps its aisle.
- Harrowby playtest (2026-10-05, HB-5): "The entire northwest wall is lined with countless duplicates of that one object ... some objects are suitable for lining an entire wall, and some are not." Log shelves stand alone or in pairs (Westwood: 112 of 122 alone, never more than 2 side by side), at most two to a wall (kit/objects.py max_run, wall_cap; checker `pieces.run`).
- Harrowby playtest (HB-1): supplies spread one by one down a whole wall. They stand in clusters of 1-5 of mixed kinds (sacks of three sizes, then a barrel, then a crate), 1-4 units of bare wall between clusters (Westwood's p25-p75 gaps), never more than 3 of one kind on a wall (Furnisher._cluster, _cluster_gap).

## Examples

- Westwood: Con05C, cell 154,100 (42 tiles, coverage 0.17); Con06a, cell 153,212 (36 tiles, 0.19).
- Ours: Starwell seed 4, room 20, iron and coal (25 tiles, coverage 0.22).

## Learned in the room lab (2026-10-05)

- Westwood's storerooms are sparse and few-kinded; what makes them read real is a heap of one kind in a corner and
  a stack or a knot standing free, not a stocked wall. Every wall stocked with a cluster of every kind was the first
  thing that gave ours away (AUC 0.96 -> 0.72 with the heaps).
- Barrels and crates have walls: `orient()` refuses a type on a wall Westwood seldom stands it against (Barrel on the
  SE and SW walls), so a heap's home corner is chosen where its kind may stand.
- A store heaped in one corner trips the checker's furniture offset: the fill goes where the stores are thinnest.
- What still gives them away: rows along a wall align more than Westwood's (0.71 against 0.45), three walls used
  against two, and above all the shell (Westwood's stores are alcoves, cell blocks and caves).

## What passed the blind test (2026-10-06, the independent judge of r16: 5/10, chance; generated 5.2, Westwood 5.8)

The storeroom was the first type the independent judge could not tell from Westwood's. What made it work:
- **touching clumps, not rows**: each heap grows by touching a piece already in it at a random bearing, within three
  units of its wall, its pieces 0.25-0.65 apart (Westwood's nearest gaps 0.4-0.6);
- **mixed kinds in one heap**: a lead kind, a second and an odd piece, a piece in two of the room's other kinds;
  sacks in their three sizes; the odd kind twice a room at most;
- **few kinds, two walls**: 3-5 types, the stores against the home walls, a third only to balance the room;
- **nothing alone**: no single barrel mid-floor, a stack of crates standing free only near the heaps;
- **no lights in the store** (Westwood's have none inside), the house's candelabras left out;
- **fuller than the old target**: cover 0.17 (the curated median 0.16).
The judge's remaining tells: single crates at even gaps along a front wall; crates in regular pairs and a 2x3 block of
kegs mid-floor; great casks side by side along a wall; an ore store's racks crowding a door.

