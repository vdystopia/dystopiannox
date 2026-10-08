# Transporters: lifts, stairs, portals and passages in Westwood's maps

Measured 2026-10-08 on the 107 campaign maps (Con/War/Wiz) by `py rules/transporters.py` (writes
`rules/out/transporters.json`: every link, every stairs piece and every scripted move, with the summary), read from
the map data through `validate/transport.py`, and on the decompiled map scripts (`noxtools ns decomp`; pass the folder
with `--scripts`). The engine's side is read from OpenNox v1.9.0-alpha13's source (the original's C: elevator, shaft
and pentagram update and collide functions, `server.AttachPending`) and proved on our test map in the client
(`mapgen/designs/test_transport.py`, section 8). The process that uses this is `skills/nox-transporters/SKILL.md`;
the kit is `mapgen/kit/transport.py`.

**One idea, four shapes.** Every transporter moves the player from a spot A to a spot B, and B is most often a part of
the map that cannot be walked to: a cellar, a mine level, an island, a tower floor, a crypt drawn somewhere else on the
256 x 256 grid. A Nox map has one floor: "down a lift" and "up the stairs" are a jump across the grid, and the second
place is a walled-off area drawn in an empty part of the map. Westwood has four ways to make the jump:

| Kind | What the player sees | Objects | Links | Westwood (campaign) |
|---|---|---|---|---|
| Lift | a platform rises and sinks; he rides it and comes up out of a pit elsewhere | ELEVATOR platform + ELEVATOR_SHAFT pit | platform and pit name each other (ExtentLink) | 172 working lifts in 84 maps |
| Portal | a pentagram glows when he steps on it; a flash, and he stands somewhere else | TeleportPentagram (seen) or InvisibleTeleportPentagram (unseen, instant) | the pad names where it sends him (ExtentLink): usually an arrival marker | 254 pads in 48 maps |
| Stairs | he walks onto a flight of stairs and arrives at the foot or head of another | decorative stairs pieces + an InvisibleTeleportPentagram on them | a pad on each flight names a marker in front of the other | 10 in-map pairs (castle, Dun Mir, crypt); more lead to the next map |
| Passage (scripted) | the screen fades out at a door or tunnel mouth and back in elsewhere | none: a script | a trigger or polygon calls Blind, MoveObject, UnBlind | 51 blinded moves in 46 maps |

Map exits (InvisibleExitArea, ExitCaveDown, LOTDStairs*Exit with a MapName, 240 in 105 maps) change the map and are
not transporters; `kit/story.py exit_to` lays them.

## 1. Lifts (elevator and pit)

**Engine** (OpenNox `nox_xxx_updateElevator_53B5D0`, `nox_xxx_updateElevatorShaft_53B380`, the collide functions
`sub_551AE0` and `sub_551C40`):
- The platform (class ELEVATOR) and its pit (ELEVATOR_SHAFT) are joined at load by extent: the platform's xfer
  `ExtentLink` names the pit (`server.AttachPending`); Westwood also sets the pit's `ExtentLink` back to the platform.
- An **enabled** platform cycles by itself, forever: it waits one second, rises (`Height` 0 to 64, 2 a frame: about a
  second), waits a second, sinks back. Whoever stands on it rides up with it (the collision raises him to the
  platform's height); at height 32 he is moved to the pit, under the floor, and comes up out of it. While the platform
  sinks, whoever stands on the pit rides back up onto the platform. So **a lift is always two-way**, and a player who
  stands still rides it back and forth.
- A **disabled** platform stops; a script turns it on (`ObjectOn`, `ObjectGroupOn`). Westwood starts 69 of its
  213 lift objects disabled (exits that open with the quest, secret lifts). The create flags (ENABLED, 0x1000000) are
  stored only with an object's extended fields; without them it starts enabled.
- Walking onto the pit while the platform is away drops the walker (fall flag) and lands him on the platform's spot:
  the pit is never a dead end. A unit bigger than the pit's box cannot ride.
- Sounds: the platform's start and stop sounds by type (`nox_xxx_elevatorAud_53B490`, 249-260); Westwood adds the
  machinery in scripts (Con01A `PlayEntranceLiftSounds`: `AudioEvent(ChangeSpellbar)` every 7 frames while it runs,
  `CreatureCageAppears` when a switch starts it).

**Types by setting** (platform, pit; how many working lifts; where):

| Platform | Pit | Lifts | Maps (each class) | Floors under the ends |
|---|---|---|---|---|
| CaveElevator | CaveElevatorPit | 70 | caves, sewers, dungeons, crypts (Con02, 04-06, 08-09; War01-09; Wiz01-06) | DirtDark2, GreenBrick, BrokenCobbleDirt |
| Elevator | ElevatorPit | 39 | the mines and wooden works (Con01A's mine, Con03, 05, 09) | WoodGray, ManaMineDirt, CaveHardBrown |
| GreenElevator | GreenElevatorPit | 28 | Ix and its swamps (Con02a, 08, 09) | DirtDark2, DirtLight2, SwampGrass |
| LOTDElevator | LOTDElevatorPit | 24 | the Land of the Dead (Con10) | LOTDPitted, LOTDBlackMarble |
| RedElevator | RedElevatorPit | 7 | the volcano (Con07, Wiz07) | VolcanicCraggy |
| WhiteElevator | WhiteElevatorPit | 4 | Galava's castle (Wiz02, 03, 07) | StoneLight, GalavaBrick |

BlueElevator is never placed in a campaign map. A **CaveElevatorBase** stands exactly under 84 of the cave
platforms and 59 of their pits (offset 0, 0); no other type has a base.

**Where the two ends are** (172 working lifts): the far end is walled off from the near one in 169 (98%); the lift is
the only way into its area in 48; there is a way back (the lift itself) in all. Distance between the ends: p5 371 px,
median 1734, p95 4452 (a lift jumps across the map). Wall clearance (centre to the nearest wall cell's centre):
platforms p5 35 px, least 23; pits p5 32, least 26. The two ends stand on different floors in 125 of 172 and in
different room polygons in 78 (a cave under a town: its own light).

**What stands round them**: lights (ColorLight at 73 platforms and 63 pits, Torch 25 / 28), triggers (33 / 54: the
switch or the polygon that starts it), gears at the mine lifts (Gear3-6), cave rubble and webs in caves, the
destination's own furniture.

**Examples**
- Con01A (the mine): `Conj01:EntranceElevator`, Elevator at (2472, 3233), enabled, its pit at (2336, 3556);
  `Conj01:ExitElevator` at (1875, 3648) to the pit at (4015, 2749), 2321 px, starts **disabled** and is the only way to
  the exit tunnel: `ActivateExitElevator` (the ExitSwitch) gives 100 xp, plays `CreatureCageAppears` and turns on the
  group `ExitLiftAndGears` (the lift and its gears); the secret lift (288, 1829) to (910, 2268) is turned on with its
  wall group when the secret is found (`ActivateSecretElevator`: `WallGroupOpen` + `ObjectGroupOn`).
- Con02a (Ix): the urchin den is a separate area at the map's south edge; a GreenElevator at (1806, 5589) brings the
  player up into the town at (3795, 2944), 3310 px away; `Con02a:AldwinElevator`, a CaveElevator at (3967, 460) in
  Aldwyn's tunnel, rises to (4761, 1024) in town.
- Con05A: the chapter starts on a lift: a CaveElevator at (515, 2853) and its pit 54 px away in an 89-cell shaft room.
- War01A: `War01A:SewerBottom`, CaveElevator at (4393, 4278) to (2392, 3082): the sewer is its own area.

Broken or prop lifts: 30 platforms name no pit (all but two disabled: props) and 11 pits have no platform; two enabled
platforms with no pit (Wiz06a CaveElevator, Wiz07D WhiteElevator), the cave lifts whose pit lies off the floor
(Con04c, War04c, Wiz04c; Con08e, War08e, Wiz08e) and War02A's ElevatorPit in a one-cell pocket are Westwood's own
defects or unused pieces, which the checker reports.

## 2. Portals (teleport pentagrams)

**Engine** (`nox_xxx_updateTeleportPentagram_53BEF0`, `nox_xxx_collidePentagram_4EAB20`,
`nox_xxx_fnPentagramTeleport_53C060`, `nox_xxx_updateInvisiblePentagram_53C0C0`):
- A TRANSPORTER pad names its target by extent (`ExtentLink`); at load it is joined to the TRANSPORTER with that
  extent (a target must itself be a TRANSPORTER: Westwood's targets are InvisibleTeleportPentagram markers or other
  pentagrams). A pad with `ExtentLink` 0 does nothing: it is an **arrival marker**.
- A **TeleportPentagram** that something steps on (and that is enabled) plays its glow with its target (about a
  second), then sends whatever stands in its circle (radius 20) to the target's spot, with the teleport flash (fx 137)
  and sound (147) at both ends. An **InvisibleTeleportPentagram** with a target sends at once, with no glow and no
  sound: Westwood's stairs, trapdoors and hidden traps.
- **Westwood never links two pads both ways** (0 of 254): a pad that lands the player on a pad that sends him back
  would bounce him. A two-way portal is two one-way links: pad A sends to a marker beside pad B; pad B sends to a marker
  beside pad A. The marker stands 40-194 px off the return pad (p5 43, median 59, p75 110).
- Landing on a pad that leads on sends the player on once its glow ends: Westwood does it on purpose in the Land of
  the Dead's pentagram chains (Con10a: 22 pads, pentagrams landing on pentagrams) and in War11a (16 pads landing
  exactly on another).

**Counts**: 181 TeleportPentagram and 73 InvisibleTeleportPentagram pads with a target; 186 land on a marker, 68 on
another pentagram. 248 start enabled; 6 are switched on by a script (Wiz01A's `BriefTeleporter`). The far end is
walled off from the near one in 219 (86%), the only way into its area in 103, and the player can get back (on foot,
by another pad or a lift) in 213; for the other 41 the map data shows no way back (a script, a chain or the exit
takes over). Distance
p5 182 px, median 1400, p95 4765. Landing clearance median 97 px, least 28; the landing area is small (median 540
cells: a room).

**Examples**
- Wiz01A: `FirstWiz:Teleporter` (2519, 2633), enabled, sends the player to the pentagram `Wiz01A:BriefTeleporter`
  (4543, 1714), which starts **disabled** until the briefing ends and then sends him on to (1008, 1601).
- Con07F: 13 pentagrams among small walled cells (188-390 cells each), each 195-699 px from where it lands the
  player: a teleport maze.
- Con07C: eight pentagrams inside one walled area (not isolated): shortcuts across it.
- Con11a: a one-way pentagram (1737, 3829) to (3012, 2670).

## 3. Stairs

Stairs are pictures: every stairs piece is IMMOBILE, BELOW, NO_COLLIDE (`GalavaStairs*`, `DunMirStairs*`,
`LOTDStairsDown*`) or an EXIT piece (`LOTDStairs*Exit*`). What moves the player is an **InvisibleTeleportPentagram
on the stairs' main piece** (within 15 px of it), linked to an arrival marker in front of the other flight. A stair
that leads to the next map has an InvisibleExitArea on it instead (Galava's carpeted stairs in Con07C-H: each castle
floor is its own map).

**In-map pairs** (both flights on one map, two one-way pads):

| Map | Down | Up | Ends |
|---|---|---|---|
| Con07B, War07A, Wiz02A, Wiz07F | GalavaStairsDown (631, 740) | GalavaStairsUp1 (1895, 3876) | the castle's floor and its dungeon |
| Wiz02C | GalavaStairsDownCarpeted, GalavaStairsDown2Carpeted | GalavaStairsUp1Carpeted, GalavaStairsUp2Carpeted | the castle's floors |
| Con06b, War06b, Wiz06c | DunMirStairsDown (1537, 5138), (3953, 699) | DunMirStairsUp (4614, 565), (2200, 2244) | Dun Mir's levels |
| Con04b, War04b, Wiz04b | LOTDStairsExitBack1 (1984, 4863) | LOTDStairsUpExit1 (2689, 3144) | the crypt's levels (EXIT pieces naming no map: inert in a solo game) |
| Con04c, War04c, Wiz04c | LOTDStairsDown2 (4311, 982) | LOTDStairsExitBack2 (980, 3353) | the crypt's levels |
| Con10a-d (each class) | LOTDStairsDown3, LOTDStairsDown4 | | the Land of the Dead (half lead to the next map) |

**Shape** (medians, px from the main piece; `rules/out/transporters.json` summary.geometry.stairs, which the kit
reads):

| Main piece | Pieces round it | Pad | Arrival back at it |
|---|---|---|---|
| GalavaStairsDown | EndPiece (-26, 25), SidePiece (-26, -18), SidePiece (18, 30) | (-1, 4) | (51, -40) |
| GalavaStairsDownCarpeted | EndPiece (-26, 26), SidePiece (-24, -19), SidePiece (18, 31) | (-2, 4) | (48, -42) |
| GalavaStairsDown2Carpeted | Down2EndPiece (26, 26), Down2SidePiece (-17, 30), Down2SidePiece (26, -17) | (5, 5) | (-53, -50) |
| GalavaStairsUp1 | none | (4, -3) | (-60, 57) |
| GalavaStairsUp1Carpeted | none | (4, 2) | (-50, 55) |
| GalavaStairsUp2Carpeted | none | (-3, 1) | (52, 60) |
| DunMirStairsDown | EndPiece (-25, 27), SidePiece (-27, -17), SidePiece (20, 26) | (0, 1) | (34, -31) |
| DunMirStairsUp | none | (-2, 0) | (-34, 36) |
| LOTDStairsExitBack1 / UpExit1 | none | (1, 0) / (-1, -2) | (-29, -31) / (33, 30) |
| LOTDStairsDown2 / Down3 | none | (11, -9) / (0, 0) | (-22, 25) / (-34, -32) |

The arrival is 40-100 px in front of the flight's mouth, never on its pad. **Where the flights stand**: a flight down
stands 3-5 cells inside a room's west corner (Con07B, Con06b: the room's walls run off from behind it); a flight up
stands in an alcove or against the room's NE wall, walls one or two cells round it, its mouth opening down-left into
the room (Con07B's GalavaStairsUp1, Con06b's DunMirStairsUp, Con04b's LOTDStairsUpExit1).

## 4. Scripted moves (passages)

70 functions of the campaign scripts move the player (`MoveObject(GetHost(), ...)`) in 46 maps; 51 blind the screen
first. The pattern (Con08a `GoToMine`, `GoToCave`; Con08b `GoToTemple`, `EnterTemple`, `LeaveTemple`, `GoToIx`): a
trigger at a doorway or tunnel mouth calls a function that checks the caller is the player, calls `Blind()` (and
`Frozen` on the player and his followers), and after `FrameTimer(30-60)` a second function moves him to a waypoint
(`MineExitWP`, `CaveExitWP`) and calls `UnBlind()`. The rest: chapter ends and map switches (`MapSwitch`,
`ChangeMaps`, `ChapterEndB`), the jail (War07A `PutPeopleInJail`), and moves of creatures out of the way
(Con04c `ClearKeeperDoor`, Con06a `leavingDunMir`). A passage is the door into a building whose inside is drawn
elsewhere: the temple of Ix, the mine and the cave under it.

## 5. What the destination is

Most far ends are a **separate walled area** drawn in an empty part of the grid (lifts 98%, pads 86%): a cave level
under a town (Con02a's tunnels), a sewer (War01A), a crypt level (Con04b-c), a castle floor (Con07B), a tower cell
(Con07F). It has its own floor, often its own light (a room polygon of its own: 78 of 172 lifts), and most often more
than the lift: a fight, a chest, the next step of the quest. Some are in the same area: shortcuts (Con07C's garden),
a lift down a cliff in one cave.

## 6. Rules for our maps (what the kit and the checker hold to)

1. One call lays any kind (`kit/transport.py Transporters.add(kind, a, b, name, ...)`), in Westwood's types for the
   setting (lift by `LIFTS`, stairs by `STAIRS`).
2. Both ends linked: a lift's platform and pit name each other; every pad names a marker (`transport.link`).
3. Never land the player on a pad that sends him on (`transport.bounce`); a two-way portal or stairs is two one-way
   pads, each landing beside the other's pad (59 px, Westwood's median).
4. Every landing on open floor: not in the void, not in a wall, not on a blocking object (`transport.landing`), 23 px
   or more from a wall cell's centre (`transport.wall`: Westwood's least), in an area with room to move or a way on
   (`transport.pocket`).
5. The far end's places reachable on foot from where the player lands (`serves=`, `transport.serves`).
6. A way back or the map's exit from wherever a transporter leaves the player, or the design declares it one-way and
   the story goes on from there (`transport.stranded`); every transporter's start reachable (`transport.unreached`).
7. A disabled transporter is turned on by the story (`A.enable` of each of `t.sources`), as Westwood's exit lifts are.

## 7. Notes

- The water and floor types `*NoTeleport` (`WaterDeepNoTeleport` ...) stop the Teleport spell landing there; an island
  that must be reached only by its portal should be ringed with them if the player could cast Teleport.
- `py validate/validate.py Con01A` (any corpus map) shows the transport findings on Westwood's maps; on the 107
  campaign maps the check fires on 11: the lifts of section 1, and two pads landing where no floor is (Wiz01A's
  briefing teleporter, Wiz02C: no floor under the landing).

## 8. Proof in the game (2026-10-08)

`mapgen/designs/test_transport.py` (TestTrans) lays one of each: a cave lift to a cellar, a two-way pentagram to an
island, castle stairs to an upper floor, a passage to a crypt. In the OpenNox client (hosted with `-autosrv`, driven
by a test script that pushes the player onto each start in turn) all eight legs moved the player, logged by the
map's `transport.go`: the lift in 85 frames each way (2714, 1794) to (3289, 4600) and back, the pentagrams in 19-20
frames, the stairs and the passage both ways. The host of an `-autosrv` game starts NO_COLLIDE (it walks through
objects, not walls), so a test driver clears that flag first: a player who does not collide never triggers a pad or
rides a lift.
