# Cultures: how Westwood furnishes its ogre lairs, the Land of the Dead and Dun Mir

`py rules/cultures.py` measures the rooms of Westwood's single-player maps (each layout once) that belong to a culture: a
room belongs when at least two of its pieces carry the culture's prefix (LOTD, Ogre, DunMir). For each culture it writes
the rooms' size, walls and floors, and for each object type the share of rooms holding it, its count per 100 floor
tiles where present, and where it stands: against the NE and NW walls (the back walls the camera sees), against the SE
and SW walls, or free in the room. Output: `rules/out/cultures.json`.

## Land of the Dead (47 rooms in 8 maps, median 45 tiles)

- **Walls:** LOTDBrick 0.37, LOTDOrnate 0.17, BrickBlue 0.13, IronFence 0.09.
- **Floors:** LOTDPitted 0.24, TileDark 0.18, LOTDBlackMarble 0.18, LOTDDark2 0.09, DungeonStoneDark 0.09.
- **On the back walls:** wall sconces (LOTDWallSconse1/2 in 30-40% of rooms, 88-94% against the back walls),
  candelabras (100% back), tapestries (100% back).
- **At the walls:** mana obelisks (26% of rooms, 7 per 100 tiles; 59% back, 41% front).
- **Free on the floor:** bones and skulls (ArmBoneImmobile in 40% of rooms at 10 per 100 tiles, SkullImmobile 34% at
  8), tombstones (half free, half at the back), incense basins (all free).
- Rarer set pieces: judgement balances, the lich god's statues, arks, lich thrones (with their base and shadow parts).

## Ogres (18 rooms in 7 maps, median 42 tiles)

- **Walls:** DungeonStone 0.37, OgreCage 0.25, OgreWall 0.18.
- **Floors:** GreenBrick 0.43, SwampGrass 0.33, DirtDark2 0.08.
- **Free on the floor:** straw heaps (OgreStraw1 in 72% of rooms at 8.6 per 100 tiles, and its four siblings: 95-100%
  free), stools, crude round tables, meat and carcasses (OgreHutMeat 15 per 100 tiles where present).
- **At the walls:** crude beds (OgreBed1: 100% back), barrels, torch poles, spider webs (100% back).
- The ogres' hearth is a fire pit (OgreFirePit: a real fire, it burns) with stools round it.

## Dun Mir (54 rooms in 17 maps, median 89 tiles)

- **Walls:** DunMirCathedral 0.52, then dungeon stone and Galava's walls.
- **Floors:** DunMirBrick1 0.24, GreenBrick 0.09, RugRed 0.08 (carpets), TileRed 0.05.
- **On the back walls:** Dun Mir chests (DunMirChest4 in 48% of rooms, 86% back; DunMirChest3 100% back), wall torches
  (DunMirTorchNorth/East on the back walls), hanging shields and swords, bookcases, desks.

## How the kit uses it

- Room recipes (`mapgen/kit/identity.py` ROOMS): `ogre_den`, `ogre_hall` and `ogre_hoard`; `dark_chapel` and
  `dark_crypt`. Each names its culture's pieces (`prefer`) and its own lights (`lights`: sconces for the Land of the
  Dead, torch poles for ogres).
- The furnisher (`mapgen/kit/furnish.py`): a `scatter` slot strews straw, meat and bones over the floor in small heaps;
  groups for an ogre's fire pit ringed by stools, its crude tables, and the judgement balances in pairs; rows of
  tombstones and a colonnade of mana obelisks (`rack_rows` kinds `lotd_tombs`, `obelisks`); each culture's own
  hangings (`CULTURE_DECOR`).
- Families (`rules/room_types.py`): an ogre's fire pit counts as a hearth; mana obelisks, judgement balances and arks
  stand like statues.
- Buildings (`BUILDINGS`): the demon forge (`dunmir_hall`, furnished as Dun Mir), the ice temple (`lotd_ornate`, Land
  of the Dead) and the ogre keep (`dungeon_block`, ogres). The biome maps place them (`kit/biome.py`
  `Dresser.structure`), furnish them and set their keepers on guard (`Dresser.garrison`).
