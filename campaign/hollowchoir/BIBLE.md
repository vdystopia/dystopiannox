# The Hollow Choir: campaign bible

A ten-act Nox single-player campaign built with the dystopiannox kit (2026-10-09, the user: "a full build of a
comprehensive nox campaign. 10 acts (maps) with one overarching coherent story and some side quests that persist
through several of the maps. Add continuity so that choices in one map carry over to the next. Use everything that we've
built so far. Including some of the new resources, like new monsters and weapons.").

Every act is one map, built by `skills/nox-story-map/SKILL.md`, with the shared cast, tokens and chain in
`mapgen/kit/campaign.py`. This file is the story every act's builder works from: never contradict it; where it is
silent, invent within it.

## The story in one paragraph

Long ago the realm's founders cast **five bells** and hung them in five shrines across the land. Rung together at the
turning of each year, their peal keeps the **Ember Brood**, a swarm of fire-demons and their mother, the **Ember
Matriarch**, asleep beneath the world. Each bell's clapper is a **Spirit Stone**, and without its stone a bell is
dumb. A cult called **the Hollow Choir**, led by the **High Caller Morvaine**, has begun stealing the stones: they
believe that when the bells fall silent the Matriarch will rise, burn the world clean and remake it with the Choir
as her voice. The player is a sellsword who steps off a river barge at **Brackwater** on the night the Choir's hired
bandits rob its bell shrine. Following the stolen stones across swamp, mine, glacier, castle, ogre land, barrow and
volcano to Morvaine's spire, the player wins back the stones and returns to Brackwater as the Brood breaks loose,
to ring the bells again or fall with the town.

## The cast (recurring; `campaign.CAST`)

| Name | Who | Acts | Notes |
|---|---|---|---|
| **Captain Ilsa Rook** | captain of the Brackwater watch; dry, tired, honest | 1, 5, 9, 10 | hires the player; trusts the player more if the bandit Rusk is handed to her |
| **Doran Ashforge** | Brackwater's old smith | 1, 3 (by letter), 8, 10 | side quest *The Starsteel Blade* |
| **Wenna Fell** | Brackwater's herbalist | 1, 2 (by note), 5, 10 | side quest *The Missing Brother*: her brother Tam |
| **Tam Fell** | Wenna's brother, a bell-ringer's apprentice the Choir took to read the bells' old script | 5 (rescued), 10 | |
| **Rusk** | a bandit lieutenant hired by the Choir; a coward with a conscience | 1 (captured), 6, 9 | the act-1 choice: free him or hand him over |
| **Brother Edric** | the last keeper of the bells' lore, at Brackwater's shrine | 1, 7, 10 | side quest *The Last Verse* |
| **Vess** | the Choir's assassin, a duelist who steps through space (the Blink Duelist, M5) | 4 (duel), 9 | the act-4 choice: spare her or kill her |
| **High Caller Morvaine** | the Choir's leader; a necromancer who sings the dead up (Bone Caller abilities, M3, as a boss) | named in 2-8, faced in 9 | |
| **Gruthak, the Ogre Lord** | warlord of the Marches (the Ogre Lord, M1) | 6 | paid by the Choir with a stolen stone |
| **The Ember Matriarch** | the mother of the Brood (M4, as a boss) | stirs in 8, rises in 10 | |
| **The Baron Aldric Thorne** and his **chancellor Severin** | lord of Thornkeep; Severin is the Choir's man at court | 5 | Severin is unmasked (A.turn) |

## The acts (`campaign.ACTS`)

| Act | Map | Setting | Main quest | New resources |
|---|---|---|---|---|
| 1 | **Brackwatr** - Brackwater | a river town: docks, bridges, the bell shrine on the square | the shrine robbed in the night; track the bandits to their camp on the riverbank; capture Rusk; **choice A** | the forge (S1) at Doran's smithy; side quests begin |
| 2 | **Mirewood** - the Mirewood | swamp | follow the Choir to its ritual circle; kill the Bone Caller who sings there (M3); find the Choir's map pointing to Greycrag; **choice B** (the reliquary) | M3, swamp creatures |
| 3 | **Greycrag** - the Greycrag mines | cave town with a deep lift (transporters) | the Choir is digging for the second bell, sunk in the flooded deep; reach it first and take its stone into safe keeping | M2 Giant Crabs in the flooded deep; lifts; starsteel ore |
| 4 | **Frosthol** - Frosthollow | snow village under a glacier shrine | the third bell's keeper is murdered; climb to the shrine; duel Vess (M5); **choice C** | M5 boss duel |
| 5 | **Thornkeep** - Thornkeep | castle town (`Curtain`) | ask the Baron's help; find who at court serves the Choir (Severin); rescue Tam from the dungeon; learn of the Spire and the Emberforge | the act-1 choice opens the front gate or a sewer passage (transporters) |
| 6 | **OgreMarch** - the Ogre Marches | forest and ogre lands | the road east is held by Gruthak, paid with the fourth stone; win it back | M1 Ogre Lord boss; Rusk's parley if he was freed |
| 7 | **AshBarrow** - the Ashen Barrow | crypts of the Land of the Dead culture | the bells were cast here; the fifth stone lies with the founders; the Choir's dead hold the barrow | M3 Bone Callers; the reliquary's effect |
| 8 | **Emberforg** - the Emberforge | lava, the founders' forge | the Choir gathers its stones at the forge to wake the Matriarch; break the ritual; Morvaine escapes to his spire with what he holds | M4 Ember Matriarch stirring (a lesser rising); the forge finishes *The Starsteel Blade* |
| 9 | **HollowSpr** - the Hollow Spire | Morvaine's tower: floors joined by stairs and lifts | climb the spire, defeat Morvaine, take back the stones | M3 Morvaine as boss; M5 Vess (foe or ally by choice C); allies by choice A |
| 10 | **LastBell** - The Last Bell | Brackwater again, burning: the Brood has broken out under the town | reach the bell shrine through the burning town, set the stones and ring the bells, then face the Ember Matriarch | M4 boss; every side quest pays off; endings by tokens |

Each act's exit leads to the next (`sm.exit_to`), behind a gate the act's main quest opens. Act 10 ends the campaign
with a closing sign and the shrine's peal.

## Choices and side quests that cross maps (continuity)

The game keeps the player's inventory from map to map (and in saved games) but forgets script variables, so every
choice and every side quest's progress is an **item the player carries**: a **token** (`campaign.TOKENS`). A later
act reads it with a condition (`q.when(has=TOKEN)`), and a token is given (`A.give`) or taken (`A.take`) by the story.
Tokens are items the player cannot use up or sell by accident; the dialogue always says what the item *is* in the
story ("Take this blue orb: it is the watch's seal"). Every act gives the player what a later act reads, and every act
that reads a token still works without it (a different line, a different way, never a dead end).

### Choice A: Rusk (act 1)
In act 1 the player captures Rusk at the bandit camp. Rusk begs to be let go; Ilsa wants him in a cell.
- **Hand him to Ilsa** -> token **WATCH_SEAL** (Ilsa's seal of the watch). Act 5: the Thornkeep gate guards honour the
  seal (the front gate opens). Act 9: Ilsa and two watchmen wait at the spire's foot and fight beside the player.
  Act 10: Ilsa holds the square.
- **Free him** -> token **RUSK_KNIFE** (Rusk's knife, his promise). Act 5: no seal: the player gets into Thornkeep by
  the sewer passage. Act 6: Rusk waits at the Marches and brokers a parley: Gruthak will duel the player alone instead
  of with his whole warband. Act 9: Rusk's crew holds the spire's lower floor. Act 10: Rusk's crew fights in the
  square.

### Choice B: the reliquary (act 2)
The Bone Caller in the Mirewood sings from a bone reliquary that whispers to whoever holds it.
- **Smash it** at the ritual circle -> nothing carried; the Mirewood's dead fall quiet.
- **Keep it** -> token **RELIQUARY**. Act 7: the barrow's dead take the player for one of the Choir: its outer
  wardens do not attack (the inner crypt still does). Act 10: the Matriarch calls to the reliquary: the player must
  give it up to Brother Edric before the last fight, or it summons an extra wave of imps.

### Choice C: Vess (act 4)
Beaten in her duel at the glacier shrine, Vess yields.
- **Spare her** -> token **VESS_OATH** (her silver token). Act 9: Vess turns on Morvaine and fights beside the player.
- **Kill her** -> she drops her blade: the **Bloodthirst** (power weapon W5). Act 9: no Vess.

### Side quest: The Starsteel Blade (Doran; acts 1, 3, 8, 10)
1. Act 1: Doran asks the player to bring starsteel, which only the deep mines hold; he gives **DORAN_LETTER**.
2. Act 3: the starsteel lies in the flooded deep among the crabs: **STARSTEEL**. Doran's cousin at the Greycrag forge
   reads the letter and says only the founders' forge can work it.
3. Act 8: at the Emberforge's anvil, with the letter and the starsteel, the player forges the **Flamebrand at
   masterwork** (W1, tier 3); the forge takes STARSTEEL.
4. Act 10: Doran sees the blade and gives the player his own hammer, the **Quake Hammer** (W3) at its best tier.

### Side quest: The Missing Brother (Wenna; acts 1, 2, 5, 10)
1. Act 1: Wenna's brother Tam went to the shrine the night of the robbery and never came home; token **WENNA_ASK**.
2. Act 2: in the Choir's swamp camp the player finds Tam's satchel and a Choir order to take "the ringer's boy" to
   Thornkeep: **TAM_SATCHEL**.
3. Act 5: with the satchel, the player knows to search Thornkeep's dungeon; Tam is freed: **TAM_FREED** (the
   satchel is given back to Tam). Without it, a guard's rumour still leads there, later.
4. Act 10: Tam reads the bells' old script for Brother Edric (with the Last Verse, below); Wenna's potions wait at the
   shrine.

### Side quest: The Last Verse (Brother Edric; acts 1, 3, 4, 7, 10)
The bells' founders carved the words of the ringing on stone tablets in three places.
1. Act 1: Edric asks the player to bring the verses: **EDRIC_ASK**.
2. Act 3, 4 and 7: a tablet in each (the deep bell chamber, the glacier shrine, the founders' crypt) gives a
   **VERSE_STONE** each (the same type: the count matters, 0-3).
3. Act 10: with all three verses (or two, and Tam to read the third), Edric rings the bells true: the Brood is cut
   off and the Matriarch fights alone (no extra waves). With fewer, the fight is harder.

### The stones
The Spirit Stones themselves are tokens too: **SPIRIT_STONE** (one type, counted). Act 3: 1 (the second bell's, kept
safe). Act 6: +1 (won back from Gruthak). Act 7: +1 (the fifth, from the founders' crypt). Act 9: +2 (from Morvaine:
the first and the third, the ones the Choir stole in acts 1 and 4). Act 10 needs five: the player sets them in the
shrine. A player who arrives with fewer (impossible on the main path) is told where they were lost.

## Endings (act 10)
The bells ring and the Matriarch falls in every ending; what survives depends on the tokens:
- **WATCH_SEAL**: Ilsa and the watch hold the square; she offers the player a captain's place.
- **RUSK_KNIFE**: Rusk's crew holds the river gate; Rusk turns honest (or says he will).
- **TAM_FREED**: Tam and Wenna together at the shrine; Tam reads the third verse.
- **VESS_OATH**: Vess appears on the shrine roof at the end and is gone again.
- **RELIQUARY** given up: Edric breaks it on the bell; kept: an extra wave, and Edric's last line is a warning.
- **VERSE_STONE x3**: the Brood is cut off at the first peal.
A closing sign in the shrine sums up the player's road.

## Tone and craft
- Westwood's register (rules/DIALOGUE.md): short lines, plain words, no modern idiom, a little dry humour; the
  player is never addressed by class. Every act's lines are written from Westwood frames (`tests/storylab.py frames`).
- Each act: a hook at the start, the main quest gating the exit, one or two local side quests of its own as well as
  the cross-map ones, fights with a reason, shops in the towns (acts 1, 3, 4, 5, 10), loot within budget.
- Use the new resources where the story puts them; the gauntlets' armoury is *not* copied into the campaign: power
  weapons are rewards, found or earned (W1-W6 spread across the acts: W2 Chakram Storm in act 6 from Gruthak's hoard,
  W4 Stormcaller in act 7 for casters, W6 Frostbite in act 4, W5 Bloodthirst from Vess, W1 and W3 from the Starsteel
  quest), and the new monsters are the Choir's champions and the bosses.
- Scale: bigger than Westwood's (the user's standing rule), but each act about Thornwick's size or smaller: ten acts.
