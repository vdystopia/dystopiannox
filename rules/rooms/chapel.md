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

| | Westwood's campaign (1 room, Con07B) | Profile |
|---|---|---|
| coverage | 0.06 | 0.05-0.18 (target 0.10) |
| open floor | 0.62 | 0.55-0.88 |
| pieces per tile | 0.20 | 0.08-0.35 |
| distinct types | 7 | 8+ (6 in the Land of the Dead) |
| caps | Wiz07F: 8 benches in 123 tiles | pews 1 per 10 tiles, at most 16; columns 1 per 24 tiles, at most 8; statues 1 per 24, at most 6; sarcophagi 2 |

## Size

60-260 tiles; longer than wide, the altar at the end of the long axis.

## Culture variants

- Town (Dun Mir altar): pews (Bench, LightBench), Statue2, cathedral columns, sarcophagi (Crypt pieces).
- Land of the Dead (`dark_chapel`): the lich god's statue over the altar, mana obelisks and arks along the walls,
  judgement balances in a pair, LOTD tapestries and sconces, bones strewn; obelisks 1 per 18 tiles, tombstones 1 per 28,
  LOTD columns 1 per 30 (Ambermere's 300-tile barrow had a block of 20 obelisks and arks down its middle).

## Where people stand

The priest at the altar's side (past the statue that flanks it); the faithful in the pews. Never on the runner, before the altar or in the aisle. (`STANDS["chapel"]`: beside the altar, a back wall.)

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
