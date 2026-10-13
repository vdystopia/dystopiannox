# Crypt

Family: the dead. Feel: **quiet, ordered, symmetric**. Kit kinds: `crypt` (a chapel's family crypt), `dark_crypt` (the
Land of the Dead's tombs). Profile: `kit/roomtypes.py TYPES["crypt"]`. Composed by `kit/sacred.py crypt` (the recipes'
`composer="crypt"`; until QA round 1 by the motif engine, kit/motifs.py).

## The user's rules (QA round 1, 2026-10-13; review/qa1/sacred.md Q1C-13..Q1C-18)

- "The objects in these rooms need better organization, arrangement, and balance. Add more object diversity, like
  bones. Use the breakable coffin objects sometimes. Add a high chance for these rooms to contain mana obelisks."
- RM-CRYPT-09 (49 tiles, two sarcophagi): "Worst one in the set, very empty."
- RM-CRYPT-10 (dark crypt, LOTD walls): "The wooden doors mismatch with the double doors. Generally, the double door style
  should be used for all doors with this tile set. This room also needs coffins or graves or something to give it a crypt
  identity" (its rows of tall LOTD tombstones did not read as graves).

## The set piece (kit/sacred.py crypt)

Laid about the axis from the main door to the far wall (the door in the middle of its wall when it is the building's
entrance, `building.CENTRE_DOOR_ROOMS`; never reshaped, `SHELL_KEEP`):
- **The centrepiece** on the far wall in line with the door, spread over a map's crypts: a crypt chest, a great square
  sarcophagus or a monument; **mana obelisks** flanking it in 4 crypts of 5 (else statues of the dead), and a second
  pair by the door in a crypt of 90 tiles or more.
- **The rows of the dead** either side of a middle aisle, mirrored: sarcophagi of one model (40%) or the breakable
  coffins (40%), or the old dead's sarcophagi nearest the far wall and coffins nearer the door (25%); across the aisle,
  one or two to a half-row, a walk round the far end; along the aisle in a narrow crypt (the aisle narrows to a pace);
  a row a side door's way crosses left out on both sides, the next tried; else tombs along the side walls, else a bier
  on the axis. The Land of the Dead's crypts lie in coffins and sarcophagi too, with its own gravestones at the heads.
- **Bones** heaped at the rows' heads, mirrored; **graves** (tombstones; LOTD gravestones in the Land of the Dead) at the
  heads against the side walls; statues of the dead in pairs along the side walls in a big crypt; a pair of tombstones
  flanking the aisle's foot.
- Candelabras in pairs (LOTD candelabras in the Land of the Dead); a tapestry pair on the far wall when it is a back wall.
- The LOTD styles hang their double door in every doorway (`building.DOUBLE_DOOR_STYLES`; RM-CRYPT-10), checked by
  `doors.lotd`.

## Checked by

`sacred.symmetry` (floor pieces paired across the door's line), `sacred.dead` (two coffins, sarcophagi or graves at
least, and 4+ kinds of piece; LOTD gravestones alone are not graves), `doors.lotd`; planted cases STsDead, STdLotd. The
grammar's irregularity and mixed-tomb rules stand aside (`kit/grammar.py SYMMETRIC`).

## Before QA round 1 (kept for the record)

## Purpose and feel

Where the dead lie. Rows of sarcophagi and coffins with aisles to walk between; statues of the dead; little else.

## Focal point

The rows of tombs.

## Pieces

- Must: tombs (2+: sarcophagi, coffins, tombstones).
- May: mana obelisks, monuments, statues of the dead, crypt chests, tombstones, bones, a tapestry or two.
- Never: beds, desks, tables, chairs, stoves, forges, lab pieces, bars, counters, racks, hearths, straw, barrels, sacks,
  bookcases.

## Composition

- **Back walls:** a tapestry or two; a crypt chest in a corner; statues of the dead.
- **Front walls:** bare.
- **The middle:** sarcophagi and coffins side by side in rows, aisles between; columns. An L-shaped or narrow crypt lays
  its dead along the walls instead.


## Archetypes

Westwood's 25 curated campaign crypt rooms differ in structure, not just in details (clustered by where the focal stands, how the room is zoned, which walls are used, what the middle holds, density: `mapgen/kit/archetypes.py`). Each room draws one by these frequencies, spread over a map's rooms of the type; both engines compose from it (the recipe engine: `kit/identity.py ARCHETYPE_RECIPES`; the motif engine: its zone plans from the archetype's rooms).

| Archetype | Share | Westwood rooms | What it is |
|---|---|---|---|
| tomb niche | 32% | War03c@74,214, War03c@83,223, War03c@85,203, War03c@94,212, War03d@52,214, War03d@62,222, War03d@64,202, War03d@74,210 | a small side chamber: one or two sarcophagi off the middle, a tombstone at the wall |
| tomb row | 16% | War03c@73,224, War03c@95,202, War03d@52,223, War03d@74,201 | a big vault with a row of three or four sarcophagi along one side and tombstones behind them, the rest of the floor open |
| wall tombs | 24% | Con04a@100,130, Con04a@128,136, Con04a@136,150, Con04a@138,118, Con04a@138,97, War03c@100,229 | sarcophagi against the walls, torches, a crypt chest or obelisks in the middle |
| tombstone yard | 24% | Con04a@148,127, Con04a@150,108, Con04b@142,44, Con04c@194,152, War03c@80,98, War03c@94,112 | no sarcophagi: tombstones in a loose grid over the floor, a crypt chest |
| statue vault | 4% | Con04a@112,146 | statues in pairs on every wall, tombstones in rows between (recipe engine: the kind's own recipe) |

## Density and openness

| | Westwood's campaign (30 rooms, 8 maps) | Profile |
|---|---|---|
| coverage | 0.01-0.08-0.23 | 0.08-0.30 (target 0.16) |
| open floor | 0.46-0.74-0.91 | 0.40-0.85 |
| pieces per tile | 0.04-0.07-0.20 | 0.06-0.40 |
| distinct types | 1-2-11 | 3+ |
| caps | | tombs 1 per 5 tiles, at most 30 |

## Size

30-200 tiles (Westwood's catacombs reach 400).

## Culture variants

`dark_crypt`: LOTD tombstones in rows, mana obelisks at the walls, sconces and candles, bones and skulls strewn.

## Where people stand

The keeper beside a crypt chest or a statue of the dead; never in an aisle between the rows of tombs. (`STANDS["crypt"]`: beside a crypt chest or statue, a back wall.) The restless dead stand about the floor (StoryMap.keepers).

## Common mistakes

- Sarcophagi side by side in two rows head to head with no aisle: a block of 16 (Harrowby): a row's depth is the
  deepest tomb's across the row (`Furnisher.rack_rows`), so the aisle stands between the rows. Statues of the dead go on
  a back wall in the compose step.

- One sarcophagus in a 58-tile crypt, 5% covered (Thornwick v0.1).
- Only coffins: a crypt with nothing but its rows and no wall used reads as a store of coffins (the room score flags a
  crypt with under 3 kinds of piece and no wall used).

## Examples

- Westwood: Wiz02A / Con07B, cell 169,176 (235 tiles, 14-17 types, coverage 0.06, open 0.74). (G_CryptD's 209-tile crypt,
  once cited here, is a quest map's: not campaign evidence.)
- Ours: Thornwick's family crypt (see `review/out/Thornwick/rooms/`).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's 25 curated crypts hold 1-5 types (median 2): two to six sarcophagi in short aligned rows, none against a
  wall and none far from one, a crypt chest; 0.67 tombs per 10 tiles. Two rows with a wide aisle (3.6), so each keeps
  near its wall, capped at a tomb per 12 tiles; no columns, tapestries or plants (AUC 1.0 -> 0.89). Tombs along the walls
  (`wall_gap`) read worse: Westwood's stand free of them.

## Full enough (QA round 1, second pass; Q1C-19)

The coordinator found crypt 05 "almost bare", crypt 02 "3 sarcophagi and little else" and the dark crypt 10 "mostly empty
floor". After its rows the crypt dresses its walls and corners in mirrored pairs (`kit/sacred.py dress`, `crypt_pieces`):
urns (StatueVase, facing the axis), rubble, gravestones, a small statue pair (LOTD obelisks in the Land of the Dead),
candle groups, monuments, skulls and rib cages, cobwebs in the far corners; each kind once, then more until it holds
`fullness_goal` kinds (6, a kind more every 45 tiles past 30, 10 at most) and covers 10% of its floor. The rows run the
floor's whole length (a depth a side door's way takes is stepped over), and where a band is left without a row single
tombs lie on the middle line. Checked by `sacred.fullness` (STsFull).
