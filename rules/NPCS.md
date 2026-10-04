# Creatures and NPCs: placement, movement and behaviour

**Sources.**
- `py rules/npcs.py` measures every creature on Westwood's single-player maps, each layout once: 4,482 creatures, 2,942 of them hostile. It writes `rules/out/npcs.json`.
- The map scripts were decompiled with OpenNox's own tool. Build `noxtools` from opennox-lib (`go build ./cmd/noxtools`), then run `noxtools noxscript decomp <map>.map out.go`. That gave 136 maps of NoxScript as readable Go.

**Building.**
- `mapgen/kit/npcs.py` places creatures.
- `mapgen/kit/behaviours/behaviours.go` holds the scripted behaviour sets.
- `mapgen/designs/npclab.py` is the test map.

## How Westwood places creatures

**Default actions.** The default action is the creature's xfer `DefaultAction`, an ai.ActionType: 0 idle, 3 escort, 4 guard, 5 hunt, 10 roam.

| | Share of hostile creatures |
|---|---|
| idle | 61% |
| guard | 35% |
| roam | 4% |
| escort | 0.3% (9) |

Idle and guarding creatures stand still until they see the player, then fight. Movement before that comes from scripts.

**Groups.** Creatures mostly stand alone: the median group (same type within 4 cells) is 1, and the 90th percentile is 2. Bats, spiders, imps and wasps come in up to threes.

**Where they stand.**
- About **2 cells from a wall** at the median, for every action: in corners and along edges, not in the open middle.
- **Far from the player's start:** 25th percentile 89 cells, median 110-125 cells. The castle maps are the exception, at a median of 65.
- About 23 cells from the nearest door.
- **Roamers start on a waypoint:** a median 1.6 cells from one, and 95% of them within 8 cells.

**Density per 100 floor tiles.**

| Environment | Density |
|---|---|
| swamp, cave | 0.91 |
| forest | 0.84 |
| dungeon | 0.75 |
| town | 0.66 |
| ice | 0.65 |
| castle | 0.42 |
| lava | 0.35 |

**Sight range.**
- 150 for most creatures.
- Longer for sentries and hunters:
  - archers, swordsmen and scorpions: 500;
  - grunts and trolls: 450;
  - bears: 400;
  - wolves, demons, ogres and albino spiders: 350.

**Aggressiveness.**
- 0.5 for nearly all; scripts raise it to 0.83 when roused (the "GoMedieval" pattern).
- The editor's default for a hostile creature is 0.83. A creature written without it has 0 aggressiveness and 1 health, so the map writer now calls the editor's `InitForMonsterName`.

**Status flags.** CAN_DODGE (646), DESTROY_WHEN_DEAD (with CAN_BLOCK for skeletons), CAN_CAST_SPELLS, HOLD_YOUR_GROUND, ALWAYS_RUN.

**Scripted creatures.** 20% are wired to script callbacks. The events used, by count:
- enemy sighted 125, is hit 106, looking for enemy 98;
- end of waypoint 41, death 34;
- retreat, change focus and lost enemy, 8-9 each.

Bosses are almost all scripted: Lich 96%, Beholder 92%, mechanical golem 81%, will-o'-wisp 75%, Necromancer 74%.

**Waypoints.**
- About 2.3 per 100 floor tiles (a median of 156 per map). Their flags are always 1.
- Most link into chains: degree 2 for 4,411, 3 for 2,197, 1 for 2,098. 1,878 stand alone; scripts move creatures to these.
- Linked waypoints are 7.4 cells apart at the median (25th-75th percentile: 5-11).
- 18% are named for scripts.
- The links carry flag 128, which the roaming AI follows.

## How Westwood moves them

**Without a script.**
- **Roam (10):** walks to the nearest waypoint whose links match the creature's `ActionRoamPathFlag`. It then keeps choosing a linked waypoint other than the one it came from. With no waypoint it waits and gives up. Westwood's roam flags: 1, 128, 255, 8, 32.
- **Escort (3):** keeps with the creature named in `EscortObjName`.

**With scripts.** The 136 decompiled map scripts move creatures with these calls:
- `Move(obj, waypoint)`: 1,176;
- `Wander`: 285; `CreatureGuard`: 227; `CreatureFollow`: 183; `CreatureIdle`: 349; `CreatureHunt`: 116;
- `GoBackHome`: 109; `Attack`: 142;
- `AggressionLevel`: 676; `LookAtObject`: 733;
- `Frozen`: 1,086, to hold actors in cutscenes;
- `ObjectOn` and `ObjectOff`: 1,618 and 1,896, to make creatures appear and vanish;
- `PauseObject`: 55; `SetRoamFlag`: 47.

They hang them on callbacks (`SetCallback(obj, event, func)`): 3 enemy sighted, 4 looking for enemy, 5 death, 7 is hit, 9 collision, 11 end of waypoint, 13 lost enemy.

**Recurring patterns.**
- **Patrol:** looking for enemy calls `Wander`.
- **Alert:** enemy sighted sets `AggressionLevel` 0.83; lost enemy sets it back to 0.5.
- **HomePatrol:** `GoBackHome`, pause, then `Wander`.
- **Ogre patrol:** a leader moved along a waypoint chain by `Move`, its followers on `CreatureFollow`.
- **Set pieces:** monsters off until a trigger switches them on.

## Coding new behaviour sets

OpenNox runs every `.go` file in `maps/<Name>/` as the map's script. The package is named after the map in lower case. The scripts use the NoxScript 4 API (`github.com/noxworld-dev/noxscript/ns/v4`), interpreted by yaegi.

**The API.**
- **Objects by script name.** `ns.Object(name)` finds an object; the map writer now saves `scr` names.
- **Waypoints by name.** `ns.Waypoint(name)` matches a bare name, or a name after `map:`.
- **Creature actions.** Methods on a creature:
  - `Wander`, `Guard(post, face, dist)`, `Hunt`, `Follow`, `Attack`;
  - `Flee(target, dt)`, `Move(waypoint)`, `WalkTo(point)`;
  - `Pause`, `Freeze`, `LookAtObject`, `Enable`;
  - `AggressionLevel`, `SetRoamFlag`, `RetreatLevel`, `ChatStr`.
- **Events.** `obj.OnEvent(ns.EventEnemySighted | EventIsHit | EventEndOfWaypoint | EventLostEnemy | EventDeath, ...)`.
- **Timers and map events.**
  - `ns.NewTimer(ns.Seconds(n), fn)` and `ns.OnEachFrame(n, fn)`;
  - `ns.OnMapEvent(ns.MapInitialize, fn)`, which fires once a player is in the game.

`kit/behaviours/behaviours.go` holds six behaviour sets built from these:

| Set | What it does |
|---|---|
| `Sentry` | Guards its post facing out. On sighting an enemy it calls out and rouses the allies listed, who hunt. When the enemy is lost it walks back to its post. |
| `Patrol` | Walks a route of waypoints in turn (round, or there and back), pausing at each. It fights what it meets and takes up the route again when the enemy is lost. |
| `Pack` | The leader wanders and the others follow. When any of them sees or is hit by an enemy, all hunt. When the leader dies, the rest flee. |
| `Skittish` | Wanders. When hit, it flees from the attacker for a few seconds, then wanders again. |
| `Ambush` | A group waits unseen (disabled) until the player comes within reach, then appears and attacks. |
| `Townsfolk` | Walks between named spots, lingers, and turns to look at a player passing by. |
| `Villager` | A townsfolk who keeps an eye out: twice a second it looks for a living hostile creature within its fear radius; if one is near it runs to its home doorstep and waits there until eight quiet seconds have passed, then takes up its rounds again. The town's own people (Maidens, NPCs, shopkeepers) and the player are no threat. The town lab's 13 villagers use it. |

**Shops.** A shopkeeper's wares are map data, not script: MonsterXfer `ShopkeeperInfo` holds the buy and sell multipliers (Westwood: 1.0 and 0.31-0.33), a greeting text key and the items (`x2 RedPotion`). Westwood's shopkeepers are immortal and on guard. `Population.shopkeeper(type, x, y, items)` writes one; the map writer fills nested structures like this from the spec. The town lab's store has one behind its counter, and its inn a barkeeper behind the bar. A greeting is a key into the game's text file (`nox.csf`: a 24-byte header, then ` LBL` records, each with ` rtS` or `WrtS` strings stored as inverted UTF-16); some fit any town's trader: `Con05A.scr:ShopKeeperTalk1` ("Welcome, Wanderer! We carry the finest wares in all of Nox!"), `Con02:BarkeeperDefault`, `Con02a:Mystic`.

**Generating a map's script.** `kit/npcs.py` writes a map's `behaviours.go` and its `config.go` (who does what). It also writes a `Diagnose` self-check that prints to the server log how many named creatures and waypoints the script can find. NpcLab: "creatures 25 of 25 - waypoints 8 of 8".

```python
pop = Population(spec, rng)
pop.creature("GruntAxe", x, y, action="guard", face=(fx, fy), scr="GateSentry")
pop.roam_loop(points, "Swordsman", n=2)                  # Westwood's unscripted roam on a linked loop
pop.escort("OgreWarlord", at, "OgreBrute", spots)        # Westwood's unscripted escort
pop.behaviours.sentry("GateSentry", face, rouse=["GateGuard"])
spec.scripts.update(pop.behaviours.files(spec.d["name"]))  # built beside the map; installed into maps/<Name>/
```

**Testing.**
- `py tests/check_scripts.py <map>_scripts --go <go.exe>` checks the code compiles with `go vet` against `ns/v4` v4.16.1, the version the installed OpenNox v1.9.0-alpha13 bundles. A newer method fails at load ("undefined method").
- The dedicated server loads the scripts ("go scripts loaded") and the self-check runs.
- The behaviours themselves start at MapInitialize, which needs a player in the game. Load NpcLab in a Solo game (F1, `racoiaws`, `load NpcLab`) and walk through the sections.
