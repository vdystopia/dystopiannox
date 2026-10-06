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

## Where people stand

The sleeper at the bed's side (never at its foot, where the chest is), else by the chest; never between the table and its chairs. (`STANDS["bedroom"]`: beside the bed, beside the chest, a back wall.)

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

## Learned in the room lab (tuneA, 2026-10-05)

Westwood's campaign bedrooms (40, then 31 once cells, guard posts and lords' chambers were retyped), piece by piece (review/roomlab/westwood_features.json), against ten generated a round:

- **What they hold**: the bed (26 rooms; a wood bed 8, a cot 6), a nightstand (25), bookcases (25: one alone in about
  half), a desk with its chair (22), a chest (27, Dun Mir or plain). Median 7 kinds of object. A table set in a third of
  them, mostly the bigger rooms, and never a table and a desk together (the HB-3 rule). **No plants** (0 of 40); hangings
  in one in six; a rug object in one in five (a bearskin or a red rug); a carpet laid in the floor tiles far more often.
- **Where**: everything against the two back walls (walls used: median 2). The bed headboard to a back wall about
  0.7 of the room's diagonal from the door, with its nightstand and the chest beside it (bed to chest 0.6 units); the
  desk and its chair with a bookcase beside it (0.66) on the other back wall. A bookcase may stand alone on a short
  stretch between a door and a corner.
- **What gave ours away** (classifier AUC 0.99 at the start): plants in the corners, trophies and tapestries, two rugs
  and a table set on a rug in the middle, a bench on a front wall, a third wall used, too many kinds (9.5 against 7).
- **A stamp reads worse than a mix** (the lesson of rounds r1-r6): a recipe that put Westwood's commonest layout in
  every room (the bed far from the door with the chest and nightstand at its head, the desk and a bookcase beside it,
  two walls used) brought the classifier's AUC from 0.99 to 0.83-0.88, but an independent blind judge picked it out
  more easily (8/10, scored 4.8) than the kit's own recipe (6/10, scored 6.4, above Westwood's 6.0): "the chest pressed
  against the bed's head, a desk crowding the bed, a lone bench on the SE wall with a candelabra, the carpet's middle
  empty, single pieces instead of a run of shelves". The measures are a check, the eye the judge.
- **The recipe now** (`kit/identity.py ROOMS["bedroom"]`, r7): the kit's composition (the bed headboard to a wall with
  its nightstand, the chest centred on its own back wall with a rug before it, shelves end to end, the desk with its
  chair or a small table set, a carpet in some) with Westwood's proportions: the desk in 0.7 of rooms, a table in 0.4,
  a bench in 0.3, a plant in 0.3, at most two hangings and no decoration pass (`decorate=False`).
- **What still gives them away**: the lab's rooms are plain rectangles with doors in the back walls, and 1.25 times
  Westwood's size: with Westwood's pieces they come out at 0.10-0.12 cover, just under the checker's sparse line
  (Westwood's median, 0.117). Westwood's bedrooms are shaped (L-rooms round an alcove, niches, a carpet laid to the
  shape) and carry an odd lived-in piece (a barrel, a crate, a spittoon) the brief forbids.
