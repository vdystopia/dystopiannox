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

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.shop`); ledger `review/qa1/civic.md` (Q1A-n).
These rules come before Westwood's statistics above wherever they disagree (the user's word over Westwood's habit).

Every room of the type:
- **The dead space is used** (Q1A-1, Q1A-7): the S corner takes a group of its own; the front corners and the SE and
  SW walls take mixed stock, benches or urns, mirrored; where the floor is still bare a group goes there, bigger rooms
  more. Checked: `civic.s_corner`.
- **Diversity** (Q1A-2): several kinds of piece, more in a bigger room; heaps mix their kinds (never one family alone,
  never the same piece side by side). Checked: `civic.kinds`.
- **The back walls dressed** (Q1A-3): the NE and NW walls hung at even steps, mirrored about each stretch, one
  tapestry colour to a room; a bare stretch takes a pair of the type's wall piece. Checked: `civic.bare_wall`.
- **Balance** (Q1A-4, Q1A-13): pieces centred on their wall or between a piece and a wall; mirrored pairs; one kind of
  table, column, statue to a room; lights in matching corners or flanking the focal piece.
- **Carpets** (Q1A-10): a table set at its carpet's exact middle; a carpet only where its whole rectangle and trim
  lie on the room's floor.

For this type:
- One trade to a shop (armourer, apothecary, general store), drawn per room.
- The counter out from a back wall, facing the way in; the keeper's space behind it and his spot there (Q1A-6, nox18);
  his goods mirrored either side of him on that wall (trader's shelves or potion shelves), lights flanking the counter.
- The other back wall lined with the trade's goods (potion shelves and bookcases, racks in an even row, trader's
  shelves).
- The walk from the door to the counter lined with a mirrored display of the trade (armour racks and pole arms, glowing
  jars and apple crates, steel crates and barrels) in a shop of 60 tiles or more.
- Stock heaped in the S corner and the front corners and mirrored on the front walls, each heap of mixed kinds (nox8:
  never a shop of barrels alone). The walls hung with the trade (shields and crossed arms, paintings, trophies).

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2C-7)

The user, the whole set: "These are very poor and need a lot of improvement. Consider the path from the door to the
shopkeeper's desk. Don't block it with objects. Treat the shop less like a chapel and more like an armory." RM-SHOP-01:
"Cluttered mess. Way too many objects in the middle of the floor. No path ... from the door to the shopkeeper's desk";
-02: "too heavily concentrated in the south. Meanwhile, the north is very empty"; -03: "Awful scattered mess ... the
random barrels, crates, and sacks need to be changed"; -05: "No path from the door to the shopkeeper's desk". Round 2's refinements (PROCESS.md top section) apply too: centred on the room, facing designed, pieces never touching, storage against the wall, floors ending at a hard line, fullness from kinds. Composed by `kit/civic.py`; ledger `review/qa2/ledger.md`.

Composed as the armoury (rated 4.8): no axis, no display down the walk (the chapel look), nothing loose mid-floor.
- **The counter** out from a back wall on a stretch long enough for the keeper's goods either side of him, across from
  the main door where it can be (`civic.shop_counter`), his goods mirrored against its wall (`flank_goods`), lights
  flanking it.
- **The walk** from the door to the customer's side of the counter (in from the doorway, then along) kept clear
  (`civic.shop_walk`). Checked: `qa2.shop_way`.
- **The walls:** the other back wall lined with the trade's goods; the front walls lined with the trade's wares in rows
  against them (`civic.wall_stock`: racks for an armourer, crates, barrels and apples for a store, apples and sacks for
  an apothecary); stock heaped against the walls in the corners; a kind of stock the shop lacks against any bare
  stretch; the back walls hung with the trade.
- **Wares on show** in rows standing free, each row one kind, mirrored about the room's middle line, clear of the walk
  (`civic.display_rows`).

## QA round 3 (2026-10-23; review/qa3/ledger-civic.md Q3N-2)

The user: "The shop is simply too big, and there's not enough stuff to fill it. Make it smaller. Improve the object
diversity. Add a few rows of something other than lamps and apple crates" (RM-SHOP-03, a large square shop of 168
tiles; 01, 02, 04, 05, of 54-78 tiles, 5 of 5).

- **A shop is a small room:** 50-110 tiles (Westwood's shops are under 100); a large shell is given to a store room or
  split, never furnished as one shop with its middle empty.
- **Rows of more than one kind:** the wares standing free come in rows of different kinds (racks of clothes or arms,
  barrels, sacks, crates, shelves of goods), one kind to a row, never lamps or apple crates in every row; a big shop
  takes more kinds, not more of the same.
- Rule written; not re-rendered (a single note).
