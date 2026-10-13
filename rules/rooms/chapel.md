# Chapel

Family: ceremonial. Feel: **open**, ordered toward one end, **symmetric**. Kit kind: `chapel` (a town's nave). Profile:
`kit/roomtypes.py TYPES["chapel"]`. Composed by `kit/sacred.py chapel` (the recipe's `composer="nave"`).

The chapel set was split three ways in QA round 1 (2026-10-13, review/qa1/sacred.md Q1C): the rings of mana obelisks
round an altar are **mana rooms** ([mana_room.md](mana_room.md)), the Land of the Dead's chapel and any chapel of the
dead are **covens** ([coven.md](coven.md)). This brief is the town's chapel only.

## The user's rules (QA round 1)

- "Generally, chapels should have a much more symmetric layout. The carpet that runs down the middle with benches and / or
  pillars and pews evenly and symmetrically placed on either side and an altar at the end, centered." [Q1C-1, Q1C-3]
- "Chapels should always be aligned with the main door. The character should walk in and be on the main path facing the
  altar." [Q1C-2] RM-CHAPEL-09: "Center the door, altar, benches and pillars in the room. Add some carpet or paving
  leading up to the altar." RM-CHAPEL-03: "The carpet and altar should be centered in the room and be aligned with the
  door. Needs drastically more objects." RM-CHAPEL-08: "Needs a carpet or path from the door to the altar. Balance and
  line up the pillars and benches better."
- "all rooms use the same altar - try different objects" [Q1C-4]; nox14: "needs more pillars, benches, and statues ...
  Give the priest a better location instead of being behind a random pillar. Have the priest stand closer to the altar."
  [Q1C-11, Q1C-12]
- RM-CHAPEL-01 "Barely recognizable as a chapel"; 04 "Scattered mess"; 05 "Needs better centering and alignment. But the
  flow is good. The benches also seem to be randomly placed." [Q1C-10]

## The set piece (kit/sacred.py chapel)

Everything is laid about the **axis**: the line from the main door's middle straight across the room. The building puts
the main door in the middle of its wall (`building.CENTRE_DOOR_ROOMS`, `_wall_middle`) and keeps inner doors 6 units off
the axis (`ALTAR_AXIS`); the shell pass never reshapes the room (`SHELL_KEEP`).
- **The altar end**, one of four, spread over a map's chapels by deficit (`CHAPEL_ALTARS`): Dun Mir's altar alone
  between fire basins; the holy font (`OrbPoolWithOrb`) or a fountain before the altar; a saint's great statue
  (`HorrendousStatue`, facing out from the back wall) behind the altar. Every end keeps a Dun Mir altar against the far
  wall, centred on the axis; statues flank it a pace out; candelabras flank the statues.
- **The priest's spot** beside the altar (`Furnisher.spots` role `priest`; `STANDS["chapel"]` asks for it first).
- **The runner**: carpet squares centred exactly on the axis from the door to the altar's front, two squares wide when
  the axis lies on a seam between squares, three when it runs through their middles (squares are 2 units; seams lie at
  odd coordinates).
- **The pews**: rows either side of the runner, one to three to a half-row, from three units before the altar toward the
  door every 2.5 units, the back quarter of the nave open; a row a side door's way crosses is left out on both sides. A
  pew per 10 tiles, 20 at most (the cap rose from Westwood's 8: "needs more ... benches"), in more rows of fewer pews, the rows spread down a long nave up to 3.6 units apart.
- **The columns**: a pair at the outer end of the rows at one even pitch down the whole nave (every row in a short nave,
  every other in a long one) and on past the rows to the door; in a narrow nave against the side walls.
- **The side aisles**: statues against the side walls between the column pairs; tapestries of one colour on the back
  side wall at the bays, and either side of the altar when the far wall is a back wall.
- **The narthex** by the door: a pair of founders' sarcophagi either side of the runner in a nave of 150 tiles or more,
  else a pair of statues; candelabras by the door.
- A warm colour light on the axis mid-nave.

The irregularity rules of the placement grammar (even gaps, stepped rows, rings, lone columns, the runner as a floating
carpet) stand aside in the symmetric types (`kit/grammar.py SYMMETRIC`): the user's word over Westwood's habit.

## Checked by

`sacred.axis` (the altar within a unit of the door's line, the door within 1.6 units of its wall's middle),
`sacred.symmetry` (floor pieces off the axis each have a twin of their kind mirrored across it), `sacred.carpet` (carpet
squares mirrored across the axis), `sacred.altar_kind` (no one altar end in more than 60% of a map's 3+ chapels); planted
cases STsAxis, STsSym, STsCarp, STsAltr (`validate/selftest.py`).

## Before QA round 1 (kept for the record)

## Purpose and feel

A place of worship: people come in, walk up an aisle and sit facing the altar. The pews are a few rows near the altar,
not a carpet of benches; the back of the nave, toward the door, stays open. Quiet, symmetric, the eye drawn to the altar.

## Focal point

The altar (Dun Mir's, or the lich god's statue in the Land of the Dead) on the wall straight across from the main door, in
line with it (`door=True` in the compose step; an inner door keeps 6 units off that line: `building.ALTAR_ROOMS`).
Statues stand either side of it.

## Pieces

- Must: the altar; pews (4+); statues (2+).
- May: a colonnade down the nave, a pair of sarcophagi by the door, tapestries, fire basins, the holy font or a fountain,
  a saint's statue. (Since QA round 1 no chest or plant: they stand alone and break the symmetry.)
- Never: tables, beds, desks, stoves, shelves, racks, stores (barrels, crates, sacks), hunting trophies (Ambermere's
  chapel had a bear's head on its wall), straw.

## Composition

- **The altar wall** (across from the door): the altar centred, statues either side; tapestries.
- **The other back wall:** tapestries of one colour.
- **Front walls and corners:** plants; a chest; a bench or two.
- **The middle:** a carpet runner up the aisle from the door to the altar; pews two to a side in rows nearest the altar,
  split by the aisle; a colonnade in pairs either side of the pews from 5 units ahead of the altar; open floor toward the
  door.
- **Movement:** straight in and up the aisle; nothing in the door's line.


## Archetypes

Westwood's 1 curated campaign chapel room differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Few rooms: the archetypes also draw on kin types' rooms (each counted half a room), as named. (The sanctum, the holy thing ringed by four obelisks, is the mana room's since QA round 1.) Each room draws one by these frequencies, spread over a map's rooms of the type; the set piece (kit/sacred.py) reads it: a colonnade chapel takes fewer pews to a row and a column pair at every row (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| pewed nave | 67% | Con07B@143,201 | pews in short rows either side of a carpeted aisle, columns ringing the nave among them, tapestries of one colour, candelabras in pairs, a statue by the altar |
| colonnade chapel | 33% | -kin: Con04c@75,78 | the altar at the end of a colonnade, statues in pairs facing across the aisle, a few pews near the altar (kin: Con04c's colonnade hall) |

## Density and openness

| | Westwood's campaign (1 room, Con07B) | Profile |
|---|---|---|
| coverage | 0.06 | 0.05-0.18 (target 0.10) |
| open floor | 0.62 | 0.55-0.88 |
| pieces per tile | 0.20 | 0.08-0.35 |
| distinct types | 7 | 8+ (6 in the Land of the Dead) |
| caps | Wiz07F: 8 benches in 123 tiles | pews 1 per 10 tiles, at most 20; columns 1 per 16 tiles, at most 12; statues 1 per 16, at most 10; sarcophagi 2 |

## Size

60-260 tiles; longer than wide, the altar at the end of the long axis.

## Culture variants

- Town (Dun Mir altar): pews (Bench, LightBench), Statue2, cathedral columns, sarcophagi (Crypt pieces).
- Land of the Dead: its chapel (`dark_chapel`) is a coven since QA round 1 ([coven.md](coven.md)).

## Where people stand

The priest at his spot beside the altar, between it and the statue that flanks it (QA round 1, nox14: he had stood
"behind a random pillar"); the faithful in the pews. Never on the runner, before the altar or in the aisle.
(`STANDS["chapel"]`: the priest's spot, else beside the altar, else a back wall.)

## Common mistakes

- A nave far over its size (Harrowby's first chapel, 288-323 tiles: 4-6% covered): a village takes the
  `village_chapel` role (34 x 26 units, its nave about 100-130 tiles); the town's `chapel` keeps its size (shrinking it
  moved every other map's layout). Pews 1 per 14 tiles; a free group of statues only in a nave of 180 or more (a pair
  had stood among a small nave's pews); a founder's tomb against a side wall from 140, a second from 200.

- "way too many benches and not enough object diversity ... too many of the same object (chapel benches, tavern tables
  and chairs)" (Greywatch, 2026-10-05: 46 pews wall to wall).
- The altar beside the door instead of across from it, the aisle off the door's line, half the nave bare (Ambermere
  review, 2026-10-05: 6% covered).
- A god statue among a block of 8 columns (a barrow): columns go in pairs either side of the aisle.
- Filling the nave to a house room's coverage (the old target was 0.18): the floor toward the door is meant to be open.

## Examples

- Westwood: Wiz07F, cell 143,201: a temple of 123 tiles, 8 benches facing the far end, 6 columns, 8 tapestries, 2
  statues: coverage 0.05, open 0.66.
- Westwood's campaign has one chapel: Galava's temple above (Con07B, War07A, Wiz02A, Wiz07F share it; the priest stands
  in it). It has no altar: no campaign room holds one (Dun Mir's altars stand in Con06a's cave hall and outdoors in
  Con03A). The altar, the god statue of the `dark_chapel` and the 79-81-tile LOTD rooms this brief once cited come from
  the quest map G_LOTD: the kit keeps the altar as a rule of its own (`identity.ROOMS["chapel"]` prefer), not as
  Westwood's habit.
- Ours: Thornwick's and Greywatch's naves after the type split (see `review/out/<map>/rooms/`).

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

- **Eight pews at most** (Westwood's Con07B: 8 in 123 tiles), a pair per 15 tiles, two to a side of the aisle.
- **Columns ring the nave near its walls,** the side aisles between them and the pews, not hard against the pews.
- **Statues by the altar turn along its wall toward it.**
- **Sarcophagi rarely** (a quarter of naves), never by default behind every set of pews; **no plants.**
- At most six hangings.
- Still missing: the cross-shaped carpet of Westwood's temple (the shell's floor), a lectern by the altar.

## Full enough (QA round 1, second pass; Q1C-19)

After the set piece the nave's walls and corners are dressed in mirrored pairs until it holds `fullness_goal` kinds (8, a
kind more every 45 tiles past 30) and covers 7%: fire basins, statues, urns, monuments, gargoyles, victory statues, orb
pedestals, light benches along the side walls; the statue cap (a statue per 16 tiles) held. Checked by
`sacred.fullness`.
