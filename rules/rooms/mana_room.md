# Mana room

Family: ceremonial. Feel: **balanced**, **symmetric** about the room's middle. Kit kind: `mana_room` (the `mana_sanctum`
role; an option of the college, the keep and the grovelord's shack). Profile: `kit/roomtypes.py TYPES["mana_room"]`.
Composed by `kit/sacred.py mana_room` (the recipe's `composer="mana"`).

## Where it comes from

QA round 1 (2026-10-13, review/qa1/sacred.md Q1C-5..Q1C-8), of the chapel lab's sanctums (RM-CHAPEL-02, 06, 07): "The
square mana obelisk arrangements with the altar in the middle in 2, 6, and 7 are excellent, but they do not fit in with
the identity of a chapel. They all need to have the carpet underneath them made even and symmetrical. Try some other
centerpiece objects. separate these rooms into their own category - mana rooms. define them by 1-4 arrangements of mana
crystals evenly and symmetrically placed and a wide selection of other arcane objects."
- RM-CHAPEL-02: "Center the mana obelisks on the carpet. The southwest side of the carpet extends further than the other
  sides. Fill the southeast side of the room a little bit more, and move the treasure chest away from the corner."
- RM-CHAPEL-06: "The room is way too big and empty. Add a second mana obelisk arrangement and orient them in the
  southwest and southeast of the room so they're balanced. Fill the room with many more objects."
- RM-CHAPEL-07: "Center the mana obelisk arrangement in the room. Improve the layout of the benches and add more objects."
Kin in Westwood: the shrines with four obelisks round the holy thing (Con07D's key, Wiz02B's and Wiz11A's spell books).

## The set piece (kit/sacred.py mana_room)

The axis runs down the room's long dimension through its middle (`centre_axis`).
- **The rings**: one to four, by the room's size (1 under 100 tiles, 2 under 170, 3 under 230, else 4) and what fits:
  one in the middle; two along the long axis at its quarters; three in a row at its thirds; four in a square. Each is
  four mana obelisks (`Obelisk`, sometimes `ObeliskPrimitive`, `LOTDManaObelisk` in the Land of the Dead) at the room's
  screen axes round a centrepiece, on whole units so the ring is mirrored exactly. Rooms with more rings win over a bigger
  centrepiece.
- **The centrepiece**, spread over a map's mana rooms (`MANA_CENTRES`): a crystal column, a great mana crystal, a crystal
  stalagmite, the orb pool, an orrery, a generator, Dun Mir's altar. A showpiece (orrery, generator) stands once: in the
  only ring or the middle of three, the other rings round a crystal.
- **The carpet** under each ring, centred exactly: its edges on the squares' seams as far out on every side (an odd
  count of squares round an even middle, an even count round an odd one); every ring has its carpet or the layout is
  taken up whole (a ring without one beside a ring with one is lopsided).
- **The walls**, mirrored: crystal clusters in the four corners; on each back wall a centred workstation, potion
  shelves or a chest (02: "move the treasure chest away from the corner"), bookcases end to end either side of it,
  workstations or potion shelves at the quarters of a long wall, star charts or zodiacs above; small generators flanking
  the middle on the front walls; glowing jars in pairs; crystal clusters flanking each ring across the room; an orrery
  (else a crystal) on the open floor between two rings; candelabras in pairs by the end walls; a colour light.

## Pieces

- Must: mana obelisks (4+).
- May: centrepieces, wizards' workstations, glowing jars, generators, an orrery, bookcases, potion shelves, a chest, star
  charts and zodiacs, crystal clusters, candelabras.
- Never: beds, desks, stoves, smithy pieces, counters, racks, tables, straw, tombs, plants, hearths, supplies, trophies.

## Checked by

`sacred.symmetry` (pieces paired across the long axis, or about the room's middle along it: the back walls' pieces are
mirrored about their own wall's middle), `sacred.carpet` (the rings' carpets mirrored across the axis). The grammar's
irregularity rules (rings, even gaps, corner singles) stand aside (`kit/grammar.py SYMMETRIC`). The checker's straight
way in keeps its first 4 units clear of everything, but its "no column or statue in line with the door further in" rule
stands aside in the sacred rooms: a ring in the middle is the room.

## Where people stand

A keeper beside a workstation or an obelisk (`STANDS["mana_room"]`), never inside a ring.

## Full enough (QA round 1, second pass; Q1C-19, Q1C-20)

A mana room with doors on several walls had come out about 2% dressed. After the rings and the walls the composer dresses
the wall stretches between the doors and the open floor between rings and walls in mirrored pairs (`kit/sacred.py dress`,
`mana_pieces`): mine crystals, glowing jars, crystal pillars, small generators (once), primitive obelisks, candelabras,
urns, orb pedestals, mana carts, fire basins, crystal stalagmites; a pair across the axis, else about the room's middle
along it; until the room holds `fullness_goal` kinds (8, a kind more every 45 tiles past 30, 12 at most) and covers 7%.
Each placement takes its own kind of crystal (corners mana crystal clusters, the rings' flanks blue stalagmites, the
dressing mine crystals), so no one kind repeats past the room score's most. Checked by `sacred.fullness`.
