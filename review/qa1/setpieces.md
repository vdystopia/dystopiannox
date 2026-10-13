# QA round 1: exterior set pieces (shrine, well, graveyard, garden, farmyard and orchard, town square)

The user's QA round 1 feedback (2026-10-13, `review/reviews/QA-round1.md`, Exteriors > shrine, well, graveyard, garden,
farmyard; in-game screenshots nox2, nox6, nox7, nox13), in the columns of `review/FEEDBACK.md`. Over every exterior
the user's two themes: **spaces too empty, too few kinds of thing**, and **no balance or symmetry: things placed at
random, not lined up**. Both are answered in every row below: each set piece is now composed as a whole in its yard's
frame (`kit/yards.Frame`), mirrored about its way in, its rows even, with several kinds of thing in it.

Before: the kit at master b005f84 (round 1 as rated). After: branch `qa1-setpieces`. Pictures: before
`review/out/qa/round1/exteriors/<type>/`, after `review/out/qa/qa1-setpieces/exteriors/<type>/` (lab iteration
`qa1b`: `py tests/scenelab.py <scene> --n 10 --seed 11 --iter qa1b`, the round's own seed and plots).

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| Q1X-1 | shrine (all ten 1, drop): "Change shrines drastically. Give them a square or rectangular shape defined by obelisks and mana pillars or parallel statues that lead to a grand centerpiece. Needs much more structure." | P§2 Yards (a shrine is a court); `rules/scenes/shrine.md` QA round 1; `kit/setpieces._shrine`, yards kind "shrine"; the wall shrine theme retired | `exterior.set_variety` (STsetv); look: the lab's shrines | none | check |
| Q1X-2 | (the themes) "lack of balance and symmetry: things placed randomly, not lined up with each other" | P§2 Yards (the Frame, mirrored pairs); every set piece below | `exterior.set_symmetry` (STsetm), `exterior.grave_rows` (STgrows), `exterior.crop_rows` (STcropr) | none | check |
| Q1X-3 | (the themes) "spaces are too empty and lack object diversity" | P§2 Yards (three kinds at least); P§4 | `exterior.set_variety` (STsetv), `exterior.grave_variety` (STgvar), `exterior.well_feature` (STwellf) | review | check |
| Q1X-4 | well: "Make sure that when wells appear in maps, the player can interact with them to fully heal health and mana, like in the original nox campaign"; nox13 "Make all wells heal the player" | P§2 the centre first; `kit/setpieces.healing_well` (the WishingWell, Westwood's TRIGGER well, named HealWell<n> for the behaviour scripts); every design's well, `well_side`, the well yard | `exterior.well_heals` (STwellh); the healing itself: the behaviour helper's script, in the game | none | check |
| Q1X-5 | well (all ten 1): "This isn't so much a feature as it is just a well ± a sign. Try to make the well a larger feature. Give it a small area of cobblestone beneath it." | P§2 Yards; `rules/scenes/well.md`; yards kind "well" (`setpieces._well`: 5 x 5 or 7 x 7 squares of grey cobbles), `well_side` paved 3 x 3 (`Theme.pave`) | `exterior.well_feature` (STwellf) | none | check |
| Q1X-6 | well: "Add more objects like buckets. Surround some wells by a fence or a gate." | `setpieces._well` archetypes plain, fenced (low fence, centred gate, lamps), market (benches on four sides, lamps at the corners); water barrels and the bucket of tools (Nox has no bucket) | `exterior.well_feature`, `exterior.set_variety`; look: the lab's wells | none | check |
| Q1X-7 | EX-WELL-05: "There is no well." | the dressing's `well_side` had found no room in its clearing and the lab laid nothing; a well is a yard now, planned before the land is carved (never dropped) | the scene lab's "missing" count (0 of 10) | none | review |
| Q1X-8 | graveyard: "the graves just look very scattered and random ... organization and balance. The graves/headstones should be in symmetrical, even rows"; 07 "The graves are all on one side and not balanced. very large space with very little in it"; 08 "Graves are very randomly scattered" | P§2 Yards; `rules/scenes/graveyard.md` QA round 1; `yards._graveyard` (rows evenly spread over the whole yard, mirrored, one kind to a row) | `exterior.grave_rows` (STgrows) | review | check |
| Q1X-9 | graveyard: "Stone walls don't make sense for the graveyard perimeter itself ... only ... for smaller mausoleum-type buildings within the graveyard and the back wall (opposite of the gate). EX-GRAVEYARD-05 does this PERFECTLY"; 01 "change the southeast wall to a gate"; 02, 09 "center the mausoleum"; 06 "better if the mausoleum was not connected to the fence perimeter" | `yards.plan` (fence all round, stone only the back wall; no stone pen); `_graveyard` (the mausoleum centred on the back wall, built in or free-standing off it) | look: the lab's graveyards (the walls' materials and the mausoleum's place) | review | review |
| Q1X-10 | 10: "the cobblestone path really adds a lot ... The gate is slightly off-center with the cobblestone path"; nox7 "The alignment on the cobblestone path is way off with the mausoleum and the gate" | `yards.plan` (the gate's side an odd number of squares), `yards.door_between` (the gate in exactly its two middle cells: Spec.door had hung some a cell off), `_graveyard` (the path of whole squares up the axis to the mausoleum's door) | `exterior.gate_path` (STgatep) | none | check |
| Q1X-11 | graveyard: "Use more item variety, like coffins, more dead / spooky trees, buckets of tools, barrels, torches, bones, skulls, etc. A graveyard should never have exclusively graves"; 02 "The obelisks on either side of the entrance look excellent" | `_graveyard`: the gravedigger's corner and the keeper's stores mirrored, dead trees, torch poles at the mausoleum, stone pillars at the gate | `exterior.grave_variety` (STgvar) | review | check |
| Q1X-12 | graveyard: "Try combining headstones with patches of dirt to make fresh-looking graves once in a while" | `_graveyard`: a mirrored pair of fresh graves on dug earth in four yards of five | look: the lab's graveyards | none | review |
| Q1X-13 | garden: "Plants in gardens should generally grow on dirt, not grass. EX-GARDEN-01 ... the ground inside of the garden fence is just regular grass"; 04 "the plants are growing in grass" | P§2 Yards; `rules/scenes/garden.md` QA round 1; `Village.garden` and the field: the whole plot dug earth (`yards.yard_ground`) | `exterior.crop_ground` (STcropg) | none | check |
| Q1X-14 | garden: "space rows of crops out and make them even and balanced"; 03 "Use fewer plants per row and space them out a little bit more, and keep them even"; 05, 06, 08 the same; nox2's garden "more or less perfect" | `yards.lay_crop_rows` (the field's even rows, nox2's, for every garden: no hand jitter, no cut beds, plants 23 px apart, rows mirrored) | `exterior.crop_rows` (STcropr) | review | check |
| Q1X-15 | garden: "use garden fences more often. Use a wider variety of objects as well. A barrel of tools a wheelbarrow etc."; 02 "A couple random plants and items tossed together" | `Village.garden`: three in four fenced with a gate centred toward the house's door; the water barrel and the bucket of tools either side of the way in; an apple tree with apples by most (Nox has no wheelbarrow) | `exterior.set_variety` for declared gardens' yards; look: the lab's gardens | review | review |
| Q1X-16 | garden 05, 06: "The garden being directly next to one of the walls of the structure ... This is an excellent orientation" | `Village.garden` keeps its site beside the house wall; its gate never on the side against the wall | look: the lab's gardens | review | review |
| Q1X-17 | farmyard: "the exteriors are too empty on all of them. Add some more variety. An apple tree with apples on the ground (the item that players can pick up), a well, multiple gardens"; 01, 03 interiors too empty | `rules/scenes/farmyard.md` QA round 1; the lab's farmstead (`recipes._farm_plan`, `_farm_build`: a well yard, two gardens, an orchard, the harvest scenes); `setpieces.apple_tree`. The rooms' emptiness: the rooms helper | `exterior.set_variety`; look: the lab's farmyards | review | review |
| Q1X-18 | nox6: "Good structure for an orchard, but too empty. Add a few crates of apples and some apples on the ground that the player can pick up" | `yards._orchard` (larger; TreeApple in even mirrored rows, RedApple windfalls below each crown, crates of apples outside the gate, the tool barrel and a barrel) | `exterior.set_variety`; look: the farmyards' orchards | review | check |
| Q1X-19 | EX-FARMYARD-04: "The hearth floor tiles are not centered with the actual fireplace" | the rooms' hearthstone (`kit/shells.py`), the rooms helper's (with nox17, nox21) | (the rooms helper's) | none | none |
| Q1X-20 | nox13: "This town square is excellent. The benches are lined up in an organized fashion, and so are the lamp posts ... add a second layer of cobblestone immediately around the well / center of the square" | P§2 the centre first; `Village.square_piece` (3 x 3 squares of grey cobbles round the well, a brick kerb against the square's rough cobbles) | look: a town's square (Brackwater) | none | review |
| Q1X-21 | (dirt ground for camp and garden areas blended properly) | the gardens' and graves' earth on whole squares, blended by the kit's ordinary edges (OUTDOOR_BLENDS); the paving's edges (`setpieces.ensure_blends`); generic blending is the tile helper's | `floors.*` (the tile helper's) | review | review |

## Not done here, and why

- Q1X-19 (the hearth tiles) and the farmhouses' empty rooms belong to the rooms helper (`kit/shells.py`, the furnisher).
- The healing itself (Q1X-4): the wells are the WishingWell, named `HealWell<n>`; the script that heals the player is
  the behaviour helper's.
- No wheelbarrow or bucket object exists in Nox: the bucket of tools (BarrelWithTools) and water barrels stand for
  them.

## Totals

| | Items | Check | Review only | Not covered |
|---|---|---|---|---|
| QA round 1 set pieces, before | 21 | 0 | 10 | 11 |
| QA round 1 set pieces, after | 21 | 12 | 8 | 1 |
