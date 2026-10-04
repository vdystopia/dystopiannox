# Weapons and the projectiles they fire

**Sources.**
- `py rules/weapons.py <thing.dec>` reads the game's object database (`thing.bin`, decrypted with noxcrypt) and writes `rules/out/weapons.json`.
- OpenNox's source shows what the handlers do: `legacy/GAME4_3.c` `nox_xxx_useLesserFireballStaff_53F290` (WandUse) and `spell_harpoon.go`.

## How a weapon fires

Every weapon names a USE handler in `thing.bin`, with arguments. What happens when it is used follows from those.

| Handler | Weapons | What it does |
|---|---|---|
| `WandUse <delay> <missile> <?> SINGLE_SHOT\|MULTI_SHOT <sound> <charges>` | Lesser Fireball staff (`20 Fireball 3.0 SINGLE_SHOT SmallFireballWand 10`), Fire Storm staff (`10 Fireball 1.0 MULTI_SHOT`), Sulphorous Flare (`200 YellowStarShot`), Sulphorous Shower (`100 YellowStarShot MULTI_SHOT`) | Spawns the named missile object, owned by the wielder, just in front of them along the way they face, moving at the missile's own SPEED plus the wielder's velocity. MULTI_SHOT adds two more, 8 direction steps (of 256) either side. A shot waits out the delay (in frames) and uses a charge. |
| `WandCastUse <charges> <?> <spell>` | Force wand (`SPELL_CHAIN_LIGHTNING`), Death Ray wand, Infinite Pain wand (`SPELL_FORCE_OF_NATURE`), Oblivion Orb (`SPELL_PLASMA`) | Casts the spell as if the wielder had. |
| `BowUse` | Bow, crossbow | Fires an arrow from the equipped quiver (`AmmoUse`). |
| `FireWandUse` | Web wand | A spray of its own. |
| `AmmoUse` | Quiver, fan chakram | Ammunition and thrown weapons. |

The weapon decides what is fired and how often. The missile decides how it flies and what it does on impact:

| Missile | Speed | Flight (UPDATE) | Impact (COLLIDE) |
|---|---|---|---|
| Fireball | 192 | ProjectileUpdate | SparkExplosionCollide 128 |
| WeakFireball / PitifulFireball / StrongFireball / TitanFireball | 192 | ProjectileUpdate | SparkExplosionCollide 64 / 10 / 192 / 255 |
| YellowStarShot | 350 | ProjectileUpdate | YellowStarShotCollide 2 |
| ArcherArrow / ArcherBolt | 800 / 1000 | ProjectileUpdate | ArrowCollide |
| HarpoonBolt | 800 | HarpoonUpdate | HarpoonCollide |
| SmallEnergyBolt | 192 | HomingProjectileUpdate | ProjectileCollide 2 |
| MagicMissile | 32 | MagicMissileUpdate | BoomCollide |
| ImpShot | 400 | ProjectileUpdate | ProjectileCollide 5 |
| OgreShuriken / CherubArrow / GolemArrow | 400 / 800 / 800 | ProjectileUpdate | MonsterArrowCollide `<min> <max>` |
| RoundChakramInMotion | 300 | ChakramInMotionUpdate | ChakramInMotionCollide |

Notes on the table:
- The number after a collide handler is the impact's damage. The weakest fireball and the Titan's share a missile and differ only there.
- MonsterArrowCollide takes a damage range.

## The harpoon

The harpoon is the warrior's ability (`abilityHarpoon`, `spell_harpoon.go`). It creates a `HarpoonBolt` owned by the player and records it on the player's own update data (`HarpoonBolt` and `HarpoonTarg`).

**In flight.** The bolt homes on a creature near the player's cursor. It breaks at `MaxHarpoonFlightDistance`.

**On impact.**
- It deals `HarpoonDamage`.
- It hooks the creature: the player's update pulls it in by `HarpoonForce` every frame.
- The rope is a client effect, sent by `NetHarpoonAttach`.

**Breaking.** The rope breaks when any of these happens:
- the target goes past `MaxHarpoonDistance`, or comes within `MinHarpoonDistance`;
- it has existed longer than `MaxHarpoonExistence`;
- the target stops moving;
- the line of sight is lost;
- either side dies.

`getHarpoonData` panics for any owner that is not a player.

## A fireball staff that shoots a harpoon

There are three ways. The second is built.

1. **Data mod: change the staff's USE line to `WandUse 20 HarpoonBolt 3.0 SINGLE_SHOT SmallFireballWand 10`.** WandUse spawns any object, so the staff would fire harpoon bolts, and they would hook and pull. But the ability's bookkeeping is skipped. The player's `HarpoonBolt` stays empty, so the rope never breaks (cleanup only deletes a bolt it recorded), and the target is pulled for as long as it lives. A creature holding the staff would crash the server (the panic above). The change also alters `thing.bin` for every map. Not recommended.

2. **Map script (built, `mapgen/kit/behaviours/weapons.go`, `HarpoonStaff`).** One named Lesser Fireball staff throws harpoons while the host player holds it. The script works like this each frame:
   - it finds the player's new fireballs and deletes them;
   - in their place it creates a `HarpoonBolt` that has no owner and does not collide, facing the same way;
   - it flies the bolt (26 px a frame, about the game's 800);
   - it strikes the first living creature in its path (impale damage) and reels it to the player with `PushTo` for 40 frames;
   - it drops the bolt at a wall or after 320 px.

   The ownerless bolt keeps the game's harpoon code out of it: its update returns at once, and it never collides. What it lacks is the rope line, which only the engine can send.

   To try it, load the Harpoon map (`mapgen/designs/harpoonlab.py`) in a Solo game, pick up the staff by the start, and fire at the zombies. The other staff beside it is ordinary, for comparison.

3. **Engine change (the faithful version).** OpenNox is open source. A new USE handler, say `HarpoonWandUse`, registered next to WandUse in `legacy/object_use.go`, would call `noxServer.abilities.harpoon.createBolt(wielder)` for a player wielder, and fall back to WandUse for a creature. The rope, homing, pull and breaking would then all be the game's own. A staff whose USE line names it (a `thing.bin` edit, or a modded copy of the Lesser Fireball staff) throws real harpoons. This needs OpenNox rebuilt: Go plus a C compiler for its cgo legacy code.

## Writing scripts against the installed game

OpenNox v1.9.0-alpha13 bundles NoxScript `ns/v4` v4.16.1 (the version is in `opennox-server.exe`). Newer API, such as `Obj.Vel()`, fails at load with "undefined method".

Check generated scripts against that version with `py tests/check_scripts.py <map>_scripts --go <go.exe>`.
