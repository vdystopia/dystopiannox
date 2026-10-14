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

Cover 0.06-0.12-0.24; open 0.30-0.88 (Q1T: below); types 9+ (the relics counted: a furniture family of their own since the second pass).

## Checked by

`sacred.axis` (the altar, the lich god or the bier, on the door's line; the door in its wall's middle),
`sacred.symmetry`, `sacred.carpet`, `sacred.altar_kind` (over a map's covens), `sacred.dead` (coffins or sarcophagi and
4+ kinds of piece). The grammar's irregularity rules stand aside (`kit/grammar.py SYMMETRIC`).

## Where people stand

The priest at his spot beside the altar; the faithful in the pews; the restless dead about the nave.

## Full enough (QA round 1, second pass; Q1C-19)

Dressed as a crypt is (urns, rubble, LOTD gravestones, obelisks, candle groups, monuments, bones, cobwebs) until it holds
`fullness_goal` kinds (8, a kind more every 45 tiles past 30) and covers 10%. Checked by `sacred.fullness`.
Since the third pass the dressing also takes gargoyles and burning skull heaps, never crates (no stores in a coven).

Only pieces a person sees count (QA round 1, third pass: crypts 02 and 05 still read as empty at full size, the count having taken skulls and candles a few pixels wide as kinds): a piece at least an urn's size on screen (a circle of 7 px, a box of 11) with a furniture family, or a standing light (candelabra, brazier, basin); bones, skulls, cobwebs, candles, bottles and books count together as one kind at most and never toward the covered floor (`kit/sacred.py counted_kind`). The dressing fills the back walls (NE, NW) first and stands what is tall there only; a front wall (SE, SW) takes low pieces.

Open floor from 0.30, not Westwood's emptier rooms' figure: the user's first theme of QA round 1, "spaces are too empty and lack object diversity" (Q1T), over Westwood's habit (the coordinator, 2026-10-13). The way in and the reachability checks stand as they were, so the paths stay clear.

## QA round 2 (2026-10-14; review/qa2/ledger.md Q2S-4)

RM-COVEN-03: "This layout is excellent, with one exception - there are simply too many mana obelisks. It's okay to line most of the wall, but don't line the entire wall with mana obelisks." RM-COVEN-04: "The room is not properly centered. The row of mana obelisks on the southeast wall is quite far from the wall, while the row on the northwest wall is close to it ... There are also too many mana obelisks." RM-COVEN-01: "Carpet is slightly off-center with the door and altar".

- **Obelisks line most of the side walls**: from the altar's end over `COVEN_OBELISK_RUN` (60%) of the nave, the door's end left to the dead and the dressing (round 2: 22 in the large covens, now 14); the dressing never adds more obelisks (`crypt_pieces(obelisks=False)`), it takes statues, broken coffins, urns of two kinds, rubble.
- **Centred on the room** (Q2T-1): the axis is the room's own middle between its side walls (kit/sacred.py `room_middle`, `door_axis`), and the building hangs the main door exactly on its wall's middle (`building._centre_door`: a single door on a wall cell's middle, the family's double door across two; the Land of the Dead keeps its double door). Round 2's rooms had stood a unit off: the door at the wall point nearest the middle, a double door's second half a cell to one side.
- **Carpets as drawn** (Q2T-2, recurring Q1C-3): a floor tile (x, y) is drawn centred at uv (x + y + 2, x - y - 1) (MapEditor TileRenderer; `kit/furnish.py square_centre`), a unit toward -v of where the kit had read it; seams lie at odd u and even v. Runners and ring carpets are laid in those coordinates (`lay_carpet(true_uv=True)`), an even count of squares across a seam, an odd one across a square's middle; a one-square runner where only that fits (`narrow=True`). No dressing stands on a carpet (`_clear_spot`).
- Monuments at the runner's foot stand clear of a centred double door's way.

Checked by `sacred.carpet`, `sacred.symmetry`, `sacred.altar_kind` (a coven's altar is the piece nearest its far wall). Pictures: review/out/qa/qa3/rooms/coven/.
