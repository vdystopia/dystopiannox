# Smithy

Family: work. Feel: **balanced, hot and hard**. Kit kind: `smithy` (a village forge, a demon forge). Profile:
`kit/roomtypes.py TYPES["smithy"]`.

## Purpose and feel

The forge and the smith's counter: iron is worked at one end and sold over the counter at the other.

## Focal point

The forge's glowing coals (a cinder bin) centred on a back wall, the bellows beside them, the anvil before them.

## Pieces

- Must: the forge, the bellows and the anvil; water and tool barrels, crates of iron (2+); the counter.
- May: racks of pole arms, hanging swords and armour stands (three to a row, a row of each kind); a work table with a
  stool.
- Never: beds, desks, bookcases, an altar, a throne, tombs, lab pieces, a bar, rugs, plants, black-powder barrels.

## Composition

- **A back wall:** the coals centred, the bellows beside them, the anvil 2.4 units before them.
- **The other back wall:** swords and pole arms on racks.
- **Front walls:** water barrels, tool barrels, crates of iron.
- **The middle:** the counter set out from a back wall, the smith's spot behind it; a row of armour stands and a row of
  weapon racks.
- **Movement:** from the door to the counter; the forge behind.

## QA round 1: the themes applied (2026-10-13)

The user rated other types in QA round 1 and asked that the round's themes apply to this one ("Much of the feedback
boiled down to": too empty, not enough object diversity; no balance or symmetry, things placed randomly, not lined up
with each other). These rules override the Westwood-measured sparseness above where they differ; `kit/works.py`
composes the room by them after the recipe (its loose pieces are taken up first: `SPEC[kind]['keep']`), ledger
`review/qa1/works.md` (Q1B-n).

- **The forge** stands on a bordered square of brick centred under it ("place furnaces on a small brick square", nox17;
  Q1B-8).
- **Back walls:** a row of hanging swords and pole arms centred on the other back wall, armour stands closing it.
- **Corners and walls:** water barrels, steel crates and tool barrels heaped in the S corner, the same small heap in the
  W and E corners; heaps of iron and tools along the walls, never one kind.
- **The middle:** the counter the recipe set; in a big smithy stacks of stock in mirrored pairs on the axis.
- **Never emptier:** the room ends with at least the visible pieces and kinds its recipe gave it, and master's lab
  average for the type (a tenth more in a room of 80 tiles; `SPEC[kind]['least']`, `Finish.top_up`); bones, candles
  and small gears are one kind at most and never count as pieces.

## QA round 2 (2026-10-14, ledger `review/qa2/ledger.md` Q2V-3)

The user (mean 3.6): RM-SMITHY-01/02/05: "There is a barrel and a mannequin behind the desk where the shopkeeper would
be standing. There needs to be room for the shopkeeper." 02: "The floor border around the northwest side of the brick
surrounding the forge is missing." 03: "Just slightly overcrowded. Remove an object or two from the middle of the room
and move a few objects closer to the southwest wall." (04 kept.)

- **The keeper's space** (as the shop and the armoury): the floor between the counter's back and its wall, the counter's
  length and a little, holds nothing (`Finish.keeper_zones`: a zone every placement keeps out of, and the wall behind it
  is no bare stretch for the walls' racks or heaps). **Checked by** `composition.keeper_space` (STq2kpr).
- **The forge square bordered on every side that meets the floor** (Q2T-6): `works.brick_square` draws the square's
  edge on the side toward a door too (`shells.blend_pattern` keeps three cells clear of every door, which had left the
  NW side bare), short of the doorway itself; the square is chosen under the forge as drawn (`SQUARE_V`).
- **Not crowded in the middle** (Q2T-8): the middle's stacks two or three pieces in mirrored pairs on the long axis, the
  front walls a share more (`fill` 0.55); the top-up fills the walls, never groups at bare spots mid-floor (`no_bare`),
  and in a smithy of 100 tiles or more its extra pieces go on the walls only (`extras_walls`); a big smithy is filled to
  0.27 pieces a tile, a smaller one to 0.32 (round 2's own fullness, never emptier); big pieces (forge, counter) keep
  0.9 units clear; round 2's kinds of rack, barrel and crate kept (`keep_kinds`).

## Density and openness

| | Westwood's campaign (2 rooms, Con06b, War06b) | Profile |
|---|---|---|
| coverage | 0.01-0.06-0.06 | 0.10-0.38 (target 0.24) |
| open floor | 0.76-0.96-0.96 | 0.25-0.80 |
| distinct types | 3-6-6 | 10+ |

Westwood's forges are bare workshops; ours sell over a counter, so they hold more.

## Size

30-110 tiles.

## Where people stand

The smith behind his counter (the furnisher's keeper spot, StoryMap.shops), else beside the anvil; never among the racks. (`STANDS["smithy"]`: the keeper's spot, beside the anvil, beside the forge.)

## Common mistakes

- "The shopkeeper is standing in the middle of the shop, surrounded by a random scattering of objects ... He needs to be
  standing somewhere that makes sense, like behind a desk. Instead of six armor racks, use three armor racks and three
  weapon racks" (Starwell, 2026-10-05: the smith's shop too).
- Bellows without an anvil or coals read as hearth tools, not a forge.

## Examples

- Westwood: Con06b, cell 168,82 (47 tiles): Dun Mir's forge.
- Ours: Starwell seed 4, room 19, the forge (47 tiles, coverage 0.15).

## Learned in the room lab (2026-10-05, review/roomlab/LOG_tuneC.md)

- Westwood's one curated smithy (Con06b): the bellows and anvil, water barrels and barrels in a knot, a dark crate,
  two stools; coverage 0.06. The racks stand against the back walls, never in rows dead centre (the shop's independent
  judge: rows read as generated); the stores heap as a store's (`store_heaps`, water barrels leading). The counter
  stays (the user: the smith behind his counter).
