# Ogre den

Family: martial. Feel: **minimal, rough**. Kit kind: `ogre_den` (where the ogres sleep). Profile:
`kit/roomtypes.py TYPES["ogre_den"]`.

Split from the barracks in QA round 1 (2026-10-13, Q1R-8): "Ogre barracks are completely different than regular
barracks. These ones in general look pretty good because they're more minimal, as would be expected of ogres. The
expectations for ogre barracks are different than for human barracks. Separate these two categories out." Westwood's
ogre barracks (Con05C, Con09c, Con11a, War02A) are its rooms here (`rules/rooms/curated.py` CULTURE_SPLIT).

## Purpose and feel

The ogres sleep on straw heaped over the floor. Few kinds of thing, rough and crude; the user rated them 3-4 of 5 and
kept four of seven as they were. Keep them minimal: what they lacked was balance and their front corners.

## Focal point

None: the straw over the floor, the crude beds against the back walls.

## Pieces

- Must: straw (4+ heaps).
- May: crude beds (OgreBed) on the back walls, the crude table with its bench and stools, barrels and sacks in a knot,
  meat, mana obelisks (ObeliskPrimitive) **in pairs**, skulls nailed up, torch poles.
- Never: shelves, desks, chests, rugs, counters, an altar, a throne, tombs, lab pieces, stoves.

## Composition

- **Mana obelisks:** a symmetric pair in the two corners at the ends of the longest back wall (RM-BARRACKS-04: "When
  placing two mana obelisks, place them with symmetry. For example, in the corners"); four, one to each corner, in a den
  of 150 tiles or more. Never an odd one. (`kit/finish.py obelisk_pair`: the corner cleared of what was heaped there.)
- **The front corners and the S corner:** never bare: a knot of barrels and sacks, meat (RM-BARRACKS-05 "the right side
  is too empty"; -08 "needs more objects, especially on the SE"; -10 "add an object or two to the south corner area").
- **The middle:** straw heaped over the floor, the crude table with its stools.
- **Walls:** a skull or two nailed up on the back walls.

## Checks

`rooms.qa1_obelisks` (an odd number of obelisks), `rooms.qa1_south_corner` (planted cases STq1Obl, STq1Sth).

## Examples

- Ours: QA round 1 RM-BARRACKS-01, -02, -07 (kept as they were), -04, -05, -08, -10 (the notes above).
- Westwood: War09c / Con09c, cell 62,206 (56 tiles); Con05C, cell 122,91 (136 tiles).

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2F-5)

Rated 4.0, all five Fix: "All of them need a couple more sacks or barrels." Now (`kit/finish.py _ogre_den`,
`ogre_stores`): a heap of sacks and barrels side by side (three, four from 90 tiles), flush against the longest free
stretch of a back wall (the dungeon's front walls are drawn over what stands by them), blocking straw cleared from under
it; when the first heap is short, a second on another wall. Laid before the skulls are nailed up (the knowledge base
keeps a floor piece from under a hanging). The corner knots are barrels only (a sack in a knot stood off its wall,
Q2T-5). Every den holds 2-4 more stores than in round 2.
