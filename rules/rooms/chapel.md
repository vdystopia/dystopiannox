# Chapel

Family: ceremonial. Feel: **open**, ordered toward one end. Kit kinds: `chapel` (a town's nave), `dark_chapel` (the Land
of the Dead's: a barrow hall, an ice temple). Profile: `kit/roomtypes.py TYPES["chapel"]`.

## Purpose and feel

A place of worship: people come in, walk up an aisle and sit facing the altar. The pews are a few rows near the altar,
not a carpet of benches; the back of the nave, toward the door, stays open. Quiet, symmetric, the eye drawn to the altar.

## Focal point

The altar (Dun Mir's, or the lich god's statue in the Land of the Dead) on the wall straight across from the main door, in
line with it (`door=True` in the compose step; an inner door keeps 6 units off that line: `building.ALTAR_ROOMS`).
Statues stand either side of it.

## Pieces

- Must: the altar; pews (4+); statues (2+).
- May: a colonnade down the nave, a pair of sarcophagi behind the pews, tapestries, plants in the corners, a chest.
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

## Density and openness

| | Westwood (4 chapels and temples) | Profile |
|---|---|---|
| coverage | 0.05-0.08-0.09 | 0.05-0.18 (target 0.10) |
| open floor | 0.66-0.81-0.83 | 0.55-0.88 |
| pieces per tile | 0.04-0.10-0.20 | 0.08-0.35 |
| distinct types | 2-3-6 | 8+ (6 in the Land of the Dead) |
| caps | Wiz07F: 8 benches in 123 tiles | pews 1 per 10 tiles, at most 16; columns 1 per 24 tiles, at most 8; statues 1 per 24, at most 6; sarcophagi 2 |

## Size

60-260 tiles; longer than wide, the altar at the end of the long axis.

## Culture variants

- Town (Dun Mir altar): pews (Bench, LightBench), Statue2, cathedral columns, sarcophagi (Crypt pieces).
- Land of the Dead (`dark_chapel`): the lich god's statue over the altar, mana obelisks and arks along the walls,
  judgement balances in a pair, LOTD tapestries and sconces, bones strewn; obelisks 1 per 18 tiles, tombstones 1 per 28,
  LOTD columns 1 per 30 (Ambermere's 300-tile barrow had a block of 20 obelisks and arks down its middle).

## Common mistakes

- "way too many benches and not enough object diversity ... too many of the same object (chapel benches, tavern tables
  and chairs)" (Greywatch, 2026-10-05: 46 pews wall to wall).
- The altar beside the door instead of across from it, the aisle off the door's line, half the nave bare (Ambermere
  review, 2026-10-05: 6% covered).
- A god statue among a block of 8 columns (a barrow): columns go in pairs either side of the aisle.
- Filling the nave to a house room's coverage (the old target was 0.18): the floor toward the door is meant to be open.

## Examples

- Westwood: Wiz07F, cell 143,201: a temple of 123 tiles, 8 benches facing the far end, 6 columns, 8 tapestries, 2
  statues: coverage 0.05, open 0.66.
- Westwood: G_LOTD, cells 40,72 and 70,210: the lich god's statues in 79-81-tile rooms, open 0.71-0.81.
- Ours: Thornwick's and Greywatch's naves after the type split (see `review/out/<map>/rooms/`).
