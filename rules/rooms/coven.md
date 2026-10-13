# Coven

Family: ceremonial. Feel: **balanced**, ordered toward one end, **symmetric**. Kit kinds: `coven` (a necromancers' coven
in any building: the `coven` role), `dark_chapel` (the Land of the Dead's: a barrow hall, an ice temple). Profile:
`kit/roomtypes.py TYPES["coven"]`. Composed by `kit/sacred.py coven` (the recipes' `composer="coven"`).

## Where it comes from

QA round 1 (2026-10-13, review/qa1/sacred.md Q1C-9): "Create an additional separate chapel category for necromancy. call
them Covens. Use coffins and sarcophagi and bones, as well as altars, pews, monuments, statues, cauldrons, etc. This is
a place where the dead are worshipped and dark necromancy is practiced. many Mana obelisks lining the walls. All of the
rules regarding balance and centering of normal chapels should apply to covens as well. RM-CHAPEL-10 will serve as the
basis for the coven category." RM-CHAPEL-10 was the Land of the Dead's chapel (`dark_chapel`): the lich god's statue,
LOTD columns, mana obelisks along the walls and in a row, judgement balances, bones. Westwood has no such room in its
campaign (no evidence: the lab compares it with the ceremonial family's pool).

## Purpose and feel

The dead worshipped, dark rites at the altar: the congregation's pews face the dark altar down a runner, the dead lie in
coffins and sarcophagi in the nave, their bones heaped by them, the walls lined with mana obelisks glowing blue.

## The set piece (kit/sacred.py coven)

Everything is laid about the axis from the main door to the far wall, as the chapel's ([chapel.md](chapel.md)): the
main door in the middle of its wall, inner doors off the axis, the room never reshaped.
- **The dark altar**, one of three spread over a map's covens (`COVEN_ALTARS`): the lich god's statue on a back wall
  with a sarcophagus lying across the axis before it (the altar of the dead); a bier (a sarcophagus) between two
  flaming skulls; a pyre of burning skulls between judgement balances. Arks or balances flank it.
- **A cauldron** on the axis before the altar (one to a room: HB-1); the runner stops short of it.
- **The priest's spot** beside the altar (`STANDS["coven"]`).
- **Mana obelisks** in the far corners and **lining both side walls** at an even step (3.3 units), in pairs.
- **Pews** in up to three rows either side of the runner, LOTD columns at the ends of the first and last rows.
- **The dead**: coffins (the breakable ones) lying along the aisle in pairs nearer the door, bones heaped by them; a pair
  of sarcophagi in a coven of 150 tiles or more.
- **Monuments** flanking the runner's foot by the door; bones before the altar and along the obelisks.
- Lights: LOTD candelabras in pairs by the altar and by the door, candle groups beside the altar; LOTD tapestries and
  banners on the back walls; a colour light mid-nave.
- Its own pieces in any building (`lift`: LOTD, Lich, Crypt, Coffin, Dun Mir).
- On LOTD floors no carpet is laid (Westwood never carpets them): the runner is the bare floor between the pews.

## Pieces

- Must: tombs (2+: coffins, sarcophagi); statues (4+: the mana obelisks, balances, arks).
- May: the dark altar, pews, LOTD columns, a cauldron, monuments, bones, LOTD tapestries and banners, candles.
- Never: beds, desks, smithy pieces, counters, racks, tables, straw, plants, supplies, bookcases, trophies.

## Density

Cover 0.06-0.12-0.24; open 0.45-0.88; types 9+ (the relics counted: a furniture family of their own since the second pass).

## Checked by

`sacred.axis` (the altar, the lich god or the bier, on the door's line; the door in its wall's middle),
`sacred.symmetry`, `sacred.carpet`, `sacred.altar_kind` (over a map's covens), `sacred.dead` (coffins or sarcophagi and
4+ kinds of piece). The grammar's irregularity rules stand aside (`kit/grammar.py SYMMETRIC`).

## Where people stand

The priest at his spot beside the altar; the faithful in the pews; the restless dead about the nave.

## Full enough (QA round 1, second pass; Q1C-19)

Dressed as a crypt is (urns, rubble, LOTD gravestones, obelisks, candle groups, monuments, bones, cobwebs) until it holds
`fullness_goal` kinds (8, a kind more every 45 tiles past 30) and covers 10%. Checked by `sacred.fullness`.
