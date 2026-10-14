# Shrine

Family: ceremonial. Feel: **open, still, round one thing**. Kit kinds: `shrine` (a small holy room in a town, a keep or a
grove), `dark_shrine` (the Land of the Dead's). Profile: `kit/roomtypes.py TYPES["shrine"]`.

## Purpose and feel

A small holy room round one thing: an altar, a relic on its pedestal, the god's statue. Not a chapel (a congregation's
nave of pews): a shrine is visited one at a time. The holy thing faces the door down a short runner, statues flank it,
candles burn before it, a basin of fire in each front corner; a kneeling bench or two; the rest is open floor.

## Focal point

The altar (DunMirAltar; the lich god's statue in a dark shrine) on the wall across from the door, in line with it.

## Pieces

- Must: the altar, statues flanking it (2+).
- May: candles before it, a runner and a kneeling bench or two, flame basins (DunMirFlameBasinLit) in the front corners,
  a tapestry or two of one colour, statues in the far corners, plants.
- Never: tables, desks, beds, hearths, stoves, shelves, forges, lab pieces, bars, counters, racks, barrels, crates,
  sacks, trophies.

## Composition

- **The back wall across from the door:** the altar centred, a statue either side, candles before it.
- **The other back wall:** a tapestry or two.
- **Front walls:** the door; a basin of fire in each corner.
- **The middle:** a runner from the door to the altar, a kneeling bench or two either side; open floor.
- **Movement:** straight from the door to the altar.

## QA round 1: the themes applied (2026-10-13)

The user rated other types in QA round 1 and asked that the round's themes apply to this one ("Much of the feedback
boiled down to": too empty, not enough object diversity; no balance or symmetry, things placed randomly, not lined up
with each other). These rules override the Westwood-measured sparseness above where they differ; `kit/works.py`
composes the room by them after the recipe (its loose pieces are taken up first: `SPEC[kind]['keep']`), ledger
`review/qa1/works.md` (Q1B-n).

- **The axis** from the main door to the altar on the far wall (the user: "Chapels should always be aligned with the
  main door. The character should walk in and be on the main path facing the altar"): a runner down it, centred (three
  floor squares on a square's middle, two between; only where the room is wide enough); an avenue of obelisks in
  mirrored pairs at even steps lining the runner and the door's way in; a pair of kneeling benches either side in a wide
  shrine (one pair: four or more is a chapel); flame basins in the two far corners (and the near ones in a big shrine);
  a pair of tapestries on the far wall either side of the altar, else one on a bare back wall; a chest against a back
  wall. Never a lone statue or bench outside the mirrored pairs.
- **dark_shrine:** the same axis with the Land of the Dead's pieces: the lich god's statue, mana obelisks, incense
  basins, coffins in mirrored pairs along the side walls, bone heaps mirrored, the Land of the Dead's tapestries or
  banners on the bare back walls.
- **Never emptier:** the room ends with at least the visible pieces and kinds its recipe gave it, and master's lab
  average for the type (a tenth more in a room of 80 tiles; `SPEC[kind]['least']`, `Finish.top_up`); bones, candles
  and small gears are one kind at most and never count as pieces.

## QA round 2 (2026-10-14, ledger `review/qa2/ledger.md` Q2V-2)

The user (mean 4.2): RM-SHRINE-02 (dark shrine): "The mana obelisk is too close to the statue." 03: "The mana obelisk
arrangement is not centered on the carpet." 04: "The northeast side of the carpet is not properly bordered." (01, 05
kept.)

- **Centred on the room** (Q2T-1): the shrine is composed on the room's middle across the line from its main door
  (`works.axis_along`); a shrine's outside door stands in its wall's middle (`building.CENTRE_DOOR_ROOMS`; not the dark
  shrine's, whose small many-doored rooms the user rated 4 and 5 as they were). The recipe's altar or lich statue on
  the far wall off that line is set on it again.
- **The square centred on its carpet** (Q2T-2): the editor draws a floor square half a square (one unit) further to the
  SW than the kit counts it (measured on a lone rug tile; `works.SQUARE_V`), so the carpet's squares are chosen about the
  altar as drawn: 4 x 4 squares on a seam, 3 x 3 or 5 x 5 on a square's middle, the four obelisks the same 1.25 (or 0.85)
  units in from its edges on every side.
- **A carpet bordered all round** (Q2T-6): a carpet is laid only where every square of its trim stands on the room's
  floor, clear of the walls (`Finish.carpet`); in a shrine too narrow for that the square of obelisks stands without a
  carpet rather than with a trim missing along a wall.
- **Clear gaps** (Q2T-4): the obelisks keep 0.9 units from the altar and from the lich statue (`BIG_GAP`); the flanking
  pair stands that much further out; an obelisk the recipe set hard against the statue is taken up first.

## Density and openness

| | Westwood's campaign (6 rooms, 6 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.04-0.06 | 0.00-0.14 (target 0.05) |
| open floor | 0.72-0.97-1.00 | 0.65-0.97 |
| pieces per tile | 0.00-0.11-0.16 | 0.04-0.40 |
| distinct types | 0-1-2 | 4+ |
| caps | | benches 1 per 20 tiles, at most 3 (four or more is a chapel) |

## Size

12-120 tiles (Westwood's: 12-136).

## Culture variants

`dark_shrine` (Con10c / Wiz10c, Con10d, Wiz11A): the lich god's statue, mana obelisks either side, incense basins burning
(LOTDIncenseBasinLit), LOTD tapestries and sconces, bones strewn; no benches.

## Where people stand

The priest (or the keeper of the relic) at the altar's side, past the statue that flanks it; never on the runner or
before the altar. (`STANDS["shrine"]`: beside the altar, a back wall.)

## Common mistakes

- Rows of pews: four benches or more is a chapel (`reads_as`).
- The altar on a side wall, the visitor coming at it sideways (the chapel's rule: across from the door).

## Examples

- Westwood: Con10c / Wiz10c, cell 30,140 (66-72 tiles: four incense basins, a chest, a pentagram); Con10d, cell 132,51
  (136 tiles: the orb pool among candles, in a cave); Con07H, cell 118,85 (12 tiles: the Heart of Nox on its pedestal); Wiz11A,
  cell 50,215 (36 tiles: mana obelisks and a book); Wiz02B, cell 120,120 (25 tiles: four obelisks, a book, bones);
  Con07D, cell 118,78 (42 tiles: four candelabras, four obelisks, a chest).
- Ours: the room lab's shrines and dark shrines.

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

Westwood's five shrines (curated: Con07D, Wiz02B, Wiz11A's three) are built round a ring, not an altar wall.
- **Four obelisks in a diamond** (at the screen's top, bottom, left and right) round the holy thing in the open middle,
  a ring of carpet under them on a built floor (Con07D); the holy thing is the altar where the room has the floor for it,
  else a basin of fire, else bare floor (Westwood's: a key or a spell book). Clear of the doors' lines (GW-7).
- Candelabras in the corners, a chest, a tapestry or two; **no plants, no statues of the town's kind.**
- **The Land of the Dead's** niche is a shrine by its mana obelisks; the lich god's statue only where it fits.
