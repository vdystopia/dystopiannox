# ModLab: creative additions to Nox

ModLab is a small test map with new things to try. Each one has a sign beside it and an ID (W1-W6, M1-M5, T1, S1) so you can rate them one by one.

- **W1-W6**: weapons with powers (QA round 1 added the Flamebrand's variants W1B and W1C, and tiers for W1, W2, W5 and W6).
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
| Tests without touching the game folder | `tests/modlab_e2e/lab.py` (the server's self-test, and real-player runs in OpenNox's e2e mode with the probes beside it) |
| QA round 1 ledger | `review/qa1/mods.md` (Q1M-1 … Q1M-13) |

## How to play it

1. Start OpenNox (`opennox-hd.exe`) and begin a **Solo** game. Use a **Warrior** for W1, W1B, W1C, W2, W3, W5 and W6. Use a **Wizard** for W4 (it is a Lightning Staff, a wizard's staff). The game's class rules decide who can hold what; a fresh Warrior may also lack the strength to lift the great sword and the war hammer.
2. In the game, press **F1** to open the console. Type `racoiaws` (this turns on cheats), then type `load ModLab`.
3. You start at the west end of a long gallery:
   - **Armoury** (by the start): a row of weapons per power, with the row's sign at its west end; the row's tiers or sizes lie left to right in the order the sign gives (for example "small, medium, large"). A chest by the start holds a second Chakram Storm, a second Bloodthirst and potions. Two signs by the start wall (SP1) say how the Spirit class plays.
   - **Training yard (T1)**: further east along the gallery.
   - **Monster pens (M1-M5)**: five pens along the gallery's north-east side. Go in through the gap in each pen's wall.
   - **Forge (S1)**: through the gap in the south-west wall, next to the armoury.
4. Click a sign to read it.

## The features

### Weapons

Tiers: a weapon's tier is set where it is placed (ModLab lays each tier out; `mods.weapon(wid, x, y, tier=...)`). For W1 and W3 the tier also chooses the game's enchantments, and the forge raises them.

| ID | Name | Base item | What it does | How it works |
|---|---|---|---|---|
| W1 | Flamebrand | Longsword | Every swing throws a ring of fire around you, hit or miss. ModLab has small (tier 0), medium (tier 2) and large (tier 3) flames. | The game's own `FireRing` enchantment (`FireRing1`..`FireRing4`; in Solo the level picks the flame: small flames at 1, medium and fire at 3, fire and large flames at 4). It casts the game's Cleansing Flame spell at you on every swing (OpenNox `modifiers.go`). The game refuses a second ring while the first one's flames last; that is the game's rule for this ring. |
| W1B | Flamebrand of Mana | Longsword | Every swing throws a ring of blue mana flames. A creature they touch is slowed for 3 s and loses a little life (1-4 by tier); a player they touch loses mana. Small, medium, large. | The game's `BlueFireRing` enchantment (the mana version of the ring). The flames' own touch drains mana from players only (Nox's creatures have no mana), so the script adds the slow and the small "drain" damage to any creature within 28 px of one of your blue flames. |
| W1C | Flamebrand Wave | Longsword | Every blow that lands sends two waves of fire over a quarter circle toward the creature struck, the second 8 frames behind the first. Two blows' waves can burn at once. Small, medium, large flames (5, 9, 12 damage per wave). | Script flames (`SmallFlame`, `MediumFlame`, `Flame`), laid an arc at a time outward from you (34 to 154 px), owned by you so their burns are yours and do not hurt you. See "W1C: why on a blow" below. |
| W2 | Chakram Storm | RoundChakram | When thrown, more chakrams fan out beside it: tier 1 two (±15°), tier 2 four (±12°, ±24°), tier 3 six in a wider fan (±16°, ±32°, ±48°). They cut every creature they pass and fly back to you. | The script watches for a thrown `RoundChakramInMotion` that you own and that carries this chakram. It then flies ownerless, NoCollide, NoUpdate chakrams of its own. (Tier 0, the first version, throws four.) |
| W3 | Warp Hammer | WarHammer | A blow that lands warps you a short way back from the creature you struck: 100 px, 15 more per tier; sideways if a wall is behind you. At most once a second. | IsHit event, then `SetPos` with the game's teleport flash at both ends. The way is checked for walls every 14 px, so you never pass through a wall. It was the Quake Hammer, whose knock-back the game's own Impact enchantment already gives. Forged tiers: WeaponPower and Material, and Stun at masterwork. |
| W4 | Stormcaller | ForceWand (the Lightning Staff) | Its chain lightning burns green and poisons every creature it strikes. | See "W4: the green lightning" below. The staff has 200 charges. |
| W5 | Bloodthirst | GreatSword | A kill feeds you. Tier 1: 5 s of haste. Tier 2: 5 s of haste and invisibility. Tier 3: a force field that soaks 50 damage and lasts up to 15 s. It no longer drinks life on each blow (the game's Vampirism enchantment does that). | The kill is seen by the creature's Death event: yours if your blow landed on it in the last 1.5 s, or you hold the Bloodthirst within 130 px of it. (The game raises no IsHit for a blow that kills, which is why the first version's "haste on a kill" never fired on a one-blow kill.) Invisibility: the game ends it at your next attack, so for those 5 s the script lays it on again. The force field is the game's Force Field spell at level 3: each blow on you is halved and the half it turns comes off its 50; a blow that would kill you leaves 2 health and breaks it. |
| W6 | Frostbite | MorningStar | Each blow slows the creature for 4 s. A third blow on the same creature within 5 s freezes it for 3 s (stunned). Tier 2: a mana flame also burns under it while it is frozen. Tier 3: a fire burns under it instead. | IsHit event and a hit count per creature. Frozen = the game's FREEZE and HELD enchantments. The flame is a `MediumBlueFlame` or `MediumFlame` laid under the creature for 3 s, owned by you; the script burns the creature every 10 frames while it stands in it (fire 4, mana flame 2: creatures have no mana to burn). |

**W1C: why on a blow, not on every swing.** No script event fires on a swing. The one sign of a swing a script can see is the FireRing enchantment's ring itself. The first build kept FireRing1 for that, put the ring out the frame after and sent the wave instead. A play test showed the ring still drawn round every swing: the game sends each ring flame to the player's screen once, as a flame the client moves by itself (`MSG_CLIENT_PREDICT_LINEAR`), so putting it out on the server does not take it off the screen. So the wave answers a landed blow, aimed at the creature struck.

**W4: the green lightning.** The Lightning Staff casts the game's own chain lightning, and the engine draws it in its own colour; no script can change that colour. So the moment that lightning first strikes a creature, the script ends it and throws its own chain in its place:
- How it ends the game's lightning: the game ends a chain lightning whose caster carries the RUN enchantment (OpenNox `GAME4_3.c`, `nox_xxx_onFrameLightning_52F8A0`); the script gives you RUN for two frames.
- The script's chain: up to four creatures, 18 damage (+4 per tier) at the first, each strike three quarters of the one before. The beam is the game's CHARM ray, a stream of green sparks drawn like the lightning's blue ones, renewed for 0.8 s along each link.
- Every creature struck is poisoned: the game's Poison spell at level 4 (+1 per tier). The game then tints it green and takes 1 health every 16 frames at level 4 (every 8 at level 5), starting a second after the last blow. The poison wanes a level every 1000 frames.
- What differs from the request: the staff's own blue sparks still flash for the first frame of each shot, before the script ends the spell. NoxScript's GREEN_BOLT effect would be a true green zap, but OpenNox alpha13's client draws nothing for it (tested beside LIGHTNING and CHARM).

**How a melee blow is detected.** No script event fires when you swing, so a blow is detected when it lands. Every creature's IsHit event is watched. The event's "caller" is the attacker as the game records it. That is the weapon or missile that did the damage if there is one, otherwise its owner. The script counts the blow as yours if the caller is:
- you;
- an item you have equipped; or
- something you own.

It then runs the power of the weapon you hold.

### Monsters

Nox has no crab, ogre lord or similar art, so each monster is an existing creature with new stats and scripted abilities. It waits frozen in its pen until you come within 230 px or strike it, then shouts its line. It comes back 20 s after it dies.

| ID | Name | Base creature | Health | What it does | Difficulty |
|---|---|---|---|---|---|
| M1 | Ogre Lord | OgreWarlord | 700 | Every 70 frames it throws a boomerang chakram if it can see you (within 420 px); it cuts you (12) going out and coming back. Below half health it throws three in a fan. **New:** every 5 s, if you are 90-380 px away with nothing between, it throws a harpoon: it hooks you (10 damage) and drags you to it, then it attacks. | boss |
| M2 | Giant Crab | Scorpion | 450 | Its shell gives back two thirds of every blow's damage. It scuttles sideways around you. Its snap (14 damage) pins you for 1.2 s, and the shell stays open for 2 s after it. (Its sign and explanation are another QA item.) | hard |
| M3 | Bone Caller | Necromancer | 320 | **New:** every 5 s he raises two Skeletons or one Skeleton Lord (about two times in five), up to 6 standing. Every 2.5 s, if he sees you within 400 px, he casts the game's Slow at you (while you are not slowed) or Magic Missile. He runs from you when you come within 190 px; if you catch him (within 110 px) he teleports 150-260 px away, at most every 8 s, and a Ghost rises where he stood (3 ghosts at most). Kept: while 2 or more of his bones stand, a bone ward halves the damage he takes. When he dies, his bones and ghosts crumble. | hard |
| M4 | Ember Matriarch | EmberDemon | 380 | Births an Imp every 4 s, up to 5 at once, and heals 3 per living imp every 2 s; each imp bursts into flame when it dies. **New:** permanent protection from fire (the game's enchantment, with its red orbiting sparks); vampirism, so each of her blows heals her; each of her blows also burns you for 5 more with a burst of sparks; when she dies, a great ring of fire spreads from her (five rings of flames, 50 to 190 px out, 10 damage when a ring passes over you). | hard |
| M5 | Blink Duelist | Swordsman | 280 | Every 110 frames, if you are 70-340 px away, he teleports behind you and attacks. Once, below 35% health, he is invulnerable for 2 s. **New:** permanent haste and infravision (the game's enchantments, renewed every 10 s); each of his cuts slows you for 3 s, and a second blade follows 7 frames later (6 damage, and the slow again). | medium |
| T1 | Training targets | GruntAxe ×3, Bear, OgreBrute, Urchin | stock | Frozen until you come within 150 px or strike them. They come back 6 s after they die. | easy |

**How a monster's blow on you is seen.** No script event fires when a creature strikes a player. So the script watches your health each frame. A drop that the script did not cause itself is the blow of the nearest living creature within 80 px. If that creature is the Matriarch or the Duelist, its power answers.

**What could not be done as asked.**
- **M5 dual-wielding.** Nox's swordsman is drawn from fixed animation frames with a sword and a shield in every frame. No script, and no change to the engine short of new art, can swap the shield for a sword. So the second sword is in his blows (the second blade above), not in the picture.
- **M1's rope.** The game draws the warrior harpoon's rope between player and target only for its own harpoon, which no script can start. The Ogre Lord's harpoon is the game's harpoon bolt, flown by the script. It sticks in you while you are dragged, with no rope.
- **The death ring (M4)** is the script's flames, not the game's ring spell. The game refuses a new ring to a caster that still has one burning, so two Matriarchs dying close together would get only one ring.

### SP1: the Spirit class (Mystic)

It is not in ModLab itself. The Mystic is an engine mod (`mods/engine/SPIRIT.md`) in a separate game program, `opennox-spirit-hd.exe`. Two signs by the start wall (SP1a, SP1b) say how it plays:
- The Mystic is the Conjurer with Spirit (the cyan bar) instead of mana. It has the same spells, armour and weapons.
- Spirit refills by itself three times slower than mana, and mana crystals give it none. Blue potions still work.
- Half the damage of every physical blow the Mystic lands (staff, bow, crossbow, fists) becomes Spirit.
- So it fights up close to keep casting.

The full explanation is in `SPIRIT.md`, "How the Mystic plays". To try the Mystic against ModLab's monsters, load ModLab in the Spirit build.

### S1: Smithing

1. Lay a weapon beside the anvil (it must lie within 110 px of it).
2. Step onto the **forge plate**, the grey stone patch south-east of the anvil, and stand on it for about 2/3 of a second.
3. The smith reforges the weapon. It vanishes from the anvil, and the smith drops the new piece at his feet.

Five short signs in the forge say this where it happens: at the plate (S1), at the anvil (what it raises), by the
smith (his levels), by the spare weapons (prices and melting) and by the gold. The plate is only the grey floor patch:
there is no pressure-plate object. (The QA picture's "brown pressure plate" was the editor drawing a spare Staff, which
has no picture in the editor; the spare is a Morning Star now. QA round 1, S1.)

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

### QA round 1 (2026-10-13): the new powers and abilities

Two kinds of test, both on a private copy of the game folder (hard links and junctions, its own `maps\ModLab`, its own `nox.csf.json` and save folder), so the installed game was never touched. To run them again: `py tests/modlab_e2e/lab.py setup`, then `... server`, `... play probe_warrior.go warrior`, `... play probe_wizard.go wizard` or `... play probe_fx.go` (a game window opens for `play`).

**1. The dedicated server's self-test** (no player; stand-in creatures in the sealed test cell; 54 `modlab selftest: … ok` lines, no panic, no script error):
- W2: tiers 1/2/3 threw 2/4/6 chakrams.
- W3: the wielder warped 115 px away from the creature it struck.
- W4: the chain struck 4 creatures; the wielder carried RUN (the cut); 4 poison casts. Poison alone at level 5: 15 health in 6 s against 0 for an unpoisoned twin.
- W5: tier 1 hasted; tier 2 hasted and invisible; tier 3 force field up. Two 30-damage blows took 15 and 15 from the field's wearer and 30 and 30 from a control without it; the field still stood after soaking 30.
- W6: tiers 2 and 3 froze (FREEZE and HELD) on the third blow and laid their flames; 6 burns in the first second.
- W1C: one blow made one wave and a second blow a second wave burning at once; 128 flames laid; the creature in front lost 36, the one behind 3 (from elsewhere).
- W1B: the creature the blue ring reached was slowed and lost a little life.
- M1: the harpoon, thrown at 212 px, hooked the stand-in and dragged it to 30 px in 13 frames.
- M3: five raises filled 6 places; his Slow slowed the foe; Magic Missile put 3-4 missiles in flight; he teleported 150 px and a ghost rose; on his death 7 bones and ghosts crumbled.
- M4: protection from fire and vampirism on her; her touch took 5 more; her death ring laid 69-107 flames.
- M5: haste and infravision on him; his cut slowed the foe; the second blade fell.
- Respawns, the forge steps and the M2 crab as before.
- Yaegi panicked on `b.minions, b.ghosts = nil, nil` (the same family as the earlier `b.o, b.engaged = nil, false`); now two assignments. Enchantments laid on a frozen creature did not take, so a monster's standing enchantments are laid when it wakes.

**2. A real player, through OpenNox's e2e mode** (the installed `opennox-hd.exe` with scripted mouse input: Solo, Warrior or Wizard, `load modlab`; a probe script logged each power with a real hero swinging east at a held target):
- W3: three landed blows each warped the Warrior 122 px.
- W5:
  - Tier 1: one-blow kills gave haste.
  - Tier 2: haste and invisibility 3 frames after each kill, and still invisible 40 frames later while swinging. Before the fix, the game's own rule had ended the invisibility at the next attack.
  - Tier 3: the force field came up on a kill.
- W6 tier 3: slowed on the first blow, frozen on the third, 27 fire burns.
- W1C: real blows laid 384 wave flames and killed the target.
- W1B: the target was slowed by the blue ring.
- W1: the game's ring of 48 flames on a real swing.
- W2 tier 3: 18 chakrams in flight from three throws.
- W4 (Wizard): a green chain on every staff shot (every 42 frames). No damage from the game's lightning followed the cut. In screenshots the target turns green (poison) and green sparks run along the chain, with a burst of the staff's blue sparks at each shot.
- M1: the harpoon hooked the Warrior at 219 px and dragged him to 48 px in 10 frames (about 17 px a frame).
- M5: haste and infravision; the Warrior slowed on his first cut; 13 cuts, 13 second blades.
- M4: protection from fire and vampirism on her; with her imps removed, her health rose about 8 per blow she landed (150 to 247 over 11 blows); her death ring took 33 from the Warrior.
- Things the first round could not check and this one did: a real blow's IsHit counts as yours (W3, W5, W6, W1C); W2 sees your throw.

**Earlier (2026-10-09), still standing:**
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

**Not verified yet (needs the user's play session):**
- How the new effects look and feel at play speed: the green beam against the staff's blue burst (W4); the wave's size and the ring sizes (W1, W1B, W1C); the death ring (M4); the harpoon's drag without a rope (M1).
- From the earlier round: gold being charged at the forge, standing on the plate, the smith's chat (S1); whether the M2 scuttle reads as a crab.
- Balance: health, damage and timings are first guesses. A fresh level-1 Warrior has 20-34 health in this build: the Matriarch's blows (about 15 each) and her death ring can kill one quickly.

## Known limits

- **Swing versus hit.** W1C, W3 and W6 fire when a blow lands, not when you swing; no script event exists for a swing. W1 and W1B fire on every swing because they are the engine's own enchantments. W5 fires on a kill.
- **Class rules.** A Warrior cannot use W4 (a Lightning Staff: Wizards only), and a Wizard or Conjurer cannot use the melee weapons. To try everything you need two characters.
- **The campaign uses these mods.** The Hollow Choir maps place W1-W6 and M1-M5. A rebuild of those maps picks up this round's changes:
  - the Stormcaller becomes a Lightning Staff, which Conjurers cannot hold (act 7's library text says "for wizards and conjurers");
  - the Quake Hammer becomes the Warp Hammer (act 10's Doran's hammer);
  - Bone Callers raise up to 6 and teleport;
  - Matriarchs leave a ring of fire.

  The installed maps keep the old scripts until rebuilt.
- **Names.** A monster's name over its head is still the base creature's. Custom names per object are not reachable from NoxScript 4.16. The signs and the monsters' shouted lines carry the new names.
- **Forge stock.** It is finite (the vault copies). Forge levels and xp live in script variables, so a saved game does not keep them.
- **Shared event callbacks.** A creature has one callback per event. The mods watch every creature's IsHit and Death events, except those handed to `ModLeaveAlone`. Creatures driven by kit.npcs behaviours (sentries, packs and so on) must be left alone (`mods.attach(pop.behaviours)` does it), so the melee powers do not fire on them.
- **Unplaceable creatures (corrected 2026-10-09).** The Skeleton and Wolf failures first reported here were not the creatures. The map writer could end a file one crypt block short, so OpenNox read past the end ("cannot read next section: EOF", then a panic). That happens to about one map size in eight, whatever the map holds; the same bug was behind the old "Zombies cannot be placed" rule. `Shared/Map.cs` now writes a spare block, and the checker's `setup.file_tail` rule flags a map built without it. Zombie, Skeleton and Wolf placements load; `UNSAFE_PLACED` is empty.
- **HarpoonStaff (fixed 2026-10-09).** OpenNox's `PushTo` pushes *away* from the point for a positive force (`server/object.go` Push: `obj.Pos() - p`), so the harpoon's reel pushed creatures away. `weapons.go` now reels with a negative force.

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

**A sign is one line of 120 characters at most** (`mapgen/kit/signs.py`). The game prints a sign as "The sign reads: ..." on one line, drops line breaks, and crashes to the desktop on a text past 239 characters (QA round 1: M2's sign, 274 characters). ModLab's `sign()` joins the lines and lays a longer text on a short row of signs ("M2 (2 of 4): ..."); the checker's `signs.text` errs past 200.

### Composing gauntlets: limits

- **Any number of each monster and weapon** may be placed. Each is independent and keyed by its script name.
- **Per-monster caps:**
  - A Bone Caller keeps at most 6 bones (Skeletons and Skeleton Lords) plus 3 ghosts, and an Ember Matriarch at most 5 imps. These are per caster, so three Matriarchs means up to 15 imps plus their flame bursts. A Matriarch's death ring is about 100 flames for 2 s.
  - The Ogre Lord's chakrams live at most 8 s each, about 1 per 2.3 s per Lord (3 below half health).
  - Keep it to about 3 casters (M3 or M4) per arena.
- **Rough threat for a mid-level warrior:** M5 medium < M2, M3, M4 hard < M1 boss. A Matriarch together with a Bone Caller in one room is very hard: the imps' fire plus skeletons, and two healing or warding casters.
- **Awake monsters** (`wait=0`) use the game's own AI from the start. Their abilities start once the player exists and comes within range. Frozen ones (`wait>0`) stay put until approached, which suits rooms that open one at a time.
- **The forge is optional and once per map.** It uses the fixed script names `S1_Anvil` and `S1_Smith`. The smith must stand within about 50 px of the anvil, and the plate must be about 130 px away.
- **Do not place** Zombie, VileZombie, Skeleton or Wolf (`UNSAFE_PLACED`).
- **Creatures owned by kit.npcs behaviours.** Pass `pop.behaviours` to `attach()`. The powers still damage those creatures, but W1C, W3, W5 and W6 do not trigger on them.
- **Self-test.** Run `py tests/server_smoke.py <design> --seconds 40` and look for `modlab selftest: … ok` lines with no "PANIC". With no `test_cell`, the stand-ins stand beside the first monster.
