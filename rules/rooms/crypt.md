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

## Density and openness

| | Westwood (28) | Profile |
|---|---|---|
| coverage | 0.01-0.08-0.23 | 0.08-0.30 (target 0.16) |
| open floor | 0.45-0.75-0.91 | 0.40-0.85 |
| pieces per tile | 0.04-0.08-0.20 | 0.06-0.40 |
| distinct types | 1-3-14 | 3+ |
| caps | | tombs 1 per 5 tiles, at most 30 |

## Size

30-200 tiles (Westwood's catacombs reach 400).

## Culture variants

`dark_crypt`: LOTD tombstones in rows, mana obelisks at the walls, sconces and candles, bones and skulls strewn.

## Common mistakes

- One sarcophagus in a 58-tile crypt, 5% covered (Thornwick v0.1).
- Only coffins: a crypt with nothing but its rows and no wall used reads as a store of coffins (the room score flags a
  crypt with under 3 kinds of piece and no wall used).

## Examples

- Westwood: Wiz02A / Con07B, cell 169,176 (235 tiles, 14-17 types, coverage 0.06, open 0.74); G_CryptD, cell 42,24
  (209 tiles).
- Ours: Thornwick's family crypt (see `review/out/Thornwick/rooms/`).
