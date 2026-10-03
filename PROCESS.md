# How a map is made

This is the repeatable process, the basis of the phase 6 skill. Each step names its tools. Order
matters: work from the centre outwards and from identity to detail.

## 1. Identity: what the place is

Write a `MapIdentity` (`mapgen/kit/identity.py`) before anything is built:

- **Theme**: one sentence on what this place is and what happens there ("a logging and milling village in a deep forest vale…").
- **Environment type**: town, forest, swamp, cave, dungeon, castle, ice or lava (`rules/environments.py`). Statistics are only ever compared with Westwood's maps of the same type.
- **Areas**: each with its purpose (the village heart, the miller's glade, the woodcutter's clearing…) and landmark.
- **Buildings**: each with a role (inn, store, smithy, home, cottage, mill, woodcutter), a name and an occupant. A role fixes:
  - the room program (an inn is a tavern, a kitchen and the innkeeper's bedroom);
  - the wall style and minimum size;
  - whether it faces the square or the road;
  - the outdoor scenes that show the trade (deliveries at the inn, a woodpile at the woodcutter's).
- **Rooms**: each kind has an identity (`ROOMS`): what it is for, what it must contain, what it may contain, and the allowed object types (a bedroom's storage is a chest, never a barrel). Nothing else goes in.
- **Outdoor scenes** (`SCENES`): every prop group has a reason and a place (beside the door, against a side wall, in front).

## 2. The centre first

Place the central feature at the heart of the main area: the village square and its landmark (a
well). Then lay out the streets leaving it toward the other areas.

## 3. Buildings, from the centre outwards

1. Public buildings face the square across a clear margin.
2. Homes line the streets, entrances facing them.
3. The outlying areas get their own features: the mill house and pond, the woodcutter's hut and stumps, the standing stone.

Rooms are sized by kind (a tavern takes most of an inn's floor) and furnished only from their identity.

## 4. Plan the water with room for its banks

Reserve the stream's and pond's bands before anything is built, keeping roads clear of them except
at crossings. Every transition (road to grass, grass to bank, bank to water) needs room for its own
blend. Westwood's town roads almost never run within two tiles of water.

## 5. The land grows around what was placed

Only now draw the map's shape (`Land.carve`): a margin of open ground with an irregular edge around
the square, buildings, roads, water and features, plus the clearings, ending in the forest wall.
Never start from the borders and fit the village into what's left.

## 6. Ground, water, life

1. Dig the water into the land, with a bridge where the road crosses.
2. Grass variety patches, kept clear of roads, banks and buildings.
3. Scenes, gardens, benches, street lights.
4. Vegetation from the forest edge inward: tree lines, groves outside settled areas, undergrowth and flowers in single-type patches.

## 7. Check, review, playtest

- `validate/validate.py`: errors must be zero. Warnings compare with Westwood's maps of the same environment, including furniture outside a room's identity.
- `review/review.py`: comparison sheet and design measurements (paths, vegetation structure, roads crowding water…). Apply `review/RUBRIC.md`, including criterion 8 (identity), and record the review in `review/reviews/`.
- Playtest in the game; log the findings in `ROADMAP.md`.
