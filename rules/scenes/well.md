# Well

Kit: the catalogue's `well_side` (`kit/scenes.py`, laid by `kit/dressing.Exterior`; ROLE_SCENES "manor"). Lab:
`py tests/scenelab.py well`. Westwood's evidence: four campaign wells (Con02a, Con07B, Con09a, War07A), the same
place reused across the three campaigns' versions of a town.

## What Westwood uses

**Westwood's well is the `WishingWell`** (the round stone wishing well), in every one of its campaign wells. The kit
lays `Well`. The user has not chosen whether to switch the landmark, so the kit keeps `Well` for now; switching is one
word in `well_side` (and the lab's signature already finds both).

## Purpose

The well where water is fetched: a public landmark in a town square, a castle court or a village, clear on every side
so it can be walked up to.

## Must, may, never

- Must: the well, on open ground near a road, a short way off it.
- May: a sign a little apart (Westwood: Sign1, SignIx08; the kit lays none: a sign needs its text); a trader's pitch
  as a neighbour (Con07B), never round the well itself.
- Never: barrels, buckets, benches, troughs or water carts beside it (none of Westwood's four has any).

## Round 4 (2026-10-06)

- `well_side` is the well alone (it had laid a water barrel, barrels, a bench and sacks round it), with 60 px kept
  clear round it (`Theme.clear`).

## Round 5 (2026-10-06)

The judge (the closest of three: "the restraint is right"): "no road, square or signpost; placed by geometry". The lab
sets the well 3.5 squares in from the hamlet's road. Still to do: a signpost a little apart (Westwood's Sign1, SignIx08)
needs a string-table text (kit/camps.signpost).
