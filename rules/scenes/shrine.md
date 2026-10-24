# Shrine or waystone

Kit: the catalogue's `shrine` (a wall scene) and `waystone` (open, by a road in the wild) in `kit/scenes.py`, laid by
`kit/dressing.Exterior`. Lab: `py tests/scenelab.py shrine` (since round 4 in the hamlet's ground, among houses).
Westwood's evidence: 28 campaign scenes (Con04b's castle garden, Con05A, Con07B-E, War03a-c, War04a-b, War07A, Wiz02B).

## QA round 3 (2026-10-23): the centrepiece centred as drawn [Q3N-3]

EX-SHRINE-01 (the obelisk court with the gold wolf; 4, Fix): "The main statue/altar is slightly out of center with the
cobblestone path down the middle. Make sure it's lined up and centered."

- The centrepiece is centred on the aisle as it is drawn, not by its point. The gold wolf's point stood on the axis to
  the pixel (v -37.00, the aisle's drawn middle -37.0), but the game draws its pedestal 0.4 uv (6 px) to the north-east
  of its point. Each centrepiece's drawn base was measured on the editor's render: the render with the piece less the
  render without it, and the outline of its base fitted. The results are in `setpieces.DRAWN_BASE`, as uv offsets from
  the point: gold wolf (-0.70, +0.39), HorrendousStatue1 (+0.46, -0.28), HorrendousStatue2 (+0.43, -0.43), the altar
  (-0.43, -0.26), the obelisk about 0. Each is set across the axis so that its base lands on it (`setpieces._on_axis`).
  Along the axis it stays where it was.
- Lab (seed 11; not re-rendered for the page): 01's wolf moves 0.39 uv SW, and its pedestal's front edge is now centred
  on the aisle. The other four courts' centrepieces move 0.07-0.43 uv across. No tiles change.
- Any sprite can be drawn off its point (the same family of fault as the floor tiles drawn half a square SW,
  `yards.TILE_DJ`). A piece that must line up with paving is placed by its drawn footprint.

## QA round 2 (2026-10-14): the aisle on the axis, the statue facing the way in [Q2X-3, Q2T-1, Q2T-3]

**This section overrides the rounds below.** EX-SHRINE-01/02/04: "The path down the center of the shrine is not lined
up with the middle and the statue." EX-SHRINE-05: "The statue is facing the wrong way. Have it face the direction of the
entrance, aligned with the path."

- The aisle is three squares wide (one in a narrow court), its middle square on the court's axis and the centrepiece's
  line. On a way in from an i side (south-east) the aisle had been two squares laid on the wrong lattice, half a square
  off the axis: the tiles are drawn half a square toward -j of the squares' middles (`yards.TILE_DJ`), and
  `yards.Frame.squares` now picks tiles by where they are drawn.
- The great statue faces the way in down the aisle: HorrendousStatue1 faces south-east (a way in from the i1 side),
  HorrendousStatue2 south-west (the j0 side) (`yards.GREAT_STATUE`); the gold wolf faces south-east only, so a court
  entered from the south-west takes the seated statue. The open chapel's statue behind its altar is the Statue1 letter
  that faces the way in (`yards.STATUE_LETTER`).
- The paving ends at a curb (CobbleStoneTrim), never blended into the grass (`setpieces.CURB`).

## QA round 1 (2026-10-13): a court, not a wall [Q1X-1, Q1X-2, Q1X-3]

**This section overrides the rounds below.** The user rated all ten of the lab's wall shrines 1, "drop": "These are all
awful. Change shrines drastically. Give them a square or rectangular shape defined by obelisks and mana pillars or
parallel statues that lead to a grand centerpiece. Needs much more structure." Westwood's shrines against a wall are no
longer the model.

- Kit: a shrine is a court of its own, `kit/yards` kind `"shrine"` (planned before the land is carved, `yards.plan` /
  `plan_any`; built after its walls, `yards.build`), laid by `kit/setpieces._shrine` in the yard's `Frame`. The
  catalogue's wall `shrine` theme is retired (cap 0; no role calls for it).
- The court: 9 x 11 to 11 x 15 squares of paving (RoughCobble with an aisle of grey cobbles, or the reverse), entered
  from the screen's bottom (its south-east or south-west side, `yards.FRONT_ENTRY`), so its centrepiece stands at the
  back, seen over the court.
- Its shape is set by its pieces: one at each corner, a row down each long side evenly spaced between them, all in
  mirrored pairs; an aisle up the axis to a dais and the grand centrepiece; braziers or flame basins either side of
  the way in.
- Archetypes (`yards.SET_ARCHS`): obelisk court (mana obelisks at the corners, stone obelisks down the sides, urns
  lining the aisle, the great seated statue or the gold wolf between flame basins); statue avenue (victory statues
  facing each other across the aisle, torch poles down the sides, stone obelisks at the corners); mana court (dark mana
  obelisks at the corners, blue mana obelisks down the sides, stone obelisks lining the aisle, a ring of mana crystals
  round a blue obelisk); open-air chapel (columns at the corners and down the sides, benches in rows facing the altar,
  a statue behind it, flame basins and urns).
- Checks: `exterior.set_variety` (three kinds of thing at least), `exterior.set_symmetry` (its pieces mirrored about
  its axis, 80%); look at the lab's pictures for the shape and the centrepiece.

## What Westwood's are

Statues, not offerings. Statues of one kind, three in a row along a screen diagonal ~49 px apart (Con04b, Con07C,
Wiz02B) or two flanking a way ~115-160 px apart; a lone statue between a pair of stone pillars (Monument1) ~100 px
either side; torch poles or wall torches by them; and 0.94 of their pieces within two cells of a built wall (castle and
town walls). Waystones (Con03A, War03a): two to four milestones (DunMirMileStone) in a row along a diagonal, 30-45 px
apart, an altar stone (DunMirAltar2) at the row's end. No flowers, sacks or stones left as offerings.

## The kit (round 4, 2026-10-06)

- `shrine` stands against a house's or a fence's wall (any side), ~34 px off it: six statue kinds (Statue2a, b, c, e,
  g, h), each in three layouts: three in a row 49 px apart with a torch pole at one end (70%) and the other (40%) and a
  pillar beyond (40%); a pair 160 px apart with a torch pole between and pillars outside (40%); a lone statue between
  two pillars with a torch pole or two.
- `waystone`: an altar and two to four milestones in a row 32 px apart, a second altar 30%; or two milestones with the
  altar between.
- Never: candles (SW-8), flowers or offerings.

## What still gives it away

Westwood's stand in castle courts and gardens against long straight walls; the lab's against small houses' walls.

## Round 5 (2026-10-06)

The judge: "the wrong backing: against wooden peasant cabins or floating in a glade, instead of masonry or a ruin". The
lab sets the shrine by the village's chapel. Then the kit: the shrine stands only against masonry, a castle's walls or a stone house
(`Theme.house_roles`: chapels, shrine and mausoleum buildings, keeps, manors, the town hall, barracks, towers,
gatehouses, gaols, observatories), never a cabin.

## Archetypes (round 6, 2026-10-06)

Westwood's 28 outdoor shrines (by their pieces):

| Archetype | Westwood | What it is |
|---|---|---|
| statue row | 13 of 28 (Con07C, Wiz02B, Con04b, War04b) | statues of one kind in a row of two or three against masonry, torches by them |
| crypt court | 5 of 28 (Con04b) | two or three sarcophagi in a cluster, a cross or statue among them, a stone pillar either side, torch poles |
| lone statue | 5 of 28 (War03c, Con05A, War04b, Con07E) | one statue with a torch pole or a flame basin |
| chapel nave | 3 of 28 (Con07B, War07A) | tapestries, benches, columns, candelabra (a roofless chapel) |
| milestone altar | 2 of 28 (Con03A, War03a) | Dun Mir milestones in a row with an altar (the kit's `waystone`) |

The kit (`scenes.THEMES["shrine"]`): the row, the pair and the lone statue for six statue kinds, and since round 6 the
crypt court (Crypt1, Crypt4, Crypt3 70%, a cross or statue, Monument1 either side, torch poles). AUC 0.917 -> 0.874
(round6). The lab still builds the same small stone shrine or mausoleum each time (the judge: "the same chapel box"):
a town-wall site for the shrine is the next step.

## Structures and sites (round 8, 2026-10-06)

Westwood's 26 shrines against walls, clustered by their pieces (`kit/scenes.SHRINE_LAYOUTS`, each as often as
Westwood's): castle row 4 (Con07C, Wiz02B: three statues ~97 px apart, wall torches between), tight row 2 (Con04b:
three ~49 px apart, a chest, torches, a pillar), alternating row 2 (Con04b: victory statues between), pair 5, lone
statue 5 (a wall torch, a torch pole or a flame basin beside it), crypt court 5 (sarcophagi side by side along the wall,
pillars at both ends, a cross ~93 px out), chapel nave 3 (Con07B, War07A: tapestries, columns, candelabra, a statue,
benches). Distances from the wall's centre line: statues 16-51 (median 29), pillars 11-22, wall torches 10-20, torch
poles 20-47, sarcophagi 41-67, benches 67-121. Sites: DungeonStone on DirtDark2 or broken cobbles 12 (Con04b, War04),
GalavaTowerWall on GalavaBrick3 7 (Con07C/E, Wiz02B), Cobblestone on grass 4, StoneGray on GalavaBrick2 3 (the naves).
The lab stands each on a straight run of one of these walls on its paving (`recipes._shrine_plan`). AUC 0.846 -> 0.389.
