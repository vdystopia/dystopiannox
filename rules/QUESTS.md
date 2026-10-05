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
  table entry's own wave file. Our lines have none, so they are silent.
