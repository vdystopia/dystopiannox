# Overnight 2026-10-04 to 05: story maps

The brief: a large map with a theme and a mission, a start, challenges, rewards, missions, fights and an exit; a
finished product with a story and quests; NPCs who all have a purpose; custom dialogue (text, no audio); chests with
loot; shops that buy and sell. The loop: create, audit, fix, repeat.

## What is installed and ready to play

A campaign of six linked maps, each exit putting you at the next map's start:

1. **Thornwick**: chapter one, a forest market town at a ford.
2. **TNorth**: the King's Road north of Thornwick, a waystation.
3. **Rimehold**: chapter two, a snow outpost under the Rime Pass.
4. **RimePass**: the far side of the pass, where the road drops toward the volcanic country.
5. **Emberhol** (Emberhollow): chapter three, a volcanic caldera town. Built by a fresh agent following the
   skill alone (see below).
6. **AshRoad**: the road out of the caldera; it closes chapter three.

How to play: start a Solo game, press F1, type `racoiaws`, then `load thornwick`. The exits carry you on. Any chapter
can also be started directly: `load rimehold`, `load emberhol`.

### Thornwick: the Red Hand

- **Start:** the King's Road from the south. Tobin the carter sits by his plundered wagon; the Red Hand robbed him.
- **The ambush:** four Red Hand lookouts sit round their fire with Tobin's stolen crates in a secluded grove off the
  road. When you pass the bend they come out of the trees. Tobin pays you for them.
- **Main quest:** Reeve Aldric (in his hall, the big stone manor) has barred the north gate until the Red Hand is
  broken. Their camp is in the old pines north-west, past the graveyard; Garrick the Red leads them (a sentry archer
  rouses the camp). Garrick dead, Aldric pays 300 gold and opens the gate. The road north is the exit.
- **The Varn Emerald:** Mirela at the Lantern (the inn) gives you a copy of Father Odo's key to the Varn crypt
  behind the chapel. The restless dead are inside (skeletons, ghosts, a skeleton lord) and the emerald is in the
  family's chest. Choose: Mirela pays 300 gold; Father Odo lays the dead to rest and blesses you.
- **Wolves at the Mill:** Hobb the miller pays for the wolf pack denned up the east path.
- **The Brannoc Greatsword:** old Brannoc, outside the forge, lost his grandfather's sword at the old watchtower in
  the north-east wood. An ogre warlord holds the ruin now. The sword earns you a breastplate.
- **Shops:** the general store, the inn and the smithy (weapons and armour) buy and sell.
- **Everyone talks:** eight townsfolk each have a rumour that points at a quest; the watch patrols the square;
  the gate guards, Pell the farmer.
- **Loot:** the bandits' chests, the crypt's grave goods, the tower's chest, three caches hidden in the woods.
- **The land:** the stream the town is named for, a rope bridge, the Pell farm, rock piles, the graveyard.

### Rimehold: the dark shrine

- **Start:** the road up from TNorth.
- **Main quest:** the shrine of standing stones on the frozen lake kept the pass warm; the ogres of the old keep
  stole its heartstone and the flame died. Warden Hrolf has sealed the pass gate. Kill Skarg in the keep, carry the
  heartstone into the ring of stones: the flame returns, the gate opens, the pass is the exit.
- **The lake troll** rises from the snow by the shrine the first time you walk out to it.
- **The Lost Trapper:** Inga's husband Oskar went into the ice cave (now in its own dim light) and never came back.
  His bones lie among the spiders with his crossbow and a note. Bring the crossbow home.
- **The Great Bear:** Torvald of the hunters' lodge pays for the bear of the west pines.
- **Shops:** the trading post and the Frozen Kettle inn. Seven townsfolk with rumours.

### Emberhollow: the three vents (chapter three)

- **Start:** down from the Rime Pass into a smoking caldera. Tamsin the ash-runner, at the milestone, points the way
  and warns of imps; a nest of fire imps beside the road swarms whoever passes.
- **Main quest:** demons from the forge capped the mountain's three vents, and Warden Kael has shut the Cinder Gate.
  Open the vents in any order: one in the western ashfield (imps, an ember demon), one on the crater lake's rim
  (demons), one before the demon forge (its garrison). A vent opens once its keepers are dead. All three open: the
  gate unlocks and the road out is the exit.
- **Rescue:** Brin is trapped at the obsidian diggings, ringed by scorpions; clear them and he walks home to his
  sister Maren, who pays.
- **A choice:** the Ember Eye in the ash cult's ruined temple (an undead high priest and his acolytes): Sister Ilsa
  breaks it and blesses you, or Corvin at the inn buys it.
- Three shops (smithy, trading post, inn), caches, six townsfolk with rumours.

### Mirefen: the drowned chapel (chapter five, the new swamp palette)

- A swamp palette measured on Westwood's swamps (swamp grass and weeds, shallow water with deep hearts, root walls,
  two-part swamp trees, polyps, frogs and flies, carnivorous plants, leeches, wasps, wisps), tried on a lab map until
  every measure sat in Westwood's swamp ranges.
- **Main quest:** the necromancer Morvane holds the old chapel, sunk in black water in the east fen, and raises the
  drowned; Elder Haska keeps the north causeway shut until he dies.
- **The Lost Boy:** Tam hides between the wasp nests in the west reeds; kill the wasps and he runs home to his father.
- **The Great Leech** of the deep pool, for Brask the eel-catcher. Two shops, five townsfolk with rumours.
- Its exit leads home to Thornwick.

## The skill, tested

The first draft of the phase 6 skill (`skills/nox-story-map/SKILL.md`) was handed to a fresh agent that knew
nothing of tonight's work. Following the skill and the two example maps, it built Emberhollow: a new biome and new
quest shapes, 0 errors, loaded in the server with all 40 story objects found. Its list of what was unclear or
missing became tonight's last round of kit fixes: a checker rule that proves a story gate seals the exit, a
`when_true` event, counted objectives, a building-style override, biome floors buffered as Westwood buffers them,
creatures only where the player can walk, nothing planted inside buildings. Seeds that failed with up to 10 errors
now build clean. The skill now says what the agent had to work out alone.

Balance: Westwood's maps hold about 500 gold in all (median; at most 2,570), a chest about 40, and quest givers
reward with experience and items, almost never gold (`rules/QUESTS.md`). The maps' rewards were trimmed toward that,
with items as the main reward.

## How it works (new tonight)

- **Custom text without audio.** OpenNox reads `nox.csf.json` in place of the game's string table when it exists.
  `mapgen/strings.py` writes it: all of nox.csf plus each installed map's own lines. Dialogue, journal entries,
  signs and shop greetings all use it. To go back to stock: `py mapgen/strings.py --remove`.
- **The quest kit** (`kit/quests.py`, `kit/behaviours/quests.go`): NPCs whose lines depend on quest stages and what
  you carry, yes/no questions, actions (gold, items, journal, unlock, open the exit, set creatures hunting), events
  on deaths, places and pickups. Deaths and items are read from the world, so a loaded save cannot strand a quest.
  Quest givers are immortal.
- **Chests hold loot**, armour can be placed, doors lock to keys or to scripts, exits put you at the next map's start.
- **`kit/story.py`**: the steps every story map shares; **`kit/camps.py`**: bandit camps, a wagon wreck, a wolf den,
  a ruined tower, caches, signposts.
- **Checks:** every map compiles its scripts against the game's NoxScript, loads in the OpenNox server, and its
  self-checks find every creature, waypoint and story object; the checker proves each story gate seals its exit.
  `py tests/campaign.py` does all of it for the whole chain. `review/storymap.py` draws the labelled overviews.
- **The skill:** `skills/nox-story-map/SKILL.md`, the first draft of phase 6.

## Your four points from yesterday

1. Storeroom racks: at most 5 to a row, a step apart, wide aisles.
2. A wall with one bookcase is filled with bookcases; shelves fit tight into corners.
3. Great halls: fewer table sets, on a big floor-tile carpet.
4. Outdoors: rock piles in Westwood's manner; few aspens right against the boundary.

## Things to know

- The quest state lives in the script: a saved game that is reloaded restarts the scripts. Deaths and carried items
  are read from the world, so quests continue, but a reward might be offered twice.
- Untested in the client (the server cannot talk to NPCs): dialogue windows, portraits, the journal, the shrine flame
  appearing. Please tell me if a conversation does not open or shows a key instead of text.
- OpenNox leaves some script calls unimplemented in this version (quest status, custom-string journal and
  dialogue); the kit avoids them.
