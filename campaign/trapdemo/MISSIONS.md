# TrapDemo missions

Ten self-contained mission maps, TrapDem01..10 (labels TD-01..10), each a finished medium map round its traps: a
camp at the way in with the person who gives the mission, rooms with a purpose furnished by the room kit, trap
passages between them (kit/trapkit, every kind across the set), monsters that use the traps, a BossLab boss
(approved by the user for any map, 2026-10-23), a main quest and a side quest (kit/quests.py). Built with
`kit/trapdemo.py` Mission; the template is `mapgen/designs/trapdemo01.py`. Each map has its own boss.

Shape of every mission (rules/TRAPS.md T1-T9): the first trap passage is a standard one near the camp (taught where
a mistake is cheap); the side quest's room hangs off the main line behind a trap of its own; the hard passages come
after the middle; monsters guard rooms between traps from the second room on, more toward the boss; the boss's hall
lies before the vault with the main quest's item; the giver pays on the way back. 7-10 rooms, 5-7 trap passages,
two or three plain corridors. Dialogue by rules/DIALOGUE.md (short, plain, Westwood's register; journal entries are
orders; a yes/no offer, a refusal line, a reminder, the thanks with the reward).

| Map | Title | Setting | Boss | Giver (donor map, script; portrait) | Main quest | Side quest | Trap emphasis |
|---|---|---|---|---|---|---|---|
| TrapDem01 | The Reliquary of Saint Varo | crypt | B4 Lord Mortivane, necromancer | Brother Aldous (Wiz02A TowerNPC; ArchivistPic) | bring the saint's reliquary up from the sanctum | Pell's satchel in the ossuary's store | spike, flame (built) |
| TrapDem02 | The Cinder Foundry | forge | B9 Ignis Varr, pyromancer | Foundry-master Hask (Con02a Bryan; QuarterMasterPic) | shut the runaway forge: the quench lever in the furnace hall, then Ignis Varr, and bring back the Master's Hammer | the guild ledger in the cold store | flame, block (presses), push |
| TrapDem03 | The Serpent Steps | temple | B6 Garet Hawkeye, ranger (a rival relic hunter) | Nala the scout (Con07B Shari; MaidenPic6) | the jade idol from the inner shrine | her lost brother's map case in a side vault | arrow, spike, pit, trigger |
| TrapDem04 | The Collapsed Seam | mine | B3 Oskar Thorne, the Golemwright | Foreman Brannoc (Con03A Rastur; MalePic9) | reach the deep seam, break the golemwright's hold, bring back the seam's heartstone | a trapped miner's lamp (he did not make it) | pit, crumbling floor, push, block |
| TrapDem05 | The Vault of Night | lotd | B1 Vael the Unbound, archmage | Ingrid the lich-hunter (War01A Evelyn; IngridPic) | the Night Orb from the vault beneath the beams | a hunter's silver key in the ossuary | sentry, spell, blade |
| TrapDem06 | Thornhold Keep | castle | B10 High Warden Aurelian, a warden gone mad | Castellan Theodric (Con02a Mayor_Theogrin; TheogrinPic) | the keep's seal from the warden's chapel | the armoury's key in the gatehouse cellar | arrow, trigger, block, sentry |
| TrapDem07 | The Quiet Catacombs | crypt | B5 Silas Vane, the Quiet Knife | Widow Maren (Con02a Gretchen; MaidenPic4) | her husband's signet from the assassin's lair | a candle of remembrance from the old chapel | spike, blade, pit, spell |
| TrapDem08 | The Storm Anvil | forge | B7 Dravik Stormblade | Smith's lad Dudley (Con03B Dudley; WoundedApprenticePic) | the storm anvil's heart from Dravik's forge-hall | his master's tongs in the slag store | flame, push, block, blade |
| TrapDem09 | The Sunken Sanctum | temple | B8 Kesh of the Red Sands | Father Morgan (Con02a Morgan; MorganPic) | the sun disk from the drowned sanctum | an acolyte's prayer book in the cistern | arrow, sentry, pit, trigger |
| TrapDem10 | The Warlord's Trial | castle | B2 Sir Garrick the Verdant | Herald Evelyn (War01A Evelyn; IngridPic) | run Garrick's trial hall by hall and defeat him in the arena | the champion's banner in the trophy hall | every kind |

Item types for quest items (check each with `py review/catalog.py <name>`): MayorsScepter, TreasureBag,
RedOrbKeyOfTheLich, BlueOrbKeyOfTheLich, GreenOrb, RedOrb, BlueOrb, AmuletOfClarity, AmuletofCombat, Spectacles,
SponsorshipLetter, SilverKey, GoldKey, RubyKey.
