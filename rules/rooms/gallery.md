# Gallery

Family: ceremonial. Feel: **open, the walls the show**. Kit kind: `gallery` (a manor's or a college's long gallery).
Profile: `kit/roomtypes.py TYPES["gallery"]`.

## Purpose and feel

A long room to walk and look: paintings hung along both back walls at even spacing, a bench or two in the middle facing
them, statues in pairs, one curio, plants in the corners. The floor is open: the walls are the show. Westwood's one
gallery (in the Galava house the Conjurer and Warrior campaigns share) is 210 tiles of paintings, lanterns and plants.

## Focal point

The paintings along the back walls.

## Pieces

- Must: paintings (6+ hung; 4+ to read as a gallery), a bench.
- May: a second bench, a pair of statues, statues toward the far corners, an orrery as a curio, plants in the corners, a
  tapestry of one colour.
- Never: tables, desks, beds, shelves, stoves, forges, bars, counters, racks, an altar, tombs, barrels, crates, sacks,
  trophies.

## Composition

- **Back walls:** paintings at the middle and the ends of every stretch, at least 3 units apart (ROOMS["gallery"]
  ["decor_at"] = "any").
- **Front walls:** plants in the corners; a statue toward each far corner in a big gallery.
- **The middle:** a bench or two facing the walls, a pair of statues, one curio; open floor to walk the walls.
- **Movement:** along the walls, from one painting to the next.

## Density and openness

| | Westwood's campaign (1 room) | Profile |
|---|---|---|
| coverage | 0.01 | 0.00-0.14 (target 0.04) |
| open floor | 0.95 | 0.65-0.97 |
| pieces per tile | 0.12 | 0.04-0.35 |
| distinct types | 10 | 5+ |
| caps | 7 paintings, 9 plants in 210 tiles | benches 1 per 30 tiles, at most 6 |

## Size

60-260 tiles (Westwood's: 210).

## Culture variants

None.

## Where people stand

The curator beside a statue, else against a back wall between the paintings, facing the room; never before a painting
or between the benches. (`STANDS["gallery"]`: beside a statue, a back wall.)

## Common mistakes

- One painting a wall (the first lab version: kit/furnish.py place_decor hangs one hanging at the middle of each stretch;
  the gallery asks for the ends too).
- Furniture in a row down the middle: the furniture must reach the room's ends (validate/checks.py SPREAD_MIN), so the
  statues go toward the far corners.

## Examples

- Westwood: Con07E / War07D, cell 203,112 (208-210 tiles: seven paintings, sixteen lanterns, nine plants, an orrery, blue
  tapestries, two flame basins, a statue).
- Ours: the room lab's galleries.
