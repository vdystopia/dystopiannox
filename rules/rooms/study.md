# Study

Family: private. Feel: **full, balanced, themed**. Kit kind: `study` (a steward's, a reeve's, a foreman's office; an
archmagister's study). Profile: `kit/roomtypes.py TYPES["study"]`.

## Purpose and feel

One scholar's or official's room for work and for receiving a visitor: the desk, the books, a table to talk at, a few
things of the owner's trade or taste. It is full, every wall used, everything of one theme, nothing repeated that stands
alone. The user's exemplar of a very good room is a study: "It feels very full, balanced, and themed."

## Focal point

The desk with its chair, centred on a back wall, bookcases either side of it to the corners.

## Pieces

- Must: the desk; bookcases (2+); a chest.
- May: a round or square meeting table with chairs on a carpet; a curio (a telescope, an orrery, a crystal globe);
  statues; hangings between the bookcases; plants; a lab piece for a wizard (an alchemist's desk, once); candelabras.
- Never: beds, stoves, forges, bars, counters, racks, an altar, a throne, tombs, straw; stores (barrels, crates,
  sacks); a dining table (Table1-4).

## Composition

- **NW wall (or the back wall with the most room before it):** the desk centred with its chair, bookcases either side of
  it to the corners (`line near=desk`).
- **NE wall:** bookcases end to end with a hanging between, the chest (`line other`, `storage at=center`).
- **Front walls:** statues between candelabras; plants in the two front corners.
- **The middle:** one group that shows the use, a round table and two chairs on a carpet of floor tiles; one curio
  standing free.
- **Movement:** from the door to the desk, past the meeting table; the door is never on the desk's wall line.

## Density and openness

| | Westwood's campaign (2 rooms, Con02a) | Profile |
|---|---|---|
| coverage | 0.07-0.10-0.10 | 0.09-0.30 (target 0.17) |
| open floor | 0.70-0.78-0.78 | 0.32-0.85 |
| pieces per tile | 0.21-0.31-0.31 | 0.25-0.90 |
| distinct types | 7-9-9 | 12+ (fewer in a small room) |
| most of one stand-alone piece | 4-5-5 | 3, or 1 per 25 tiles (chairs at their table not counted) |
| walls with a purpose | 3-4-4 | 4; back walls lined 35%+ |

## Size

30-120 tiles.

## Culture variants

A wizard's study (Starwell) takes a telescope or orrery and an alchemist's desk; an official's (Greywatch, Ambermere) a
ledger desk, a chest, trophies or tapestries.

## Where people stand

The scholar at the side of his desk, else by his bookcases; never between the meeting table and its chairs. (`STANDS["study"]`: beside the desk, beside a bookcase, a back wall.)

## Common mistakes

- Three round-table groups in a 143-tile reeve's study (Harrowby): a study takes its meeting table and at most one
  sitting group; no dining set.

- "Study: too small and empty" (DysVale review): too small a room for its kind, and too few pieces.
- Single-instance shelves lining a wall: potion shelves and showpieces stand once.
- A second table set beside the meeting table: it turns the study toward a dining room.
- Harrowby playtest (2026-10-05, HB-4, the reeve's library): "There are two statues way too close to each other ... Too many candelabras. The treasure chest should be centered between the end of the bookcase and the door." Statues 2 units apart unless a pair flanking something, two to a wall at most; candelabras by the room's size (kit/objects.py light_cap: 4 in 100-200 tiles); a chest between a door and a row of shelves stands centred between them (Furnisher.centre_by_doors; checker `pieces.clearance`, `pieces.lights`).

## Examples

- **Ours, the exemplar:** Starwell seed 4, room 9, the archmagister's study (66 tiles declared, 50 by the checker's
  count): "The room in the fifth screenshot is exceptional. It feels very full, balanced, and themed. This is an example
  of a very, very good room." The NW wall: the desk centred with its chair, bookcases either side to the corners. The NE
  wall: bookcases end to end with a trophy between, the chest. The middle: a round table and two chairs on a carpet, a
  telescope standing free. The front walls: statues between candelabras, plants in the front corners. Coverage 0.11,
  open 0.50, 26 pieces of 15-17 types, all four walls used, back walls 51% lined, the most of one stand-alone kind on a
  wall 2. (`review/out/Starwell/rooms/09.png`)
- "Many of the smaller office/bedroom-type rooms seem to be very good" (Starwell, 2026-10-05).
- Westwood: Con02a, cells 69,161 and 71,132: a desk among a few bookcases, a hearth, chairs (32 and 48 tiles).

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's studies are few (3 curated); the pool (libraries) puts the hearth with its bellows in 5 of 9 and no curio
in the middle. Adding the hearth made a study read as a living room (the room score's reads-as rule): left out. The
user's praised composition (SW-7) is kept; the chest now goes up before the bookcases take its wall (2 of 10 had
none), plants fewer.
