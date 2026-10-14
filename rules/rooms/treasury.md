# Treasury

Family: stores. Feel: **balanced, guarded**. Kit kind: `treasury` (a keep's strongroom, a town hall's treasury, a
guild's counting room). Profile: `kit/roomtypes.py TYPES["treasury"]`.

## Purpose and feel

Where the wealth is kept and counted: strongboxes in a row along the back walls, each with room before it to open, the
treasurer's counting table in the middle, tally shelves, shields and crossed arms on the walls. Few pieces, all of value;
open floor round the table so the boxes can be reached.

## Focal point

The row of strongboxes on a back wall.

## Pieces

- Must: chests (3+), the counting table with a chair.
- May: tally shelves (TraderShelves), shields and crossed arms hung on the walls, a second row of chests.
- Never: beds, hearths, stoves, plants, barrels, crates, sacks, bookcases, bars, counters, an altar, a throne.

## Composition

- **A back wall:** the strongboxes in a row, the floor before them clear.
- **The other back wall:** hanging shields and crossed arms; the tally shelves.
- **Front walls:** bare, or a second row of chests in a big strongroom.
- **The middle:** the counting table and the treasurer's chair, open floor round it.

## QA round 1: the themes applied (2026-10-13)

The user rated other types in QA round 1 and asked that the round's themes apply to this one ("Much of the feedback
boiled down to": too empty, not enough object diversity; no balance or symmetry, things placed randomly, not lined up
with each other). These rules override the Westwood-measured sparseness above where they differ; `kit/works.py`
composes the room by them after the recipe (its loose pieces are taken up first: `SPEC[kind]['keep']`), ledger
`review/qa1/works.md` (Q1B-n).

- **The strongboxes** in an even row centred on a back wall (the far one when the camera sees it), each with room before
  it to open.
- **The middle:** the counting table with its chairs centred on a carpet on the axis; sack piles in mirrored pairs
  either side in a big strongroom.
- **Corners and walls:** heaps of coin sacks of three sizes in the W and E corners, a great cask and sacks in the S
  corner, a pair of guardian statues flanking the far wall's middle (past the row of chests when it stands there),
  tapestries in a pair on it, else one on a bare back wall. No trophies of crossed weapons or shields: they are shop
  racks, which the type's profile forbids.
- **Never emptier:** the room ends with at least the visible pieces and kinds its recipe gave it, and master's lab
  average for the type (a tenth more in a room of 80 tiles; `SPEC[kind]['least']`, `Finish.top_up`); bones, candles
  and small gears are one kind at most and never count as pieces.

## Density and openness

| | Westwood's campaign (3 rooms, 3 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.02-0.03 | 0.03-0.24 (target 0.12) |
| open floor | 0.81-0.89-0.97 | 0.45-0.90 |
| pieces per tile | 0.07-0.08-0.11 | 0.08-0.50 |
| distinct types | 5-6 | 5+ |
| caps | | chests 1 per 10 tiles, at most 6; one table |

## Size

20-120 tiles (Westwood's: 54-117).

## Culture variants

Dun Mir's (Wiz06c): Dun Mir chests under hanging shields. The ogres' (Con05B): their chests and sacks with gold.

## Where people stand

The treasurer behind his counting table (the far side from the door), else beside the strongboxes. Never between the
chests and the floor before them. (`STANDS["treasury"]`: behind the table, beside a chest, a back wall.)

## Common mistakes

- Nine chests down one wall (the first lab version, Dun Mir chests the checker reads as stand-alone pieces): a row of
  three, a second in a big room.
- Barrels and sacks: that is a storeroom.

## Examples

- Westwood: Con05B, cell 192,58 (54 tiles: the ogres' chests, gold, sacks, a great cask); Wiz06c, cell 163,93 (117
  tiles: Dun Mir chests, six shield hangings); Con06b, cell 163,93 (116 tiles: three Dun Mir chests, a table of food
  and four chairs).
- Ours: the room lab's treasuries.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's one curated strongroom (Con05B, the ogres', 54 tiles): two chests, sacks of two sizes and a great cask
  over a bare floor. The object knowledge agent found ours read as armouries (trader's shelves and hung shields
  dominating): the recipe now holds three strongboxes (the knowledge base's cap) on the back walls, sacks of coin and a
  cask in heaps, the counting table and chair; no shelves of wares, no hung arms. The cap on stores rose to one per 6
  tiles (Con05B: five on 54 tiles). The brief's Con06b and Wiz06c examples were corridors (curated out).

## QA round 2 (2026-10-14; review/qa2/ledger.md)

RM-TREASURY-03: "The giant barrels are too close to other objects." Giant barrels keep the wide gap of a big piece (Q2T-4). [Q2N-11] Not re-rendered this pass (a single note; the user's scope).
