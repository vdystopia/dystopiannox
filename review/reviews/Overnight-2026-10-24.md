# Overnight 2026-10-23/24: QA round 3 into the process, and traps

## 1. QA round 3 into the process; round 4 to rate

Your round 3 ratings (155 of 155 items, 128 keep, 27 fix, 6 set notes) are saved in `review/history/qa-round3/`
and summarised in `review/reviews/QA-round3.md`. Every note became a written rule with its cause and the kit fix,
in three ledgers: `review/qa3/ledger-rooms.md` (Q3R-1..10), `ledger-civic.md` (Q3C-1..7, Q3N-1..2) and
`ledger-ext.md` (Q3X-1, Q3N-1..3). By the rule (a set note, or two or more fixes/notes), these were regenerated:

| Set | What changed |
|---|---|
| Crypt | the pair of crates is gone from every crypt (no crates of any kind in crypts now); urns, rubble and broken coffins take those spots |
| Shrine | no two shrines share an altar (stone altar, sacred fire, holy font, the Land of the Dead's ark, burning skulls; saint's or wolf's statue, tomb, scales, bier); the same rule written for every type with a centrepiece |
| Tavern | every carpet ends at a solid trim like 02's; a stone border across the barkeep's opening |
| Throne room | five different plans, not just new pieces (dais with benches, twin thrones, petition hall, ...) |
| Barracks | foot chests back to the bed, facing away, right at the foot; a chest in each gap between pairs of beds |
| Great hall | the brick border edged all the way round (the NE wall too) and every carpet's whole trim in a contrasting colour; the cause was a seam rule shared with the kitchen hearth (Q3N-1), fixed for every room |
| Hall | 01 and 03 rebuilt on 02/04's plan: one colonnade each side, a fountain at the end, a carpeted nave, benches, urns and plants on the walls |
| Smithy | the 80-99 tile smithies about a sixth emptier: stock by the walls, racks and armour stands instead of mid-floor barrels |
| Bridges | only BR-01, BR-06 and BR-11 (the cobblestone ones), as you asked: the cobble now ends exactly at the bridge on both banks |

Single notes (kitchen hearth, the shop's size and variety, the bandit camp's blocked cave, the graveyard obelisk,
the shrine's centring) became rules and kit fixes without new pictures.

**Rate it here: [QA round 4](https://claude.ai/artifact/MNBrtLqtoWhpBdYUdHKHcL)** (the same page as before: 1-5,
keep/fix/drop, notes per set; each set shows your round 3 note, what changed, and the round 3 pictures for
comparison). Two flaws I saw in the final pictures are named in the page's intro rather than hidden: great hall 03's
carpet ends one row short, and a hall's fountains straddle the carpet's end.

## 2. Traps: what Westwood does, what the engine does

- `rules/traps/WESTWOOD_SCRIPTS.md`: all 120 decompiled campaign and quest map scripts catalogued (triggers, effects,
  Westwood's timings, 29 set pieces, how traps and monsters combine, layout and signposting).
- `rules/traps/ENGINE.md`: every trap object's behaviour from the OpenNox source (damage, timing, jumping, pits,
  arrows, sentries, plates, walls, the script API, what would need an engine change).
- `rules/TRAPS.md`: the facts measured in the game tonight (a real player stood in each trap, walking, running,
  jumping: `tests/traps_e2e/run.py traptest`, `jumptest.py`), the trigger vocabulary, the rhythm, our rules T1-T9.

What Westwood does, in short: traps are short and readable (visible hardware, a sound or a demonstration before
damage), taught alone before they are combined, and a dungeon's traps work with its monsters (a pursuer treads your
plates; a guardian's death opens the next stage). Their rhythm: danger 0.5-1 s, safe 2-5 s, re-arm 1.5-4 s, a
4-20 frame stagger turns a row into a wave, countdowns of 10-16 s, a gauntlet of 4-7 ideas with a well between.

How traps are switched (step 2), all built into the kit and used in the labs:

| Trigger | How it works here |
|---|---|
| Pressure plates | pressed and released are both triggers (step-off fire, hold-the-row arrows, weights); player-only or anyone's (a monster treads them too); visible or hidden wires |
| Levers | on/off or toggling; off-switches, gates, a quench that drowns a forge |
| Invisible triggers | room entries (the door slams), wake zones that start a block wave, a mouth that restarts a cycle |
| Motion detection | sentry beams (fixed, sweeping, carried, cycled) and a statue's eye: move while its lamps burn and it rays you |
| Kills | a guardian's death opens a gate |
| Timers | loops, waves, countdowns, latches (three plates within 4 s), combinations |
| Items | lift the key or the gold and the room springs |

Two engine facts shaped everything: OpenNox alpha13 never hands a plate's or lever's script name to Go scripts, so
the kit watches them as zones every frame; and only walls written as secret walls can open, so gates are secret
walls. No engine change was needed.

## 3. What was built

- **The trap kit** (`mapgen/kit/traps.py`, `kit/behaviours/traps*.go`, `kit/trapkit/`): groups, clocks, movers,
  zones, plates, levers, watches and an action queue in one runtime, and 10 kinds x 10 patterns (spikes, flames,
  blocks, pushers, arrows, pits, blades, sentries, spells, triggers), each pattern with its tells, its answer, what
  a careless player pays, and a tier: standard (any class, some skill) or hard (punishes mistakes).
- **TrapLab** (`mapgen/designs/traplab.py`): ten maps, TLSpike ... TLTrigger, a hub hall with the ten stations of
  one kind off it, each with a sign, a portal back and a pit room.
- **TrapGaunt** (`mapgen/designs/trapgaunt.py`): ten gauntlets, TrapGnt01-10, 5 to 14 stages each (86 in all) in a
  winding route with rest rooms between; standard stages first, hard ones later; seven with monsters that join from
  the first third on and rise, three pure traps. Falls drop you back into the room before.
- **TrapDemo** (`mapgen/kit/trapdemo.py`, `designs/trapdemo01-10.py`, `campaign/trapdemo/MISSIONS.md`): ten
  missions, each a medium map with an expedition camp and its quest giver (voiced), 8-13 rooms furnished by the room
  kit, 5-10 trap passages between them (65 in all), monsters by setting, a BossLab boss with the approved weapons,
  a main quest and a side quest. The ten, one line each:

| | Mission | Setting | Boss | Quests |
|---|---|---|---|---|
| TD-01 | The Reliquary of Saint Varo | crypt | Mortivane (B4) | Saint Varo's reliquary for Brother Aldous; Pell's satchel |
| TD-02 | The Cinder Foundry | forge | Ignis Varr (B9) | the Master's Hammer (the quench lever drowns the forge first); the guild's black book |
| TD-03 | The Serpent Steps | temple | Garet Hawkeye (B6) | the Serpent's Eye; Tavin's map case |
| TD-04 | The Collapsed Seam | mine | Oskar Thorne (B3) | the Heartstone; Wynn's torch |
| TD-05 | The Vault of Night | Land of the Dead | Vael the Unbound (B1) | the Blue Idol for Ingrid; Hagen's silver key |
| TD-06 | Thornhold Keep | castle | Aurelian (B10) | the amulet in the chapel; the armoury key |
| TD-07 | The Quiet Catacombs | crypt | Silas Vane (B5) | Tomas's diamond for Maren; the book of the dead |
| TD-08 | The Storm Anvil | forge | Dravik Stormblade (B7) | the anvil's heart for Dudley; the master's tool bag |
| TD-09 | The Sunken Sanctum | temple | Kesh of the Red Sands (B8) | the sun disk for Father Morgan; Edwin's prayer book |
| TD-10 | The Warlord's Trial | castle | Sir Garrick (B2) | the trial: beat Garrick, bring the Gold Key; Roderick's amulet |

Rooms follow your design rules: no open torches indoors (rooms take candelabras or braziers by setting; passages
an unseen light, so nothing stands in a trap's lane), passage mouths kept clear, lived-in camps.

## 4. How they were tested

- **The simulator** (`review/traps/sim.py`): every station on a fine grid in time, the trap runtime replayed in
  Python; it plans the cheapest careful route (with jumps no longer than the game's, levers and plates it may use,
  what the route sets off fed back) and tries a careless straight walk and run at arrival moments spread over the
  trap's whole cycle. An exact frame-by-frame replay judges every route.
- **The game** (`tests/traps_e2e/tour.py`): every station of all 30 maps played in OpenNox itself; a probe walked a
  hero with 3000 health along the careful route and the careless walk and run, the game's traps doing the damage
  (traps reset before each run: clocks, movers, zones, sentries' beams, guns' timers, eyes' clocks).
- **Real input** (`tests/traps_e2e/realwalk.py`): where shoves decide (pushers, blocks, closing walls), a careless
  walk with the game's own movement, so the engine shoves and drops the player.
- **Missions**: every mission loaded in the dedicated server (scripts start, quests start: 0 problems in all ten).

The game test found several faults in my own tools, all fixed and re-run: a jump planned 0.2 squares too long;
skull fireballs treated as instant; a jump landing on a plate not counted as pressing it; moving blades planned
too close; the saw's breakable walls and the motion eye not modelled; plates that start a wave or fire arrows not
used or not avoided; the crumbling floor's drop 6 frames early; careless walks tried only in the first 3 s of long
cycles; beams and gun timers not reset between runs; damage summed across stations in the real-input walk; beams
stopped at the walking clearance instead of the wall (the simulator now reproduces the game's lighthouse deaths to
1-2 frames); the block kit's dwells and blows not mirrored; the tour parking the hero in the camp fire during jumps.

It also found real faults in the maps, fixed:

- **Doors meant to start open stood shut.** A secret wall written "open" kept a slide counter of 0 in the file and
  the engine left it closed: the closing room, the sealed fire room, Locked in, Guard key and combination and one
  sentry station could not be entered by a real player. They are now written as Westwood's start-open walls are
  (scan flag 8, no state), from the engine's own map reader; rebuilt everywhere; checked again with real input.
- **Too easy, made harder:** the rolling wave, the carousel, the runaway block, the closing room (careless walks
  cost 0-24 HP), falling stars, the skull gallery, hold the row (helpers' fixes); the lighthouse (one beam missed
  every careless walker the simulator tried: now two back to back); the jaws (31 HP: a fourth row).
- **TrapDem01** had two easy passages: now a pit passage and the sliding doors (hard).

## 5. Results

**Rate them here: [Nox Trap Review](https://claude.ai/artifact/TxeMNBE4scJ3mMy5QfHcPf)** (the QA page you know: 1-5, keep/fix/drop, notes; tabs TrapLab / TrapGaunt / TrapDemo; every caption says what the station is, its answer, and what the game test found).

The rule each station is judged by (rules/TRAPS.md T2/T3): a careful player gets through for at most 25 HP
(standard) or 90 HP (hard), and a careless walk or run costs at least a third of a 100 HP wizard or drops him into
the pit. "In the game" means OpenNox itself, through the tour and the real-input walks; the full per-station tables
are in `review/reviews/Overnight-2026-10-24-results.md`.

**241 of 251 stations pass in the game** (the latest tour of each map, after all the fixes):

| | Stations | Pass | Not passing (and why) |
|---|---|---|---|
| TrapLab (10 maps) | 100 | 96 | spell: gas vents (careful 47), falling stars (32); trigger: guard, key and combination (92); push: pushers on the beat (0 careless, see below) |
| TrapGaunt (10 maps) | 86 | 81 | gas vents x2 (35), guard, key and combination (97), lane plates in Ember Run (64), Hold still in the Gauntlet of All (180) |
| TrapDemo (10 maps) | 65 | 64 | gas vents in the Quiet Catacombs (36) |

Spike, flame, block, arrow, pit, blade and sentry labs: 10 of 10 each. Gauntlets 4, 5, 6, 8, 9 and all ten
missions but one passage: everything passes.

What the ten that do not pass mean:
- **Gas vents (4) and falling stars:** spell traps. The simulator cannot plan spells, so the "careful" route the game
  walked is not the real answer (time the vents; stop short and let the stars land). Their careless walks all bite
  (90-145 HP; falling stars 27-34). Worth a look in play.
- **Guard, key and combination (2):** a puzzle (kill the guard, take the key, two levers put the fire out) the
  simulator cannot plan either; the route the game walked went through the fire. By reading the script the answer
  is cheaper; not proven in the game.
- **Lane plates in Ember Run, Hold still in the Gauntlet of All:** the same stations pass on their own (0 HP); in
  these gauntlets the rising monsters joined in (a monster that bumps you while the eye watches gets you rayed).
  That is the traps-with-monsters mix you asked for; rate whether it feels fair.
- **Pushers on the beat (TL-PUSH-01):** with real input a careless walker was held back with no harm. It is the
  first station of its lab, where the real-input walk starts badly; in missions 2 and 8 the same pattern drops a
  careless walker into the pit.

Fixed after the run (07:45): **the closing room (TL-BLOCK-09, TG-08-S12).** A real walker stopped at its doorway.
The door was open (the game reported it so every frame); the entry corridor was two squares wide and centred half a
square off the station's line, so a straight walker caught the wall post at its corner. The corridor is now three
squares wide on the station's line with a two-cell door. With real input the walker now enters, the door slams
behind him, and the creeping wall pins him: 252 HP (lab), 240 HP (gauntlet 8).

Known open points, not hidden:
- Hard tier is sometimes gentle on a careless *run*: a run outpaces several traps. The rule asks walk or run; many
  hard stations punish the walk hard and the run less.
- The scripted tour cannot be shoved and passes through walls; pushers, blocks and doors were checked with real
  input (careless walks only). A careful real-input route is the next tool to build.

## 6. Where things are

- **Installed in the game** (map list): TLSpike, TLFlame, TLBlock, TLPush, TLArrow, TLPit, TLBlade, TLSentry,
  TLSpell, TLTrigger; TrapGnt01-10; TrapDem01-10 (voiced: 79 lines, all through the voice gate).
- **Code:** all on `master`, pushed (also the branches `traps` and `qa3-merge`). The kit: `mapgen/kit/traps.py`,
  `kit/trapkit/`, `kit/behaviours/traps*.go`, `kit/dungeon.py`, `kit/trapdemo.py`, `kit/trapdemo_dress.py`; the
  designs: `mapgen/designs/traplab.py`, `trapgaunt.py`, `trapdemo01-10.py`; the tests: `review/traps/sim.py`,
  `tests/traps_e2e/tour.py`, `realwalk.py`; the page: `review/traps/page.py`, `summary.py`.
- **Rules:** `rules/TRAPS.md` (now with the start-open wall fact), `rules/traps/WESTWOOD_SCRIPTS.md`,
  `rules/traps/ENGINE.md`.
- **QA round 4** page: https://claude.ai/artifact/MNBrtLqtoWhpBdYUdHKHcL; **traps** page:
  https://claude.ai/artifact/TxeMNBE4scJ3mMy5QfHcPf.

I did not rebuild any of your existing maps. BossLab and the weapons are used as approved (each mission's boss).
