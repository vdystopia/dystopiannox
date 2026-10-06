# Library

Family: work. Feel: **full of books, quiet**. Kit kind: `library` (a college's, a manor's, an observatory's chart
room, a temple's). Profile: `kit/roomtypes.py TYPES["library"]`.

## Purpose and feel

Books, and a place to read them. Walls of bookcases end to end; in a big library, stacks in rows down the middle with
aisles; a reading table on a carpet.

## Focal point

The lined back walls themselves, the desk among the bookcases.

## Pieces

- Must: bookcases (6+); a reading table.
- May: a desk with its chair, chairs at the table, a carpet, a curio (telescope, orrery, globe), a hearth, statues,
  hangings, plants.
- Never: beds, stoves, forges, bars, counters, racks, an altar, a throne, tombs, straw; stores.

## Composition

- **A back wall:** bookcases end to end, the desk among them.
- **The other back wall:** bookcases end to end.
- **Front walls:** a statue, a plant.
- **The middle:** in a big library, stacks of bookcases in rows (never on the carpet); the reading table with its chairs
  on a carpet; a curio.
- **Movement:** aisles between the stacks; a way from the door to the table.

## Density and openness

| | Westwood's campaign (7 rooms, 5 maps) | Profile |
|---|---|---|
| coverage | 0.06-0.12-0.19 | 0.10-0.32 (target 0.17) |
| open floor | 0.50-0.63-0.76 | 0.30-0.80 |
| pieces per tile | 0.17-0.33-0.38 | 0.25-0.90 |
| distinct types | 8-12-19 | 8+ |
| walls with a purpose | 2-4-4 | 3+; back walls 50%+ lined |

## Size

30-200 tiles (Con07D's great library is 494).

## Where people stand

The librarian beside his desk, else by the bookcases; never in the stacks' aisles or at the reading table. (`STANDS["library"]`: beside the desk, beside a bookcase, a back wall.)

## Common mistakes

- "put bookshelves end to end for the entire length of the wall" (TreePlace v0.3): never a lone shelf on a long wall.
- A study with two bookcases is not a library, and a library with few books reads as a study.
- Harrowby playtest (2026-10-05, HB-4): "The shelves lining the northwest and northeast walls are the kind of objects that can be used to span an entire wall, lined up side by side." Bookcases are the fabric that lines walls (Westwood: 69% of them in runs of 3 or more); statues, candelabras and chests are not (kit/objects.py role).

## Examples

- Westwood: War07A, cell 119,187 (72 tiles, 19 types); Wiz01A, cell 108,137 (128 tiles, 15 types).
- Ours: Starwell seed 4, room 5, the star charts (48 tiles); room 7, the college library (162 tiles, stacks in rows).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's 7 campaign libraries keep the middle bare, hold no plants or curios, warm themselves at a hearth (3 of
  7) and seat their readers at round or oval tables; stacks of bookcases down the middle belong only to a great
  library (Con07D's 494 tiles). The recipe now: the hearth sometimes, the desk among bookcases on one back wall, the
  other back wall lined end to end (the user's HB-4), a reading table with chairs, a chest; stacks past 100 tiles.
- Still a giveaway: back walls lined far more than Westwood's (0.65 against 0.11), a constraint of the house rules
  (no bookcase on a front wall; a room at least as covered as Westwood's median).
