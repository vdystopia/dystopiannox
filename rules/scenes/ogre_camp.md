# Ogre camp

Kit: `kit/camps.py ogre_camp` (PROCESS.md section 5), people by `kit/posts.py camp_posts`. Lab:
`py tests/scenelab.py ogre_camp`. Westwood's evidence: five campaign ogre fires (Con05B x3, Con09b, Wiz02C), each
found from its fire pit: read loosely.

## What Westwood's are

A fire pit (OgreFirePit, lit or not) in a pocket of the swamp's root walls (RootLight; Con09b's huts of OgreWall) on
swamp ground: meat on the pit's side and a carcass, a log bench or two and stools round it, bones dropped close about
it (40-75 px), two or three barrels or sacks, a torch pole or two, rocks and short rock pillars at the walls; 5-30
pieces, median 13. The ogres sleep in their huts (OgreBed, bearskins, straw inside); no straw row by the fire.

## The kit (round 4, 2026-10-06)

- Bones four to seven, 40-75 px round the pit (they had lain 100-130 out).
- Straw bedding by the fire only now and then (half the camps a heap or two, else none).
- The stock two to four in its row; the big carcass 50%; the warlord's bearskin out by the fire 30%.
- The tusk gate (palisade wings and skull posts) in 40% of camps.
- Lab: every ogre camp in a pocket of RootLight on dirt (1.7 times the hideout's size).

## What still gives it away

Five Westwood scenes: the classifier separates everything (AUC 1.0) on where the fire lies (Westwood's by a path) and
the open ground; by eye the swamp pocket, the pit and its benches read as Con05B's.

## Round 5 (2026-10-06)

The judge: "one fire layout stamped every time; the torch pole a step from the fire ring or alone; the bearskin behind
a bench; a chest (Westwood's ogre camps never have one)". The meat one of four sets; one to three seats from six places,
each turned a little; bones none in two camps of five, else two to six mostly to one side; no bearskin by the fire; the
chest 25%; without the gate the torch pole stands by the store at the camp's edge.

## Archetypes (round 6, 2026-10-06)

Westwood's five ogre fires (`kit/camps.py` `OGRE_ARCH`, `ogre_arch`, `ogre_camp(..., arch=)`):

| Archetype | Westwood | What it is | The kit |
|---|---|---|---|
| hut yard | 3 of 5 (Con05B x2, Con09b) | the fire before the huts: two meat racks (OgreHutMeat) and a carcass on the cook's side, a log bench or two, the take in sack chests by the fire, the warlord's bearskin bed (OgreBed, OgreBearskin) at the back, a torch, a tusk mound at the yard's edge | `hut_yard`: two racks and a carcass 50%; one to three seats; one or two sack chests (the loot in the first); one or two OgreBeds with the bearskin before them 130-190 px back; a torch (OgreTorchUnlit or TorchPole); the tusk gate 40%, else a lone tusk mound 50% |
| bone pit | 1 of 5 (Con05B's swamp hollow) | the fire ringed by a mess of bones (a dozen arm and leg bones and skulls), the meat and carcass, two stools, barrels, a big sack chest, boulders and rock pillars round the rim | `bone_pit`: nine to thirteen bones in two drifts 58-120 px out, two stools, two barrels, SackChestLarge2, two or three boulders, two to four pillars, small rocks |
| cave fire | 1 of 5 (Wiz02C) | the fire in a cave, two log benches, a knot of barrels and water barrels, torch poles round the walls, rock pillars | `cave_fire`: two benches, three barrels and two water barrels in one knot, two or three torch poles, two pillars |

Never a chest (the take is in sack chests, Con05B). **Sites.** Westwood's fires lie on their paths through swamp grass
(Con05B, Con09b) or in a cave (Wiz02C). The lab: every camp in a RootLight pocket now floored with SwampGrass (blended),
the trodden path in from the mouth to the fire (DirtLight2). The batch: six hut yards, two bone pits, two cave fires
(`recipes.OGRE_ORDER`).

AUC: 0.997 -> 0.854 (round6).

## Structures (round 8, 2026-10-06)

`kit/camps.OGRE_ARCH`: cage_yard (Con05B: meat, carcass, meat in a row 17-19 px apart ~70 px off the fire, two sack
chests side by side, an unlit torch and a tusk mound against the wall, a barren plant), cold_pit (Con05B: an unlit pit,
two racks touching, one bench), hut_camp (Con09b: one rack, two benches on one side, torch poles, a barrel, a table and
a stool along the wall), bone_pit (Con05B: the rack and carcass touching, bones in two drifts, two stools apart, two
barrels, a big sack chest, rocks in one clump by the wall), cave_fire (Wiz02C: benches on opposite sides, barrels and
water barrels in a knot at the wall, torch poles at the wall). The fire 108-212 px from the wall; never a gate, straw,
bed or bearskin in the open (Con09b's beds are inside its hut). AUC 0.828 -> 0.558.
