# Trap engine semantics (OpenNox ~v1.9.0-alpha13, from source)

Sources: `opennox/src` (Go + transpiled C in `src/legacy/*.c`), `opennox-lib`, `thing.bin` (decoded with
`noxtools things thing2json`), Westwood usage from `corpus/out/nox_corpus.db` + `corpus/out/json/*.json`.
Citations are `file:function`. C files are in `src/legacy/`. "frame" = server tick, 30/s.
Anything not proven from code is marked **UNCONFIRMED**.

## 0. Ground rules that apply to every trap

### 0.1 Units and shapes
* World units: one wall-grid step = 23 units, a floor tile diamond = 46 units across
  (`GAME1.c:nox_xxx_tileNFromPoint_411160` uses `(x+11.5)/46`).
* thing.bin `SPEED` is divided by 32 (`server/object_type.go` ~l.411, `fv := Speed/32`); missiles get x2 on top.
* `EXTENT CIRCLE r` = circle of radius r. `EXTENT BOX w h` is a **diamond** (square rotated 45 deg), not an
  axis-aligned box: `server/object_type.go:ShapeBox.Calc` puts the corners at `+-(w+h)*0.35355` along X/Y.
  A 32x32 box (Pit, PressurePlate is 45x45) covers `|dx|+|dy| < 22.6` around its centre.
  The point-in-shape test is `GAME5_2.c:nox_xxx_map_57B850`.
* All thing types start **Enabled** (`server/object_type.go` "typ.flags |= object.FlagEnabled"); a map object
  stores its own flags only when they differ from the type (`GAME3_3.c:nox_xxx_mapReadWriteObjData_4F4530`
  reads a 1-byte "has extra data" marker, then the flags masked by 0x11408162 and calls ObjectOn/ObjectOff).
  In the corpus JSON the marker is `term` (255 = flags stored, 0 = type defaults = enabled) and the stored
  flags are `cflags` (0x1000000 = enabled, 0x40 = NO_COLLIDE without enabled = starts OFF).

### 0.2 Movement physics (needed for timing)
* Per frame the server runs 5 velocity sub-steps of 0.2 (`server.go:Server.updateCollide` ->
  `GAME4_1.c:nox_xxx_updateObjectsVelocity_5118A0`): `vel += (force - vel*drag)*0.2; pos += 0.2*vel`.
  Drag (`Float28`) is 0.5 for non-missiles (`server/object_type.go`, `typ.Field13 = 0.5`), so terminal
  speed = 2 x force per frame.
* Player base speed = 100/32 = 3.125 (thing.bin NewPlayer SPEED 100). Walk force = SpeedCur, run force =
  2 x SpeedCur (`object_update.go:unitUpdatePlayerImplA`, "switch from walking to running", cursor > 100 units
  from the player = run). So **walk = 6.25 u/frame (187 u/s), run = 12.5 u/frame (375 u/s)**.
  Slow enchant halves SpeedCur (`server.go:updateUnitsCCC`).

### 0.3 The collision filter (most important rule for "jump over" traps)
`GAME5.c:sub_548360` decides whether two objects can collide at all. No collision if:
* either has flag DESTROYED|NO_COLLIDE (0x60);
* both have ALLOW_OVERLAP (0x8);
* **one has BELOW (0x1) or SHORT (0x10) and the other has AIRBORNE (0x4000) or FALLING (0x20000)** -
  *unless one of them is the invisible `Trigger` thing type* (it is special-cased by name);
* door vs ALLOW_OVERLAP/BELOW object; elevator vs elevator; shaft vs shaft; same team when flag 0x400.
Pairs are de-duplicated per frame (`GAME5.c:nox_xxx_collSysAddCollision_548630`), so a COLLIDE handler runs
**once per frame per touching pair**, and then `GAME5.c:nox_xxx_collide_548740` calls it.

### 0.4 Contact damage formula (DamageCollide)
`GAME3_3.c:nox_xxx_collideDamage_4E9430`: on each frame of contact with an object that has health,
damage = `N >> 1` where N is the thing.bin argument; special case N == 1 -> 1 damage on odd frames only.
So per frame: N=1 -> 1 on odd frames and 0 on even frames, 2 -> 1, 3 -> 1, 4 -> 2, 6 -> 3, 8 -> 4, 10 -> 5.
BUT for Flame, Lava and Explosion damage `nox_xxx_damageDefaultProc_4E0B30` rounds any result (even 0) up to 1 after fire
protection (`if (!a4) a4 = 1`), so the even-frame 0 of a SmallFlame still hurts: flames deal at least 1 per frame.
Per second of contact: N=1 flame 30, 2 -> 30, 3 -> 30, 4 -> 60, 6 -> 90, 8 -> 120, 10 -> 150 (N=1 non-flame: 15).
* There are **no invulnerability frames** for players (`GAME3_3.c:nox_server_handler_PlayerDamage_4E17B0`,
  `GAME3_2.c:nox_xxx_damageDefaultProc_4E0B30`): every frame of contact hurts.
* Armour: Blade/Impale/Explosion/Bite/Claw/Impact are reduced by armour (`(1-armour)*dmg`), Crush by half
  armour, Flame and Lava are **not** reduced by armour (switch in `nox_server_handler_PlayerDamage_4E17B0`),
  only by fire protection (`nox_xxx_checkFireProtect_4DFE40` in `nox_xxx_damageDefaultProc_4E0B30`).
  Minimum 1 damage after reduction. Monster subclass flag 0x400 ignores Flame and Lava, 0x200 ignores poison.
* A single hit of 20+ puts the player in a stagger state 30 (`nox_xxx_damageDefaultProc_4E0B30`, end).
* Buff 23 (invulnerable) blocks everything.
Damage type ids (opennox-lib `object/damage.go`): 0 Blade, 1 Flame, 2 Crush, 3 Impale, 4 Drain, 5 Poison,
6 DispelUndead, 7 Explosion, 8 Bite, 9 Electric, 10 Claw, 11 Impact, 12 Lava, 13 DeathMagic ...

### 0.5 ObjectOn / ObjectOff / ObjectToggle
Script `ObjectOn/Off/Toggle` -> `object.go:Object.Enable/Toggle` -> `GAME3_3.c:nox_xxx_objectSetOn_4E75B0` /
`nox_xxx_objectSetOff_4E7600`: set/clear flag ENABLED (0x1000000) and, **only for classes FIRE (0x2000),
READABLE (0x40000) or FLAG (0x10000000)**, also clear/set NO_COLLIDE. Elevators play a sound.
Clients do not draw VISIBLE_ENABLE things while disabled (`nox_xxx_unitSetOnOff_4E4670` syncs it).
For every other class, OFF does nothing by itself: the object's UPDATE function must read the flag
(spikes, traps, pits, triggers, sentries do - see each section).

## 1. Jumping (question 3) - the key mechanic for "jump over" traps

Code: `object_update.go` case `player.CCJump` and `unitUpdatePlayerImplA` case `server.PlayerState12`.
* Jump does **not** change height (z). It sets flag **AIRBORNE (0x4000)** on the player and enters state 12.
  Refused while Berserker Charge or War Cry is active, or when `nox_xxx_playerCanMove_4F9BC0` fails; it cancels
  spells being cast (`nox_xxx_cancelAllSpells_4FEE90`).
* Cost: **90 stamina** (`GAME4.c:nox_xxx_playerSubStamina_4F7D30`). Stamina max 100, regenerates
  100/30 = 3 per frame (`object_update.go`, `ud.Field22_3 += 100/TickRate`), so **at most one jump per ~30
  frames (1 s)**. With `pl.Field3656 != 0` the jump is refused with an exertion sound + text message 13
  (UNCONFIRMED what Field3656 is; probably exhausted/over-encumbered).
* Duration: the JUMP animation of NewPlayer has 9 frames x (1+1) ticks (thing.bin NewPlayer draw: JUMP
  frames_per_dir 9, field_8 1; read by `server/object_type.go:PlayerAnimFrames`) -> **AIRBORNE for 18 frames
  (0.6 s)**, then the flag is cleared and the state returns to 0.
* While jumping the force is fixed to facing x 2 x SpeedCur (= the run force, 6.25) every frame; the direction
  cannot be steered. With the physics of 0.2 that gives: **running jump = 225 units, walking jump = 214,
  standing jump = 203 units** (terminal 12.5 u/frame). Haste/slow scale it (SpeedCur).
* While AIRBORNE the collision filter (0.3) skips every object with **BELOW or SHORT**:
  all flames, FireGrateFlame, CampFire, LavaFountain, OgreFirePit (SHORT); Spike/PeriodicSpike (SHORT+BELOW);
  Pit/ForestPit/PitCrumblingFloor (BELOW); PressurePlate (BELOW); Glyph/BearTrap/PoisonGasTrap (SHORT);
  crates, CaveBoulders (SHORT) -> **all jump-clearable**.
* **Not** skipped (still hit while jumping): SpikeBlock / StoneBlock / IronBlock (SHADOW only), RotatingSpikes
  (no flags), Boulder / RollingBoulder (SHADOW), walls, monsters, missiles (arrows and fireballs are AIRBORNE
  but the player is neither SHORT nor BELOW), the invisible **`Trigger`** thing (special-cased by name in
  `sub_548360`), and SentryGlobe beams (not a collision, see 9).
* Landing inside a hazard: the frame the flag clears, normal collision resumes, so if the player's centre is
  still inside a pit/flame at frame 18 he falls/burns. Keep pits/flame strips **narrower than ~150 units**
  along the run direction to leave margin for a late jump (225 max at full run).
* Monsters never jump (no code path); permanently AIRBORNE monsters (Bat, FireSprite, ...) ignore every
  BELOW/SHORT trap.

## 2. Flames, fire grates, camp fires (question 7)

thing.bin (class FIRE|DANGEROUS|LIGHT, flags ALLOW_OVERLAP|SHORT|FLICKER, UPDATE NoUpdate):

| thing | radius | COLLIDE | damage per frame | per second |
|---|---|---|---|---|
| SmallFlame (+Immobile, +Cleanse) | 4 | DamageCollide 1 FLAME | 1 (odd frames 1, even frames 0 rounded up to 1 for flame) | 30 |
| MediumFlame | 6 | DamageCollide 2 FLAME | 1 | 30 |
| Flame | 8 | DamageCollide 3 FLAME | 1 | 30 |
| LargeFlame | 12 | DamageCollide 4 FLAME | 2 | 60 |
| FireGrateFlame (LIFETIME 14) | 12 | DamageCollide 10 FLAME | 5 | 150 |
| CampFire r10 / OgreFirePit r25 / LavaFountain r24 (LavaFountain is not FIRE class) | | DamageCollide 6 FLAME | 3 | 90 |
| SmallBlueFlame / MediumBlueFlame / BlueFlame / LargeBlueFlame (r 4/6/8/12) | | ManaDrainCollide 3/6/9/12 | 0 HP; drains that much **mana per frame** (players only) | |

* Damage path: `GAME3_3.c:nox_xxx_collideDamage_4E9430` (formula in 0.4). Flame damage ignores armour, is
  reduced by fire protection (`nox_xxx_checkFireProtect_4DFE40`); fire-immune monsters (subclass 0x400) ignore it.
* Blue flames: `GAME3_3.c:nox_xxx_collideManadrain_4E9490` - players with mana only, no HP damage.
* "Immobile" variants only add class IMMOBILE (mass forced to 1e10 in `server/object_type.go`, not pushable).
  "Cleanse" variants only change a ray-trace mask in `nox_xxx_updateObjectsVelocity_5118A0`.
* **ObjectOff works**: FIRE class => OFF also sets NO_COLLIDE (no damage) and the client hides it; ObjectOn
  restores both (`nox_xxx_objectSetOff_4E7600` / `nox_xxx_objectSetOn_4E75B0`). Instant, same frame.
* **Jump-clearable** (SHORT). A radius-12 flame is a 24-unit disc; even a 100-unit-deep strip is easily jumped.
* FireGrate itself (BOX 32x32, BELOW, NoCollide, NoUpdate) is decoration. FireGrateFlame has LIFETIME 14
  (UNCONFIRMED how lifetime expiry is applied; probably self-deletes after 14 frames, so a "flame jet" needs a
  script that re-creates it with `CreateObject("FireGrateFlame", pos)` on a timer).
* No burning / afterburn status: the collide code applies no buff.

## 3. Floor tiles: lava, water

* **Lava tile** (tile index 6 = "Lava" in the thing.bin FLOR list): `GAME4_1.c:nox_xxx_updateObjectsVelocity_5118A0`
  adds a pseudo-collision with code 6 for any object that is **not AIRBORNE**, has health, and whose new position
  is on a Lava tile; `GAME5.c:nox_xxx_collide_548740` then deals **2 damage of type 12 (Lava) per frame**
  (60 HP/s), not reduced by armour, reduced by fire protection, ignored by fire-immune monsters.
  **Jumping over lava avoids the damage.** Monster pathing avoids lava (`unit_ai_path.go` checks tile 6).
* **Water / deep water**: no damage and no drowning code found. The tile is only used for footstep sounds
  (`object_update.go`, material 128 = RunOnWater) and teleport permission
  (`GAME1.c:nox_xxx_mapTileAllowTeleport_411A90`, the *NoTeleport* water tiles). Deep water blocks movement only
  if the map puts walls around it - UNCONFIRMED (no tile-collision code found).

## 4. Spike and PeriodicSpike (question 2)

* Both: class DANGEROUS|IMMOBILE|VISIBLE_ENABLE, flags ALLOW_OVERLAP|SHORT|BELOW, circle r=3 (contact when the
  player's r=10 circle overlaps, i.e. centre within ~13 units), COLLIDE `DamageCollide 2 IMPALE` =>
  **1 damage per frame (30 HP/s), reduced by armour**.
* Spike UPDATE `SwitchUpdate` -> `GAME4_3.c:nox_xxx_updateSwitch_53B320`: enabled => collidable,
  disabled => NO_COLLIDE. PeriodicSpike UPDATE `LoopAndDamageUpdate(3 1 5)` -> `GAME4_3.c:sub_53B300`:
  **identical behaviour**. The three numbers are parsed (`GAME4_3.c:sub_536580`) but **never read by the
  server**: PeriodicSpike does **not** cycle by itself in this engine. Any up/down rhythm must come from a script
  toggling it (WW did that with timers); the looping art is client-side only.
* Spikes are special-cased to stay on the collision list although immobile
  (`GAME4_3.c:nox_xxx_unitHasCollideOrUpdateFn_537610`).
* Westwood: 12290 Spike objects in 41 maps as dense carpets; 9785 with default flags (= ON), 2503 stored OFF
  (term 255, cflags 0) and raised by script.
* **Jump-clearable** (SHORT/BELOW). For timed spike floors toggle with ObjectOn/Off/Toggle: the safe window is
  exactly the scripted OFF time (frames).

## 5. Pit, ForestPit, PitCrumblingFloor - falling (question 3)

thing.bin: class HOLE|DANGEROUS|IMMOBILE|VISIBLE_ENABLE, flags BELOW|ALLOW_OVERLAP, BOX 32x32 (diamond,
`|dx|+|dy| < 22.6`), UPDATE TrapDoorUpdate, COLLIDE TrapDoorCollide, XFER HoleXfer, INIT BreakInit,
CREATE AnimCreate. The three are the same machine; only the art differs.

HoleXfer (`GAME3_3.c:nox_xxx_XFerHole_4F51D0`), corpus JSON names in brackets:
* script handler (`UnknownScriptHandler`): called when something first touches a disabled hole (event 20);
* `FallX`, `FallY` (ints): **where a faller is teleported**;
* `ScriptTime1`: absolute frame of a pending opening (normally 0); `ScriptTimeout`: uint16 **delay in frames**
  between the first touch and the opening; `ScriptActivated`: already-triggered latch.

Collide (`GAME3_3.c:nox_xxx_collideTrapDoor_4EAB60`), for any object that is not a door:
* **Hole enabled** = open pit: if the object's centre is inside the diamond (`nox_xxx_map_57B850`) and the object
  fits (circle diameter <= 32, i.e. radius <= 16; box W,H <= 32; point-shaped items always), set flags
  FALLING|IN_HOLE and store FallX/FallY and the pit centre. Players (r=10), most humanoids (r 10-15) and all
  items fall; **monsters with radius > 16 never fall** (check thing.bin EXTENT).
* **Hole disabled** = intact floor: on the first touch (latch 0), unless the toucher is a player with **Tread
  Lightly** active (ability 4), set the opening frame to now + ScriptTimeout (only if the timeout > 0), call the
  script handler, set the latch.

Update (`GAME4_3.c:nox_xxx_updateTrapDoor_53DE80`):
* disabled and the opening frame reached -> **turns itself ON (becomes an open pit)**, anim state 2->4, sound 874;
  5 s later the art switches to fully open (state 8). It stays open for good.
* enabled -> animation only; clears the latch.

Fall (`GAME4_1.c:nox_xxx_updateFallLogic_51B870`):
* While IN_HOLE: velocity zeroed, pulled to the pit centre (force 3), z += vz, vz -= 1 per frame. After
  **11 frames** (z < -50) the object is raised to z=90, IN_HOLE is cleared and it is **teleported to
  (FallX, FallY)**; it drops ~11 more frames and lands (landing sound for players). **No damage and no death**
  anywhere in the fall code. WW sends fallers to a lower room or onto a `PitExit` (class EXIT, ExitCollide)
  that loads another map. FallX/FallY must always be set (0,0 would put the player at the map origin).
* So a pit costs position: the penalty is whatever waits at FallX/FallY (a pit-bottom room with monsters, or
  the walk back to the gauntlet start). A real death pit needs FallX/FallY over lava/spikes, or a script.

Crumbling timing in Westwood data (PitCrumblingFloor ScriptTimeout): 4 frames (1094 objects, 29 maps),
5 (372), 1 (52), 0 (50), 30 (1). With 4 frames the floor opens ~0.13 s after the first touch: at run speed
(12.5 u/frame) the player moves ~50 units in that time, so one 32-box tile is crossed safely only when running;
a field of crumbling tiles drops a walker. **Holes stored ON (cflags 0x1000000) are permanent pits; stored OFF
are crumbling/trap floors.** WW also has 222 plain *Pit* objects stored OFF with timeout 0: those never open by
themselves; a script ObjectOn's them (trapdoors).
* **Jump-clearable**: BELOW => no collide while airborne, neither falling into an open pit nor triggering a
  crumbling one. Landing inside an open pit = fall.
* Pushed into a pit: yes by composition - falling only checks the centre position, so any push (SpikeBlock
  contact, script `PushTo`, fireball blast `nox_xxx_mapPushUnitsAround_52E040`) that moves the centre into an
  open pit makes the player fall.

## 6. SpikeBlock, StoneBlock, IronBlock and the Mover (question 2)

thing.bin: SpikeBlock = class OBSTACLE|DANGEROUS|SIMPLE, flags SHADOW, BOX 60x60 (diamond, corners 42 units from
the centre on X/Y), z 0-45, SPEED 60, MASS 9999999, COLLIDE `DamageCollide 3 IMPALE` (**1 damage/frame,
30 HP/s, armour-reduced**), UPDATE `SpikeBlockUpdate`. StoneBlock/IronBlock: same body, `DefaultCollide` (no
damage). *Immobile variants: class IMMOBILE.
* `SpikeBlockUpdate` is registered with a **nil function** (`server/object_type.go` init:
  `RegisterObjectUpdate("SpikeBlockUpdate", nil, 2200)`), as are crates, coffins, MovableBookcase1-4,
  SmallStoneBlock. A block does nothing by itself and ObjectOn/Off do nothing to it (not FIRE class).
* **How Westwood moves them**: script `Move(block, waypoint)` (War04a "CloseBlockTrap01": `ObjectOff(plate)`,
  `Move(SpikeBlock01, wp14)`, `Move(SpikeBlock02, wp15)`, after 20 frames `BlockTrapBoom`, after 50 frames
  `ResetBlockTrap` -> ObjectOn(plate)). That is a two-block **crusher**.
* `Move` for a non-monster (`server__script__builtin.c:nox_server_scriptMoveTo_5123C0`): finds every **Mover**
  object whose `MovedObjExtent` equals the block's map extent id and calls
  `nox_xxx_moverGoTo_5124C0`: Mover ON, state 0, start waypoint = wp. **Without a Mover placed in the map the
  block does not move.** Westwood placed 871 Mover objects (70 maps), all stored OFF (cflags 0x40).
* Mover (thing `Mover`: SIMPLE, NO_COLLIDE|EDIT_VISIBLE, UPDATE MoverUpdate, XFER MoverXfer) -
  `GAME5.c:nox_xxx_unitUpdateMover_54F740`, xfer `GAME3_3.c:nox_xxx_XFerMover_4F5730`
  (`MovingSpeed` int, `WaypointID` start, `MovedObjExtent`, `MoveType` = initial state byte,
  `WaypointStartID`/`WaypointEndID` = current/previous waypoint, `MoverAcceleration`/`MoverSpeed` floats):
  * state 0 + enabled: snap the Mover onto the carried object, speed = MovingSpeed x 0.25, head to the waypoint;
  * state 1: each frame the **carried object is teleported onto the Mover** (`nox_xxx_unitMove_4E7010`) and the
    Mover's velocity is set to `dir x speed`; drag decays it inside the frame, so the real pace is about
    0.74 x speed = **0.18 x MovingSpeed units/frame** (WW MovingSpeed 15 -> ~2.8 u/frame, 83 u/s; computed,
    UNCONFIRMED in play);
  * on passing a waypoint: 0 links -> carried object placed exactly on it and the Mover **stops for good**
    (state 3, removed from updates); 1 link -> follow it; several links -> random link that is not the one it
    came from (so a 2-way chain ping-pongs, a loop circulates);
  * disabled -> state 2 (pause), re-enabled -> resume.
  * The Mover also stops if the carried object loses flag ACTIVE (0x4) or is destroyed.
* What a moving block does to a player: the block is teleported, then the normal overlap resolution
  (`GAME5.c:sub_54AD50` circle-vs-box) adds a separation force on the lighter object proportional to the
  overlap, so **the player is shoved along** in front of the block, and takes the DamageCollide damage every
  frame of contact. Against a wall the player is squeezed and keeps taking 1/frame (no instant kill; there is
  no crush-death code). A shove can carry the player into an open pit (section 5).
* **Not jump-clearable** (SHADOW only, not SHORT). Avoid by timing (gaps between passes) or side alcoves.
* Script `obj.CreateMover(wp, speed)` (ns v4, `object.go:Object.CreateMover`) is **broken in alpha13**: it never
  sets `MovedObjExtent` (UpdateData field 8 stays 0, and the C update removes a Mover with field 8 == 0 on its
  first tick) and it stores the speed as float32 where the C code reads an int. Place Mover objects in the map
  instead (MoverXfer) and drive them with `Move(obj, wp)` / ObjectOn / ObjectOff.

## 7. RotatingSpikes, boulders, doors

* **RotatingSpikes**: class OBSTACLE|DANGEROUS|SIMPLE|VISIBLE_ENABLE, flags NULL, circle r=12, z 0-30,
  MASS 100000, COLLIDE `DamageCollide 8 IMPALE` = **4 damage/frame (120 HP/s, armour-reduced)**, **no UPDATE**
  (thing.bin UPDATE missing): the rotation is client art only. Static unless carried by a Mover.
  **Not jump-clearable** (no SHORT flag). Gotcha: ObjectOff hides it (VISIBLE_ENABLE) but, not being FIRE
  class, it keeps colliding and damaging (from `nox_xxx_objectSetOff_4E7600`; UNCONFIRMED in play) - Delete it
  or move it instead of switching it off. RotatingSpikesImmobile: same, immobile.
* **Boulders**: CaveBoulders (SIMPLE, SHORT, r12, mass 13), BoulderCave/BoulderMine (OBSTACLE, r32, mass 999),
  Boulder / BoulderIndestructible (OBSTACLE, SHADOW, r32, mass 10, drag forced to 0.01 in
  `server/object_type.go` so they roll far when pushed), RollingBoulder (same + `DamageCollide 3 CRUSH`,
  1 dmg/frame). UPDATE `BoulderUpdate` is **not registered** anywhere (logged as unknown handler), INIT
  `BoulderInit` (`GAME3_3.c:nox_xxx_unitBoulderInit_4F0420`) only stores the spawn point. So boulders are
  **pushable rubble / physics props**, never self-propelled. A "rolling boulder trap" = RollingBoulder carried by
  a Mover, or pushed every frame with script `ApplyForce`/`PushTo` (low drag makes a single strong push roll it
  a long way). CaveBoulders are SHORT: jumped over, and arrows fly over them.
* **SpikedDoor**: plain DOOR class with DoorUpdate/DoorCollide/DoorXfer. Neither `GAME3_3.c:nox_xxx_collideDoor_4E8AC0`
  nor `GAME4_3.c:nox_xxx_updateDoor_53AC50` deals damage - cosmetic.

## 8. ArrowTrap1/2 and Skull1-4 (question 4)

thing.bin: ArrowTrap1/2 = class IMMOBILE|VISIBLE_ENABLE, r8, UPDATE `SkullUpdate(MercArcherArrow)`, INIT
`SkullInit(1 1)` (ArrowTrap1) / `SkullInit(-1 1)` (ArrowTrap2), COLLIDE NoCollide. Skull1-4 = same with
`SkullUpdate(StrongFireball)` and SkullInit (-1 -1)/(1 -1)/(-1 1)/(1 1).
* **Direction is fixed by the thing type**, not by the map: `GAME3_3.c:sub_4F0450` converts the (dx,dy) pair to
  a facing (`nox_xxx_xferDirectionToAngle_509E00`). World +x = screen right, +y = screen down, so
  (1,1) = shoots **down-right (SE)**, (-1,1) = **down-left (SW)**, (1,-1) = up-right (NE), (-1,-1) = up-left (NW).
  ArrowTrap1 = SE, ArrowTrap2 = SW, Skull1 NW, Skull2 NE, Skull3 SW, Skull4 SE. (A script could re-aim with
  `LookAtDirection`; UNCONFIRMED that it sticks for these objects.)
* Update (`GAME5.c:nox_xxx_updateShootingTrap_54F9A0`), only while **enabled**:
  * every **30 frames** it scans (`sub_54FBB0` -> `sub_54FBF0`): any player or monster (class 6), not dead,
    inside the **700 x 700 square centred on the trap** (+-350 units), that is an *enemy* of the trap
    (`server/object.go:Server.IsEnemyTo`: an unowned, teamless trap is an enemy of **players and monsters
    alike**; give the trap a team to make it ignore that team), with a clear line of sight
    (`nox_xxx_mapCheck_537110`) and **in front** of the trap (`nox_server_testTwoPointsAndDirection_4E6E50`,
    8-sector table; exact cone width UNCONFIRMED, expect the front half/quarter);
  * on a fresh detection the cooldown is cleared, so it **fires at once**, then at most **one shot per 30
    frames** while the last scan saw a target (it can fire one extra shot after the target left, until the next
    scan);
  * projectile spawned at radius+4 in the facing direction (`nox_xxx_createArrowTrapProjectile_54FA80`),
    velocity = facing x missile speed (MercArcherArrow SPEED 800/32 x2 = **50 u/frame**), sound 889, FX.
* Arrow damage: `ArrowTrapDamage = 25` (gamedata.bin) written into the arrow's MonsterArrowCollide data;
  `GAME3_3.c:nox_xxx_collideMonsterArrow_4EB800` deals it as **IMPALE (type 3, armour-reduced)** and deletes the
  arrow. Shields can block (player blocking state in `nox_server_handler_PlayerDamage_4E17B0`).
* Skull fireball (`StrongFireball`, `SparkExplosionCollide 192`): `GAME3_3.c:nox_xxx_fireballCollide_4E9AC0` deals
  192>>1 = **96 FLAME** to the hit target plus area damage 96 in radius 64 (falloff, inner 15) and a push
  within 50 units. Deadly; ~12 u/frame (192/32 x2).
* Arrows/fireballs are AIRBORNE missiles: they pass over SHORT objects (crates, CaveBoulders) - cover must be a
  non-SHORT obstacle (pillar, wall, StoneBlock). Jumping does not dodge them.
* Westwood stored 469/477 ArrowTrap1 and 322/326 ArrowTrap2 **OFF** (cflags 0x40) and switched them on by
  script/plate; default (term 0) = ON.
* Designer levers: ON/OFF window, placement relative to the corridor (700-unit square, front only), 1 shot/s.
  Smoke things ArrowTrap1Smoke/2Smoke are client FX.

## 9. SentryGlobe (question 5) - Westwood's "laser"

thing.bin: SentryGlobe, SentryGlobeN/E/S/W (identical except editor art), SentryGlobeMovable (not IMMOBILE,
mass 99999999): class LIGHT|SIMPLE(|IMMOBILE)|VISIBLE_ENABLE, flags AIRBORNE, r10, UPDATE SentryGlobeUpdate,
XFER SentryXfer.
* SentryXfer (`GAME3_3.c:nox_xxx_XFerSentry_4F5E50`): `BasePosRadian` (start angle), `RotateSpeed`
  (radians **per frame**), `CurrentPosRadian`.
* Update (`GAME4_1.c:nox_xxx_updateSentryGlobe_510E60`), while **enabled**, every frame: cast a ray of
  **600 units** at the current angle (`cos/sin`; 0 = east/right, pi/2 = south/down, pi = west, 3pi/2 = north),
  stopped by walls (`nox_xxx_mapTraceRay_535250` mode 5); then add RotateSpeed to the angle. Every object in
  the ray's bounding box with health, not BELOW/NO_COLLIDE, not SHORT (except monsters in quest mode), whose
  circle touches the segment (`GAME4_1.c:nox_xxx_sentry_511020`, `nox_xxx_mathPointOnTheLine_57C8A0`) takes
  **500 damage of type 16 (ZapRay)** - full damage for players, i.e. **instant death**, every frame.
* While **disabled** the angle is reset to BasePosRadian (so ObjectOn always restarts the sweep from the base).
* Detection is purely geometric (beam contact); nothing "sees" or alarms. Monsters are killed too.
* **Not jump-clearable** (the victim filter checks the victim's BELOW/NO_COLLIDE/SHORT, and a jumping player is
  none of those). Beams stop at walls, not at objects: hide behind wall corners.
* Westwood: RotateSpeed 0 (static beams toggled by script) or 0.0042-0.0377 rad/frame = one revolution every
  50 s down to 5.6 s (Con10c/d, War10c/d, LOTD). Angles: 3.927 (= 5pi/4, up-left), 2.339/2.356 (down-left),
  0.785 (down-right), 3.14 (left), 4.71 (up).

## 10. Glyph, BearTrap, PoisonGasTrap (question 6)

* **Glyph** (class DANGEROUS|SIMPLE|NOT_STACKABLE, flags ALLOW_OVERLAP|SHORT, r10, COLLIDE GlyphCollide, XFER
  GlyphXfer, DIE GlyphDie, INIT GlyphInit, no UPDATE).
  * GlyphXfer (`GAME3_3.c:nox_xxx_XFerGlyph_4F5890`): `Angle` (facing byte), `TargX/TargY` (spell target
    point), `Spells` (up to 5 spell names). Init data = `server/object_glyph.go:GlyphInitData`.
  * Trigger: any object colliding with it (`spell_trap.go:nox_xxx_collideGlyph_4E9A00`), refused by
    `GAME3_3.c:sub_4E9A30` when same team as the glyph, (game flag 512) both owners players, or the toucher has
    **Tread Lightly** active. No enabled check: ObjectOff does not disarm it (not FIRE class) - delete it.
  * `spell_trap.go:triggerTrap`: **one-shot** (the glyph is deleted), casts every stored spell from the glyph
    with the owner's level, or **level 2** when unowned, at the toucher (or, when detonated without a toucher,
    at the nearest unit within `GlyphRange = 75`); blue sparks + sound; then every other Glyph within 100 units
    with line of sight is set to detonate next frame (**chain reaction**).
  * Jump-clearable (SHORT). Monsters and pushed objects set it off too.
  * Script: `NewTrap(pos, spells...)` / `obj.TrapSpells(...)` create/arm glyphs at runtime (ns v4).
* **BearTrap** (SHORT, r10): first non-friendly, non-Tread-Lightly toucher gets ENCHANT_HELD (5) and
  ENCHANT_ANCHORED (14) for **90 frames (3 s)**; the trap becomes ClosedBearTrap (deleted after 90 frames)
  (`GAME3_3.c:nox_xxx_collideBearTrap_4EB890`). Held units ignore move forces (`nox_xxx_updateObjectsVelocity_5118A0`
  skips force for buffs 5/25/28). One-shot. Jump-clearable.
* **PoisonGasTrap** (SHORT, r10): spawns a ToxicCloud for `ToxicCloudLifetime = 15` s and deletes itself
  (`GAME3_3.c:nox_xxx_collidePoisonGasTrap_4EB910`). ToxicCloud (`GAME4_3.c:nox_xxx_updateToxicCloud_53D850`,
  `sub_53D8C0`): every 5-10 frames, players/monsters within **75 units** with line of sight take **3-10 POISON**
  damage (no armour) and get poisoned. One-shot trigger, 15 s hazard zone. Jump-clearable trigger.

## 11. PressurePlate, Trigger, buttons, levers, switches (question 8)

Things: PressurePlate (TRIGGER|IMMOBILE, BELOW|ALLOW_OVERLAP, BOX 45x45, UPDATE `TriggerUpdate(TriggerPressed
TriggerReleased)` = press/release sounds, CREATE TriggerCreate sets default colours), **Trigger** (same, invisible
in game, EDIT_VISIBLE, sounds Null), Button1-4 and ChainPull1-6 (TRIGGER|IMMOBILE|VISIBLE_ENABLE, AIRBORNE, r8,
z 20-35, TriggerUpdate with ButtonPress/ChainPull sounds), Lever1/2, BrassLever1/2, FloorLever1-4, WallSwitch1-4,
LOTDSwitch1-4, SwitchA/B/C1-4 (UPDATE `ToggleUpdate(...)`). All share COLLIDE TriggerCollide and XFER TriggerXfer.

TriggerXfer (`GAME3_3.c:nox_xxx_unitTriggerXfer_4F4E50`), corpus names in brackets:
* `SizeX`, `SizeY`: ints, **capped at 60**, become the object's BOX shape (a diamond, see 0.1; 60x60 covers
  `|dx|+|dy| < 42.4`). 0 for buttons/levers (they keep their circle).
* `EdgeColor`, `BackColor`: editor/client colours only.
* `UnkInt1` = trigger flags word; **bit value 2 = one-shot**: after the first release the trigger goes to state 5
  and never fires again (Westwood "EntranceSwitch" has UnkInt1 = 2).
* `ScriptOnPressed`, `ScriptOnReleased`, `ScriptOnCollided`: script function names (map script handlers).
* `AllowedObjClass`: 0 = any; otherwise the toucher's class must share a bit. `IgnoredObjClass`: toucher must
  share no bit. Class bits (opennox-lib `object/class.go`): MISSILE 0x1, MONSTER 0x2, PLAYER 0x4, OBSTACLE 0x8,
  FOOD 0x10, EXIT 0x20, KEY 0x40, DOOR 0x80, INFO_BOOK 0x100, TRIGGER 0x200, TRANSPORTER 0x400, HOLE 0x800,
  WAND 0x1000, FIRE 0x2000, ELEVATOR 0x4000, ..., IMMOBILE 0x400000, WEAPON 0x1000000, ARMOR 0x2000000.
  Westwood uses 6 (monsters + players) and 4 (players only).
* `AllowedTeamID` / `IgnoredTeamID`: team byte filter (0 = off).
* `TriggerState` (byte state), `Unk7`, `UnkInt2` (saved anim frame): runtime state, write 0.

Collide (`GAME5.c:nox_xxx_collideTrigger_54FCD0`), only while **enabled** and not spent (state != 5): toucher must
have **mass > 0** (`nox_xxx_objectGetMass_4E4A70`), pass the class and team filters, and `ScriptOnCollided`
(if set) is called **every frame of contact** (event 1) and must return true; then the plate records "touched
this frame" and the toucher. When disabled every touch is ignored and the state is cleared.

TriggerUpdate (`GAME4_3.c:nox_xxx_updateTrigger_53B1B0`), per frame:
* idle + touched -> press sound, anim frame 1, **ScriptOnPressed** (caller = toucher, trigger = plate), state 1,
  release-not-before = now + 0 frames for `Trigger`/`PressurePlate`, now + 30 frames for buttons/chains.
* pressed + frame > release time + not touched this frame -> release sound, anim 0, **ScriptOnReleased**, state
  back to idle (or 5 = spent if one-shot).
* So plates **re-arm automatically**: Pressed fires on the first frame of contact, Released on the first frame
  without contact (1-frame latency), Pressed again on the next contact. Buttons stay down at least 1 s.

ToggleUpdate (`GAME4_3.c:nox_xxx_updateToggle_53B060`), levers/switches: first touch -> ScriptOnPressed, state 3,
30-frame cooldown; once released it rests "on" (state 1); next touch after the cooldown -> **ScriptOnReleased**,
back to "off" (or spent if one-shot). So levers alternate Pressed/Released callbacks per use, max one flip per
second.

Who can press what:
* Players walking: yes. **Jumping players do NOT press PressurePlates** (BELOW vs AIRBORNE, 0.3) but **DO hit the
  invisible `Trigger`** (special case) - use Trigger for "can't jump past" detectors, PressurePlate for
  "jump over the plate" puzzles.
* Monsters (mass > 0): yes unless filtered out by AllowedObjClass (use 4 for players only).
* Pushed crates/boulders (OBSTACLE 0x8, mass 3-13): yes while they move onto it if the class filter allows (0 or
  includes 8). Whether a crate **resting** on a plate keeps it pressed is UNCONFIRMED: immobile plates are not on
  the active collision list (`nox_xxx_unitHasCollideOrUpdateFn_537610` skips IMMOBILE+ALLOW_OVERLAP objects),
  so contact is only detected while the crate itself is active - test in TrapLab.
* Missiles: only via the `Trigger` thing (AIRBORNE missiles skip BELOW plates) with class 0x1 allowed
  (Westwood "Bankshot" ForceOrb triggers).
* Buttons/levers are used by clicking: the client sends MSG_TRY_COLLIDE and the server calls the object's
  COLLIDE with the player **without a distance check** (`server__network__sdecode.c`, case 0x7B); the client
  limits the reach (UNCONFIRMED range).

## 12. Walls (question 9)

* Script `WallOpen/WallClose/WallToggle` (ns v3) / `WallObj.Enable(closed)`, `Toggle()`, `WallGroup(...)`
  (ns v4) -> `wall.go:Wall.open/close/toggle`: **only walls with flag SECRET (0x4) react**; everything else is
  silently ignored. `Destroy()` breaks breakable walls.
* Secret wall state machine (`server__system__server.c:nox_xxx_updateUnits_51B100_D`, wall data byte 21):
  1 closed, 4 opening, 3 open, 2 closing. Opening/closing **slides over 23 frames (0.77 s)** (counter byte 22
  0..23). Open walls auto-close after `Secret_OpenWaitSeconds` x 30 frames when scan flag 4 is set and 8 is not;
  closed walls auto-open after the same time when both 4 and 8 are set (UNCONFIRMED meaning of scan flags 1/2;
  Westwood: 4222 walls flags 1 state 1 = script-only closed; 323 walls flags 8 state 3 = start open).
* During a slide the server only re-activates units within a 85x85 box so their wall collision is re-evaluated.
  A closing wall therefore **pushes overlapping players out** through the normal wall-collision resolution (UNCONFIRMED
  direction); **there is no damage or kill code** for walls. A sliding wall can block/trap but cannot crush.
* No "pushing wall" object exists. Moving obstacles are only: Mover-carried objects (SpikeBlock, StoneBlock,
  IronBlock 60x60 boxes, MovableBookcase1-4 12x36/36x12, crates, coffins, RotatingSpikes, SentryGlobeMovable,
  RollingBoulder) - see section 6. A StoneBlock or IronBlock on a Mover is the "sliding wall that shoves you
  into a pit".

## 13. Other moving/active things

* **SteamPipe1-4** (UPDATE BlowUpdate, `GAME4_3.c:nox_xxx_updateBlow_53C160` + `sub_53C240`): while enabled,
  pushes non-immobile objects within 400 units in a narrow cone along its facing with force
  `(400-d)^3 x 5e-7 / mass` (strong near the pipe). But the four types face diagonally (DirectionInit +-1,+-1)
  and the diagonal branches in `sub_53C240` use an impossible range test (`>= 0.5773 && <= 0.1732`), so **as
  shipped they never push**. Only a cardinal facing would work (re-aim by script, UNCONFIRMED). Not used by WW.
* **Elevators** (`GAME4_3.c:nox_xxx_updateElevator_53B5D0` / `nox_xxx_updateElevatorShaft_53B380`): an enabled
  elevator rises over 32 frames, waits 30 frames, descends, waits 30... and carries units within 64 units to
  its linked shaft; disabled = parked. ObjectOn/Off play start/stop sounds. Transport between floors, not a trap.
* **InvisibleTeleportPentagram / TeleportPentagram** (TRANSPORTER): teleport on touch (391 WW objects) - usable
  for "fail = sent back" without a pit. Not analysed in detail (UNCONFIRMED timing).

## 14. Map-script API for traps (question 10) - ns v4 v4.21.0 as used by OpenNox (go.mod)

Package `github.com/noxworld-dev/noxscript/ns/v4` (our kit imports it in `mapgen/kit/behaviours/*.go`).
Implementations in `opennox/src/script_ns*.go`, `object.go`.
* Objects: `Object(name) Obj`, `ObjectGroup(name)`, `CreateObject(typ string, pos Positioner) Obj`,
  `obj.Delete()`, `obj.DeleteAfter(dt Duration)`, `obj.Enable(bool)` / `obj.Toggle() bool` / `obj.IsEnabled()`
  (= ObjectOn/Off/Toggle, section 0.5), `obj.SetPos(Pointf)`, `obj.Pos()`, `obj.SetZ(z)`,
  `obj.Flags/SetFlags/FlagsEnable/FlagsDisable`, `obj.SetTeam`, `obj.LookAtDirection(dir)`, `obj.LookWithAngle`.
* Movement: `obj.Move(wp WaypointObj)` (monsters walk; other objects need a map Mover, section 6),
  `obj.WalkTo(p)` (monsters), `obj.CreateMover(wp, speed)` (**broken in alpha13**, section 6),
  `obj.ApplyForce(Pointf)` and `obj.PushTo(pos, force)` (adds a force for one frame; PushTo pushes **away from**
  pos with magnitude `force`, not divided by mass - `server/object.go:Object.Push`). Scripts run after the unit
  update each frame (`server.go`: `updateUnits` then `ScriptTick`), so a force applied from a timer/OnFrame
  callback acts on the next frame: calling PushTo every frame = conveyor/wind (terminal drift = 2 x force
  u/frame for drag 0.5).
* Damage: `obj.Damage(source Obj, amount int, typ damage.Type) bool` (goes through the full damage pipeline:
  armour, protections), `obj.Enchant(enchant, dt)`, `obj.EnchantOff`, `obj.Freeze(bool)`, `obj.SetHealth`.
* Spells: `CastSpell(spell, source, target Positioner)`, `CastSpellLvl(spell, lvl, source, target)`: source may
  be a waypoint/point - OpenNox then casts from an invisible caster at that position (`script_ns_spell.go`), so
  fireball/lightning/fist traps from a waypoint work. `NewTrap(pos, spells...)` / `NewTrapAdv`,
  `obj.TrapSpells(...)` make glyphs.
* Walls: `Wall(x, y) WallObj`, `WallGroup(name)`, `.Enable(closed bool)`, `.Toggle()`, `.Destroy()`,
  `NoWallSound(bool)`; secret walls only (section 12).
* Waypoints: `Waypoint(name)`, `WaypointGroup`, `NewWaypoint(name, pos)`, `.Enable/.Toggle` (waypoint links).
* Time: `NewTimer(dt Duration, fnc Func, args ...any) Timer` (+ `Timer.Cancel()`), `Frames(n)`, `Seconds(s)`,
  `OnFrame(fnc)`, `OnEachFrame(n, fnc)`, `Frame()`, `FrameRate()`. (ns v3's `FrameTimer`, `SecondTimer`,
  `FrameTimerWithArg` exist only in v3.)
* Events: trigger/plate/lever callbacks are the **xfer script names** (`ScriptOnPressed` etc.); inside them
  `GetCaller()` = toucher, `GetTrigger()` = plate. `obj.OnEvent(...)` only works for **monsters** (enemy sighted,
  death, ...). `OnMapEvent(MapInitialize|MapEntry|MapExit|MapShutdown)`, `OnPlayerJoin/Leave/Death`, `OnChat`.
  **No polygon-enter events** (ns v4 has `// TODO: InPolygon`); poll instead with
  `FindAllObjects(ns.InRectf{...} / ns.InCirclef{...}, ns.HasClass(class.Player))` in `OnEachFrame`.
* FX/sound: `Effect(effect, p1, p2)`, `AudioEvent(audio.Name, pos)`, `Music(...)`, `obj.ChatStr`, `PrintStr*`.
* **Panicking (unimplemented) in this build** (`panic("implement me")`): MakeFriendly, MakeEnemy, BecomePet,
  BecomeEnemy, ObjType.HasSubclass, Obj.GiveXp, Obj.SetRoamFlag, **ObjGroup.Delete**, ObjGroup.Wander,
  ObjGroup.SetRoamFlag, IsTalking, IsTrading, SetHalberd, Get/SetQuestStatus(+Float), ResetQuestStatus,
  JournalEdit, JournalDelete, JournalEntryStr, JournalEditStr, JournalDeleteStr, SetShopkeeperText(+Str),
  TellStoryStr, Unused5e, Unknownb8, Unknownb9. For traps: delete group members one by one, never
  `ObjectGroup(...).Delete()`.

## 15. What needs an engine change (question 11)

| wanted trap | status | why / where to patch |
|---|---|---|
| Sliding block / wall that shoves the player | **possible without patch**: StoneBlock/IronBlock/SpikeBlock + map Mover + `Move` | needs Mover objects in the map writer (MoverXfer). `CreateMover` fix would allow runtime creation: `opennox/src/object.go:Object.CreateMover` must set `ud.Field_8 = obj.Extent` and store an int speed (or change the C read in `GAME5.c:nox_xxx_unitUpdateMover_54F740`). |
| Timed crusher (two blocks slam) | **possible**: Movers + `Move` on a timer, WW War04a pattern | damage is only 1/frame (DamageCollide 3); an instant kill needs a script `Damage` on players inside the gap at the slam frame. |
| Rolling boulder chasing the player | partly: RollingBoulder on a Mover path, or `PushTo`/`ApplyForce` toward the player every frame | no homing/AI for boulders: `BoulderUpdate` is unregistered (`legacy/object_update.go` has no entry). A real "BoulderUpdate" would be a new Go update registered in `server/object_type.go`. |
| Conveyor floor | **possible by script**: `OnEachFrame(1, ...)` + `FindAllObjects(InRectf, HasClass player)` + `ApplyForce` | no floor-tile conveyor in the engine; a native one would hook `GAME4_1.c:nox_xxx_updateObjectsVelocity_5118A0` next to the lava tile check. |
| Self-cycling spikes | script timers (PeriodicSpike does not cycle) | native cycling would need `GAME4_3.c:sub_53B300` to use its parsed (3 1 5) data. |
| Real height jump / jumping over walls | not possible | jump is a flag, not z. |
| Fall damage / death pits | not native | teleport via FallX/FallY to a lethal area, or script `Damage` on arrival. |
| Wind / steam push | SteamPipe broken for its diagonal facings | fix the diagonal range test in `GAME4_3.c:sub_53C240`, or use script forces. |
| Wall that crushes | not possible | secret-wall code has no damage; use Mover blocks. |

## 16. Quick reference table

| object | damage (per frame unless noted) | type | ObjectOff stops it? | jump-clearable? | notes |
|---|---|---|---|---|---|
| SmallFlame / Medium / Flame / Large | 1 / 1 / 1 / 2 | Flame (no armour) | yes (FIRE => NO_COLLIDE + hidden) | yes (SHORT) | r 4/6/8/12 |
| FireGrateFlame | 5 | Flame | yes | yes | lifetime 14 (UNCONFIRMED) |
| CampFire / OgreFirePit | 3 | Flame | yes | yes | |
| LavaFountain(2/3) | 3 | Flame | **no** (not FIRE class) | yes (SHORT) | |
| Blue flames | mana drain 3-12 | - | yes | yes | players only |
| Lava tile | 2 | Lava (no armour) | n/a | yes (AIRBORNE skip) | fire protection reduces |
| Spike / PeriodicSpike | 1 | Impale (armour) | yes (own update) | yes | PeriodicSpike does not cycle |
| SpikeBlock (on Mover) | 1 + shove | Impale | no (move/stop the Mover) | **no** | crusher, pit pusher |
| RotatingSpikes | 4 | Impale | **no** (hidden but still hurts, UNCONFIRMED) | **no** | no rotation server-side |
| RollingBoulder | 1 | Crush (half armour) | no | **no** | needs Mover/forces |
| Pit (ON) | fall -> teleport FallX/Y | - | yes (OFF = floor) | yes | radius <= 16 falls |
| PitCrumblingFloor (OFF) | opens ScriptTimeout frames after first touch | - | n/a | yes | Tread Lightly immune |
| ArrowTrap1/2 | 25 per arrow, <= 1/s | Impale | yes (no scan when OFF) | **no** | fixed SE/SW facing, 700x700 front zone |
| Skull1-4 | 96 + 96 splash r64 per fireball | Flame | yes | **no** | fixed diagonal facing |
| SentryGlobe | 500 (instant death) | ZapRay | yes (angle resets) | **no** | 600-unit beam, stops at walls |
| Glyph | its spells, once | - | **no** (delete it) | yes | chain within 100 |
| BearTrap | held 3 s | - | no | yes | one-shot |
| PoisonGasTrap | cloud 15 s, 3-10 poison every 5-10 frames r75 | Poison | no | yes (trigger) | one-shot |
| PressurePlate | trigger | - | yes (ignores touches) | yes (not pressed) | re-arms, 0-frame release |
| Trigger (invisible) | trigger | - | yes | **no** (catches jumpers) | max 60x60 diamond |

## 17. Design implications (what makes each trap fair / avoidable)

1. **Jump = 18 frames airborne, 203-225 units forward, 90 stamina, max ~1 per second.** Everything SHORT or BELOW
   is skipped while airborne: flames, fire grates, spikes, pits, crumbling floors, plates, glyphs, bear/gas traps,
   lava tiles, crates. A "jump the flames" strip should be <= ~150 units deep (run-up jump covers 225; leave 50+
   for late presses) and have >= 30 frames of safe floor between consecutive jumps (stamina).
2. Things a jump does **not** beat: SpikeBlocks, RotatingSpikes, boulders, arrows, fireballs, sentry beams, the
   invisible `Trigger`. Use these when the answer should be timing or cover, not jumping.
3. **Flames**: ObjectOn/Off is instant and reliable (FIRE class). Timed flame jets = toggle on a NewTimer; give
   an OFF window of at least 20-25 frames per 100 units of strip to walk through (walk 6.25 u/frame, run 12.5),
   or make the strip jumpable. Damage is small per frame (30-60 HP/s) - long strips, not single flames, are the
   threat. Blue flames punish casters (mana), not HP.
4. **Spikes**: always on unless scripted; PeriodicSpike is the same as Spike. Build rhythm with timers; the safe
   window is exactly the OFF time. 1 dmg/frame minus armour - mostly a chip-damage floor.
5. **Pits**: no death, only relocation to FallX/FallY - always set it (pit-bottom room, gauntlet restart, or a
   lethal area if wanted). Pits are 32x32 diamonds (22.6 units from centre): a single row is trivially jumped,
   two rows (~64 units) still easy, keep total width <= 150 units. Big monsters (radius > 16) walk over pits -
   do not rely on pits to stop them.
6. **Crumbling floors**: 4 frames after the first touch (WW default) the tile opens and stays open; runners make
   it across single tiles, walkers drop. Jumping or Tread Lightly avoids triggering. Give a visual tell (WW art)
   and use ScriptTimeout 10-20 frames for "run!" corridors (1 tile per 32 units at 12.5 u/frame = ~3 frames).
7. **Arrow traps / skulls**: fixed diagonal facing per thing type (choose ArrowTrap1 for SE, ArrowTrap2 for SW,
   Skull1-4 for the four diagonals), detection only in front within +-350 units with line of sight, first shot
   immediately, then 1 per 30 frames. Safe spots: behind the trap, outside the 700x700 square, behind a non-SHORT
   obstacle or wall corner. Arrows: 25 impale (armour helps, shields block); skull fireballs: ~96 + splash - use
   skulls sparingly. Traps also shoot monsters (unless given the monsters' team).
8. **Sentry globes**: instant death on beam contact, beam length 600 (walls stop it). Make them readable: slow
   RotateSpeed (0.004-0.01 rad/frame = 21-50 s per turn), a wall corner/pillar line to hide behind, or toggle
   static beams on a timer. Never pair with forced movement (pushers/conveyors) unless deliberately lethal.
9. **SpikeBlocks / crushers**: need a map Mover per block (MovedObjExtent = block extent id, stored OFF) and a
   `Move(block, wp)` call; pace ~0.18 x MovingSpeed u/frame (15 -> ~2.8 u/frame). Damage is low (30 HP/s) but the
   shove can carry the player into pits or pin him. Provide side alcoves and a predictable cadence (WW: close,
   20 frames, effect, 50 frames, reset).
10. **Plates vs Triggers**: PressurePlate = visible, jumpable (jumping skips it), re-arms instantly. Trigger =
    invisible, catches jumpers, max 60x60. Use AllowedObjClass 4 (players) so monsters do not set traps off,
    or 6/0 to let monsters and pushed crates do it deliberately. One-shot = UnkInt1 bit 2.
11. **Levers/buttons**: callbacks alternate Pressed/Released for levers; 30-frame cooldown; buttons hold >= 1 s.
12. **Glyphs**: one-shot, any non-friendly toucher (monsters too), chain-detonate within 100 units, ObjectOff does
    not disarm. Jumpable.
13. **Walls**: only SECRET walls open/close, 23-frame slide, never damage. Good for "door slams shut behind you" and
    timed gates, not for crushers.
14. Script plumbing: use `NewTimer(ns.Frames(n), fn)`/`OnEachFrame` for cycles, `FindAllObjects(InRectf/InCirclef,
    HasClass player)` for area checks (no polygon events), `CastSpell(spell, waypoint, target)` for magic traps,
    `ApplyForce` each frame for conveyors/wind. Avoid `ObjectGroup(...).Delete()` and `CreateMover` (both broken).
