# Throne room

Family: ceremonial. Feel: **open and processional**, with character. Kit kind: `throne_room` (the keep's, the college's
Hall of the Star). Profile: `kit/roomtypes.py TYPES["throne_room"]`.

## Purpose and feel

Where a lord sits in state and is approached. The visitor enters at one end and walks the length of the room toward the
seat: the room is built for that walk. It is the opposite of a study: few pieces, much open floor, every piece placed for
effect and most of them in pairs. Its character comes from variety (statues, braziers, columns, tapestries of one colour,
a carpet) and from symmetry, never from more of one piece.

## Focal point

The throne (Dun Mir's four-piece throne, or the lich's in the Land of the Dead), centred on the NW wall, facing SE down
the room to the door in the SE wall, in line with it. Westwood's Dun Mir throne faces SE only, so it stands on the NW
wall; the building gives the room its door on the SE wall (`building._seat_throne`).

## Pieces

- Must: the throne; statues (4+), two flanking the throne against its wall; hangings (2+); columns (2+, in pairs).
- May: braziers or floor candelabras before the dais, a carpet runner, a bench or two by the walls for those who wait,
  plants in the corners, a chest.
- Never: tables, beds, desks, stoves, shelves of any kind, racks, stores (barrels, crates, sacks), hunting trophies,
  straw. Nothing in the aisle.

## Composition

- **NW wall (the back):** the throne centred, statues flanking it, braziers before the dais; tapestries of one colour
  either side.
- **NE wall:** tapestries of the same colour.
- **SE wall:** the door, in line with the throne.
- **SW wall and front corners:** a bench or two; plants.
- **The middle:** a carpet runner and a clear aisle from the door to the throne; a few pairs of columns spread down the
  whole length, set back from the walls (never a row down the middle); pairs of statues between the columns, facing each
  other across the aisle.
- **Movement:** straight in through the door and up the runner to the throne; nothing within 12 units of the door's
  line but the runner.

## Density and openness

| | Westwood's campaign (4 rooms, Con06b, Con10d, Con11a, Wiz11A) | Profile |
|---|---|---|
| coverage | 0.01-0.03-0.05 | 0.03-0.12 (target 0.06) |
| open floor | 0.81-0.93-0.94 | 0.65-0.92 |
| pieces per tile | 0.02-0.10-0.11 | 0.10-0.35 |
| distinct types | 5-8-11 | 9+ (the user asked for character) |
| caps | halls: 6 columns at the median | columns a pair per 26 tiles, at most 8; statues 1 per 14 tiles, at most 10; benches 2 |

## Size

60-260 tiles; long rather than square, the throne at the far end of the long axis.

## Culture variants

- Dun Mir (the kit's): DunMirThrone, Statue2 statues, Column5-8 or cathedral columns, tapestries.
- Land of the Dead: the lich's throne with its base and shadow, mana obelisks, LOTD tapestries and columns, candelabras:
  the Lich Lord's room in Con10d (356 tiles, coverage 0.03, open 0.85, with the judgement balances and arks), the
  finale's in Con11a (296 tiles, 0.01, 0.93) and Wiz11A's niche (84 tiles, 0.05, 0.81). (The 50-tile G_LOTD room this
  brief once stood on is a quest map's.)

## Common mistakes

- "The throne at the end of the room is facing sideways towards the store room. The pillars are in the dead center of
  the room, making walking straight in through the door impossible. There are also two statues that mysteriously face
  directly against the wall." (Greywatch's keep, 2026-10-05)
- "The throne room is also kind of empty and barren. It's just a long room with tons of the same exact pillars. It
  doesn't have any character." (Starwell's Hall of the Star, 2026-10-05: 22 columns 3.4 units apart down both sides,
  hunting trophies on the walls)
- Filling the floor to a house room's coverage: a throne room is open by nature (the user: "should, by its nature, be
  more open with less object density").
- An orrery or any curio in the aisle: it stands in the way of the throne's view of its door.

## Examples

- Westwood: Hecubah's throne room in Con06b, cell 55,144 (492 tiles; it ends in the void and its walls are half crystal,
  so `rules/rooms/westwood.py` reads it by hand: `HAND`): the three-piece Dun Mir throne looks down a runner to its
  doors, wolf statues flanking it, flame basins in pairs along the runner: coverage 0.01, open 0.94.
- Westwood: the Lich Lord's throne room in Con10d (War10d, Wiz10d), cell 89,143: 356 tiles, the lich's throne on its
  base, six LOTD columns, fourteen tapestries, obelisks, the judgement balances: coverage 0.03, open 0.85.
- Westwood's campaign has 4 throne rooms (Con06b, Con10d, Con11a, Wiz11A), all read by hand; none is a town's. The
  profile stays fuller than they are (the user's choice: character, a pair of columns and statues), and smaller
  (60-260 tiles against their 84-492).
- Ours: Starwell's Hall of the Star (seed 4, room 6, 170 tiles): the throne on the NW wall down a runner, statues and
  braziers, four pairs of columns, statues across the aisle, tapestries of one colour: coverage 0.04, open 0.81,
  13 types (`review/out/Starwell/rooms/06.png`).
