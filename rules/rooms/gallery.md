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

## Learned in the room lab (2026-10-05, track B; review/roomlab/LOG_tuneB.md)

Westwood's gallery (Con07E, curated) shows its pieces apart, each in its own bay along the walk: the orrery, a flame
basin, crystals among plants, a statue; paintings and blue tapestries hung between them. So: exhibits toward the walls,
not a bench group in the middle; a bench at most; paintings hung on every free stretch (the room is decorated). Still
missing: the bays themselves (the shell) and enough exhibits for a room of 200 tiles.

## QA round 1 (2026-10-13): the round's lessons as rules

The user rated other types in round 1 and asked that the round's themes apply to this one too: "Much of the feedback
boiled down to" rooms too empty with too little diversity, and no balance or symmetry ("things placed randomly, not
lined up with each other"). Composed by `kit/civic.py` (`civic.gallery`); ledger `review/qa1/civic.md` (Q1A-n).
These rules come before Westwood's statistics above wherever they disagree (the user's word over Westwood's habit).

Every room of the type:
- **The dead space is used** (Q1A-1, Q1A-7): the S corner takes a group of its own; the front corners and the SE and
  SW walls take mixed stock, benches or urns, mirrored; where the floor is still bare a group goes there, bigger rooms
  more. Checked: `civic.s_corner`.
- **Diversity** (Q1A-2): several kinds of piece, more in a bigger room; heaps mix their kinds (never one family alone,
  never the same piece side by side). Checked: `civic.kinds`.
- **The back walls dressed** (Q1A-3): the NE and NW walls hung at even steps, mirrored about each stretch, one
  tapestry colour to a room; a bare stretch takes a pair of the type's wall piece. Checked: `civic.bare_wall`.
- **Balance** (Q1A-4, Q1A-13): pieces centred on their wall or between a piece and a wall; mirrored pairs; one kind of
  table, column, statue to a room; lights in matching corners or flanking the focal piece.
- **Carpets** (Q1A-10): a table set at its carpet's exact middle; a carpet only where its whole rectangle and trim
  lie on the room's floor.

For this type:
- Composed on the axis from the door: a runner down it; statues and flame basins in mirrored pairs at even steps
  beside it, benches and urns mirrored by the side walls.
- Paintings first, then blue tapestries, at even steps along both back walls, mirrored about each stretch.
- Plants in matching corners (a gallery is the one type whose Westwood rooms hold plants); lights in matching corners.
