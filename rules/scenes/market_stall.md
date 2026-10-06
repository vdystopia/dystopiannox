# Market stall

Kit: the catalogue's `market_stall` (`kit/scenes.py`, laid by `kit/dressing.Exterior`; ROLE_SCENES "store", "inn", by
a store or an inn within 12 squares). Lab: `py tests/scenelab.py market_stall`. Westwood's evidence: three campaign
stalls (Con02a, Con03A, Con09d).

## Purpose

A trader's pitch: a striped awning (TraderTent, purple and orange or green and red) on its poles, the stock set out
round it.

## What Westwood's hold

11-16 pieces, about six kinds, compact: barrels in a short row of three or four (Barrel2), a water barrel, an iron
crate (CrateSteel3), a pair of apple crates, a torch pole or two at the edges, a cart parked at the side (Con09d), an
armour rack (Con09d); a potion seller's cauldron, fairy jar and cushioned stool (Con03A). No tables of goods, signs or
heaps of baskets.

## Round 4 (2026-10-06): the stall lays

It had laid in none of the lab's ten clearings:
- every ware was a must, and they stood where the awning's cloths are: now the apple crates must stand (one or two,
  ~104 px before the awning's middle), the rest where they fit: two to four barrels in a row, the water barrel and an
  iron crate at the awning's ends, a torch pole behind (50%), a cart at the side (35%), an armour rack (15%), a sack;
- the dressing's cut test (`Exterior._lay`) read the open ground under the awning, between its sides, as a pocket the
  scene cut off: the ground under an awning now counts as blocked with it;
- the lab: the store at the clearing's side with its door toward the middle (the building's u runs along the squares'
  i), the market's square 6.5 squares before the door (a door keeps three squares clear), the hamlet's forest paths
  joining it at its edges, never through its middle (the dressing keeps a path's lane clear).

Laid in 8 of 10 clearings (r3-door). Then the stock as Westwood's stands (Con09d): the apple crates under the
awning's front (the dressing had kept every piece 60 px off the cloths; now 30 off a side, 10 off a top, nothing off a
pole), the barrels in a row behind under the back cloth, an iron crate at the front corner, a torch pole at one end
(60%) and the other (30%), the cart at the side (35%), an armour rack (15%), a sack (25%).
