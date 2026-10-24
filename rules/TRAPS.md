# Traps and environmental hazards

How Westwood builds traps, what the engine really does, and the rules our trap maps follow. Sources:
`rules/traps/WESTWOOD_SCRIPTS.md` (every trigger and effect in the 120 decompiled campaign and quest map scripts,
29 set pieces, Westwood's timings), `rules/traps/ENGINE.md` (the engine source, cited per fact) and the in-game
bench (`mapgen/designs/traptest.py`, `py tests/traps_e2e/run.py traptest`; its log is
`rules/traps/bench-2026-10-23.log`). The kit: `mapgen/kit/traps.py` + `mapgen/kit/behaviours/traps.go`; walled
rooms and corridors: `mapgen/kit/dungeon.py`.

The user's brief (2026-10-23): Westwood's traps are short and simple; ours must range from short and simple to very
long, complex gauntlets; in a dungeon traps combine with monsters ("the true Nox experience"); challenging but not
impossible; a variety of difficulty, nothing easy.

## 1. Facts measured in the game (OpenNox alpha13, a warrior with no armour)

| Thing | What it does | Measured |
|---|---|---|
| Walk / run | right button held, cursor near / far | walk ~3.3 units a frame (100/s), run ~6.9 (207/s) |
| Jump (space) | 18 frames airborne, forward at run speed, 90 stamina (one a second) | ~120-125 units airborne from a walk or a run; z stays 0 |
| Spike carpet (Spike, 11.5 px grid) | on: hurts every frame; off: harmless, hidden | ~5 HP a frame standing on it; jumpable |
| PeriodicSpike | the same as Spike: **does not cycle by itself** in this engine | ~4-5 HP a frame, always on |
| Flame (r 8), 3 in a row | on/off by script, instant | ~3 HP a frame on; one line walked through: 8 HP; jumped: 0 |
| FireGrateFlame | the hottest flame | 5 HP a frame |
| SpikeBlock moved by the script (SetPos 4 px a frame) | **shoves the player** along and hurts | pushed 137 units, 1 HP a frame |
| RotatingSpikes | static unless moved; shoves out | 4 HP a frame (pushed out at once) |
| ArrowTrap1 / ArrowTrap2 | facing fixed by type: 1 shoots SE (+x+y), 2 shoots SW (-x+y); scans 700x700 in front, fires at most 1 a second | ~25 a hit (73 and 97 in 3 s) |
| Skull1-4 | fireball guns (NW/NE/SW/SE) | ~60-96 a hit, with a push |
| SentryGlobe | a 600-unit beam, stops at walls, **500 damage: instant death**; narrow | one square beside the beam: no harm |
| Pit (on) | **no damage**: the faller is teleported to FallX/FallY after ~11 frames | landed in the sealed cell |
| PitCrumblingFloor (off) | opens ScriptTimeout frames after the first touch, stays open | fell after ~10 frames at timeout 4 |
| Secret wall | `ns.Wall(x, y).Enable(false/true)` opens / closes it (23-frame slide); only walls written secret react | worked |
| PushTo / ApplyForce | a shove from the script | PushTo force 30: ~60 units |
| Pressure plate, lever | **the xfer's script names do not reach Go scripts in alpha13**: the kit watches them as zones | polled plate fired on press and release; a jump passes over; lever toggled |
| Health regeneration | the hero regains ~0.3 HP a frame | |

Not yet confirmed in play: Glyph (no effect when stood on by the probe), the lever click from the cursor,
PoisonGasTrap, BearTrap, RollingBoulder (needs a push or a mover: it never rolls by itself).

## 2. The trigger vocabulary (Westwood, `WESTWOOD_SCRIPTS.md` section 1)

- **Pressure plates**: visible; 70% of Westwood's accept monsters and players (a pursuer sets your traps off);
  puzzle and progress plates are player-only. Pressed and released are both triggers: step-off floors that drop
  behind you, hold plates (arrows fire while anyone stands on the row), weights (take the gold off the plate and
  the room springs).
- **Invisible triggers**: room entries (the door slams behind you), one-shot set-piece starts; they catch jumpers.
- **Levers, buttons, chains**: trap off-switches, resets, starts; a lever alternates two positions.
- **Motion detection**: the sentry globe's beam (fixed, sweeping, carried, cycled so a safe gap moves), plus
  plates. Westwood never polls distances; we may (a sensor zone is a cheap circle check).
- **Kills**: a generator or a guardian's death opens the next stage; killing the bait springs the trap.
- **Timers**: loops (spikes, blocks, flame waves), countdowns (10-16 s, a tick every second), auto-resets.
- **Items**: take the key, start the clock; put it back to stop it.

## 3. Westwood's rhythm (the numbers)

Danger windows 0.5-1 s, safe windows 2-5 s, re-arm 1.5-4 s; staggers of 4-20 frames turn a row of traps into a
travelling wave; countdowns 10-16 s; a gauntlet chains 4-7 different ideas along one route with a well between
stages; each trap type is taught alone and simple before it comes big or combined.

## 4. Our rules

T1. **Every trap is readable.** Visible hardware (plates, grates, arrow traps, globes, blocks in their slots), a
    warning before damage (the sound or the sight of the cycle), and a rhythm the player can learn in one or two
    watches. Westwood signposts with hardware, sound and demonstration, never with corpses or signs.
T2. **Every trap has an answer**: timing (the off window), a route (safe tiles, alcoves, the far side of a beam's
    wall), a jump (flames, spikes, pits, plates, crumbling floor: at most ~90 units deep, so a late jump still
    clears it; ~125 is the most a perfect jump covers), a switch (an off lever beyond or beside the trap), or
    speed (run before the floor drops).
T3. **Nothing is easy**: a careless walk straight through costs at least a third of a wizard's health (100 HP is
    the yardstick) or drops the player into the pit below; the answer needs at least one read of the trap.
T4. **Two tiers.** *Standard* (skill, any class): off windows of 0.7 s or more at walking pace, a mistake costs
    20-35 HP, at most two decisions in a row before a safe spot. *Hard* (punishes mistakes): windows of 0.3-0.6 s
    or a run, a mistake costs 40-100 HP or the pit, three or more decisions chained. A map or gauntlet mixes both;
    the hard ones come after their standard version.
T5. **Pits relocate, they never kill.** FallX/FallY always lands in a pit room (bones, a monster or two, a way
    back up), never at the map origin. A death pit is a design choice (land in the boss's den), never an accident.
T6. **Sentry beams kill outright**: use them only where the safe side is plain (a wall corner, a slow sweep of
    20 s or more a turn, a gap that walks at most one beam a second) and never with forced movement next to them.
T7. **Monsters share the traps**: plates default to players and monsters; a gauntlet's monsters wait beyond a
    trap, pour in when it springs, or chase the player into it; spike blocks and blades hurt them too.
T8. **Rest between stages**: a safe tile or room with red potions (or a healing well) after every two or three
    trap stages in a long gauntlet; never a trap in the first square past a door.
T9. **Teach, then test**: the first instance of a trap type in a map is its simplest form, in a dead end or a
    side room where a mistake is cheap.

## 5. The kit

`kit/traps.py` places the objects and writes the logic as data; `behaviours/traps.go` runs it each frame:
- `T.obj(type, x, y, enabled=)`, `T.group(name, objs)`;
- `T.clock(name, group, period, on=[(t0, t1)], phase=)`: a group on and off in windows (spike waves, flame jets,
  arrow volleys: on for one frame fires one volley);
- `T.mover(name, objs, path, speed, mode=pingpong|loop|once, pause=)`: blocks, blades, carried sentries moved by
  SetPos each frame (they shove the player: a mover beside a pit is a pusher);
- `T.plate(name, x, y, size, who=, acts=, release=, once=, visible=)`, `T.lever(name, type, x, y, acts=, release=)`,
  `T.zone(name, centre, r, shape=)`: what the player (or a creature) steps on, walks up to or enters;
- actions `T.act(kind, target, delay=, frames=)`: on, off, toggle, pulse, arm, disarm, cast (a spell from a point
  at a point), cast_at_caller, walls_open, walls_close, wake, say, reset, log;
- secret walls: `m.wall(x, y, material, secret="closed"|"open")`; breakable walls: `breakable=True`.
