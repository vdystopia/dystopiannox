# Well

Kit: the catalogue's `well_side` (`kit/scenes.py`, laid by `kit/dressing.Exterior`; ROLE_SCENES "manor"). Lab:
`py tests/scenelab.py well`. Westwood's evidence: four campaign wells (Con02a, Con07B, Con09a, War07A), the same
place reused across the three campaigns' versions of a town.

## QA round 1 (2026-10-13): a feature, and the healing well [Q1X-4, Q1X-5, Q1X-6, Q1X-7]

**This section overrides the rounds below.** All ten of the lab's wells were rated 1: "This isn't so much a feature as
it is just a well ± a sign. Try to make the well a larger feature. Give it a small area of cobblestone beneath it. Add
more objects like buckets. Surround some wells by a fence or a gate. Make sure that when wells appear in maps, the
player can interact with them to fully heal health and mana, like in the original nox campaign." EX-WELL-05 had no well
at all: the dressing's `well_side` had found no room in its clearing, and the lab laid nothing.

- The well is the `WishingWell` everywhere (`kit/setpieces.healing_well`): Westwood's campaign well, a TRIGGER the
  player uses (Con02a's runs the script MakeAWish); the plain `Well` is a prop that does nothing. Each is named
  `HealWell<n>` (`setpieces.HEAL_PREFIX`) so the map's behaviour scripts can make it heal health and mana fully. The
  designs' square wells, the dressing's `well_side` and the well yard all lay it.
- A well yard (`kit/yards` kind `"well"`, `kit/setpieces._well`) is planned before the land is carved, so it is never
  dropped for want of room. The well stands on whole squares of grey cobbles (CobblestoneGrayLight, Westwood's on grass,
  blended BlendEdge; CobbleStone reads as bare earth). Nox has no bucket: the bucket of tools (BarrelWithTools) and
  water barrels stand for them. Archetypes: plain (5 x 5 squares of paving, water barrels either side, the bucket of
  tools and a barrel behind, a bench before it facing it, a torch pole at each corner); fenced (a low wooden fence and
  a gate centred on its side, lamps or torch poles flanking the gate, the same pieces round the well inside, barrels in
  a bigger yard's corners); market (7 x 7 paving, benches on its four sides facing it, street lamps at the corners,
  water barrels and the tool barrel on the diagonals). No sign (a sign needs its text; the big signs read badly, nox1).
- The dressing's `well_side` lays the healing well on 3 x 3 squares of the same paving (`Theme.pave`) with water
  barrels, the bucket of tools, a barrel and a bench or torch poles, mirrored.
- Checks: `exterior.well_heals` (a `Well` outdoors, or a WishingWell not named for the script), `exterior.well_feature`
  (no paving under it, or under two kinds of thing within 130 px), `exterior.set_symmetry`, `exterior.set_variety`.

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

## Archetypes (round 6, 2026-10-06)

Westwood's four campaign wells:

| Archetype | Westwood | What it is |
|---|---|---|
| well with its sign | 2 of 4 (Con02a, War07A) | the WishingWell alone by the street, a sign a little apart |
| bare well | 1 of 4 (Con09a) | the well alone |
| market well | 1 of 4 (Con07B) | the well among a trader's racks, a sign and a street lamp |

The kit (`scenes.THEMES["well_side"]`): three layouts, the well alone, the well with a Sign1 78 px off to one side, or 70
px off to the other. The lab sets it 3.5 squares from the hamlet's road. AUC 0.75 -> 0.75 (round6; four Westwood wells:
the classifier cannot move far).

## Round 8 (2026-10-06)

`well_side` in the screen's own frame (`Theme.screen`), the layouts in Westwood's frequencies: bare (Con09a); the sign
2, 56 px before the well (War07A, Con07B); the sign 35, 36 px (Con02a); the market well's sign and a street lamp
(StreetLampOrnate3 with its shadow) 190 px before it (Con07B; its trader's racks stand inside the shop, so not laid).
AUC 0.582 -> 0.142.
