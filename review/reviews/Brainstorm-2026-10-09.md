# Brainstorm: where to take the project next (2026-10-09)

Written after QA round 1 (550 labelled lab pictures), ModLab, the Spirit class, the 20 gauntlets and the QA/QC sweep
(`QA-sweep-2026-10-09.md`). Each idea has an effort guess (S = an hour or two, M = a session, L = several sessions)
and what it unlocks. Ideas the user's own feedback already points at come first.

## 1. Close the loops we already have

| Idea | Effort | Why |
|---|---|---|
| **Read the round-1 ratings back into the kit automatically.** A script that pulls the rating page's `ratings` and `typenotes` (ArtifactData), groups Fix/Drop by type, and writes a ledger section in `review/FEEDBACK.md` with each picture's variant data (size, culture, style, archetype) beside the verdict, so a pattern ("every small library is bare", "all ford crossings read badly") is visible at once | S | Makes every future QA round cheap to act on; the ratings become training data for the labs' judges |
| **Rated pictures as the labs' reference set.** Use Keep/5-star pictures as positive examples and Drop/1-star as negatives for the scorecards (alongside Westwood's rooms) | M | The labs currently tune toward Westwood only; this tunes toward the user's taste, which is stricter (fuller rooms, bigger scale) |
| **QA round 2 with only what round 1 failed**, plus a before/after pair per fixed item | S per round | Faster iteration; the user sees their feedback land |
| **Rebuild-on-rule-change.** When the checker gains a rule (like TW-12), a job rebuilds every installed generated map and reports which changed; the sweep found most installed maps predate TW-12 | S | No silent drift between the kit and what is installed |
| **Calibrate the checker against Westwood again** (`validate/checkcheck.py`): 7 dead rules, 4 errors that also fire on many Westwood maps (`floors.wall_blend` on 107: intended, the user's own rule, but `wall_shapes.gap`, `doors.no_wall`, `transport.landing` need a look), 3 warnings that fire on over a quarter of Westwood's maps | M | Fewer false alarms means real findings stand out |

## 2. Combat and the mods (from ModLab, the Spirit class and the gauntlets)

| Idea | Effort | Why |
|---|---|---|
| **Engine hooks for the mods**: we can now build OpenNox from source (the Spirit build). Add the small engine features the scripts lack: a per-object display name (monsters show "Ogre Lord", not "Ogre Warlord"), a melee *swing* event (so W3/W5/W6 fire on every swing like W1), `SetItemEnchantments` (so the forge upgrades the actual weapon instead of handing over vault copies), and working `Get/SetQuestStatus` (stubbed in alpha13) | M-L | Removes every known limit of ModLab at the root; quest status gives save/load-safe story state |
| **A true harpoon staff** via a `HarpoonWandUse` handler in the Spirit build (rules/WEAPONS.md option 3): rope, homing and pull all the game's own | M | The scripted one lacks the rope line |
| **More power weapons**: a bow whose arrows split into three, a shield that reflects missiles (the game's own reflect), a staff of summoning (temporary allied creature), a whip that pulls (the harpoon's reel, now pointing the right way), a boomerang axe, poison daggers that stack | S each | Each is a few dozen lines on the ModLab pattern |
| **Monster archetypes as a kit**: "shell" (damage reflection), "brood mother", "summoner", "blinker", "boomeranger" are now generic abilities; mix them onto any base creature by data (e.g. a blinking spider queen that births small spiders) | M | Dozens of new monsters from five abilities |
| **Boss fights with phases**: health thresholds switch ability sets, arenas change (gates open, lava rises via floor swaps, adds pour from monster generators) | M | Bosses the campaign can end acts on |
| **Spirit class, round 2**: Spirit abilities of its own (melee hits charge a Spirit Strike), its own portrait (repaint the Conjurer art), a separate save flag so a Mystic is a Mystic in any exe | M-L | A real fourth-class feel |
| **Encounter director**: the gauntlet's budget-per-arena idea generalised: each map area gets a difficulty budget from the story's pacing curve, spent on the biome's roster plus the new monsters | M | Consistent difficulty across a campaign instead of hand-tuned counts |
| **Smithing as a progression system across maps**: carry the smithing level in an item the player holds (a smith's token that is swapped for a better one), so it survives map changes and saves | S-M | The forge's level is lost on save today |

## 3. Story and campaign

| Idea | Effort | Why |
|---|---|---|
| **Continuity through carried items** (being built for the 10-act campaign): a choice gives the player a token (a key, a gem, a letter); later maps read the inventory to change who greets you, which gate is open, which ally appears | M | Choices that matter across maps without engine changes |
| **Faction reputation**: tokens that stack (three "favours of the Guild") change shop prices and who attacks on sight | M | Replayability |
| **Recurring characters** with a voice (Breeze casting kept per character across maps) and a route between maps | S once the casting store is shared | Coherence |
| **Side-quest chains across 3-4 maps** with partial rewards on each map | M | Keeps the player looking around |
| **Act intros and outros**: the map intro text (MapIntro section) and a scripted camera pan at the start of each act | S | Presentation |

## 4. World building and generation

| Idea | Effort | Why |
|---|---|---|
| **Rivers that run off the map** (the bridge lab shows streams ending in the clearing): carry streams under the forest wall to the map edge, and plan bridges, fords and docks with the roads (already the rule) | S-M | Bridges and rivers read as part of a landscape |
| **Interiors with more than one storey everywhere** using transporters (stairs to an upper floor, cellars) | M | Bigger buildings without bigger footprints, the user's bigger-scale goal |
| **Dungeon generator** (castle dungeons, crypt complexes) using rooms + corridors + transporters + traps, with the room lab's types (cells, torture chamber, ossuary, treasury) | L | The campaign needs dungeons; only caves and towns exist now |
| **Traps and puzzles**: pressure plates, fire jets, rolling boulders, switch-and-gate puzzles, timed doors (all are game objects plus a few script lines) | M | Variety between fights |
| **Weather and time of day** by ambient colour and particle objects per act | S | Mood |
| **A world map page**: an artifact showing every installed map, how they link, each one's status and its ratings | S | One place to see the whole project |

## 5. Process and tooling

| Idea | Effort | Why |
|---|---|---|
| **One command for everything installed**: build, check, compile, server-load, render and report every installed generated map (the sweep done by hand today) | S | The sweep becomes a habit, not an event |
| **An in-game play bot**: the Spirit build can be extended with a test mode that walks the player along a route and fires weapons, so "needs a real playtest" items (W2's throw, W4's fireball swap, the forge plate) can be proved headlessly | L | Closes the largest verification gap: everything that needs a player |
| **Screenshots from the game's own renderer** for QA pictures instead of the editor's render (the Spirit agent already captured the client window) | M | Pictures match what the user sees, lighting included |
| **Keep memory notes current**: the project moved fast (voices, transporters, fences, scene lab); the notes lagged | S | Fewer surprises in a new session |
