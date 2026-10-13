# Cellar

Family: stores. Feel: **full, in rows**. Kit kind: `cellar` (an inn's or a manor's keg cellar, a keep's buttery).
Profile: `kit/roomtypes.py TYPES["cellar"]`.

## Purpose and feel

Kegs and casks: the ale, wine and water of a house. Unlike a storeroom (provisions on shelves, crates and sacks heaped),
a cellar holds one kind of thing in rows, with a great cask or two standing free and aisles to roll a keg to the door.

## Focal point

The great cask (LargeBarrel1 or 2) standing free with kegs beside it.

## Pieces

- Must: kegs (6+): Barrel, Barrel2, piled barrels.
- May: a great cask or two, a few crates.
- Never: shelves, tables, chairs, sacks, apple crates, beds, racks, hearths, stoves, statues, black powder.

## Composition

- **Back walls:** kegs in tight rows along the walls from the corners.
- **Front walls:** kegs and piled barrels; a few crates by the door.
- **The middle:** a great cask with kegs beside it, a second in a big cellar; aisles all round.
- **Movement:** from the door down the aisles to every row.

## Density and openness

| | Westwood's campaign (4 rooms, 4 maps) | Profile |
|---|---|---|
| coverage | 0.06-0.19-0.23 | 0.12-0.42 (target 0.22) |
| open floor | 0.34-0.75-0.75 | 0.15-0.70 |
| pieces per tile | 0.20-0.36-0.59 | 0.30-1.20 |
| distinct types | 1-3-5 | 3+ |

## Size

12-80 tiles (Westwood's: 17-36).

## Culture variants

Dun Mir's (Con06b): kegs only, under the keep.

## Where people stand

The cellarer beside the great cask; else at a back wall clear of the rows. Never in an aisle or at the door.
(`STANDS["cellar"]`: beside a great cask, a back wall.)

## Common mistakes

- Five great casks in 63 tiles (the first lab version): one cask, a second only in a cellar of 40 tiles or more.
- Shelves of provisions or sacks: that is a storeroom.

## Examples

- Westwood: Con07B, cell 132,196 (17 tiles: eight kegs, two crates); Con06b, cell 56,62 and War02b, cell 194,194 (25
  tiles: five kegs); Con06a / War01A, cell 153,212 (36 tiles: seven barrels, a great cask, piled barrels, crates).
- Ours: the room lab's cellars.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's 4 curated cellars (Con06a, Con06b, Con07B, War02b) hold barrels in knots, a few dark crates, a piled
  barrel or a great cask; 1-4 types; some barrels free of the walls; coverage 0.06-0.23; no lights inside. The recipe
  heaps them as a store's (`slot="heaps"`, kit/furnish.py `store_heaps`): barrels lead, crates second in 40% of
  cellars (the type's reading wants kegs at 70% of the stores), a piled barrel or a cask as the odd piece; no
  centrepiece cask (one cellar in four has one).

## QA round 1 (2026-10-13; review/qa1/rooms.md Q1R-13)

"Many of these include only barrels. Improve the diversity. Add metal barrels and tools. Use crates more often alongside
the barrels." Rated 2-4 (mean 2.5); RM-CELLAR-01 "the gigantic wine barrels are way too close to each other and to the
other barrels"; -08 "the diversity of objects is better ... two variants of wood barrel, giant wine barrel, and crates.
It just needs to be organized a little bit better. The giant wine barrel needs more space".

This overrides Westwood's 1-4 kinds: the user's word over Westwood's habit.
- **The great casks** centred on the longest back wall, two from 45 tiles set symmetrically about its middle, 1.1 units
  clear of every other piece as the game draws them (a cask's picture is about twice its footprint: `CASK_DRAWN`).
- **Organised groups:** rows along the walls from the corners, each a group: wooden kegs and a piled barrel; metal
  barrels with a barrel of tools; crates with kegs; tools with kegs and a metal barrel; steel crates in a big cellar;
  the middle an aisle. One kind never more than three side by side (HB-5). The recipe's types take metal barrels,
  barrels of tools and steel crates.
- Checked: `rooms.qa1_cellar_kinds`, `rooms.qa1_cask_space` (planted STq1Clr, STq1Csk).
