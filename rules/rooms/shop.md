# Shop

Family: public. Feel: **balanced**: goods on show, open floor before the counter. Kit kind: `shop` (a general store, an
apothecary's, an armourer's). Profile: `kit/roomtypes.py TYPES["shop"]`.

## Purpose and feel

A trader sells over a counter. The customer comes in, sees the goods on the walls and the racks, and walks up to the
keeper.

## Focal point

The counter, set out from a back wall, with the keeper's spot behind it (`counter`; `StoryMap.shops` stands the keeper
there).

## Pieces

- Must: the counter; racks or trader's shelves (2+).
- May: trader's shelves of goods lining the back walls, racks for show three to a row (a row of each kind), crates of
  stock, potion shelves (an apothecary's, once as a pair), a chair, plants.
- Never: beds, desks, an altar, a throne, tombs, a bar, stoves, forges, black-powder barrels.

## Composition

- **A back wall:** the counter set out from it, the keeper's spot behind.
- **The other back wall:** trader's shelves of goods end to end.
- **Front walls:** crates of stock.
- **The middle:** racks for show, three to a row, each row its own kind; the floor before the counter open.
- **Movement:** from the door straight to the counter.


## Archetypes

Westwood's 8 curated campaign shop rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| lined walls | 50% | Con02a@113,142, Con09b@184,92, War07A@109,167, Con07B@106,208 | goods lining the back walls (potion shelves, bookcases, trader's shelves), the keeper's desk on a wall or a little out from it, a cauldron or a stove in a corner, the floor open |
| stock heaps | 25% | Con03A@14,198, Con03B@238,74 | a general store: steel crates and barrels heaped along both long walls, the keeper's desk with its chair at the far end; the middle an aisle |
| showroom | 25% | Con06a@142,205, War07A@132,174 | an armourer's showroom: racks hung along the walls and standing free over the floor in loose rows, the keeper's desk standing free among them |

## Density and openness

| | Westwood's campaign (16 rooms, 11 maps) | Profile |
|---|---|---|
| coverage | 0.06-0.13-0.28 | 0.12-0.40 (target 0.24) |
| open floor | 0.34-0.62-0.68 | 0.30-0.75 |
| pieces per tile | 0.14-0.21-0.44 | 0.20-0.80 |
| distinct types | 5-7-16 | 9+ |

## Size

30-140 tiles.

## Culture variants

Dun Mir's shops (7 of Westwood's 25) keep hearths and benches for customers.

## Where people stand

The keeper behind his counter, on the spot the furnisher keeps clear there (Furnisher.spots, StoryMap.shops); a second person beside the counter on the customer's side. Never among the racks. (`STANDS["shop"]`: the keeper's spot, beside the counter.)

## Common mistakes

- "The shopkeeper is standing in the middle of the shop, surrounded by a random scattering of objects ... He needs to be
  standing somewhere that makes sense, like behind a desk. Instead of six armor racks, use three armor racks and three
  weapon racks." (Starwell, 2026-10-05)

## Examples

- Westwood: Con02a / Con08a, cell 86,105 (125 tiles, 33-34 types); Con07E, cell 173,104 (154 tiles, 24 types).
- Ours: Starwell seed 4, room 17, the shop floor (81 tiles, 13 types).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Each of Westwood's 16 campaign shops keeps one trade, so ours do (`ROOMS["shop"]["trades"]`): an armourer's (racks
  three to a row, a row of armour stands and a row of pole arms; trader's shelves; swords and shields hung; steel
  crates), an apothecary's (a pair of potion shelves, bookcases, glowing jars, no racks) or a general store (steel
  crates and barrels, trader's shelves, no racks). No plants (Westwood's shops have none). Mixing every trade in every
  shop was the first giveaway (AUC 0.91 -> 0.86).
- Still a giveaway: everything in rows and the stock packed tight; Westwood's shops leave more floor between pieces.
- The independent judge (r4, r8): runs of three at even gaps and grids of racks read as generated ("three armour racks
  and three weapon racks" means variety, not three-and-three grids); a counter stranded in a corner; pieces of other
  rooms (a cauldron, potion shelves by the door, barrels in runs). r9-r11: the counter the room's one strong idea, the
  goods end to end on the other back wall, standing racks two or three against the walls, the stock in heaps as a
  store's, no hangings of décor.

