# Visual review (phase 5)

Judges what the automatic checks can't: whether a map looks and plays like Westwood's.

1. `py review/review.py <map>` renders the map and the 3 most similar Westwood maps (chosen by floor
   mix, water and buildings) and writes `review/out/<map>/sheet.png`. Each column shows the whole map
   at the same scale, then close-ups of about one game screen: a building entrance, woodland,
   waterside, and paths or open ground.
2. The same command measures the design qualities from the DysVale playtest and compares them with
   Westwood's outdoor maps (`review.md`). These are paths and how they connect to doors, tree
   clustering, trees lining edges, single-type plant clumps, and building spacing.
3. Claude applies `RUBRIC.md` to the sheet (8 criteria, scored 1–5 against the Westwood columns) and
   records the result in `reviews/<map>-<date>.md`. A map is ready for playtesting when every
   criterion scores 3+ and the checker reports no errors.

4. `py review/rooms.py <map> --each` shows the interiors. It writes a sheet of every room
   (`review/out/<map>/rooms.png`) and one close-up per room (`review/out/<map>/rooms/NN.png`). Each close-up is
   numbered and labelled with its building, kind and purpose, and lights its room while dimming the
   neighbours. Over the room's floor the walls show half see-through (a second render without walls is blended
   in, `MapEditor.exe <map> --render-image <png> full:5880 nowalls`), as the game draws the walls in front of the
   player. Show these to the playtester for numbered, room-by-room feedback. Generated maps write
   `<map>.rooms.json` beside the map (`kit/identity.rooms_sidecar`) with each room's number, building, kind,
   purpose and floor; other maps fall back to the checker's room finder.

5. The room lab improves the furnisher between playtests.
   - `py mapgen/designs/roomlab.py [seed] [kind ...]` builds `mapgen/out/roomlab/RoomLab.map` (and `RoomLab2.map`
     for the rooms the first page's field cannot hold; score both): every composed room
     kind at three sizes. "Typical" and "large" are Westwood's, and "bigger" is half as big again, the scale our
     maps aim for. Each room is a one-room house on open ground with its door in a front wall, declared in
     `RoomLab.rooms.json`.
   - `py review/roomscore.py <map>` scores every declared room of any generated map in
     `review/out/<map>/roomscore.md`:
     - coverage against the kind's `ROOM_COVER` target and Westwood's median for rooms of its kind and size;
     - coverage of the open middle;
     - the share of the back walls lined;
     - distinct types;
     - the checker's findings inside the room.
     - its identity (Starwell playtest): walls with a purpose, no showpiece repeated, no stand-alone piece four
       times along one wall, no more free tables than its kind sets, nothing outside its identity, against the
       reference room (Starwell's study; PROCESS.md section 3).
     A room passes at its coverage target, with no warnings, its back walls 35% lined (25% under 40 tiles) where its
     recipe lines walls, and no identity flag.
   - The loop: build three seeds, score them, look at the failing rooms' pictures (`rooms.py --each`), fix the
     furnisher or the recipe, and repeat. The first night took the lab from 23 to 35-37 of 42 rooms passing, then added the tavern, shop, laboratory, chapel, crypt, hall and throne room (21 kinds, 63 rooms: 47-51 pass over three seeds, then 50-56 once big rooms scaled their fill).

6. The building lab does the same for whole buildings.
   - `py mapgen/designs/buildinglab.py [scale] [seed]` builds `mapgen/out/buildinglab/BldLab.map`: every building
     role of the kit (`kit/identity.py` BUILDINGS) at one scale (1.0 is Westwood's size, 1.25 the kit's default,
     1.6 the bigger scale our maps head for), generated from its room program and furnished. It writes
     `BldLab.rooms.json` (so `roomscore.py` scores its rooms) and `BldLab.buildings.json`.
   - `py review/buildingscore.py mapgen/out/buildinglab/BldLab.map` scores each building in
     `review/out/BldLab/buildingscore.md`: its shape and size, each room against Westwood's sizes for its kind
     (below the 5th percentile is small; above the 95th is big, which the bigger scale allows), rooms that cannot
     be reached, the checker's findings inside it, and how many of its rooms pass `roomscore.py`. A building passes
     with no errors, every room reachable, no room small for its kind and every room passing.
   - Room sizes: a building's room of n footprint units has about n - 2 sqrt(n) of the checker's floor tiles (its
     walls take a strip round the edge), and Westwood's sizes are in floor tiles (`building._units_for`).

7. Story maps have their own pictures, all of which the QA gate (`py tests/qa.py <design>`, PROCESS.md section 9)
   renders into `review/out/<Name>/qa/` with an index:
   - `py review/storymap.py <map> [--routes]`: the whole map with every named story object labelled; with `--routes`,
     every route people walk, each stop's dwell and the way it faces (red where a leg or a facing is faulted);
   - `py review/spots.py <map> <script names...>`: close-ups of the story's places (camps, givers, gates, bosses);
   - `py review/exteriors.py <map> --holes`: the outdoor ground with no prop within 4 cells shaded, against
     Westwood's maps of the same environment (`--westwood` measures Westwood's);
   - `py review/catalog.py <name or regex>`: look up a thing's name in the game's catalogue.

`py review/review.py --calibrate` re-measures Westwood's 51 outdoor single-player maps (25 distinct
layouts) and rewrites `baseline.json`. Maps with 5+ buildings are compared with Westwood's towns for
the path and building measures.

## Calibration against the playtest

The measurements reproduce the playtest verdict on DysVale without being told it:

| Measure | Westwood (10th–90th percentile) | DysVale | Mossford v0.1 |
|---|---|---|---|
| Path share (towns) | 2.7–42% | **1.4%** | 18% |
| Trees lining edges | 83–100% | **72%** | **70%** |
| Small plants in single-type clumps | 23–62% | **6%** | **7%** |
| Tree clustering (1 = random) | 0.29–1.07 | 1.06 (edge of the range) | **1.46** (artificially even) |
