# ModLab: creative additions to Nox

ModLab is a small test map with new things to try. Each one has a sign beside it and an ID (W1-W6, M1-M5, T1, S1) so you can rate them one by one.

- **W1-W6**: weapons with powers.
- **M1-M5**: new monsters.
- **T1**: a training yard.
- **S1**: weapon smithing.

Everything is built from the game's own objects plus map scripts. OpenNox runs the scripts from the map's folder.

| What | Where |
|---|---|
| Map design | `mapgen/designs/modlab.py` |
| Script library | `mapgen/kit/behaviours/mods.go` |
| Python API (catalogue and placement) | `mapgen/kit/mods.py` |
| Installed map | `C:\GOG Games\Nox\maps\ModLab\` (`ModLab.map`, `mods.go`, `mods_config.go`, `ModLab.strings.json`) |
| Labelled pictures | `review/out/qa/modlab/` (`W1.png` … `S1.png`, `MODLAB-overview.png`, `MODLAB-sheet.jpg`) |

## How to play it

1. Start OpenNox (`opennox-hd.exe`) and begin a **Solo** game. Use a **Warrior** for W1, W2, W3, W5 and W6. Use a **Wizard or Conjurer** for W4. The game's class rules decide who can hold what.
2. In the game, press **F1** to open the console. Type `racoiaws` (this turns on cheats), then type `load ModLab`.
3. You start at the west end of a long gallery:
   - **Armoury** (by the start): the six weapons lie on the floor, each with a sign. A chest by the start holds a second Chakram Storm, a second Bloodthirst and potions.
   - **Training yard (T1)**: further east along the gallery.
   - **Monster pens (M1-M5)**: five pens along the gallery's north-east side. Go in through the gap in each pen's wall.
   - **Forge (S1)**: through the gap in the south-west wall, next to the armoury.
4. Click a sign to read it.

## The features

### Weapons

| ID | Name | Base item | What it does | How it works |
|---|---|---|---|---|
| W1 | Flamebrand | Longsword | Every swing throws a ring of fire around you, hit or miss. | The game's own `FireRing` enchantment. Nox's `modifier.bin` defines it, but Westwood used it on only two objects. It is an ATTACKEFFECT, and OpenNox's melee code (`GAME4_3.c`) applies attack effects at mid-swing, before checking for a hit. So it fires on every swing with no script. Forging raises it from FireRing1 to FireRing4. |
| W2 | Chakram Storm | RoundChakram | When thrown, four more chakrams fan out beside it (±15° and ±30°). They cut every creature they pass and fly back to you. | The script watches for a thrown `RoundChakramInMotion` that you own and that carries this chakram. It then flies four ownerless, NoCollide, NoUpdate chakrams of its own. |
| W3 | Quake Hammer | WarHammer | A blow that lands sends a shockwave from the creature struck. The screen shakes, and creatures nearby are hurt (8 + 4 per tier) and thrown back. | Uses the struck creature's IsHit event (see "How a melee blow is detected" below). The knockback is ApplyForce over 8 frames. There is a 12-frame cooldown. Forging adds the game's Impact and Stun enchantments. |
| W4 | Stormcaller | LesserFireballWand | Instead of a fireball it casts chain lightning. It strikes the first creature in front of you (within a 35° cone, 360 px), then up to 3 more within 180 px of each other. Each strike does ¾ of the one before (22 damage at first). | Each fireball you fire while holding it is deleted and replaced by lightning rays (Effect LIGHTNING) plus electric damage. It has 200 charges. |
| W5 | Bloodthirst | GreatSword | Each blow that lands heals you 3. A kill heals 15 and gives 3 s of haste. | IsHit event, plus the Death event within 1.5 s of your blow. |
| W6 | Frostbite | MorningStar | Each blow slows the creature for 4 s. A third blow on the same creature within 5 s freezes it solid for 2.5 s (ENCHANT_FREEZE + HELD). | IsHit event and a hit count kept per creature. |

**How a melee blow is detected.** No script event fires when you swing, so a blow is detected when it lands. Every creature's IsHit event is watched. The event's "caller" is the attacker as the game records it. That is the weapon or missile that did the damage if there is one, otherwise its owner. The script counts the blow as yours if the caller is:
- you;
- an item you have equipped; or
- something you own.

It then runs the power of the weapon you hold.

### Monsters

Nox has no crab, ogre lord or similar art, so each monster is an existing creature with new stats and scripted abilities. It waits frozen in its pen until you come within 230 px or strike it, then shouts its line. It comes back 20 s after it dies.

| ID | Name | Base creature | Health | What it does | Difficulty |
|---|---|---|---|---|---|
| M1 | Ogre Lord | OgreWarlord | 700 | Every 70 frames it throws a boomerang chakram if it can see you (within 420 px). The chakram cuts you (12) on the way out and again on the way back, then the Ogre Lord catches it. Below half health it throws three in a fan. | boss |
| M2 | Giant Crab | Scorpion | 450 | Nox has no crab art; the scorpion is the closest armoured, pincered creature. Its shell gives back two thirds of every blow's damage. It scuttles sideways around you. Its snap (14 damage) pins you for 1.2 s, and the shell stays open for 2 s after it, which is the moment to strike. | hard |
| M3 | Bone Caller | Necromancer | 320 | Raises 2 Skeletons every 5 s, up to 4 at once. While 2 or more stand, a bone ward halves the damage he takes. When he dies, his skeletons crumble. | hard |
| M4 | Ember Matriarch | EmberDemon | 380 | Births an Imp every 4 s, up to 5 at once. She heals 3 per living imp every 2 s. Each imp bursts into flame when it dies (a MediumFlame for 4 s; 6 damage if you are within 60 px). When she dies, her whole brood bursts. | hard |
| M5 | Blink Duelist | Swordsman | 280 | Every 110 frames, if you are 70-340 px away, he teleports to stand behind you and attacks. Once, below 35% health, he becomes invulnerable for 2 s. | medium |
| T1 | Training targets | GruntAxe ×3, Bear, OgreBrute, Urchin | stock | Frozen until you come within 150 px or strike them. They come back 6 s after they die. | easy |

### S1: Smithing

1. Lay a weapon beside the anvil (it must lie within 110 px of it).
2. Step onto the **forge plate**, the grey stone patch south-east of the anvil, and stand on it for about 2/3 of a second.
3. The smith reforges the weapon. It vanishes from the anvil, and the smith drops the new piece at his feet.

What the forge can do:
- **Upgrade.** It knows four lines: Longsword, Battle Axe, the Flamebrand (W1) and the Quake Hammer (W3). Each goes plain → fine → superb → masterwork.
  - Each tier uses the game's own enchantments. WeaponPower and Material rise 2 → 4 → 6. Longsword adds Fire then Lightning; Battle Axe adds Vampirism then Stun; Flamebrand adds bigger FireRings; Quake Hammer adds Impact then Stun.
  - The base cost is 100 / 200 / 400 gold. Each smithing level above 1 takes 8% off.
- **Melt.** Any other weapon (except the scripted power weapons) is melted down for 20 gold and 1 xp.
- **Smithing level.** It rises as you work steel. An upgrade gives the new tier's number in xp; a melt gives 1. Levels come at 2, 5, 9 and 14 xp, up to level 5. A tier N piece needs level N or higher.
- **The smith.** Walk up to him and he states his level, xp and prices.

To try it: 1,800 gold lies in the forge's west corner. Spare longswords, battle axes and junk weapons for melting lie along the east side.

**How it works.** A script cannot set an item's enchantments in NoxScript 4.16. So every forged piece is a copy already made in the map, with its enchantments, stored in a sealed vault. The anvil hands these out in turn: 2 of each tier for Longsword and Battle Axe, 1 of each tier for W1 and W3. When a line's copies run out, the smith says so.

## What is verified, and what is not

**Verified:**
- `py tests/check_scripts.py` compiles the scripts against NoxScript ns/v4 v4.16.1, the version alpha13 bundles. This was run on the build output and on the installed map folder.
- `py tests/server_smoke.py mapgen/designs/modlab.py --seconds 40`: the dedicated server loads the map and runs the scripts with no panic and no script error (problems=0).
  - With no player in that server, the script runs a **self-test** instead. It uses stand-in creatures in a sealed test cell and runs each power, ability and forge step. The log shows `modlab selftest: … ok` for:
    - power weapons found by name (including 2 inside a chest);
    - the W2 fan in flight;
    - W3 splash damage plus knockback;
    - W4 chain lightning striking 2 creatures;
    - W5 healing plus haste;
    - W6 slow, then freeze plus hold on the third blow;
    - M1 throw (a fan of 3 when below half health);
    - M2 snap: damage and the foe held;
    - M2 shell: a 60-damage blow became 20;
    - M3 raising 2 skeletons, and both crumbling on his death;
    - M4 brood, and an imp's flame burst;
    - M5 blink;
    - M3 and M5 deaths, and both respawning;
    - the forge taking a longsword through fine, superb and masterwork (each copy found by the anvil afterwards), refusing a 4th tier, and melting a sword.
  - The test found and fixed two real bugs. One was a yaegi panic on `b.o, b.engaged = nil, false`. The other: a vault copy moved with SetPos dropped out of the map's search index. The smith now picks the copy up and drops it, which is the game's own drop.
- A scratch "gauntlet-style" map was also smoke-tested: monsters awake from the start with no respawn, all six weapons in a chest, and a kit.npcs sentry beside them. It loaded clean and the self-test ran, then it was deleted.
- `MapEditor --render-image` renders the map. The pictures are in `review/out/qa/modlab/`.

**Not verified (needs a real play session):**
- Anything that needs a player: whether your melee blow's IsHit caller really counts as yours (W3, W5, W6), W2 detecting your throw, W4 replacing your fireball, gold being charged, standing on the plate, and the smith's chat.
  - The self-test can only call the powers directly. In a dedicated server, damage from one creature to another is ignored (same side), so the self-test strikes with no source.
- How the effects look and feel:
  - W1's ring size. FireRing is a native effect, so it should simply work.
  - The chakram sprites flying with NoUpdate set.
  - Whether the knockback strength (ApplyForce 6-8 per frame for 8 frames) is noticeable.
  - Whether the M2 sideways scuttle reads as a crab.
  - Whether teleports and rays show on screen.
- Balance: health, damage and timings are first guesses.

## Known limits

- **Swing versus hit.** W3, W5 and W6 fire when a blow lands, not when you swing; no script event exists for a swing. W1 fires on every swing because it is the engine's own enchantment.
- **Class rules.** A Warrior cannot use W4, and a Wizard or Conjurer cannot use the melee weapons. To try everything you need two characters.
- **Names.** A monster's name over its head is still the base creature's. Custom names per object are not reachable from NoxScript 4.16. The signs and the monsters' shouted lines carry the new names.
- **Forge stock.** It is finite (the vault copies). Forge levels and xp live in script variables, so a saved game does not keep them.
- **Shared event callbacks.** A creature has one callback per event. The mods watch every creature's IsHit and Death events, except those handed to `ModLeaveAlone`. Creatures driven by kit.npcs behaviours (sentries, packs and so on) must be left alone (`mods.attach(pop.behaviours)` does it), so the melee powers do not fire on them.
- **Unplaceable creatures.** OpenNox alpha13 cannot read a map with a **Skeleton** or a **Wolf** placed as a creature. The server stops at "cannot read next section: EOF", then panics, the same as the known Zombie problem. This was found here: each one alone broke an otherwise loading map. `kit/mods.UNSAFE_PLACED` refuses them for trainees. Scripts may still create them; the Bone Caller raises Skeletons. Other designs that place Wolf or Skeleton (npclab, possibly story maps) are likely affected.
- **Side note on HarpoonStaff.** OpenNox's `PushTo` pushes *away* from the point for a positive force. The ns doc says "toward", but `server/object.go` Push does `obj.Pos() - p`. So the HarpoonStaff's reel (`PushTo(h, pull)`) may push creatures away instead of reeling them in. This is untested.

## The API: placing the mods on any map (`mapgen/kit/mods.py`)

```python
import random
from kit.npcs import Population
from kit.mods import Mods, WEAPONS, MONSTERS, FORGE_LINES, UNSAFE_PLACED

pop = Population(m, random.Random(seed))            # optional: share one so creatures keep apart
mods = Mods(m, pop)                                 # m: the nox.Spec

mods.weapon("W3", x, y)                             # a power weapon on the floor (world pixels); tier=0..3
m.obj_px("Chest4", x, y, items=[mods.weapon_item("W2"), mods.weapon_item("W5", tier=2), "RedPotion"])
mods.monster("M1", x, y)                            # frozen until the player is within 230 px; never returns
mods.monster("M5", x, y, wait=0, respawn=0, hp=200) # awake from the start; health overridden
mods.trainee("GruntAxe", x, y, respawn=6.0)         # any creature type as a returning target
mods.forge(anvil=(x, y), smith=(x, y), plate=(x, y), vault_uv=(u0, v0),
           tier0={"flamebrand": ["W1_1"], "quake": ["W3_1"]})   # optional forge and its sealed vault
mods.test_cell(u0, v0)                              # optional: a sealed room for the dedicated-server self-test
...
mods.attach(pop.behaviours)                         # LAST: writes mods.go + mods_config.go into m.scripts
```

**The catalogue**

`WEAPONS[id]` gives each weapon's:
- `name`, `kind` (the script power), and `base` (thing type);
- `who` can use it;
- `tiers` (enchantments per tier, for W1 and W3);
- `text` (the sign text).

`MONSTERS[id]` gives each monster's `name`, `kind`, `base`, `hp`, `difficulty` and `text`.

`FORGE_LINES` lists the forge's lines.

**Placement calls** each return the object dict:

| Call | What it places |
|---|---|
| `weapon(wid, x, y, tier=0, name=None)` | A power weapon on the floor. |
| `weapon_item(wid, tier=0, name=None)` | A power weapon as an item for a container. |
| `monster(mid, x, y, name=None, wait=230, respawn=0, hp=None, face=None, action="guard")` | A new monster. |
| `trainee(type, x, y, name=None, wait=150, respawn=6, face=None)` | A returning training target. |

- Script names are made unique per map (`W3_1`, `M1_2`, …) unless you give `name`.
- `wait=0` means awake from the start (not frozen).
- `respawn=0` means it never comes back.

**Scripts**
- `attach(behaviours=None)` writes the two per-map files into `m.scripts`: `mods.go` (the library, with its package named after the map) and `mods_config.go` (this map's calls).
- They live alongside kit.npcs's `behaviours.go`/`config.go` and the quests' files.
- `mapgen/install.py` copies them into `maps/<Name>/`.

**Low-level calls** (for things placed some other way): `weapon_call(kind, name, tier)`, `monster_call(kind, name, label, hp, wait, respawn)` and `forge_line(...)`.

**Text.** Sign text goes through the map's `<Name>.strings.json`. ModLab's design shows the pattern: a `sign()` helper with keys `ModLab:W1` and so on, and each sign's text from the catalogue.

### Composing gauntlets: limits

- **Any number of each monster and weapon** may be placed. Each is independent and keyed by its script name.
- **Per-monster caps:**
  - A Bone Caller keeps at most 4 skeletons and an Ember Matriarch at most 5 imps. These are per caster, so three Matriarchs means up to 15 imps plus their flame bursts.
  - The Ogre Lord's chakrams live at most 8 s each, about 1 per 2.3 s per Lord (3 below half health).
  - Keep it to about 3 casters (M3 or M4) per arena.
- **Rough threat for a mid-level warrior:** M5 medium < M2, M3, M4 hard < M1 boss. A Matriarch together with a Bone Caller in one room is very hard: the imps' fire plus skeletons, and two healing or warding casters.
- **Awake monsters** (`wait=0`) use the game's own AI from the start. Their abilities start once the player exists and comes within range. Frozen ones (`wait>0`) stay put until approached, which suits rooms that open one at a time.
- **The forge is optional and once per map.** It uses the fixed script names `S1_Anvil` and `S1_Smith`. The smith must stand within about 50 px of the anvil, and the plate must be about 130 px away.
- **Do not place** Zombie, VileZombie, Skeleton or Wolf (`UNSAFE_PLACED`).
- **Creatures owned by kit.npcs behaviours.** Pass `pop.behaviours` to `attach()`. The powers still damage those creatures, but W3, W5 and W6 do not trigger on them.
- **Self-test.** Run `py tests/server_smoke.py <design> --seconds 40` and look for `modlab selftest: … ok` lines with no "PANIC". With no `test_cell`, the stand-ins stand beside the first monster.
