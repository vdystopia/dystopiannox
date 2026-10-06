# Winch room

Family: work. Feel: **open, mechanical**. Kit kind: `winch_room` (the machinery behind a castle's gate, a lift, a
drawbridge or a mill). Profile: `kit/roomtypes.py TYPES["winch_room"]`.

## Purpose and feel

The room that works a gate, a lift or a bridge: gear trains on the walls turning the shafts that run through them, the
great winch standing free with room to work it, spare parts and tools by the front walls. Westwood builds six of them,
nearly empty but for the machinery: the gears are the room.

## Focal point

The great winch (PulleyGear) standing free.

## Pieces

- Must: gear trains on the walls (Gear1-6, 2+), the winch, a barrel of tools or a crate.
- May: small gears (MechGear) on the floor, crates of spare parts, a second winch in a big room.
- Never: beds, tables, chairs, desks, shelves, hearths, stoves, rugs, plants, lab pieces, an altar, a throne.

## Composition

- **Back walls:** the gear trains, each on its own stretch.
- **Front walls:** tool barrels and crates of spare parts.
- **The middle:** the winch with room all round it to work it; small gears by it.

## Density and openness

| | Westwood's campaign (6 rooms, 6 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.00-0.03 | 0.02-0.25 (target 0.10) |
| open floor | 0.91-1.00-1.00 | 0.45-0.98 |
| pieces per tile | 0.00-0.00-0.06 | 0.00-0.60 |
| distinct types | 0-0-6 | 1+ |

Gears and winches have no furniture family (rules/room_types.py): Westwood's winch rooms measure as empty, and so do ours
but for their barrels and crates.

## Size

12-180 tiles (Westwood's: 12-180).

## Culture variants

Dun Mir's (Con06a's lever room): flame basins, a floor lever.

## Where people stand

The winchman beside the winch, else by a gear train. (`STANDS["winch_room"]`: beside the winch, beside a gear, a back
wall.)

## Common mistakes

- Four winches in a row (the first lab version): one great winch, a second only in a room of 150 tiles or more.
- Floor levers: Westwood's work a gate by script. An unscripted lever invites a pull that does nothing: leave them to
  the story's mechanisms.

## Examples

- Westwood: Con06a, cell 96,146 (110 tiles: eighteen gears, a pulley gear, a floor lever, flame basins); War07A, cell
  134,219 (63 tiles: gears and three pulley gears); War02b, cell 56,224 (180 tiles: gears, pulley gears, a lift, tool
  barrels, crates); Con01A, cell 91,146 (82 tiles); War02A, cell 216,208 (12 tiles); Wiz03a, cell 240,22 (25 tiles: a
  lift pit and a gear).
- Ours: the room lab's winch rooms.
