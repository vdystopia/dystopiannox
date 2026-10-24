# Westwood trap mechanisms: trigger → logic → effect

Source: decompiled NoxScript for all 120 maps (`scratchpad\ww\*.go`) cross-referenced with the corpus db
(`objects` xfer script fields, `groups_`, `polygons.enter_player`, `waypoints`). Helper scripts in
`scratchpad\research\` (`callers.py MAP` lists every object or polygon that calls each function; `names.py` resolves
names and groups; `resolve.py` writes `res\*.go` with the variable names replaced by object/waypoint/wall names).

Conventions used below
- Time: 30 frames = 1 s. `FrameTimer(n)` is n frames, `SecondTimer(n)` is n seconds.
- Space: map pixels. Walls sit on a 23 px grid, a floor tile is 46 px, and corridors run on the diagonal, so one
  "tile step" along a corridor is (23,23) or (23,-23) ≈ 32 px.
- `G_*D` maps are byte copies of `G_*` (only the package name differs). War/Wiz/Con chapters share most layouts
  (54 distinct campaign layouts). Counts marked "quest" use the 8 original G_ maps; "campaign" uses one map per layout.
- Things the engine does internally (how fast an arrow trap re-fires, a Fist's fall delay, a crumbling floor's delay)
  are not visible in scripts; where I state them they are inferred from how the scripts drive the objects.
- Creature `ScriptEvents` slots: slot 0 = enemy sighted, slot 1 = **death** (verified: `VKDie`, `LichDie1`,
  `BossDie1-4`, `CallNextOgre`, `ReleaseGoldKeyBombers` all sit in slot 1), slot 4 = hit, slot 5 = retreat,
  slot 7 = heard, slot 8 = end of waypoint. `SetCallback(obj, 5, fn)` = death, `7` = hit, `3` = enemy sighted.

---

## 0. The building blocks (what each trap object does and how scripts drive it)

| Object | Placed as | Script control | Behaviour seen in scripts |
|---|---|---|---|
| `Spike` (radius 3, DANGEROUS) | carpets on an ~11 px grid (50-120 per field, up to 324 in Con09d) | `ObjectGroupOn/Off/Toggle` on a named group | ON = spikes up (Castle `SwitchSpikeGroup1` plays `FloorSpikesUp` on ON, `FloorSpikesDown` on OFF). Unscripted carpets are permanently up = "do not walk here" floor (G_Temple 887, G_Crypts 685 are almost all static). |
| `PeriodicSpike` | same ~11 px carpets (Wiz02C 326, War07G 268) | usually none; group Off/On to disable | Cycles up/down by itself. Scripts only switch a field off for a window (Wiz09c `ToggleOgreTrapSpikes01`). |
| `ArrowTrap1/2` | wall-mounted, in pairs or rows, at the end of the plate lane | `ObjectOn` then `ObjectOff` | Fires while ON. **ON for 1 frame = one volley** (the dominant idiom, 67 one-frame timers in the quest maps). Held ON while a plate is occupied = continuous fire (G_Castle, G_LOTD rows). |
| `Skull1-4` "skull guns" | wall decoration in groups of 2-8 | `ObjectGroupOn/Off` | Fireball shooters (G_Forest names the group `FireballTrapSkullGuns`). Switched on for 4-5 s as a punishment, or held on until a switch kills them. |
| `SentryGlobe`, `SentryGlobeN/E/W` | ceiling globes | `ObjectOn/Off`, groups | Death-ray beam. Fixed angle (`BasePosRadian`, `RotateSpeed` 0) or sweeping (`RotateSpeed` 0.0042-0.0377 rad/frame = one turn every 50 s down to 5.6 s; rotating ones come in back-to-back pairs 180° apart). |
| `SentryGlobeMovable` | carried by a `Mover` | `ObjectOn(sentry)` + `ObjectOn(mover)` | A beam that travels down a corridor (mover speed 3-20). |
| `SpikeBlock` / `StoneBlock` / `IronBlock` (60×60) | in slots beside a corridor | `Move(block, waypoint)` or a `Mover` | Slam across, crush, wall off, push. Return by a second `Move` home. |
| `RotatingSpikes` | free or on a `Mover` | `Move` along a looped waypoint path, or mover on/off | Spinning blade that patrols or sweeps; can smash walls and kill generators (see §5). |
| `Pit` | hidden under a plate | `ObjectOn(pit)` | Hole opens; the faller lands at `FallX/FallY` (lower level). |
| `PitCrumblingFloor` | big fields (Wiz09c 202, G_Forest 154, Con04c 95) | none | Crumbles by itself when walked on (`HoleXfer.ScriptTimeout` 4, 5 in Con04c, is presumably the delay). Never scripted except a door next to it. |
| `FireGrate` | floor grid (War02A 129) | decoration only | The flame is a separate object the script creates and deletes: `CreateObject("SmallFlame" → "MediumFlame" → "Flame" → "LargeFlame")` on waypoints over the grates. Pre-placed flame groups can also be toggled (Con04c `ToggleFlameGrates`). |
| `Glyph` | floor rune | none (xfer holds 1-3 spells) | Fires its spells when stepped on: Con09b STUN+FIST, STUN+FIREBALL at a target, CONFUSE+SUMMON_VILE_ZOMBIE; War07B CONFUSE, RUN, FUMBLE, SLOW, FIREBALL. |
| Statues (`StatueVictory4*`) and invisible `ColorLight`s | facing the trap area | `CastSpellObjectLocation(spell, statue, x, y)` | The visible or hidden "caster" of a scripted spell trap (death ray, Force of Nature). |
| `Mover` | at the carried object | `ObjectOn/Off`, `Move(mover, wp)` | Carries `MovedObjExtent` along its waypoint path. `MovingSpeed` field 2-200, typical 10-40 (100 for slammers, 2 for the Castle crusher). Unit not verified. |
| `MonsterGenerator` | often on a plate, in grids, or on a mover | `ObjectOn/Off`, `ScriptOnDestroy/Damage/Spawn` | Spawner and also a trigger (see §1). |
| Walls | secret/breakable flags in the map | `WallOpen/Close/Break`, `WallGroupOpen/Close/Break` | Doors to cages, seals behind the player, rubble. |
| Doors | normal doors | `LockDoor/UnlockDoor` | Lock the player in for the duration of a trap. |

---

## 1. Trigger taxonomy

### 1.1 Counts (every object/polygon whose xfer names a script function)

| Trigger | quest (8 maps) | campaign (54 layouts) |
|---|---|---|
| Pressure plate, pressed | 495 | 262 |
| Pressure plate, released | 204 | 87 |
| Invisible `Trigger`, pressed | 160 | 723 |
| Invisible `Trigger`, collided | 32 | 124 |
| Invisible `Trigger`, released | 14 | 22 |
| Switch/lever/button, pressed | 135 | 102 |
| Switch/lever/button, released | 14 | 33 |
| Polygon `enter_player` | 80 | 115 |
| Generator destroyed / damaged / spawned | 81 / 19 / 14 | 0 |
| Creature death event (slot 1) | 2 | 128 |
| Creature sighted / hit / heard / end-of-path | 0 | 189 / 129 / 53 / 56 |
| Wishing well use | 12 | 10 |

The quest maps are trap maps: plates and generator kills dominate. The campaign uses invisible triggers and
creature events (story and AI), with plates mainly in a few trap rooms.

### 1.2 Pressure plates (`PressurePlate`, visible floor object)
- **Who can press** (`AllowedObjClass`, all 1,849 plates): MONSTER|PLAYER 1,301 (70%), PLAYER 355, any class 168,
  OBSTACLE 6 (pushed blocks), FOOD 4, KEY 3, PLAYER+items (food/key/wand/weapon/armour/treasure) 3, MONSTER 4.
  `IgnoredObjClass` is used to exclude MONSTER (15), MONSTER|OBSTACLE (9), MONSTERGENERATOR (8).
  Design reading: trap plates are shared with monsters, so chasing monsters set off (and eat) your traps; puzzle
  and progress plates are player-only; weight/item plates accept any class.
- **Sizes**: 45×45 (369, a full tile), lane strips 60×25 / 25×60 / 30×60 / 60×30 (~550), thin strips 15×60 and
  15×15 corner pieces (Con04c and Crypts arrow rows, one strip per tile edge), 20×60 strips paired side by side
  (G_Castle arrow rows), 30×30 / 32×32 per-tile plates in pit grids.
- **Pressed** = the normal "step on it". **Released** is used for:
  1. step-OFF traps: the floor drops behind you (G_LOTD `PitHit1-22`, G_Mines `APitsRelease1-50`);
  2. item/weight removal: something rests on the plate from map start, and taking it away releases the plate
     (key, gold, or a generator; see 1.6);
  3. hold logic: pressed `+1`, released `-1` on a counter, effect stays on while the counter is above 0
     (G_Castle `NorthRow1Hit/Release` etc., G_LOTD `TombPlateHit/Release`);
  4. cage release by stepping past (G_Lava `MonsterRelease`, 16 plates, player only).
- **Collided** fires every frame something touches it; used only on invisible sensors.

### 1.3 Invisible triggers (`Trigger`, editor-only box)
- PLAYER 1,398, MONSTER|PLAYER 301, MONSTER 168, any 152, **OBSTACLE 90**, PLAYER|WEAPON 18, MONSTERGENERATOR 14,
  LIGHT 6, KEY 2.
- Uses: room-entry starts (60×60 pairs across a doorway), one-shot set-piece starts, and **block arrival sensors**:
  thin `allow=OBSTACLE` strips (60×10, 45×7, 15×15, 20×60) where a moving block lands, checked with
  `IsCaller(block)`. They chain stages, play the impact sound and screen shake, and reset traps
  (G_Crypts `CrushSFX1-3`, `BlockTrapEnd`; G_Lava `WackyGroup1-11`, `SlammerGroup1Wait`; G_Mines `Smash1-9`).
- `allow=LIGHT` + `IsCaller(orb)` = "put the orb on its pedestal" (Con10c `BlueIdol`/`RedIdol`: the sentry guarding
  the idol switches off). `allow=KEY` released = key picked up (G_LOTD `StartTombRayTrap`).
- 31×31 bumpers (`ForceOrb`, Con10a 4, Con10c 19, Wiz10b 63): `PushObject(caller, 60, random ±30)` with a bounce
  sound and a flash. A pinball field.

### 1.4 Switches (Button3/4, ChainPull3-6, FloorLever1-4, BrassLever1/2, WallSwitch1-4, LOTDSwitch1/2)
- Pressed and released are the two lever positions, so one function bound to both gives a toggle
  (`ToggleSpikes1`, `ToggleWalls`, `OpenArenaWalls`). Several Button4/FloorLever have `allow=MISSILE|PLAYER`, so they
  can apparently be shot.
- Roles: trap OFF switch (G_Castle `SentryRaySwitch`, `SwitchGun1`; G_LOTD `StopMechSentry`, `StopWallUp`; G_Forest
  `DisableCaveSkullGuns`, `DisableBanditCampExitSkullGun`; G_Mines `ShutOffGuns`); trap reset (G_Crypts
  `ResetBlockTrap`, G_Forest `ResetFireballTrap`, G_Castle `ResetCrusher`); trap START (G_Lava `StartClearingSpike`,
  G_LOTD `StartKillSpike`, G_Mines `StartBreakSpikes`, Wiz04b flame lever); progress (open wall groups, elevators).

### 1.5 Polygons
`enter_player` scripts fire when the player walks into a named room polygon: G_Crypts `TriggerBlockTrap` (guarded
by a flag and `HasClass(caller, PLAYER)`), G_Castle `OpenCrusherSecret`, G_LOTD `StartBlocker`/`OpenFluffyWall`,
War02A `openGauntlet`/`closeGauntlet`, Con04c `SkeletonAmbushTimer`. G_Mines uses 76 small polygons as **force
zones**: `FFHit1/3/4` each `PushObject(caller, 25, ±10, ±10)` (a constant diagonal shove, like wind or a conveyor).

### 1.6 Items, weight and pick-up (there is no pick-up event; it is built from plates)
| Pattern | Example | Mechanism |
|---|---|---|
| Take the item → trap | G_LOTD `SkullPlate`: SilverKey on a plate (allow any). Released → `CountDown`; pressed again → `StopCountDown` | Lift the key: walls close, 11 one-second ticks, then skull guns for 5 s. Put it back before the end to cancel. |
| | G_LOTD key on `Trigger allow=KEY` → `StartTombRayTrap` (released) | Fences close, sentry and generator walls open, doors lock, a moving death-ray starts 15 frames later. Killing the generator (`StopTombRayTrap`) stops it. |
| | G_LOTD key on plate 2779 → `StartStoneBlockSentry` (released) / `StopStoneBlockSentry` (pressed) | A block slides out, 1 s later a mover-carried sentry sweeps; it stops 4 s after reaching its sensor, or when the key goes back. |
| | Con09d `Gold` on a 48×48 plate: pressed → spikes off, released → `TriggerGoldTrap` | Take the gold: 324 spikes rise at once, 4 toxic clouds 20 frames later. |
| | Con08c `GoldKeyRemoved` (plate allow=KEY, released) | Walls and a bomber cage open. |
| Leave an item → hold a door | Con10a `UnlockSpikeDoor`/`LockSpikeDoor` (plate allows player + food/key/wand/weapon/armour/treasure) | The door is open only while something stands on the plate, so you drop an item to pass. |
| Several weights at once | G_Mines `PlateHit` ×4 (allow any; counter ≥ 4), G_Forest `BanditTreasureRoomPress` ×2, `CoopBridgeLever` (hold to keep a wall open), War07G `PlateOne/Two/ThreeTrigger` (flags; all three pressed) | Co-op or push blocks/bodies onto plates. |
| Bait creature on a plate | G_Castle `TrapGenerator` (generator on plate 2265: released → walls open + 4 generators on), G_Crypts `Peek-A-Boo` (generator on plate: released → 28 walls open), G_Lava `TimerPlate` (generator on plate: released → 10 s locked-door timer), G_Castle `SecretDown/Up` (4 generators on 4 plates) | Killing the obvious enemy springs the trap. |
| Block on a sensor | G_Temple `OpenPitSecretWall`, `EnableTempleEntrance`; G_Castle `OpenScaryBlockWall1/2`, `OpenNorthWall2`; G_Lava `StopSouthBlocks` | `allow=OBSTACLE` + `IsCaller(specific block)`. |

### 1.7 Killing things
- Generator `ScriptOnDestroy` (81 in the quest maps): **generator grids**, where destroying one switches on its
  neighbours (G_Temple `GenGrid01-03`, G_Forest 3×3 `GenGrid01`, G_LOTD F/M/B rows, G_Lava `GenRow1-3`, G_Mines
  Left/Right gens) or the next in a chain (G_LOTD `HallGen4→3→2→1`, `XGen1→2→3`, `FGen1→2→3`). It also stops a
  moving generator's mover (G_Temple `GeneratorPusher01Die`, G_Lava `StopMovingGen`) and counts kills to open walls
  (G_Lava `GenGone` = 2, G_Mines `OpenBackWall1` = 3, Castle `FourDoorKill` locks a door on the first kill).
- Generator `ScriptOnDamage`: `KillGen` (G_LOTD, G_Mines) checks whether the damager is one of the rotating spikes
  and applies `Damage(generator, 1000)`, so the blades destroy generators.
- Creature death (campaign): opens the next stage (Wiz09c `CallNextOgre`, Con10d `BossDie1-4` → orb walls, Con10a
  `LichDie1+2` → walls). Two-kill gates use flags (War07G `Group1Die` counter ≥ 2 → chamber doors).

### 1.8 Doors as triggers
Not used. Doors are only an effect (`LockDoor` 283 / `UnlockDoor` 209). "Opening the door sets it off" is built with
a Trigger strip just inside the doorway (e.g. G_Castle `StartGuardRay`, War07G `LockStairGate`).

### 1.9 Timers and perpetual loops
- `FrameTimer` constants across all maps: 1 (524: arrow pulses), 30 (191), 60 (122), 10 (73), 90 (60), 15 (56),
  45 (48), 2, 5, 20, 3, 25, 4. `SecondTimer` in the quest maps: 3 (13), 2 (10), 1 (9), 5 (8), 4, 15, 30.
- Loop idiom: the function re-schedules itself (`FrameTimer(n, Self)`), alternating a state variable (ping-pong) or
  stepping through a `switch` (rotation), and stops on a flag checked at the top (`if !flag { return }`) or through
  `CancelTimer(handle)` (14 in the quest maps).
- Started by: map start (`MapInitialize`: G_Swamp `BlockPusherLoop`, Con10d `SentryRun`, G_Forest boulder and
  patrolling blades), a one-shot trigger (G_Temple `ActivateSpikeBlock01` → `SpikeBlock01Loop`, Wiz09c `SpikeHall`),
  or a switch.

### 1.10 Sentries and line of sight
"Motion detection" is the engine's own `SentryGlobe` beam (fixed, rotating, or mover-carried) plus plates. No trap
polls the player's distance in a loop. `Distance` appears once in the quest maps (the Castle crusher homing
routine) and `IsVisibleTo` only in campaign AI code (Wiz09c `StopAndListen`).

### 1.11 Stateful logic (the reusable patterns)
| Pattern | Code shape | Examples |
|---|---|---|
| One-shot | first line `ObjectOff(GetTrigger())` | 367 times in the quest maps, 814 in all maps |
| One-shot via flag | `if flag { return }; flag = true` | Castle `ActivateGeneratorHallPushers`, LOTD `StartBlocker`, Lava `StartWackiness` |
| Re-arm | `ObjectGroupOff(plates)` … `FrameTimer(n, ResetX)` → `ObjectGroupOn(plates)` | Forest `ActivateSpikeBlockTrap` (110 + 80), LOTD `StartPusher` (45 + 45), Castle `StartBlockRow1` (15 + 20), Crypts fist (120) |
| Hold counter | pressed `n++`, released `n--`, effect `n > 0` | Castle 22 arrow rows, LOTD `TombPlate`/`SetHit` rows |
| N-of-M | counter, open at N | Crypts `ButtonPuzzleButtonPress` (2), Forest `ArcherRunButtonPress` (2), LOTD `OpenGolemWalls` (2), Lava `BarrelRelease` (3 barrels destroyed), Mines `PlateHit` (4), Lava finale buttons (3) |
| Sequence counter | each press opens the next cage | LOTD `OpenMonsterWalls` (12 plates → 4 cages), Lava `MonsterRelease` (16 → 4) |
| Toggle | `if IsObjectOn(x)` or a flag | Castle `SwitchSpikeGroup1`, `OpenEastFenceWalls`, Crypts `ToggleWalls` (random start state) |
| Combination lock | 3 levers each cycle 1-4; checker on every pull | Lava `Group1-3Lever` + `OpenOopsWalls` (see set piece 24) |
| Countdown | tick sound each step, `CancelTimer` on success | LOTD `CountDown` and `Counting`, Lava `StartTimer`, Mines `Countdown`, `AnkhCountDown`, `StartRayTrapTimer`, Forest `FireballTrapTickerLoop`, Swamp `SilverKeyBlockTimer` |
| Auto reset | timer or block-arrival sensor returns the trap to its start | Crypts `BlockTrapEnd` (90) → `BlockTrapResetComplete` → `EnableBlockTrap` after 300; Lava `WackyGroup11` after 30 s |

---

## 2. Effect taxonomy (API call counts, quest / campaign)

| Effect | Calls | Use in traps |
|---|---|---|
| `ObjectOn` / `ObjectOff` | 469/401, 640/421 | arrow pulses, sentries on/off, movers start/stop, generators wake, pits open, plates disarm/re-arm |
| `ObjectGroupOn/Off/Toggle` | 78+92+0 / 136+208+21 | spike fields, arrow rows, skull guns, plate groups, gears |
| `Move` (to waypoint) | 238 / 388 | blocks slam and return, blades along paths, sentries along paths |
| `MoveObject` (teleport) | 74 / 266 | statue puzzles, the crusher's 5 px/frame homing, putting a key on its spot |
| `WallOpen` / `WallGroupOpen` | 340+144 / 25+148 | monster cages, secret exits, reward rooms, trap reveals |
| `WallClose` / `WallGroupClose` | 48+34 / 8+43 | seal the player in behind them (airlocks, block traps, countdown rooms) |
| `WallBreak` / `WallGroupBreak` | 18+19 / 13+18 | rubble effects, ambush walls bursting, blades chewing through walls |
| `LockDoor` / `UnlockDoor` | 38+53 / 245+156 | lock-ins for the trap's duration |
| `CastSpellObjectLocation` / `LocationLocation` / `ObjectObject` | 20+0+1 / 20+20+5 | DEATH_RAY from statues (30 in G maps), FORCE_OF_NATURE every 5 s (G_Temple, Con08d), FIREBALL halls (Wiz04b, War02A), TOXIC_CLOUD (Con09d), FIST from the plate itself (Crypts, Con04c) |
| `CreateObject` / `Delete` | 0/519, 0/198 | flame grate animation (War02A, Wiz04b), bones flying (War02A) |
| `Damage` | 2 / 102 | blades killing generators (`KillGen`) |
| `PushObject` | 5 / 9 | force zones (G_Mines), bumpers (`ForceOrb`) |
| `Enchant(INVISIBLE)` | 37 / 34 | invisible monsters and generators (G_LOTD, G_Castle) |
| `Effect(JIGGLE)` | 76 in all maps | screen shake on block impact |
| `AudioEvent` | 138 / 539 | `SpikeBlockMove` (71 in the quest maps), `GenerateTick` countdown (15), `HammerMissing` impact (10), `ChangeSpellbar`/`CreatureCageAppears` machinery (elevators, pits), `FloorSpikesUp/Down`, `BigGong` at trap start |
| `Print` | 41 (quest) | `MsgTrapOn` 3, `MsgTrapOff` 6, `MsgWallLowered` 9, `MsgSeWallOpen` 4, `MsgElevOn` 5, `MsgDoorUnlock` 3 |

Effect families in plain words
- **Spikes**: toggle fields, alternate two fields, rotate one raised segment around a ring, timed disable windows.
- **Projectiles**: arrow volleys (pulse or hold), skull-gun fireballs (timed bursts), scripted fireballs between two
  fixed points on a loop.
- **Beams**: sentries fixed, rotating, travelling on movers, or cycled by script so a safe gap moves.
- **Moving masses**: spike/stone/iron blocks slam and return, cross-corridor crushers, chained block cascades,
  slow room crushers, shooting blocks, blades patrolling or sweeping.
- **Floors**: pits opening under or behind the player, crumbling fields (engine), force zones and bumpers.
- **Spells from things**: statues casting death rays at the presser, invisible origins casting Force of Nature every
  5 s, Fist from the plate itself (inferred: it falls after a short delay, so moving on saves you), toxic clouds,
  glyph runes.
- **Monsters**: cage walls open, generators wake (in grids and chains), invisible spawns, creatures switched from
  idle to hunting.
- **Lock-ins**: walls close behind you, doors lock, then reopen on success, a timer, or a kill.

---

## 3. Westwood's rhythm (the actual numbers)

| Mechanism | Timing | Where |
|---|---|---|
| Arrow trap volley | ON 1 frame (2 frames for the Con10a groups) | almost every arrow function |
| Arrow trap hold | ON while the plate counter > 0 | G_Castle rows, G_LOTD tomb rows |
| Fist plate | re-arm after 120 frames (4 s); the plate's own light goes dark meanwhile | G_Crypts, Con04c `DropFist`/`ResetFistTrap` |
| Single spike block ping-pong | 150 frames (5 s) each way | G_Temple `SpikeBlock01Loop` |
| Three-row crusher | 55 frames each way; rows start at 0 / 20 / 40 frames (a rolling wave) | G_Crypts `BlockCrusherRow1-3Loop` |
| Perpetual block pushers | 90 frames (3 s) each way, 3 rows in sync | G_Swamp `BlockPusherLoop` |
| Jaw blocks (corridor stage) | impact sound at 20 frames, blocks back at 50 frames | Con04c `CloseBlockTrap01-03` |
| Row slammer | impact 15 frames, plates re-arm 20 frames later | G_Castle `StartBlockRow1-4` |
| Pusher | out 45, back 45, re-arm | G_LOTD `StartPusher` |
| Two-block trap | return after 110, re-arm after another 80 | G_Forest `ActivateSpikeBlockTrap` |
| Sweeping blades | out 60, home 60, re-arm | G_Forest `ActivateRotatingSpikes` |
| Slammers on movers | wait 3 s at the far end, retreat, re-arm on arrival | G_Lava `SlammerGroup1Wait` |
| Shooting blocks | one block every 3 s, three in rotation (9 s per lane) | G_Lava `ShootBlock1-3` |
| Chained block cascade | each pair starts when the previous lands; auto-home after 30 s | G_Lava `StartWackiness` |
| Alternating spike fields | each toggles every 60 frames, offset 60 (up 2-4 s) | Wiz09c `ToggleSpikes1/2` |
| Rotating spike segment | one of 6 segments up, advances every 30 frames | Wiz09c `SwitchSpikeState` |
| Spike chamber | pairs 1+3 / 2+4 alternate every 3 s with a 10-frame all-down gap | War07G `ChamberSpikes` |
| Unused spike pattern | 3 s up, 2 s down, two groups alternating | G_Lava `SpikeGroup1Up` etc. |
| Spike door window | spikes off 150 frames (5 s), ticks speed up (22 → 1 frame) | Wiz09c `ToggleOgreTrapSpikes01` |
| Sentry rotation (3 beams) | change every 90 frames, one beam off at a time | G_Castle `SentryRun` |
| Sentry gap (6 beams) | gap moves one beam every 25 frames; every 6th step all on | Con10d `SentryRun` |
| Rotating sentries | 0.0042 rad/frame = 50 s per turn (slowest) to 0.0377 = 5.6 s | Con10c, Con10d, G_LOTD |
| Flame grate wave | each row: off 60, then Small 2 → Medium 2 → Flame 12 → Medium 2 → Small 2 (80-frame cycle, ~0.7 s burning); 10 rows start 4 frames apart | War02A `flameWalk1-10` |
| Flame wall | 56 flames ramp up in 6 frames, hold 150 frames (5 s), ramp down | Wiz04b `flameLever` |
| Fireball hall | one fireball (or two side by side) every 60-75 frames | Wiz04b `skullHallOn`, War02A `skullHallOn1` |
| Force of Nature trap | every 5 s | G_Temple `FONTrap01Loop`, `FireFONTrap02` |
| Lock-in fireball room | ticks every 15 frames; side walls open at 3 s, guns at 10 s, reset at 15 s | G_Forest `FireballTrapTickerLoop` |
| Countdowns | 10 s (G_Lava `StartTimer`, G_Mines `AnkhCountDown`), 11 s + 5 s guns (G_LOTD `CountDown`), 16 s (G_LOTD wall-up, G_Mines sentry trap), 26 s + 4 s guns (G_Mines `Countdown`), 10 s gate (G_Swamp `SilverKeyBlockTimer`) | |
| Crusher reset | 15 s | G_Castle `CrusherWait` |
| Trap auto re-arm | 90 frames return, 300 frames until armed again | G_Crypts block trap |
| Ambush delay | walls break 45 frames after entering | Con04c `SkeletonAmbushTimer` |
| Greed trap | spikes instantly, poison 20 frames later | Con09d `TriggerGoldTrap` |
| Arena | spikes up 10 frames after the lever, cages open at 90, spikes down 90 after the kill | War02A `loadArena4` |
| Zipper | pairs of blades launched every 4 frames (20 blades in 40 frames) | War02A `cascade1-10` |

Rule of thumb from these numbers: **danger windows of 0.5-1 s, safe windows of 2-5 s, re-arm 1.5-4 s**,
countdowns of 10-16 s (26 s for a puzzle), and stagger offsets of 4-20 frames to turn a group into a travelling wave.

---

## 4. Exemplary set pieces

Format: map and approximate area (px); objects; essential script; how to get through it. S = short and simple,
M = medium, L = long chain.

### 1. Fist plates with an armed light (S) - G_Crypts (13 plates around the map), Con04c (13)
Objects: one PressurePlate 35×60 or 45×45 (MONSTER|PLAYER) with a `ColorLight` on the same spot. Four of them form a
diamond around (1230,4956).
```go
func DropFist(a1 int) {
    ns.CastSpellObjectLocation(ns.SPELL_FIST, plate[a1], ns.GetObjectX(plate[a1]), ns.GetObjectY(plate[a1]))
    ns.ObjectOff(plate[a1]); ns.ObjectOff(light[a1])
    ns.FrameTimerWithArg(120, a1, ResetFistTrap)   // light + plate back on, click sound
}
```
Play: the lit plate is the tell. Keep moving and the fist lands behind you. A dark plate is safe for 4 s. Monsters
chasing you trigger it too.

### 2. Arrow corridor, one plate per trap (S) - Con10a (EnableArrow07-38, 2 halls), Wiz10b (9), Con10c (21)
Objects: a wall line of ArrowTrap1/2 spaced 50-200 px, each with its own lane plate (60×30 / 30×60).
```go
func EnableArrow27() { ns.ObjectOn(Arrow27); ns.FrameTimer(1, DisableArrow27) }
```
Play: each plate fires one volley straight down its lane. Step around the plate or sprint through. Undead patrol
the same hall (Con10a skeleton lords that go hostile when they see you).

### 3. Greed trap (S) - Con09d (4565,3161)
Objects: `Gold` on a 48×48 plate (allow any) in the middle of 324 Spikes, 4 waypoints for clouds.
```go
func DisableGoldTrapSpikes() { ns.ObjectGroupOff(GoldTrapSpikes) }        // pressed (gold resting)
func TriggerGoldTrap() { ns.ObjectGroupOn(GoldTrapSpikes); ns.FrameTimer(20, TriggerGoldTrapPoison) }
```
Play: the field looks safe; picking up the gold raises every spike around you, then gas. Grab and run, or leave it.

### 4. Lift the key, start the clock (S/M) - G_LOTD (1514,4166)
Objects: SilverKey on `SkullPlate` (45×30, allow any), tomb walls, 8 skull guns (`TombGuns`).
```go
func CountDown() { if n < 11 { WallGroupClose(TombTrapWalls); AudioEvent(GenerateTick); n++; t = SecondTimer(1, CountDown) } else { StartTombGuns() } }
func StopCountDown() { CancelTimer(t); WallGroupOpen(TombTrapWalls); n = 0 }       // plate pressed again
func StartTombGuns() { ObjectGroupOn(TombGuns); SecondTimer(5, StopTombGuns) }       // then walls reopen
```
Play: taking the key seals the tomb and ticks for 11 s. Drop something (or the key) back on the plate to cancel, or
survive 5 s of fireballs, after which the walls reopen.

### 5. Bait generator (S) - G_Castle (2185,2645), G_Crypts (3128,1391), G_Lava (1509,1599)
Objects: a MonsterGenerator standing on a plate (allow any).
```go
func TrapGeneratorOn()  { ObjectOff(GetTrigger()); WallGroupOpen(TrapGeneratorWalls); ObjectGroupOn(WizGroup1) } // plate released
func TrapGeneratorOff() { WallGroupClose(TrapGeneratorWalls); ObjectGroupOff(WizGroup1) }                       // pressed at start
```
Play: destroying the lone generator releases the plate: 12 walls drop and 4 more generators wake. In G_Lava the same
idea locks four doors and starts a 10-tick timer instead; killing the room's 3 other generators unlocks them.

### 6. Timed spike door (S) - Wiz09c (1617-1805, 5205-5393)
Objects: 70 PeriodicSpikes in front of a SpikedDoor, a ChainPull and a plate.
```go
func ToggleOgreTrapSpikes01() { ObjectOff(plate); ObjectOff(chain); ObjectGroupOff(OgreTrapSpikes01)
    UnlockDoor(OgreSpikeDoor01); SpikeTimerAudioLoop(); FrameTimer(150, ResetOgreSpikeDoor01) }
func SpikeTimerAudioLoop() { AudioEvent(Gear1); FrameTimer(k, SpikeTimerAudioLoop); k-- }   // ticks accelerate
```
Play: pull, then cross 70 spikes and pass the door within 5 s while the ticking speeds up.

### 7. Hold-to-fire arrow rows (M) - G_Castle North/South rows (2352-2664, 2165-2550), East (3266-4199, 736-1265), West (2047-2300, 1863-2116); G_LOTD tomb (1111-1418, 4331-4922)
Objects: per row a pair of 20×60 strip plates across the corridor (two tiles wide) and one ArrowTrap2 at the row's
end. North and South have 3 rows of 6 plates each, East 10 rows, West 6.
```go
func EastRow3Hit()     { cnt3++; CheckRows(15) }
func EastRow3Release() { cnt3--; CheckRows(15) }
// CheckRows: if cnt3 > 0 { ObjectOn(EastArrow3) } else { ObjectOff(EastArrow3) }
```
Play: the trap fires continuously while anyone (or any monster) is on its row, so cross each row in one stride and do
not fight on the strips.

### 8. The 22-lane arrow hall (M/L) - G_Temple ArrowTrap09 (plates 4887-5474, 943-1449)
Objects: 22 trap pairs (ArrowTrap1 rows 1-16 on one wall, ArrowTrap2 rows 17-22 on the adjacent wall), 66 plates
60×25 laid on diagonals so each lane holds 1-5 plates. A 1-frame volley per press. The map warms up first with
ArrowTrap01-08 (one or two lanes each).
Play: find the plate-free tiles between lanes, keep moving diagonally, and never stand still in a lane. Each plate
fires again every time it is pressed.

### 9. Staggered three-row crusher (M) - G_Crypts (931-1345, 3139-3553)
Objects: 6 SpikeBlocks in 3 rows of 2 (left and right jaws), Home/Dest waypoints, 3 thin `allow=OBSTACLE` sensors
(45×7) that play `HammerMissing` on impact.
```go
func EnableBlockCrusher() { ObjectOff(GetTrigger()); BlockCrusherRow1Loop(); FrameTimer(20, BlockCrusherRow2Loop); FrameTimer(40, BlockCrusherRow3Loop) }
func BlockCrusherRow1Loop() { if st == home { Move(b6, Block06Home); Move(b7, Block07Home) } else { Move(b6, Block06Dest); Move(b7, Block07Dest) }; FrameTimer(55, BlockCrusherRow1Loop) }
```
Play: the rows close in a wave 20 frames apart, so each row's open window comes 20 frames after the previous one.
Cross a row just after it opens.

### 10. Perpetual block pushers (M) - G_Swamp (4587-4909, 2012-2334)
Objects: 3 rows of 2 SpikeBlocks, 12 waypoints, 3 15×15 impact sensors.
```go
func BlockPusherLoop() { /* swap all six between WP set A and B */ AudioEvent(SpikeBlockMove ×3); FrameTimer(90, BlockPusherLoop) }
func BlockPusherRow1Boom() { if IsCaller(b3) || IsCaller(b4) { Effect(JIGGLE, row1, 4, 0); AudioEvent(HammerMissing) } }
```
Play: running from map start, always on a 3 s beat with sound and screen shake on each slam; wait for the slam and
cross on the retreat.

### 11. Jaw corridor in three stages (M) - Con04c (3668-4151, 1138-1621)
Objects: 16 SpikeBlocks in facing pairs, 3 groups of 3 plates (the middle one 25×25, two 60×25 lane strips).
```go
func CloseBlockTrap01() { ObjectGroupOff(BlockTrap01Triggers); Move(SpikeBlock01..06 → BlockWP01..06)
    FrameTimerWithArg(20, 1, BlockTrapBoom); FrameTimerWithArg(50, 1, ResetBlockTrap) }
```
Play: each stage snaps shut 0.7 s after you step on it and reopens at 1.7 s. Step on, step back, wait for the
reopen, go. The next stage is a few tiles on. Arrow rows (`ActivateRow01-11`, 15 px strips, hold counters) and fist
plates fill the rest of this map.

### 12. Spike chamber with a fight inside (M) - War07G (2430-2874, 1050-1494)
Objects: 4 spike quadrants (59/54/66/73 Spikes) around a centre, 2 mage NPCs, chamber doors.
```go
func ChamberSpikes() { if flip { off(2,4); FrameTimer(10, EnableSpikes1And3) } else { off(1,3); FrameTimer(10, EnableSpikes2And4) }; SecondTimer(3, ChamberSpikes) }
func Group1Die() { n++; if n >= 2 { UnlockDoor(ChamberDoor1); UnlockDoor(ChamberDoor2) } }
```
Play: opposite quadrants are raised and they swap every 3 s with a 10-frame all-clear. Fight the two mages from the
lowered pair and step across during the swap. The doors open only when both are dead.

### 13. Rotating spike ring and alternating hall (M) - Wiz09c (ring 2208-2599, 4094-4485; hall 2277-2702, 5232-5658)
Objects: 6 Spike segments (46-70 each) round a room, 3 entry triggers, a lever; in the hall two overlapping fields
(90 and 60 Spikes).
```go
func StartSpikes() { ObjectGroupOff(SpikeSegTriggers); LockDoor(SpikeSegRoomDoor); FrameTimer(60, SwitchSpikeState) }
func SwitchSpikeState() { ObjectGroupOff(seg[i]); if run { i = (i+1) % 6; ObjectGroupOn(seg[i]); FrameTimer(30, SwitchSpikeState) } }
func UnlockSpikeSegRoomDoor() { UnlockDoor(SpikeSegRoomDoor); run = false }    // FloorLever4 in the room
func ToggleSpikes1() { ObjectGroupToggle(HallSpikes1); FrameTimer(60, ToggleSpikes2) }
```
Play: the door locks behind you and one segment is raised, moving round the ring each second. Walk behind it
round the room to the lever, which unlocks the door and stops the ring. The hall alternates its two fields every 2 s.

### 14. Three death-ray sentries, one safe lane (M) - G_Castle (sentries 3189-3666, 225-726; start triggers 2949,295; off switch 3869,802)
Objects: 5 SentryGlobeN with fixed angles, 2 start triggers, WallSwitch4.
```go
func SentryRun() { switch st { case 0: On(S3); On(S4); Off(S5); st = 1 /* ... */ }; if !off { FrameTimer(90, SentryRun) } else { Off(S1..S5) } }
func SentryRaySwitch() { if !off { off = true; ObjectOff(GetTrigger()); Print("MsgTrapOff") } else { off = false; SentryRun() } }
```
Play: two of the three beams are always on and the dark one changes every 3 s. Cross in the dark lane, wait at the
edge for it to come round, and turn the sentries off at the switch for the way back.

### 15. Travelling gap in a beam fence (M) - Con10d (6 sentries 1318,4224 → 2008,4914)
Objects: 6 SentryGlobeN in a diagonal line, 195 px apart, all aimed the same way (2.32 rad), so they make 6
parallel beams.
```go
// state 0: S1 and S6 off; 1: S5 off; 2: S4 off; 3: S3 off; 4: S2 off; 5: all on   (each state 25 frames)
```
Play: the off beam walks one step every 0.8 s and then all six are on for one step. Move with the gap, beam to beam.

### 16. Death-ray statues taking turns (M) - G_Castle `TakeShot` (9 plates 424-609, 5232-5415; statues 276-851, 5014-5589), G_LOTD `TakeShot` (11 plates near 540-793, 2379-2587; 4 statues), `KillEm` (14 plates 3461-3622, 218-379; 6 statues in a ring), `FireDoomStatue` (4 plates, 1 statue)
```go
func KillEm() { switch k { case 1: CastSpellObjectLocation(SPELL_DEATH_RAY, RayStatue1, GetObjectX(GetCaller()), GetObjectY(GetCaller())); k++ /* ... */ case 6: ...; k = 1 } }
```
Play: every plate press makes the next statue in the ring fire at the spot where you stood. The ray needs a moment
to land, so keep moving and never step on two plates in a row from the same spot. Generators in the same area are
invisible (`GuardGenInviso`) and the nearby wells give infravision.

### 17. Locked fireball room (M) - G_Forest (plates 2564-2817, 4692-4968; guns 2485-2919, 4670-4855)
Objects: 9 plates (various sizes down to 9×9) covering the floor, 6 entrance walls, 19 surrounding walls, 8 skull
guns, a ticking gear, a reset button.
```go
func ActivateFireballTrap() { ObjectGroupOff(plates); run = true; WallGroupClose(EntranceWalls); ObjectOn(TickerGear); Ticker() }
func Ticker() { t += 0.5; AudioEvent(GenerateTick)
    if t == 3 { WallGroupOpen(SurroundingWalls) }; if t >= 10 { ObjectGroupOn(SkullGuns) }
    if t >= 15 { ResetFireballTrap() } else { FrameTimer(15, Ticker) } }
```
Play: almost any step seals the room. At 3 s the surrounding walls drop and open the room out; at 10 s the guns
start and fire until the reset at 15 s, when the entrance reopens. The reset button (2714,4443, north of the plate
area) ends it early.

### 18. Skull-gun puzzle against the clock (M) - G_Mines (room 3135-3419, 237-509)
Objects: entry Trigger, 2 wall groups (in and out), 4 plates 60×60 (allow any), 8 skull guns.
```go
func StartCountDown() { if solved { return }; WallGroupClose(SkullWalls1); WallGroupClose(SkullWalls2); ObjectOff(StartTrapTrigger); Countdown() }
func Countdown() { if n < 26 { AudioEvent(GenerateTick); n++; t = SecondTimer(1, Countdown) } else { StartSkullGuns() } }   // guns on 4 s
func PlateHit() { hits++; if hits >= 4 { PuzzleSolved() } }     // open both walls, guns off
```
Play: you are sealed in with 26 s to load all four plates at once (blocks, players, monsters). Fail and the guns fire
for 4 s; the trigger re-arms only after a solve.

### 19. Pick up the key, flee the beam (M) - G_LOTD (key 2665,4394; sentry 2307,4523)
Objects: SilverKey on `Trigger allow=KEY`, 3 wall groups, 2 doors, SentryGlobeMovable on a Mover (speed 5), one
MonsterGenerator.
```go
func StartTombRayTrap() { WallGroupClose(TombTrapFenceWalls); WallGroupOpen(TombTrapSentryWalls); WallGroupOpen(TombTrapGenWalls)
    LockDoor(d1); LockDoor(d2); ObjectOff(GetTrigger()); FrameTimer(15, StartTheRay) }
func StopTombRayTrap() { stopped = true; ObjectOff(TombRayMover); ObjectOff(TombRay); /* walls open */ UnlockDoor(d1); UnlockDoor(d2) } // generator destroyed
```
Play: half a second after you lift the key, a beam starts gliding toward you and the room spawns monsters. The only
way out is to destroy the generator while dodging the beam.

### 20. Block trap with a reset button and a monster price (M/L) - G_Crypts (blocks 3737-3921, 1299-1483; reset button 3927,752)
Objects: 5 SpikeBlocks, polygon trigger, start and end sensors (60×5, allow=OBSTACLE), reset Button4, wall groups
for path, button alcove, monsters, secret, exit.
```go
func TriggerBlockTrap() { if !armed && HasClass(GetCaller(), PLAYER) { armed = true; WallGroupClose(BlockTrapPathWalls); WallGroupOpen(BlockTrapButtonWall)
    Move(SpikeBlock01..05 → Dest); Print("MsgTrapOn"); AudioEvent(BigGong) } }
func ResetBlockTrap() { Move(blocks → Home); WallGroupOpen(BlockTrapPathWalls); WallGroupOpen(BlockTrapMonsterWall); Print("MsgTrapOff") }
func BlockTrapEnd() { if IsCaller(SpikeBlock03) { ObjectOff(resetButton); FrameTimer(90, BlockReturn) } }   // blocks reached the end
func BlockTrapResetComplete() { if IsCaller(SpikeBlock03) { WallGroupOpen(BlockTrapPathWalls); FrameTimer(300, EnableBlockTrap) } }
```
Play: entering the room seals it, gongs, and drives five blocks down the corridor. Reach the revealed button before
they arrive and they retreat, but the reset also opens a monster alcove. If you dodge to the end instead, they return
after 3 s and the trap re-arms 10 s later. `BlockTrapSecretFound` opens a side passage.

### 21. Chain-reaction block cascade (L) - G_Lava "Wackiness" (2085-3135, 145-1073)
Objects: 22 plates (50×50, player only) over a large room, 22 SpikeBlocks in 11 pairs on Movers, 11 sensors
(allow=OBSTACLE).
```go
func StartWackiness() { if busy { return }; busy = true; Print("MsgTrapOn"); Move(Wacky1, WackyStart1); Move(Wacky2, WackyStart2); t = SecondTimer(30, WackyGroup11) }
func WackyGroup1() { if IsCaller(Wacky1) || IsCaller(Wacky2) { Move(Wacky3, WackyStart3); Move(Wacky4, WackyStart4) } }
// ... WackyGroup10 starts pair 11; WackyGroup11 (sensor or the 30 s timer) sends all 22 home and clears busy
```
Play: any plate starts a domino run of slamming pairs through the room. You can see the next pair start where the
last one hit, so read the chain and stay one step ahead. Everything resets after 30 s.

### 22. Slammers and shooting blocks (M) - G_Lava (slammer blocks 3572-3894, 1088-1433, plates 3166-3465, 667-996; shooting lane 2706-2982, 2154-2430)
```go
func StartSlammerGroup1() { ObjectOn(SlammerMover1); ObjectOn(SlammerMover2) }             // speed 100
func SlammerGroup1Wait()  { ObjectGroupOff(SlammerGroup1); SecondTimer(3, SlammerGroup1Retreat) } // blocks reached the far sensor
func ShootBlock1() { ObjectOn(ShootingBlockMover1); SecondTimer(3, ShootBlock2) }          // 2 → 3 → 1 ...
func NoShootBlock1() { ObjectOff(ShootingBlockMover1) }                                    // arrival sensor
```
Play: a slammer pair fires across the hall at top speed when you step on its plate, holds 3 s, then retreats; the
next pair is a few tiles on. In the shooting lane one of three blocks crosses every 3 s in a fixed order, so watch
one full round and cross behind the block that has just gone.

### 23. Floor that collapses as you walk (M/L) - G_LOTD `PitHit1-22` (3948-4285, 3028-3365), G_Mines `APitsRelease1-50` (1042-1441, 3396-3795) and `OpenPit1-30` (1088-1353, 4799-5064), G_Temple `GoodiePit1-32` (1207-1437, 1161-1391)
```go
func PitHit7() { ns.ObjectOff(ns.GetTrigger()); ns.ObjectOn(PitLine7) }     // plate RELEASED (40x40, player only)
func OpenPit13() { ns.ObjectOff(ns.GetTrigger()); ns.ObjectOn(FinalPit13) } // plate PRESSED (32x32)
```
Play: the release versions drop each tile behind you, so you can never go back. The press versions (G_Mines final
pits, G_Temple treasure floor) drop the tile you step on into a lower level; read safe tiles from the room or pull
the side chain (`OpenPitNorth/South`) that opens a way round.

### 24. Combination statues with punishment (M) - G_Lava (levers 4155-4339, 4615-4891; statues 4196-4616, 4645-5319)
Objects: 3 levers, 12 movable statues (N/E/S/W per group), 3 lights, 4 wall groups (East/South/West "Oops" cages,
Tada reward).
```go
func Group1Lever() { g1 = g1 % 4 + 1; /* MoveObject: statue g1 to the centre spot, the others home; light on/off */ OpenOopsWalls() }
func OpenOopsWalls() { if g1 == 2 && g2 == 2 && g3 == 2 { WallGroupOpen(EastOopsWalls) } /* 3,3,3 South; 4,4,4 West; 1,1,1 all three */
    if g1 == 2 && g2 == 1 && g3 == 4 { ObjectOff(levers...); WallGroupOpen(TadaWalls) } }
```
Play: each pull rotates which statue faces you and the lights hint at the answer. Uniform guesses open monster
cages; the right mix (2,1,4) locks the levers and opens the reward.

### 25. Blades that eat walls and generators (L) - G_Mines (blades 644-690, 2031-2077; 9 sensors 1019-1387, 1349-1717), G_LOTD (5 KillSpikes 1372-1464, 1058-1150 next to the F/M/B generator rows), G_Swamp (`BreakRotatingSpikeWall01-05`), G_Lava (`BreakClearWalls1-6`)
```go
func StartBreakSpikes() { ObjectOff(GetTrigger()); ObjectOn(BreakMover1..3) }            // FloorLever3, mover speed 15
func Smash1() { if IsCaller(BreakSpike2) { ObjectOff(GetTrigger()); WallGroupBreak(Break1) } } // ... Smash9
func KillGen() { if IsCaller(BreakSpike1..3) { Damage(GetTrigger(), BreakSpike2, 1000, 0) } } // generator ScriptOnDamage
```
Play: you release the saw yourself. It grinds down a corridor, bursting each wall section as it reaches it and
deleting the generators in its path. Run ahead of it or let it clear the generator gallery for you. G_Lava's
clearing spikes break each wall pair, then the next pair 2 s later.

### 26. Room crusher with a puzzle lock (L) - G_Castle (blocks 4899-5175, 2967-3243; 11 start plates)
Objects: 7-block wall (2 StoneBlocks, 5 SpikeBlocks) on slow movers (speed 2), 4 doors, arrival sensor, solve plate,
2 chain resets, 4 entry plates (`StartBlockRow1-4`) where block pairs slam with screen shake.
```go
func StartCrusher() { if running { return }; CancelTimer(homing); if !solved { LockDoor(CrusherDoor1..4) }; Move(CBlock1..7 → CBlockWP1..7); running = true }
func CrusherWait() { reset = SecondTimer(15, ResetCrusher) }        // wall arrived
func ResetCrusher() { /* walk the blocks home 5 px per frame (SetMe), then unlock the doors */ }
```
Play: stepping anywhere in the room locks you in and starts the wall creeping across. Keep something on the solve
plate (allow any, ignores blocks) and the doors stay unlocked; otherwise dodge until the reset 15 s after the wall
arrives, or use the chain pulls.

### 27. Race the rising wall (S/M) - G_LOTD (triggers 2261-2307, 1303-1349; walls about 2392-2553, 920-1081; switch 2568,919), G_Mines `AnkhCountDown`
```go
func Counting() { AudioEvent(GenerateTick); n++; RaiseWall() }
func RaiseWall() { switch n { case 2: WallClose(w1) case 4: WallClose(w2) /* ... */ case 16: WallClose(w8) }; if n < 17 { t = SecondTimer(1, Counting) } }
func StopWallUp() { ObjectOff(GetTrigger()); CancelTimer(t); WallOpen(w1..w8) }    // LOTDSwitch2
```
Play: a barrier rises one section every 2 s with a tick every second. Reach the switch inside 16 s and the wall
drops again. In G_Mines you must touch the ankh within 10 ticks or the exit seals.

### 28. The Gauntlet (L) - War02A (flames 861-1229, 3254-3622; fireball hall 2323,2047 → 2794,2518; smasher 1345-1713, 3622-3990; arenas; zipper 3300-3806, 4266-4772)
A string of stages along one route:
1. **Demonstration**: a red-shirt NPC runs in first. A monster-only trigger (`bonesFly`, allow=MONSTER) crushes him:
   80 bones fly out, the screen shakes, his talking skull rolls over to you. The player sees the trap kill before
   meeting it.
2. **Block smasher**: 3 trigger squares (`blockSmash1-3`) each launch 2 SpikeBlocks on movers (speed 40) across the
   path; impact sensors play `HammerMissing` + JIGGLE.
3. **Flame grate wave** (`flamesOn`): doors lock behind you, then 10 rows of 8 grates each burn for about 0.7 s in an
   80-frame cycle, rows 4 frames apart, so a fire wave rolls down the hall. Wait for the wave to pass and follow it.
   `fireGrateReward` gives 100 XP at the end.
4. **Fireball hall** (`skullHallOn1`): a fireball from one fixed point to another every 75 frames (2.5 s); cross
   between shots (250 XP reward trigger).
5. **Arenas 1-4**: a lever opens cage walls (spiders, urchins, a troll on an elevator); in Arena 4 spikes rise 10
   frames after the lever, the cages open at 90 frames, the spikes drop 90 frames after the kill and the exit
   unlocks.
6. **Zipper of Death** (`enableZipperOfDeath`): 20 rotating-spike movers launched in pairs every 4 frames, closing
   the corridor like a zip, with rumble and machinery loops every 30 and 5 frames.
7. Exit gates of 20 iron blocks on movers grind open and shut with gears (`openGauntlet`/`closeGauntlet`).

### 29. Ambush layering (S, campaign) - Con04c `SkeletonAmbushTimer` (polygon, walls break 45 frames later), `ZombieAmbush`; Wiz09c `MoveBlocks01`
```go
func MoveBlocks01() { ObjectGroupOff(BlockTrigger01); Move(Block01..12 → BlockWP01..12); WallGroupOpen(SecretWallGroup01); ObjectOn(OgreFighter01); Wander(OgreFighter01) }
func CallNextOgre() { WallGroupOpen(SecretWallGroup02); ObjectOn(OgreFighter02) }          // death of ogre 1
func MoveBlocks02() { MoveObject(SilverKey, SilverKeySpot); Effect(BLUE_SPARKS); /* blocks reshuffle */ FrameTimer(45, CloseWalls) } // death of ogre 2
```
Play: 12 iron blocks box you into an arena, one ogre at a time comes out of the walls, and the key appears when the
second dies.

---

## 5. How traps and monsters combine

1. **Shared plates.** 70% of plates accept MONSTER|PLAYER, so a pursuer sets off the same arrows, fists and
   slammers, often on itself. Puzzle and progress plates are player-only, and some exclude monsters explicitly
   (G_Castle `SecretDown`, G_Lava `MonsterRelease` ignore MONSTER).
2. **The plate releases the monsters.** Sequential cages (G_LOTD `OpenMonsterWalls`: each of 12 plates opens the next
   of 4 cages; G_Lava `MonsterRelease`: 16 step-off plates), cage per plate (Wiz09c `ReleaseA-F`: unlock the jail
   door and `CreatureHunt`), a lever that opens the arena (War02A `releaseUrchins1`), and the reset that costs a
   monster alcove (G_Crypts `ResetBlockTrap`).
3. **Bait.** A generator on a plate is the trap trigger (set piece 5). Killing a grid generator wakes its
   neighbours, so the fight grows as you win (G_Temple, G_Forest 3×3, G_LOTD, G_Lava, G_Mines).
4. **Moving spawners.** Generators on movers drift toward you or along a track (G_Temple `GeneratorPusher01-04` speed
   7-10, G_Lava `MovingGenerator` speed 25); destroying one stops its mover.
5. **Traps that kill monsters.** Rotating blades destroy generators on contact (`KillGen`, 1000 damage), and arrows
   on shared plates hit whatever stands in the lane. The player can turn a trap on the enemy (release the saw into
   the generator gallery).
6. **Fight inside the trap.** War07G mages inside the alternating spike chamber; War02A Arena 4 spikes rise as the
   troll arrives; Con10d rotating sentries in the orb room guarded by 2 liches and 2 mech golems (each death opens
   orb walls); Con10a skeleton lords patrolling the arrow hall.
7. **Lock-in then release.** The trap seals you in (walls close, doors lock) and ends with an opening that lets
   monsters in or you out (Con04c skeleton ambush 45 frames after entry; G_Swamp `OpenOgreBlockGate` opens the iron
   blocks and starts 2 generators at once; G_Crypts `Ambush` plate opens 10 walls).
8. **Invisible enemies plus a counter-buff.** G_LOTD and G_Castle enchant spawns and generators invisible
   (`GuardGenInviso`, `InvisoMonster`, `InvisoSpawn`), and G_LOTD's three wells give infravision for 30 s.
9. **Guns covering an exit.** G_Forest `StartSkullGun` turns on a skull gun at the bandit camp exit with a chain pull
   to silence it; G_Crypts' skull guns sit behind a wall switch; G_Forest `ArcherRun` needs 2 buttons pressed under
   archer fire.
10. **Monster-only triggers.** Con10a `OpenSkelPitWallGroup` (a monster walking on the plate opens the pit ambush),
    War02A `bonesFly` (the NPC victim), G_Temple `OpenBossRoomWalls` and `OpenGoldKeyExitWall` (allow=MONSTER,
    released: the guardian leaving its spot opens walls).

---

## 6. Layout patterns

**Corridor and lane sizes.** Trap lanes are 1-3 tiles wide on the diagonal. G_Castle rows are two 20×60 strips side
by side (about 2 tiles), G_Temple and Con10a lanes 60×25 or 60×30 per tile with 1-5 plates in a lane, Con04c rows use
15 px strips on each tile edge, G_Crypts' sliding arrow window has 10 traps 23 px apart along one wall. Arrow traps
sit within about 30-90 px of the first plate of their lane (median: G_Castle 27, G_LOTD 54, Con10a 76, G_Crypts
91). Block traps are 60×60 blocks parked beside a corridor whose width is one or two blocks. Spike carpets are
~11 px grids, 150-450 px across.

**Stages in a row.** Short traps come as 1-3 repetitions of one idea a few tiles apart (Con04c jaw stages 1-3,
G_Castle `StartBlockRow1-4`, War02A `blockSmash1-3`, Forest arrows 1-2). Long gauntlets chain 4-7 different ideas
along one route (War02A: smasher → flames → fireballs → arenas → zipper). The quest maps are networks of 15-30 trap
rooms, each built round one idea.

**Rest areas.** Every quest map has wishing wells that restore health (`WellOfRestoration`, `MakeAWish`: G_Temple 2,
G_Crypts 1, G_Forest 1, G_Swamp 1, G_Castle 1, G_Mines 1), and some wells counter the map's threat instead: G_Lava's
two give fire protection for 60 s ahead of its fire traps, G_LOTD's three give infravision for its invisible
monsters. Elevators and lowered secret walls (`MsgWallLowered`) mark the end of a stage.

**Signposting.**
- Not with corpses or signs: bone props are no more common near plates and arrow traps than on random floor (10%
  vs 11.5% within 100 px), and there are no signs or blood within 100 px of any of 1,182 trap points.
- With visible hardware: pressure plates are visible floor objects (the invisible `Trigger` is the hidden one), arrow
  traps, skull guns, sentry globes and statues are visible on the walls, spike carpets are visible, and fist plates
  carry their own light that goes dark while the trap re-arms. Light sources are more common near traps (68% vs
  57%).
- With sound and screen feedback: `SpikeBlockMove` grinding before blocks move, `HammerMissing` + JIGGLE screen
  shake on impact, `GenerateTick` countdown clicks, `FloorSpikesUp/Down`, a `BigGong` at the start of big traps,
  machinery sounds (gears, `ChangeSpellbar`) when pits and elevators move, and text (`MsgTrapOn`, `MsgTrapOff`).
- With demonstration: War02A shows an NPC dying in the gauntlet before the player enters, and G_Lava's `Wackiness`
  shows each next block pair starting where the last one landed.

**Teaching curve.** A trap type first appears alone and simple, then in combination. G_Temple runs single arrow lanes
(ArrowTrap01-08, 1-2 plates each) before the 22-lane hall; G_Crypts spreads single fist plates before the 4-plate
diamond; Con04c gives one hallway arrow pair before the 11-row hold field; War02A teaches each gauntlet element in a
separate room before the zipper.

**Re-usable rules for our maps.**
1. Every trap needs a visible tell (plate, wall hardware, a light that shows armed or disarmed) and a sound that
   starts 0.3-1 s before the damage.
2. Give the player a readable rhythm: a 2-5 s safe window, a 0.5-1 s danger window, and 4-20 frame offsets to make
   a wave rather than a wall.
3. Provide an off switch, a reset, or a counterplay item for every trap that can lock the player in, and reopen the
   lock-in on a timer if nothing else.
4. Let monsters use the same plates, and put a generator or monster cage on the far side or on the trigger itself.
5. Teach each mechanism once in isolation, then combine two, then build the long gauntlet, with a well between
   stages.
