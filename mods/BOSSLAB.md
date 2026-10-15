# BossLab: ten human bosses

BossLab is a test map with ten boss fights, one per arena. Every boss is a **human NPC**: the game draws it with the player's own body, so it wears the player's armour and carries the player's weapons. Each wears its own armour set, dyed its own colours, and fights its own way. Two of them, B3 and B4, raise **major minions**.

| What | Where |
|---|---|
| Map design | `mapgen/designs/bosslab.py` |
| Boss catalogue and placement (loadouts, colours, spells, stats) | `mapgen/kit/bosses.py` |
| Boss scripts (behaviours, abilities, phases, respawns, the self-test) | `mapgen/kit/behaviours/bosses.go` |
| Installed map | `C:\GOG Games\Nox\maps\BossLab\` (`BossLab.map`, `bosses.go`, `bosses_config.go`, `events.go`, `BossLab.strings.json`) |
| Pictures | `review/out/qa/bosslab/` (`lineup.png`: all ten in-game; `overview.png`: the map) |
| Real-player test | `tests/bosslab_e2e/run.py` (with `probe_tour.go`) |

## How to play it

1. Start OpenNox and begin a **Solo** game with any class.
2. Press **F1** to open the console. Type `racoiaws` (this turns on cheats), then type `load BossLab`.
3. You start at the west end of a long hall. A chest beside you holds red, blue and cure-poison potions.
4. Ten arenas open off the hall, five on each side: B1-B5 to the north-east and B6-B10 to the south-west. A sign by each gate names the boss and says how it fights. Click a sign to read it.
5. A boss waits, frozen, until you walk about 320 px into its arena or strike it. It shouts a line when it wakes.
6. When a boss dies it drops what it was wearing and carrying. Thirty seconds later it comes back, twice. After that its arena stays empty until you reload the map.

## The bosses

"Hits" are what a boss did to a test hero with **no armour** (see "What is verified"). Armour lowers them.

| ID | Boss | Wears and carries | How it fights | How to beat it |
|---|---|---|---|---|
| B1 | **Vael the Unbound**, archmage | Violet wizard robe and hat with gold trim, black cloak, Death Ray staff | **Kites.** He keeps 170+ px away. If you close in he blinks 180-260 px away (every 6 s) and fires missiles as he goes; between blinks he backs off. Every 8 s a **violet ring** appears under you and a death ray strikes it 1.4 s later (40 damage). Missile volleys every 5 s. The game's AI also casts Fireball, Lightning, Slow and Shield, and counterspells your missiles. Below 60%: rays every 5.7 s and a lasting shield. Below 30%: three rings at once around you, and 2 s of invulnerability. | Keep moving out of the rings. Corner him: he can only blink through open floor. |
| B2 | **Sir Garrick the Verdant**, warlord | Lime green plate with gold trim (helm, breastplate, arms, legs, boots), ogre axe | **Charges.** Every 6.7 s, if you are 110-430 px away in a straight line, he roars and plants his feet for 1 s, then charges in a straight line: 28 damage, a knock-back and a 1 s stun if he hits you. If he runs into a **pillar or wall** he is dazed for 2 s and takes half again from every blow. Stay in his face and he stamps (12 damage and a shove) every 7 s. Below 60%: berserk (haste and vampirism; charges every 4 s). | Bait the charge with a pillar behind you, then punish the daze. Hits about 42 per blow. |
| B3 | **Oskar Thorne, the Golemwright**, conjurer | Forest green and brown leathers, conjurer's horned helm, bow | **Summons major minions.** He wakes with two black wolves and calls two more every 12 s (up to 3 standing). Every 11 s he **chants for 2 s** with a summoning glow ahead of him; then a **Stone Golem** or **Mechanical Golem** (taking turns, 2 at most) rises there. Deal him 30 damage during the chant to **break the binding**. Every 8 s he hastes all his servants. He stays behind them and shoots his bow. Below 30%: every 20 s he sacrifices a wolf to heal 45. | Interrupt the chants; kill him before the golems pile up. His servants crumble when he dies. |
| B4 | **Lord Mortivane**, necromancer | Black wizard robe and hat, crimson cloak, Staff of Infinite Pain | **Summons major minions.** At 60% health he chants (2 s) and raises **two Skeleton Lords**; at 30% a **Lich**. A strong blow (30) during the chant breaks it, and that raising is lost. Every 12 s he raises two skeletons (up to 4). Every 9 s he throws a **life-drain tether** (up to 3 s): 3 of your health goes to him every third of a second while you stay within 340 px and in his sight. Every servant that falls heals him 15. While a major servant stands he mends 2 a second. Cornered, he **swaps places** with a servant. | Break line of sight to snap the tether. Burst him rather than his skeletons (each dead one feeds him). |
| B5 | **Silas Vane, the Quiet Knife**, assassin | Black leather (helm, armour, armbands, leggings, boots), a sword | **Stalks unseen.** He turns invisible and walks to the spot behind you; faint dust puffs mark his steps. If he reaches you he backstabs (24 damage and a short hold) and fights for 5 s, then throws **smoke** (you are confused for 1 s if close), blinks away and vanishes again. His blade poisons on every other blow. If you **hit him while he is hidden**, he is found and stumbles. Below 60% he stays visible for less time. | Keep turning; watch for the dust; swing at it. |
| B6 | **Garet Hawkeye**, ranger | Sea-green chain (coif, tunic, leggings) with white trim, green cloak, brown boots, longbow | **Keeps his range.** He shoots his bow. Come within 190 px and he **leaps back** (every 5 s), leaving a **bear trap** where he stood (4 at most). Every 7 s a fan of five arrows. Every 11 s a **yellow ring** under you, then a rain of arrows on it (18 damage and a slow). Below 60%: haste, and fans every 4.7 s. | Use the pillars for cover. Watch where he leapt from: there is a trap. About 29 damage a second if you stand in the open. |
| B7 | **Dravik Stormblade**, spellsword | Blue plate with sky-blue trim, ornate helm, great sword | **Two stances.** *Blade stance* (10 s; 7 s below 60%): hasted, he hunts you, and if you are 220+ px away he **steps on lightning** to your side (every 4 s). His blows add a jolt (4). *Storm stance* (6 s): he stands still, half of all damage is turned aside, a bolt hits you every 1.5 s within 320 px (9), and a crackling field hits anything within 110 px (6). | Back off during the storm, close in during the blade. Hits about 45 per blow. |
| B8 | **Kesh of the Red Sands**, chakram dancer | Orange leather helm and chain tunic with red trim, rust leathers, chakram | **Circles you** 210 px out, changing direction every 8 s, and throws a returning chakram every 3 s (10 damage going out, again coming back); three in a fan below 60%. Come within 85 px and he spins into a **whirlwind** for 1.5 s (7 damage and a shove every 8 frames), then darts away. | Step back from the whirlwind, then chase him down. |
| B9 | **Ignis Varr**, pyromancer | Red wizard robe and hat with orange trim, Fire Storm staff | **Area denial.** Fire cannot hurt him. He leaves **burning footsteps** (4 s each). Every 9 s a **wall of flame** across the way between you. Every 6.7 s a **yellow ring**, then a meteor on it (30 damage, flames left burning). Come within 95 px and a **ring of fire** bursts from him. Below 30%: meteors every 4.3 s and a ring of fire at once. When he dies, a last ring of fire. | Don't chase him through his own trail; go round the walls. |
| B10 | **High Warden Aurelian**, paladin | White plate with gold trim, ornate helm, steel shield, morning star | **Stands his ground.** His shield turns **70% of any blow from the front** (sparks show it). When hurt, he **kneels to pray** (every 12 s, 2.5 s), mending 2% of his health every third of a second; deal him **40 damage** during the prayer to break it, which stuns him for 2 s. From 200-420 px he calls you **to judgement**: you are dragged toward him and a yellow ring marks where his blow falls (16 damage and a 1 s hold). At 60%: 3 s of invulnerability and a heal. | Flank him; break the prayer. Hits about 39 per blow. |

## How it works

### Human NPCs (`kit/bosses.py`)

A boss is the game's **NPC** object (thing type `NPC`). Westwood dresses its NPCs the same way: 603 of them on the campaign maps, with their armour dyed. Facts found in the engine source (OpenNox v1.9.0-alpha13) and checked in the game:

- **What an NPC wears.** It puts on only the inventory items flagged EQUIPPED: create flags `0x1000100`, as Westwood writes them (legacy `GAME4_2.c nox_xxx_XFerNPC_52ADE0`). There are no class or strength checks, so any human can wear any armour and carry any weapon.
- **Colours.** An item's four enchantments fill four slots **by position**: effectiveness, material, primary, secondary. Each armour type says which of its colours each slot paints:
  - The main surface of plate, chain, leather and metal helms is the **material** slot (2nd).
  - For a wizard's robe it is the **primary** slot (3rd).
  - For a wizard's hat it is the **secondary** slot (the hat's back).
  - For a cloak's centre and a shield's face it is the **effectiveness** slot (1st).

  Any modifier's colour can go in any slot. The lime plate is the game's `MaterialTeamGreen` (0, 255, 0) in the material slot. The others are `UserColor1-27` and `UserMaterialColor1-32` (`DYE` in `kit/bosses.py` names each one). `UserColor28` and up exist in the game but not in the editor's modifier list, so the kit does not use them.
- **Spells.** The game's AI casts the NPC's `KnownSpells` only when its status flags include `CAN_CAST_SPELLS`. A caster never swings a melee weapon, but it still shoots a bow or a wand. Only the four casters (B1, B3, B4, B9) have the flag; the others fight with their weapons.
  - The use-flags pick each spell's moment: reaction, defensive, disabling, offensive, escape.
  - Haste, Drain, Swap, Teleport and others are never cast by the AI. The script does those.
- **Wands.** They never run dry (`WandChargesLimit` 0; an NPC drops an empty wand and fights with its fists).
- **Do not use `NPCWizard`.** It has no monster.bin entry, so it gets no AI at all.
- **Strength** feeds both melee and bow damage, but the weapon's own damage dominates melee. The paladin did about 75 per blow with a war hammer whatever his strength, so he carries a morning star.
- **Respawn.** A script cannot dress a new NPC in coloured armour: NoxScript 4.16 cannot set an item's enchantments. So each boss has two **spare copies**, dressed the same, frozen in a sealed vault west of the hall. The script brings the next one to the arena.

### The script (`kit/behaviours/bosses.go`)

- **The game's AI** walks the boss, swings or fires what it holds and casts its spells. The script adds the boss's own way of moving: keeping distance (Flee, blinks), charging (moved by the script a step at a time, checked for walls), circling (WalkTo points around you), stalking (invisible WalkTo behind you).
- **Telegraphed blows** are **marks**: a ring of sparks drawn where the blow will fall, which falls 1-1.4 s later. Violet means a death ray, yellow means a meteor, arrows or judgement.
- **Scripted missiles** (Vael's missiles are the game's spell; Garet's fans and Kesh's chakrams are the script's) fly with NoCollide and NoUpdate, as ModLab's do. The script strikes once within 24 px.
- **Channels** (golem rituals, the lich raising, the paladin's prayer) count the damage the boss takes while channelling. A strong enough total breaks the channel.
- **Phases** at 60% and 30% health.
- **A boss's blow on you raises no script event.** The script reads your health instead: a drop of 3 or more that the script did not cause, with the boss within 80 px, is the boss's blow. That drives the assassin's poison and the spellsword's jolt.
- **Self-test.** With no player (the dedicated server) the script runs one: a stand-in creature beside each boss, every ability counted, phases forced, each boss slain and brought back.

### Changes to the shared tools

- `mapgen/build_map.ps1`: list-typed NPC settings (`KnownSpells`), structure fields kept as properties (`BuffList`), and `create_flags` (the EQUIPPED flag).
- `validate/checks.py`: a map with Go scripts beside it counts as scripted, so things kept in a sealed room for a script (BossLab's spares, ModLab's forge vault) are noted, not errors.

## What is verified, and what is not

**Verified:**
- `py mapgen/designs/bosslab.py`: 0 checker errors. The 3 warnings are the lab's sparse decoration.
- `py tests/check_scripts.py`: the scripts compile against NoxScript ns/v4 v4.16.1.
- `py validate/selftest.py`: all checks behave.
- `py tests/roundtrip.py`: 8/8 maps round-trip.
- `py tests/server_smoke.py mapgen/designs/bosslab.py --seconds 100`: the server loaded the map with no panic and no script error. Its self-test saw every boss's abilities fire:
  - Vael's blinks, rays and missiles;
  - Garrick's charge and stamp;
  - Oskar's rituals: a Stone Golem and a Mechanical Golem;
  - Mortivane's drain and skeletons, and two skeleton lords at his phase;
  - Silas's backstabs and smoke;
  - Garet's leaps, traps, volleys and rain;
  - Dravik's bolts, field and stances;
  - Kesh's throws and whirlwind;
  - Ignis's walls, meteors, rings and trail;
  - Aurelian's prayers and blocks.

  With both phases forced: Mortivane's lich, his swap with a servant, Vael's triple rays, Silas found while hidden. All 10 bosses came back from the vault. (Aurelian's shield and Dravik's storm ward turn the test's forced health drop, so the test does not see their later phases.)
- **Real player** (`py tests/bosslab_e2e/run.py`; the installed `opennox-hd.exe` in OpenNox's e2e mode on a private copy of the game folder, a Warrior with 4000 health and no armour set down in each arena for 14 s, each boss forced to its first phase at 6 s):
  - All ten render in their armour and colours (`review/out/qa/bosslab/lineup.png`).
  - Every boss fought and used its abilities on the hero.
  - Health lost in the 14 s:

    | Boss | Lost | Boss | Lost |
    |---|---|---|---|
    | Vael | 190 | Garet | 403 |
    | Garrick | 424 | Dravik | 637 |
    | Oskar (with wolves and a golem) | 655 | Kesh | 260 |
    | Mortivane (with skeletons and two lords) | 541 | Ignis | 299 |
    | Silas | 252 | Aurelian | 709 |

  - Vael's Death Ray staff did not turn on himself. The engine's code aims a cast-wand at its NPC holder, but it did not happen in play.

**Not verified (needs your play session):**
- How the fights feel at play speed against a hero who moves and hits back: the dodge windows, whether the charge, the stalking and the circling read well.
- **Balance.** Health, damage and timings are first guesses tuned against an unarmoured test hero. A real character in armour takes less.
- Mortivane's lich (the 30% raising) was raised in the server's self-test (which forces both phases), not yet in a real-player run.
