# Fairness of the blind tests

The room lab's and scene lab's blind judges (fresh vision agents that see only the pictures) should be able to tell
generated rooms and scenes from Westwood's only by their design. Each known tell that is not design, and how it is
handled. Before and after pictures: `py review/roomlab/fairness.py <type> <before iter> <after iter>` writes
`review/out/roomlab/_fairness/`.

| # | Tell | How it is handled | Where |
|---|---|---|---|
| 1 | **Creatures.** Westwood's rooms and scenes hold monsters and NPCs (ogres, skeletons, townsfolk); the room lab's none, the scene lab's the kit's posts. Judges: "C, F and G have ogres or skeletons in them"; "E has a person in it". | Both renders are of a creature-free copy of the map: `nocreatures.ps1` loads the map with the editor's own library (NoxShared.dll), removes every object whose thing class is MONSTER (monsters and NPCs) or PLAYER, and saves the copy, which the editor renders. The real maps, which the metrics measure, are untouched. | `labrender.creature_free` (both labs); Westwood copies in `review/out/{roomlab,scenelab}/_clean/`, lab copies in `<iter>/map/clean/` |
| 2 | **The briefs leaked the generator's rules.** Judges read `rules/rooms/<type>.md`, which carry our generator's rules, caps, profile numbers, lab notes and "what gave ours away"; one judge used a cap to tell rooms apart. | Judges read a judging description per type instead: what a real room (scene) of the type is like, from Westwood's own campaign rooms (`westwood_features.json`, `westwood_scenes.json`, the curators' notes), with no generator rules or kit numbers, and following Westwood where the brief disagrees with it. JUDGE.md tells judges to read nothing else about the type or the lab (not the briefs, FEEDBACK.md, PROCESS.md, code or logs). | `review/roomlab/judging/` (README + 35 types), `review/scenelab/judging/` (README + 18 scenes), both JUDGE.md |
| 3 | **Doors.** The lab gave each room 1, 2 or 3 doors, a third each; half of Westwood's rooms have one (bedroom: 19 of 28). | `labgen.door_plan` draws each variant's door count from Westwood's own rooms of the type (their doors as the metric judge counts them; the pool's when the type is thin), by quantile so a batch follows the distribution, in a seeded order: the entrance plus one neighbouring room per further door. An open arch (0 doors) counts as 1, more than 4 as 4. The kit's builds come out as planned (bedroom: planned and built counts equal in all ten). | `review/roomlab/labgen.py` |
| 4 | **Repeated Westwood pictures.** The same few Westwood rooms (scenes) came up on every sheet of a type. | The sheets rotate: each Westwood pick costs one per earlier showing on the type's other sheets, and `review/out/{roomlab,scenelab}/<type>/westwood_shown.json` records which each sheet showed (also in `blind_key.json`). Bedroom: two sheets from one batch share no Westwood room. Where a type has few rooms of the right culture and size, rotation gives way to size by the costs below (Westwood has five town bedrooms of 28 tiles or more). | `blind.pick_westwood`, `blind.make` (both labs) |
| 5a | **The surroundings.** Outside the room was dimmed to 10%: Westwood's rooms showed their furnished neighbours faintly round them, the lab's mostly an empty field (and with Westwood's door counts most lab rooms now have no neighbours at all). The stubs of walls running on past the room's corners (kept by a 30 px wall band) were many more round Westwood's rooms, set in their buildings. | Everything outside the room and its own walls is the canvas colour; the room's walls are kept only within 17 px of its floor. The rim fix (no ground band round the walls) is kept. | `labrender.OUTSIDE`, `WALL_REACH` |
| 5b | **Scale and size.** One scale per type, but a room too big for the canvas was shrunk, which happened mostly to ours (1.25 times Westwood's size), so its furniture was drawn smaller. And the sheet paired our rooms with Westwood's of a fifth smaller floor, so ours always looked bigger. | Every picture of a sheet is drawn at one scale (the smallest any of its ten rooms needs; redrawn from the cached renders when it differs). Each generated room is paired with a Westwood room of its culture and about its floor tiles (the cost: 2.5 per e-fold of size), so the sizes on a sheet overlap. The type's own rooms before its pool's. | `blind.make`, `labref.redraw` |
| 5c | **Culture.** A batch can hold no room of a culture Westwood has (the lab has no Dun Mir host for a bedroom; Westwood has 12 Dun Mir bedrooms), so Dun Mir walls on the sheet meant Westwood. | The pairing costs 4 for a Westwood room of another culture than its generated partner. | `blind.pick_westwood` |

## Checked and not handled here (design, or other agents' work)

- **Lighting**: both are the editor's render without lighting; candles and torches look alike in both.
- **Wall, floor and door art**: the generated rooms use Westwood's building styles. Westwood's rooms are often shaped (L-rooms,
  niches, protrusions) and carry carpets laid in the floor tiles; the lab's are mostly plain rectangles. That is the
  shell's design (kit/shells.py, the shells agent), not the picture: judges may use it.
- **The scene lab's setting**: Westwood's scenes stand in towns, castles and caves, ours in a hamlet's ground or a
  forest glade; the ground away from a scene is dimmed for both, and JUDGE.md asks the judge to judge the setting only
  where the scene meets it.
- **The 1.25 scale itself** (our rooms are bigger by the user's choice): with the pairing by size the sheet no longer
  shows it; the metric judge still compares each room with Westwood's rooms of the type.
- **Composition** (a fenced square graveyard with a crypt in every generated scene, plants in the corners of generated
  bedrooms...) is design: what the judges are for.
