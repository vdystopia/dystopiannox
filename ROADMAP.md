# Map-making skill roadmap

Goal: a repeatable process that produces professional-quality Nox maps in one shot, learned from
Westwood's maps. Generated structures must be original (never copy-pasted stock layouts).

| Phase | Status | Where |
|---|---|---|
| 1. Reference corpus (all 157 stock maps, database, renders) | done | `corpus/` |
| 2. Rulebook mined from the corpus | done | `rules/RULEBOOK.md`, `rules/out/*.json` |
| 3. Kit: original buildings, furnished rooms, water features | done | `mapgen/kit/` |
| 4. Automatic checks (validator), calibrated on Westwood's maps | done | `validate/` |
| 5. Visual review against Westwood references (sheets, design measurements, rubric) | done | `review/` |
| Generator v2: layout, vegetation, village and water planners (fixes review criteria 1–5) | done | `mapgen/kit/layout.py`, `vegetation.py`, `village.py` |
| Generator v3: identity first, centre outwards (PROCESS.md) | done | `mapgen/kit/identity.py`, `PROCESS.md` |
| 6. Package as a skill | next | |
| 7. Benchmark briefs and refinement loop | | |

## Playtest feedback log

### DysVale v0.1 (2026-10-03)

Fixed in phase 3:

- **Mismatched dock planks.** Pieces were spaced on a pure diagonal; Westwood's steps have small sideways offsets. Kits now use the exact measured pixel steps (`kit/water.py` KIT_STEPS).
- **Sight gap at a corner beside a door.** Wall shapes were computed without the door opening, turning the corner into a straight piece. Westwood shapes jamb pieces as if the opening were wall (29.8% of jambs match only that way, 0.7% the other way); `nox.Spec` now does the same.
- **Gap beside a door frame.** Half-door types were placed singly in 1-cell openings. They are double doors: two halves hinged at the ends of a 2-cell opening (`rules/doors.py`). `Spec.door` builds pairs and falls back to the matching single door where the wall has no room.
- **Cluttered tavern.** There were two causes:
  - The building was sized from the style's typical house, so the tavern room was about 16 tiles; Westwood's taverns are 62-266.
  - The furnisher kept at least 60% of a full inventory.

  Buildings now grow to fit their room program. The largest room takes the entrance and the program's first role. Furniture scales with room area, and a hard cap holds each room at its kind's Westwood density (essentials and lights exempt).

Recorded for later phases (design level):

1. **No flow or coherent design.** Buildings sit at random spots with no roads or paths connecting them; Westwood towns are compact, with streets, a square, and buildings facing the streets. This needs a layout planner: a district/road graph first, buildings placed along roads with entrances facing them, then paths to every door, bridges where roads cross water, and organic outer boundaries instead of a geometric diamond. *(Generator v2, before or alongside phase 5.)*
2. **Trees and shrubs look random.** Uniform scatter instead of Westwood's structure: trees line edges and paths, groves and clearings, single-type clumps of flowers and mushrooms, undergrowth hugging walls and trees (`rules/out/decoration.json` has the measurements). This needs a vegetation planner driven by those rules. *(Generator v2.)*

Checks phase 4 must include, from this playtest (all implemented in `validate/`, each proven by a planted defect in `validate/selftest.py`):

- wall pieces beside door openings shaped as if the opening were wall
- double-door types only in 2-cell openings as matched pairs; single doors in 1-cell openings
- kit pieces at Westwood's exact step offsets
- furniture density per room within the kind's Westwood range; rooms within the kind's size range
- line-of-sight closure: no see-through gaps in building and boundary walls

### Mossford v0.1 (2026-10-03)

| Problem | Status |
|---|---|
| Black walls (invalid wall pieces) | Fixed: valid-piece table |
| See-through hole in the boundary | Rule recorded: invisible walls never on the boundary. The water kit follows it; Mossford itself still needs a rebuild |
| Abrupt bridges | Fixed in the water kit (Con05A-style decks, narrow streams). Mossford still needs a rebuild |

### DysVale v0.3 (2026-10-03)

The layout, trees and shrubs improved a lot. Fixed in generator v3:

| Finding | Fix |
|---|---|
| The square was off-centre, and a building stood on one of its tiles | The square is placed first. Public buildings face it across a clear margin, and roads stop at its edge |
| Paths near the river were hard to read because of stacked blends | Spacing comes first: the stream's band is reserved before anything is built, and the road stays 2.5 squares clear except at the bridge. Grass patches keep 3 squares from every transition. New review measure: road tiles crowding water (Westwood towns about 0.4%; v0.3 had 6.9%, v0.4 has 1.4%) |
| Exterior objects felt random | Outdoor props are scenes with a reason, tied to a building's role: deliveries at the inn, a woodpile at the woodcutter's, a water barrel at the smithy, grain sacks at the mill |
| Interiors were incoherent (a back room with four table sets) | Room identities list what each kind must, may and must never contain. The checker flags furniture outside a room's identity; on v0.3 it finds the barrels in bedrooms and the bookcases in the tavern |
| Swamp densities were averaged with towns | Westwood's maps are classified into 8 environment types (`rules/environments.py`); the checker and the review compare only like with like |
| The map needs an identity step | `MapIdentity` comes first (PROCESS.md, step 1). Generation runs from the centre outwards, and the land grows around what was placed (user direction) |

## Found by the checker (to fix in later phases)

- **Mossford v0.1** has 49 errors (black walls, 2 boundary holes, plank floor straight onto dirt at house doorsteps). It still needs a rebuild with the kit.
- **Furnisher:** a desk was placed inside a wall in RoomTest (`kit/furnish.py`, wall-hugging placement).
- **Style warnings on DysVale:** no creatures; few wall pieces per floor tile (an open layout); the tavern is small for its kind (55 tiles against Westwood's 166–269). These are for the layout planner (generator v2).

## Visual review findings

- **DysVale v0.2** (`review/reviews/DysVale-2026-10-03.md`) scores 1 on silhouette, flow and vegetation, and 2 on settlement, water and every-screen variety; interiors score 3. Generator v2 has to deliver:
  - an organic walkable shape cut out of forest
  - a road graph with buildings packed along it around a focal point
  - deep tree lines, groves and single-type plant patches
  - dressed water with bridges where roads cross

  Each is measured in `review/design.py`.

- **DysVale v0.3** (generator v2, `review/reviews/DysVale-v0.3-2026-10-03.md`) scores 4 on silhouette, flow and vegetation and 3 on settlement, water, every-screen variety and interiors. The checker finds no errors and every design measurement is within Westwood's range. Open items:
  - creatures and townsfolk (none yet)
  - denser villages
  - dressed stream banks
  - corridor width variety
  - the furnisher sometimes places furniture on a wall cell
