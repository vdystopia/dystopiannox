# Vegetable garden

Kit: `kit/village.py Village.garden` (a household's garden beside its house); the town's field is `kit/yards.py`
"field". Lab: `py tests/scenelab.py garden`. Westwood's evidence: 5 campaign gardens (Con05A, Con07B, Con09a, Wiz01A,
Wiz03b).

## QA round 2 (2026-10-14): a garden that cannot be laid is an error [Q2X-5, Q2T-7]

EX-GARDEN-01: "Absolutely perfect." EX-GARDEN-02: "There is no garden." The cottage of the small road clearing had two
neighbours built over the strip beside it, the garden found no site at its sizes and laid nothing, and the scene lab
rendered the empty clearing.

- `Village.garden` tries the least garden its rule allows (5 x 3, either way round) after every larger one; it had never
  been tried. `garden(..., dry=True)` returns the site a garden would take without laying it.
- The scene lab keeps a garden's site from its own clearing's neighbours where nothing but the least garden fits
  (`recipes._garden_plan`), so the gardens of round 2 that fitted are laid where they were.
- A variant with none of its scene's pieces gets no picture and fails the lab run (`tests/scenelab.missing_error`);
  `review/qa/package.py` refuses to package it; a declared yard with none of its own pieces is the checker's error
  `exterior.set_empty`.
- The ground inside a garden's fence is its plot's squares, flush with the fence (`yards.yard_ground`, `TILE_DJ`).

## QA round 1 (2026-10-13): dirt, fences, even rows [Q1X-13 .. Q1X-16]

**This section overrides the rounds below wherever they differ** (beds on grass, hand-planted rows, most gardens
unfenced). The user: "Plants in gardens should generally grow on dirt, not grass ... use garden fences more often. Use a
wider variety of objects as well. A barrel of tools a wheelbarrow etc. space rows of crops out and make them even and
balanced"; EX-GARDEN-03 "Use fewer plants per row and space them out a little bit more, and keep them even"; EX-GARDEN-05
and 06: "The garden being directly next to one of the walls of the structure ... This is an excellent orientation". And
of nox2's garden (Brackwater's field, `kit/yards` "field"): "more or less perfect": a low wooden fence and its gate
round dark earth, straight parallel rows.

What nox2's garden did that the lab's gardens did not: its whole ground inside the fence is dug earth; it is fenced, with
a gate; its rows are straight, parallel and evenly spread across the plot (`_spread`), with no hand jitter, no cut beds,
no failed plants. Both now follow it:
- `Village.garden` (a household's) and the field lay the same rows (`kit/yards.lay_crop_rows`) in a `Frame` from the
  way in: the rows run away from the gate, a walk up the middle of a wide plot, a row and its mirror of one crop, the
  plants 0.7 squares (23 px) apart, the rows 1.1-1.15 squares apart; the water barrel and the bucket of tools either side
  of the way in.
- The whole plot is dug earth (DirtDark2, `yards.yard_ground`, to the fence on every side); three gardens in four are
  fenced (DilapidatedShort, Westwood's low wooden fence) with a gate centred on the side toward the house's door, never
  the side against its wall; the plot keeps a side of odd length for it. The garden still stands beside its house, a
  square off its wall (05, 06).
- The household round it: an apple tree (TreeApple) with apples fallen under it (RedApple, which the player picks up) in
  seven of ten.
- Nox has no wheelbarrow; the cart (OutdoorTraderCart) is too big for a garden.
- Checks: `exterior.crop_ground` (over 30% of a garden's crops on grass), `exterior.crop_rows` (85% in straight rows of
  three, the gaps along a row even within 25%).

## Purpose

The household's kitchen garden: vegetables grown beside the house, tended, watered.

## Anchor

The beds, on the side of the house away from its door.

## Zones

- **Beds**: two or three side by side, a different crop in each (GardenCorn, GardenTomatos, GardenCabbage), two rows to
  a bed (one when the plot is narrow), plants ~20 px apart along the row; on grass, or dug earth (40%).
- **The walk**: a strip of grass between the beds.
- **Its things**: the water barrel at a path's end (70%), a spade in the ground at the other (40%), flowers at a bed's
  end (40%).
- **Fence**: most gardens unfenced; a few (30%, 5 x 4 or more) behind Westwood's low lattice fence (DilapidatedShort,
  Wiz03b's) with a gap.

## Must, may, never

- Must: crops in rows, every plant clear of any fence line (AM-1: rows in the fence's frame, gj - 1.5..gj + h - 1.5).
- May: dug earth, the barrel, the spade, flowers, the wooden fence.
- Never: one crop packed in an iron cage; a Log fence (it draws as a cabin wall); crops under a fence; food on the
  ground (apples can be picked up).

## Spacing (Westwood against the kit, r3)

| | Westwood (median, p10-p90) | Kit now |
|---|---|---|
| kinds | 4 (2-5) | 2-4 |
| commonest kind's share | 0.41 | ~0.5 |
| nearest-piece gap | 22 px | ~20 |
| near a built wall | 0.09 | low (most unfenced) |

## Variance

The size (the design's, a size up first where it fits, down to 3 x 2 where it does not), which crops, the bed count,
dug or grass, the barrel and spade, flowers, the fence.

## Mistakes (the user's words)

- "The northeast stretch of fence overlaps with the row of crops... It should be pretty obvious that this fence is
  literally on top of this row of plants." (AM-1)
- The lab's own: a first rewrite laid the rows in the squares' frame and put one on the fence line again (the half-square
  offset); the Log fence drew as a pen's walls.

## Round 2 (2026-10-05)

- Each size is tried with two squares of open land round the beds first (no crop against the wood's edge, the tree
  line or a pond), then with one (the planting then keeps two squares off); the two largest sizes before any smaller.
- The fence is Westwood's low lattice (DilapidatedShort, Wiz03b), 30%, and only round a garden of 5 x 4 or more (a
  smaller pen loses its rows to the fence). The town field: the same fence, two or three crops in bands, never Log.
- The water barrel 85% (beside a narrow bed's end too), the spade 50%, a crate, barrel or sack mid-way along a long
  side 35%; no flowers past the beds' ends (a townsman's walk stops there).
- The garden draws from its own generator, never the design's.

## What still gives it away

Size: Westwood's gardens are bigger and come with the household round them (a well, flowers, an apple tree, barrels).

## Round 3 (2026-10-06, the town setting)

- Sizes tried: two up (w + 2, h + 1), one up, the asked size, then smaller; the barrel and spade set down a little off
  the beds' exact ends.

## Round 4 (2026-10-06, the household round it)

The independent judge on r6-town (10/10, 5.4 / 7.8): "the same small stamp: two or three even beds with a water barrel
at a row end; dropped on open grass near a log cabin with no clear owning house; a corn bed starting at the cabin's
corner; a sack leaning on a cabin corner; nothing of the household round them, where Westwood's have wells, apple
trees, crates of apples, fences, paths and loose planting". Westwood's (corpus, 420 px round each): Con05A apple trees
(TreeForest11, TreeForest12), five crates of apples, six water barrels; Wiz01A bushes and plants round its beds (Plant4,
Plant5, Bush6); Con09a a WishingWell and a crate of apples.

- **Centred on a side of its house** first (`_garden_at`: the four mid-side spots before the corner-aligned ones).
- **The planting's density varies**: 0.52-0.62 squares between plants along a row, garden to garden.
- **The household** (`Village._household`, the garden's own generator): an apple tree or two at the end of the beds away
  from the house with a crate of apples under one (50%); a loose hedge of bushes along the far long side (40%); a
  second water barrel by the beds (40%); never within a square of the house or two of a door.
- The side goods (a crate, barrel or sack) on the long side away from the house.
- **The lab**: gardens asked a size larger (4 x 3, 5 x 4, 6 x 5: Westwood's run 6-9 squares); a gardener standing at
  the beds' end (60%; renders leave people out since the fairness fixes).

## Round 5 (2026-10-06)

The judge: "crop bands equal in length and ruler-straight; crops right under the fence; barrels, apple crates, a sack
and a spade each alone round the beds instead of a knot at one corner (Westwood's gardens have no tools)". Each bed's
ends 0-0.7 squares in (uneven bands); crops 12 px off a fence; no spade; the household's goods (a barrel, crates of
apples, a sack) in one knot by the water barrel, each at Westwood's gap (kit/spacing).
The garden now sits a square from its house's wall, centred on a side (Con07B's beds lie along their house).

## Archetypes (round 6, 2026-10-06)

Westwood's five campaign gardens:

| Archetype | Westwood | What it is |
|---|---|---|
| household plot | 2 of 5 (Con09a, Wiz03b) | two or three beds beside the house or along a fence, a water barrel, a stump chest |
| walled kitchen garden | 2 of 5 (Con07B, Wiz01A) | long rows of three crops against a town wall or a building, a torch pole |
| town allotment | 1 of 5 (Con05A) | many beds edged with brick, water barrels, apple crates, barrels, rocks |

Every one grows **corn and tomatoes**; cabbage in three of five. The kit (`Village.garden`): the beds' crops are corn and
tomatoes in every garden (shuffled), cabbage the third bed 60% (else corn or tomatoes again), from the garden's own
generator (`garden-crops`), so the household round it is laid as before. The household's knot (`_household`) now keeps to
open ground (a knot's apple crate had stood on a house's floor in Starwell). The kit lays the household plot (beside its
house, a square from its wall) and the field yard (`yards` field, Greywatch's kitchen garden); not yet the walled
kitchen garden or the allotment.

AUC: 0.254 -> 0.254 (round6; already under the stop line).
