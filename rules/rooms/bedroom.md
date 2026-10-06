# Bedroom

Family: private. Feel: **cosy and full**. Kit kind: `bedroom` (a family's, an innkeeper's, a lord's chamber). Profile:
`kit/roomtypes.py TYPES["bedroom"]`.

## Purpose and feel

Where one person (or a couple) sleeps and keeps their things. Small, personal, full: the bed, a chest, shelves, a place
to sit, something on the walls. Westwood's commonest building room (50 measured). The user: "many of the smaller
office/bedroom-type rooms seem to be very good".

## Focal point

The bed, headboard against a back wall, its nightstand beside it (apart from it, not touching).

## Pieces

- Must: one bed (two at most, side by side, in a couple's room); a chest.
- May: a nightstand, a run of bookcases end to end, a desk with its chair or a small table with chairs toward the front,
  a bench, a rug before the chest or a carpet, hangings on the back walls, plants in the corners, potion shelves (once).
- Never: three or more beds (that is a barracks), stores (barrels, crates, sacks), stoves, forges, bars, counters,
  racks, an altar, a throne, tombs, straw.

## Composition

- **A back wall:** the bed, headboard to the wall, the nightstand beside it; a run of shelves end to end.
- **The other back wall:** the chest snug and centred, a rug before it; hangings.
- **Front walls:** a desk or a small table with its chair; a bench.
- **The middle:** a rug or a carpet; clear enough to walk from the door to the bed.
- **The door:** a single door (never a double door into a bedroom), not in front of the bed.

## Density and openness

| | Westwood's campaign (40 rooms, 14 maps) | Profile |
|---|---|---|
| coverage | 0.05-0.14-0.23 | 0.11-0.28 (target 0.14) |
| open floor | 0.34-0.57-0.79 | 0.30-0.80 |
| pieces per tile | 0.11-0.42-0.67 | 0.25-1.0 |
| distinct types | 4-7-12 | 8+ (fewer in a small room) |
| most of one stand-alone piece | 1-2-6 | 3, or 1 per 20 tiles |
| walls with a purpose | 2-2-3 | 3+ (2 under 32 tiles); back walls 25%+ lined |

## Size

14-60 tiles; a lord's chamber up to 90.

## Culture variants

Dun Mir bedrooms (23 of Westwood's 50) take Dun Mir chests and hangings; an ogre sleeps in a den (see barracks).

## Common mistakes

- "Bedroom: very empty; nightstand too close to the bed" (TreePlace review).
- "Bedroom behind the bar: chests and rugs not centred" (DysVale review).
- A double door into a bedroom: "not believable".
- Barrels in a bedroom (DysVale v0.3: the checker's first identity finding).
- A big chamber filled with tables and chairs until it reads as a dining room: one sitting group, then open floor.
- Harrowby playtest (2026-10-05, HB-3): "Too many treasure chests in this room. Let's be real. Why are there four treasure chests? ... Hard rule: A bedroom should never have more than one table and chair set." One chest (two in a chamber of 100 tiles or more: kit/objects.py chest_cap), one table or desk with its chairs (the furnisher's `sets` rule; checker `pieces.chests`, `pieces.sets`).

## Examples

- Westwood: Wiz03b, cell 78,85 (98 tiles, 18 types); Con06b, cell 116,182 (132 tiles, Dun Mir). (G_ForesD's
  63-tile bedroom, once cited here, is a quest map's: not campaign evidence.)
- Ours: Starwell seed 4, room 10, the archmagister's chamber (36 tiles, 15 types, coverage 0.14, open 0.48), and room
  13, the innkeeper's room (28 tiles, 15 types): the smaller bedrooms the user praised.
