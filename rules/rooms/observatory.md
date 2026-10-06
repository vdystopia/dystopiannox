# Observatory

Family: work. Feel: **balanced, scholarly**. Kit kind: `observatory` (an astronomer's room in a wizards' town, a tower
top). Profile: `kit/roomtypes.py TYPES["observatory"]`.

## Purpose and feel

Where the sky is watched and charted: telescopes, one at a wall and one or an orrery standing free, star charts and
zodiacs hung between the bookcases, the astronomer's desk, the chart table. A study turned to the sky: it shares the
study's desk and books, but its pieces are instruments and its walls are charts.

## Focal point

A telescope (or an orrery) standing free with room round it.

## Pieces

- Must: a telescope or an orrery (1+), the desk, bookcases (2+), star charts or zodiacs on the walls (2+).
- May: a telescope at a wall, the chart table with stools, a chest, plants.
- Never: alchemists' desks and workstations (a laboratory's), beds, stoves, forges, bars, counters, racks, an altar,
  barrels, crates, sacks.

## Composition

- **A back wall:** the desk near a corner with bookcases either side; star charts hung between.
- **The other back wall:** a telescope at the wall; zodiacs and charts.
- **Front walls:** a chest; plants in the corners.
- **The middle:** the free telescope or the orrery with room round it; the chart table with its stools.

## Density and openness

| | Westwood's campaign (2 rooms, 2 maps) | Profile |
|---|---|---|
| coverage | 0.00-0.16 | 0.03-0.24 (target 0.12) |
| open floor | 0.39-0.98 | 0.45-0.90 |
| pieces per tile | 0.07-0.30 | 0.10-0.60 |
| distinct types | 5-18 | 8+ |
| caps | 3 telescopes (Con07B) | instruments 1 per 20 tiles, at most 4; each showpiece once (twice in 120+ tiles) |

## Size

40-200 tiles (Westwood's: 97-140).

## Culture variants

Galava's (Con07E's star hall): blue tapestries, star charts, gargoyles and lanterns, no instruments.

## Where people stand

The astronomer beside the telescope, else by his desk. (`STANDS["observatory"]`: beside a telescope, beside the desk, a
back wall.)

## Common mistakes

- A laboratory with a telescope: no workstations, no alchemist's desk.
- A row of telescopes: each instrument is a showpiece (kit/furnish.py SHOWPIECES).

## Examples

- Westwood: Con07B / War07A, cell 121,219 (97 tiles: three telescopes, a desk, statues and gargoyles, crates and
  barrels of the stores); Con07E, cell 172,104 (140 tiles: eight star charts, blue tapestries, gargoyles, lanterns).
- Ours: the room lab's observatories; Starwell's observatory role holds a star-chamber hall that could become one.

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- No Westwood observatory survives the curation as its own type; by the laboratory's lessons: no plants, the chart
  table against a wall with its stools rather than alone in the middle, the desk among two bookcases, the pieces a
  step off the walls (`wall_gap`).
