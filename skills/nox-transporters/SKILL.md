---
name: nox-transporters
description: Plan and build the lifts, stairs, portals and scripted passages of a Nox map with the dystopiannox generator (mapgen/kit/transport.py) - choosing the kind by setting, drawing the far place, placing both ends, the landing, the way back, switching them with the story, and the QA checks. Use when a map needs an elevator, a lift, stairs to another floor, a teleport pentagram, a portal, a cellar, a mine level, an island, a tower floor or any place the player reaches without walking.
---

# Transporters in a Nox map

Every transporter does one thing: it moves the player from a spot A to a spot B. B is most often a place that cannot be
walked to, drawn in an empty part of the 256 x 256 grid: a Nox map has one floor, so "down to the cellar" or "up the
tower" is a jump across the map into a walled-off area. One call lays any kind:

```python
from kit.transport import Transporters
tp = Transporters(m)                                    # once per map, after the walls and water are laid
t = tp.add(kind, a, b, name, style=, two_way=, enabled=, arrive_a=, arrive_b=, invisible=, serves=[...])
```

**Read first:** `rules/TRANSPORTERS.md` (what Westwood does, measured on its 107 campaign maps, with the engine's
rules and examples), then this recipe. The story map recipe is `skills/nox-story-map/SKILL.md`; this skill slots into
its steps (section 4). Template: `mapgen/designs/test_transport.py` (one of each kind, every far place isolated); in a story map,
`mapgen/designs/ironcrag.py` (each transporter the way to a quest's place, two switched on by the story).

## 1. Decide what the transporter is for (in the design's docstring)

Write one line per transporter: what the far place is, why the player goes there, and whether he comes back the same
way. A transporter with no purpose is a corridor with extra steps. Westwood's far places are a level of their own: a
cave under a town (Con02a), a mine level (Con01A), a sewer (War01A), a crypt level (Con04b), a castle floor (Con07B),
an arena. They hold a fight, a find or the next step of the quest.

Then choose the **kind** by the setting and the story:

| Kind | Use for | Style (`style=`) and Westwood's types |
|---|---|---|
| `lift` | mines, caves, sewers, pits, a tower's machinery; always two-way | `cave` / `dungeon` CaveElevator (+ its base), `mine` Elevator, `town` / `swamp` GreenElevator, `castle` WhiteElevator, `lotd` LOTDElevator, `lava` RedElevator |
| `stairs` | between floors of a castle, a keep, Dun Mir, a crypt | `castle` GalavaStairsDown / Up1, `castle_carpet` the carpeted pair, `dunmir` DunMirStairsDown / Up, `crypt` LOTDStairsExitBack1 / UpExit1 |
| `portal` | magic: a wizard's tower, ruins, an island, a shrine, a shortcut, a one-way trap | TeleportPentagram (seen, glows a second), `invisible=True` InvisibleTeleportPentagram (unseen, at once) |
| `passage` | a door or tunnel mouth into an inside drawn elsewhere; the screen fades out and in (Westwood's GoToMine / EnterTemple scripts) | no object at the spot; the map's script does it |

Never mix settings: a white castle lift in a cave, a pentagram in a peasant's cellar. A lift is never one-way (use a
portal or a passage); stairs and lifts read as "up" and "down" by where their ends stand, not by the engine.

## 2. Draw the far place

1. **Isolated by default.** Lay the far area as its own walled room or level in an empty part of the grid, at least
   a few cells from every other area (`m.room(...)` or the biome kit), so it cannot be walked to: the transporter is
   the way in. Keep it inside the map (12 squares from the edges, as every area) and off other areas' land.
2. **Its own identity**: its floor and walls for what it is (a cellar CaveWall on DirtDark2, a castle floor
   GalavaTownWall on GalavaBrick, a crypt DungeonStone on GreenBrick), its own light (a room polygon with its ambient
   when it is darker than the world: Rimehold's cave; `Spec.build` bites the world polygon round it).
3. **Its content**: what it is there for (the chest, the boss, the lever), furnished by its room type
   (`rules/rooms/`). Pass those spots as `serves=[...]`: the checker proves each is reachable on foot from where the
   player lands.
4. A far place of any shape (a cave level, a crag top) is a `Land` of its own: its squares from circles and capsules,
   `Land._fix_pinches`, then `L.apply(m, wall=, floor=, unlevel=True)`; keep the town's land out of that part of the
   grid with `land.forbidden` (`mapgen/designs/ironcrag.py` `cave()`). A far room of a building (a tower's upper floor)
   is an `m.room` furnished by its type (`furnish_original` on a `kit.model.Room`) and declared in the rooms sidecar;
   take out the furniture round the stairs and their landing afterwards. Camps and scenes (`camps.urchin_camp`,
   `camps.stone_ring`, `camps.Scene`) work on a far place's own `Land`.
5. A far place in the same area (a shortcut across a garden, a portal over a chasm) is fine: say so in the docstring.

## 3. Place both ends

Coordinates are world pixels: `px(u, v)` from uv, `kit.layout.square_px(i, j)` from the story kit's squares.

- **Lift** (`a` platform, `b` pit): each end on open floor, 35 px or more from a wall (Westwood's p5; 23 least); a
  lift is 32 px square and the rider must reach it from every side he comes from. The kit lays a CaveElevatorBase
  under both ends of a cave lift. Light both ends (a ColorLight or torch: 73 of Westwood's platforms have one). Mine
  lifts get gears beside them; the pit end in a cave gets rubble, not furniture on top of it.
- **Stairs** (`a` the flight down, at the upper floor; `b` the flight up, at the lower floor): the flight down
  stands 3-5 cells inside a room's west corner (`px(u0 + 5, v0 + 6)` in a uv room), the flight up against the room's NE
  wall or in an alcove (`v1 - 2`), its mouth opening down-left. The kit lays the side and end pieces at Westwood's
  offsets, an invisible pad on each flight and the arrival 40-100 px in front of the other's mouth
  (`rules/out/transporters.json` geometry). Look at both flights in the QA spots picture: walls behind, open in front.
- **Portal** (`a` the pad, `b` the far pad, or the landing when one-way): pads on open floor, clear of furniture
  (Westwood's landings: median 97 px from a wall). Two-way, the kit lands the player 59 px (Westwood's median) off
  the pad that leads back, on the clearest side; give `arrive_a` / `arrive_b` to choose it.
- **Passage** (`a` the spot, `b` the far spot): the spot in a doorway, a tunnel mouth or a dead-end recess the
  player walks into on purpose (flank it with torches or a doorframe so it reads as a way in); the script fires within
  26 px of it. Two-way passages get a spot at `b` and land 59 px off each spot.

Never land the player on a pad or passage spot that leads elsewhere: he is sent on at once (Westwood does it only in
its pentagram chains). Never put either end on a road's lane, in a doorway's way or on a story place; on an outdoor
map plan each end inside an area or yard the land keeps open (`land.area`, `sm.keep_open({area: r})`), and keep the
townsfolk's stops off it (`sm.keep_folk_away(square, r)`, in squares).

## 4. Where it goes in the build (story maps)

In `skills/nox-story-map` step order:
1. **Plan** (step 1): reserve the far area's ground (`land.forbidden`, or a part of the grid no area reaches) and
   give each outdoor end an area of its own or a place in one, kept open (`sm.keep_open({area: r})`).
2. **Land and walls** (step 4): draw the far place (`m.room(...)` or its biome structure) with the rest.
3. **After the walls, water and planting** (step 7, before the people): `tp = Transporters(m)` and `tp.add(...)`
   (a portal's landing is chosen against the walls and objects already laid).
4. **People** (step 8): the far place's keepers and foes; townsfolk tours stay out of it.
5. **The story** (step 10): a transporter that opens with the quest is laid `enabled=False` and turned on by
   `A.enable(name)` for each of `t.sources` (the far flight's or pad's name is `name + "Back"`, a lift's pit
   `name + "Pit"`), as Westwood's exit lifts are (Con01A `ActivateExitElevator`). Give it its moment: a line, a
   journal note, a sound.
6. **Build**: `Spec.build` writes `<Name>.transport.json` (the transporters as meant, for the checker) and
   `transport.go` (the passages, a self-check that every end exists, and a log line each time a transporter moves the
   player).

## 5. Check

`py mapgen/designs/<map>.py` runs the checker; the transport rules (`validate/checks.py check_transport`,
`rules/TRANSPORTERS.md` section 6):

| Rule | Severity | What it catches |
|---|---|---|
| `transport.link` | error | an enabled platform with no pit, a pad naming an object not on the map |
| `transport.landing` | error | a landing in the void, in a wall or on a blocking object |
| `transport.wall` | warning | a landing under 23 px from a wall cell's centre |
| `transport.pocket` | error | a landing area under 12 cells with no way on |
| `transport.missing` | error | a declared end missing from the built map |
| `transport.bounce` | error | a landing within 40 px of a pad or passage spot that leads elsewhere |
| `transport.serves` | error | a place the transporter serves that cannot be walked to from its landing |
| `transport.stranded` | error | a landing from which neither the start nor an exit can be reached |
| `transport.unreached` | warning | a transporter whose start cannot be reached from the start |

Reachability (`reachability.unreachable`, `story.gate`) follows transporters too: a lift both ways, a pad one way,
a passage from the sidecar.

Then the **QA gate** (`py tests/qa.py <design>`): the spots pictures show every named end (the lift's platform and
pit, each pad, each passage spot): look that each stands on open floor, the stairs have walls behind them and open
floor in front, and the far place reads as what it is. A deliberately bare test place is accepted in `QA_ACCEPT` with
its reason.

After the gate, the main session installs the map and runs `py tests/server_smoke.py <design>`: the server log shows
`transport self-check: ends N of N`. In a playtest (or the client test below) each use logs
`transport: <name> moved the player from x y to x y`.

## 6. Proving it in the client (optional, when the engine's side is in doubt)

`rules/TRANSPORTERS.md` section 8: host the map in the OpenNox client (`-autosrv`, arena-flagged copy), add a
throwaway driver script beside the installed map that clears the host's NO_COLLIDE flag (an `-autosrv` host walks
through objects and never triggers a pad) and pushes the player onto each start in turn (`p.PushTo(target, -1.5)`),
and read the `transport:` lines. Remove the driver and reinstall the solo map afterwards; never while the user plays.

## Pitfalls

- **A lift cycles for ever.** It carries anyone who stands on it, both ways, about every four seconds: never put a
  lift where creatures stand still (a guard on it rides away), and never start the player on one unless the start is a
  lift shaft as in Con05A.
- **Pads and markers are TRANSPORTER objects**: the target of a pad must be a TRANSPORTER (the kit's markers are);
  a pad aimed at a waypoint or another kind of object never fires.
- **Disabled means the create flags**: `enabled=False` writes the object with its extended fields and no ENABLED flag;
  the story must turn it on (`A.enable`), or the far place is closed for good (the checker's `transport.stranded`
  does not know the story: say in the docstring who opens it).
- **One-way is a promise**: after a one-way portal or passage the far place must lead on (the exit, another
  transporter, a door the story opens). `transport.stranded` errs otherwise.
- **The island and the Teleport spell**: a place reached only by a portal can still be reached by the player's own
  Teleport spell unless its ground is a `*NoTeleport` floor.
- **Names**: a transporter's name becomes script names (`name`, `name + "Back"`, `name + "Pit"`, `name + "To"`):
  keep it short, unique and free of the map's other names; the dialogue title rule does not apply (nobody talks).
