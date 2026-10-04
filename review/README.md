# Visual review (phase 5)

Judges what the automatic checks can't: whether a map looks and plays like Westwood's.

1. `py review/review.py <map>` renders the map and the 3 most similar Westwood maps (chosen by floor
   mix, water and buildings) and writes `review/out/<map>/sheet.png`. Each column shows the whole map
   at the same scale, then close-ups of about one game screen: a building entrance, woodland,
   waterside, and paths or open ground.
2. The same command measures the design qualities from the DysVale playtest and compares them with
   Westwood's outdoor maps (`review.md`). These are paths and how they connect to doors, tree
   clustering, trees lining edges, single-type plant clumps, and building spacing.
3. Claude applies `RUBRIC.md` to the sheet (7 criteria, scored 1–5 against the Westwood columns) and
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
   - `py mapgen/designs/roomlab.py [seed] [kind ...]` builds `mapgen/out/roomlab/RoomLab.map`: every composed room
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
     A room passes at its coverage target, with no warnings and with its back walls 35% lined (25% under 40
     tiles).
   - The loop: build three seeds, score them, look at the failing rooms' pictures (`rooms.py --each`), fix the
     furnisher or the recipe, and repeat. The first night took the lab from 23 to 35-37 of 42 rooms passing.

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
