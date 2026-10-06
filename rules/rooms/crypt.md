# Crypt

Family: the dead. Feel: **sparse, quiet, ordered**. Kit kinds: `crypt` (a chapel's family crypt), `dark_crypt` (the
Land of the Dead's tombs). Profile: `kit/roomtypes.py TYPES["crypt"]`.

## Purpose and feel

Where the dead lie. Rows of sarcophagi and coffins with aisles to walk between; statues of the dead; little else.

## Focal point

The rows of tombs.

## Pieces

- Must: tombs (2+: sarcophagi, coffins, tombstones).
- May: columns, statues of the dead or gargoyles, crypt chests, a tapestry or two, barren plants.
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
