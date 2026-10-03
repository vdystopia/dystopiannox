# Visual review rubric

Apply this to `review/out/<map>/sheet.png` (the generated map beside the 3 most similar Westwood maps),
together with the design measurements in `review.md`. Score each criterion 1–5 against the Westwood
columns on the same sheet (Westwood's own maps score 4–5), say what you see, and record the review in
`review/reviews/<map>-<date>.md`. A map is ready for playtesting when every criterion scores 3 or
more and the checker (`validate/`) reports no errors.

The close-ups are about one game screen each, so they show what a player sees at any moment.

| # | Criterion | Westwood standard (what to look for) | Supporting measurement |
|---|---|---|---|
| 1 | **Silhouette** | The playable area has an organic outline: winding corridors and branching areas cut out of darkness by forest, cliff or rock, with varied widths. It's never a plain rectangle or diamond. Several distinct areas are joined by narrower passages | — |
| 2 | **Flow** | A road or path network runs through the map: a main route, branches to every building door and landmark, and crossings where it meets water. You can read where to go from the ground | path share, paths joined, doors on path |
| 3 | **Settlement** | Buildings form compact clusters along the roads, facing them, around a focal point (square, well, fountain, market). Yards, fences and gardens fill the spaces between buildings. Sizes are mixed | gap between buildings |
| 4 | **Vegetation** | Thick tree lines several rows deep form the edges. Groves and clearings alternate. Undergrowth hugs trees and walls, flowers grow in single-type patches, and open ground stays mostly clear. Never an even sprinkle | tree clustering, trees lining edges, single-type plants |
| 5 | **Water** | Streams vary in width, banks are dressed (trees, rocks, reeds down to the water), and crossings sit where paths meet the water at narrow points | — |
| 6 | **Every screen** | Each close-up has something to look at (a focal point, variety, contrast between areas) without clutter. No empty screens, and no repeated stamped patterns | — |
| 7 | **Interiors** | Visible rooms read as their purpose (tavern, smithy, bedroom) and are composed: anchors on their own walls (back walls first) and centred, a rug before the chest or hearth, the table set in the middle, nothing standing in front of a chest, hearth or stove, furniture spread rather than bunched in a corner. Use `py review/rooms.py <map>` for a sheet of every room | checker: rooms |
| 8 | **Identity** | Every area, building, room and prop group reads as what the map's identity says it is. The square is the village's centre, an inn looks like an inn, a bedroom holds a bed, rug, shelves and chest (never a barrel or a dining table), and every outdoor prop has a reason to be where it is | checker: rooms (furniture outside the room's identity) |

When scoring, also check relations (PROCESS.md):
- paths lead to doors, and buildings open toward what they serve;
- the square is a composed set piece;
- docks reach into open water, and bridges are narrow and cross straight stretches at a right angle;
- bars meet the walls;
- chests, bookcases and desks lie along their walls;
- lights and pieces balance a room (the free corner, never beside each other);
- props are spread out, never bunched in one spot;
- double doors line up.

Lighting and mood don't show in the editor's render; judge them in a playtest.
