# Quests, dialogue and loot in Westwood's single-player maps

Measured 2026-10-04 on the corpus (`corpus/out/nox_corpus.db`, the Con/War/Wiz maps) and on their scripts,
decompiled with noxtools (`noxtools ns decomp <map>`; 107 maps). Used by the story kit (`kit/quests.py`,
`kit/story.py`) and the skill (`skills/nox-story-map`).

## Gold

| | count | p25 | median | p75 | p90 | max |
|---|---|---|---|---|---|---|
| Gold in a container (chest, barrel, coffin) | 817 | 23 | 41 | 80 | 132 | 500 |
| Gold lying on the floor | 223 | 23 | 51 | 100 | 200 | 500 |
| All the gold placed on one map | 107 maps | 113 | 524 | 1096 | | 2570 |

Containers hold few things: 1 item at the median, 4 at p90, 15 at most (917 containers). The commonest contents:
Gold, RewardMarker (a random reward the game rolls), bones, red and blue potions, food, quivers, chakrams, spell
books, field guides, keys.

By container (2026-10-05, the campaign maps; `mapgen/kit/loot.py` has the places and what each holds): chests 1461,
97% hold something (all of them indoors); sacks 77, 88%; Barrel, Barrel2 and BarrelLOTD 1956, 42%; crates 285, 51%;
coffins 407, 41%; large and piled barrels 15%; water, black-powder, steel and tool barrels, steel crates and apple
crates never. Barrels hold food (apples, meat) above all, crates potions, quivers, clothes and cider, coffins bones,
chests gold (43%) and potions. Per map Westwood's containers hold 6 potions at the median (p90 14), 2 arms or armour
(p90 9) and 9 food (p90 26). Chests and sacks are opened; barrels, crates and coffins are smashed and drop it.

## Rewards from quest givers

Westwood's scripts almost never pay quest gold: `ChangeGold` appears 18 times, nearly all negative (the player
pays: a contest's fee, a bribe, a toll). Quest rewards are experience (`GiveXp`: 100 the commonest, 50, 250, 500,
up to 1000) and items handed over or left in a chest. OpenNox alpha13 leaves `GiveXp` unimplemented, so the kit
pays in gold and items instead: keep a map's total gold, chests and rewards together, within Westwood's range,
about 500 to 1500, and give items (armour, a weapon, potions) as the main reward.

## Dialogue

- 68 of the 107 maps tell stories (`TellStory`): 854 calls.
- Dialogue types set (`SetDialog`): NORMAL 641, NEXT 74 (a page with "next"), YESNO 56 (a question). Questions are
  rare: one or two per map, at the quest's turning points.
- Every talker gets a portrait (`StoryPic`): MaidenPic, MaidenPic2/3, Townsman2-4Pic, MalePic1-9, Warrior2/3Pic,
  TheogrinPic, AldwynPic, HorvathPic, GalavaPriestPic, UndertakerPic, WardenPic, IxGuard2Pic, AirshipCaptainPic...
- Journal entries (`JournalEntry`): 99, a few per map, when a quest starts, turns and ends.
- Westwood passes sound 0 to TellStory (the decompiler names it SwordsmanHurt); the voice comes from the string
  table entry's own wave file (Dialog\<wave>.wav). Voiced: 965 of the campaign's 1391 strings, every talk line, shop
  greeting and refusal (War05A's FarmerHuffy, a second TellStory after "no"); never signs, journal entries, hints or
  mission banners. Speech runs 2.5-3.3 words a second (p25-p75 of 399 lines). Ours are voiced the same way by
  `mapgen/voice.py` (PROCESS.md "Voices").

## Quest patterns (measured 2026-10-05 on the campaign's text and scripts)

The text of every pattern follows `rules/DIALOGUE.md`. The story lab (`review/storylab/`, `py tests/storylab.py`)
scores generated quests against these campaign examples.

### The side quest: five lines and a journal entry

Westwood's side quest is the same five beats in every chapter (Brin's farmer, maiden and frog in War05A/Con05A/Wiz05A;
Ix's bridge guard; the hermit of Con03A; Galava's innkeeper and warden):

| beat | the giver says | the script does |
|---|---|---|
| offer | the trouble, where, the ask, the reward; ends in a yes/no question | YESNO dialog; on yes `JournalEntry(objective, QUEST)` |
| refusal | one sulk ("Fine then, don't return my magical staff!") | nothing; the offer is asked again next time |
| reminder | the ask again, urgent, one sentence | (while the quest is open) |
| completion | delight, thanks, the reward handed over | `JournalEdit(objective, COMPLETED)`, `GiveXp`, the reward items given |
| afterwards | "Thanks again, brave Adventurer!" | |

A quest uses 4-6 of its giver's lines and one journal entry (two with a NOTE or a HINT). The items and the person the
quest needs stand where the offer says ("in my house northwest of here", "near the docks").

With the kit: `q.errand(...)` (`kit/quests.py`) lays out the five beats, the journal entry and the done entry.

### Shapes and how often (the campaign's 82 journal objectives)

| shape | entries | examples |
|---|---|---|
| go to, find, speak to (a place, a person) | 30 | "Find Aldwyn's cottage in the Village of Ix." "Speak to one of the Priests within the Temple of Ix." |
| fetch (an heirloom, a stolen thing, an artifact) | 18 | the farmer's staff, Matilda's cloak, the hermit's spectacles, the bridge guard's boots, the Mayor's scepter, Stravas' amulet |
| fight, clear, charm, survive | 13 | the spiders in the Mayor's study, the orchard's Urchin, the Gauntlet, the Necromancer who took the Halberd |
| rescue, escort | 11 | Gearhart under Dün Mir, the women of Brin (three groups, counted), Lewis the frog from the burning house, the six mine workers |
| other (notes, a fate discovered) | 10 | "Discover the fate of Horvath's apprentice." |

A chapter map has one main quest and 2-4 side quests; Brin (War05A) has four side quests on one map, Ix (Con02a) three
(the spiders, the boots, the archery contest).

### Choice points

- **Yes or no** on an offer (56 YESNO dialogs): no gets a sulk and the offer stands.
- **Pay or not**: an entrance fee (the archery contest, 20 gold), a teacher's fee (Aldwyn, 30 gold for Charm), a
  merchant (the con man's bow at 100 against the shop's; Henrick's charmed wolves, 200 each), a joke offer (Max's
  inn for 50,000). Not enough gold has its own line: "Come back when you have 100 gold."
- **Dead or alive**: Galava's warden pays 500 gold for Morgan Lightfingers alive, 250 dead, with a line for each.
- **Two givers on one goal**: Morgan wants out of jail and his smuggler friend wants him out, each with a reward (a
  key to the Tower; an enchanted shield). Westwood's choices are mostly yes/no and how, rarely whom to betray.

### Rewards against effort

| effort | experience (GiveXp) | what the giver hands over |
|---|---|---|
| an errand, a word passed on | 25-100 | nothing, or a key |
| a side quest (fetch, clear a den, a rescue) | 250 (Brin's four quests all 250) | potions, a scroll, a spell ("Here's the Spell, as promised."), a shield, 50-100 gold |
| a bounty | 150-500 | 100 gold (Max), 250 or 500 gold (the warden) |
| a chapter's main quest | 500-1500 | gold, the way on, a named weapon or armour |

OpenNox alpha13 has no GiveXp: pay in items first and gold within the map's budget (above).

### How the journal tracks a quest

One entry when the quest is taken (QUEST), worded as the order; the same entry greyed when done (COMPLETED); a NOTE
for news the player overhears; HINTs for how to play. 99 JournalEntry calls and 71 JournalEdit (done) across the
campaign: about 3 entries a map. A counted goal says its count ("Rescue the 6 trapped mine workers.") and the screen
counts down ("You have rescued the Third mine worker! Three more to go.").
