# Rooms and buildings

Source: `rules/rooms.py` over the 120 single-player maps (campaign + quest); statistics weighted by
`1 / layout group size` so a layout shared by the three class campaigns counts once. Quartiles are
[25%, median, 75%].

Method: flood-fill every non-wall cell (diagonal wall chains block 4-connectivity); door gaps are
closed with a virtual wall. A room is an enclosed component with 2-400 floor tiles. It is a
**building** room when at least 60% of its solid walls are built materials, else **natural** (cave
pockets, tree-ringed clearings). Rooms sharing a wall cell or a door form one building. Door gap cells
use the verified rule (South: corner-(1,1); North: corner; East: corner-(1,0); West: corner-(0,1)).

## JSON schema (`rules/out/rooms.json`)

```
{schema_version: 1,
 summary: {definition, maps,
   building_rooms|natural_rooms: {rooms, rooms_weighted, buildings, tiles_per_room_q, u_extent_cells_q,
     v_extent_cells_q, aspect_q, size_bands{band: share}, doors_per_room{n: share},
     share_with_door_to_outside, door_types{type: share}, floor_materials{..}, wall_materials{..},
     floor_inside_outside[{inside, outside, share}], share_floor_changes_at_outside_door,
     furniture_per_room_q, furniture_per_100_tiles_q, lights_per_room_q, lights_per_100_tiles_q,
     share_with_light, items_per_room_q, creatures_per_room_q, rooms_per_building{n: share},
     multi_room_building_share, top_furniture_and_lights{type: share}}},
 rooms: [{id 'map:comp', map, building 'map:bN', kind building|natural, tiles, bbox[x0,y0,x1,y1] cells,
          u_extent, v_extent (cells along the wall axes), floor, floors{top 4}, walls{top 4},
          counts{furniture, light, item, creature, door, other},
          doors[{id, type, dir, gap[x,y], to: room id or null = outside}],
          objects[object ids in corpus objects table] (building rooms only)}]}
```

## Building rooms (3129 rooms, 1027 buildings)

- **Size.** Floor tiles [12.0, 34.0, 80.0]; extent along the wall axes u [4.0, 7.0, 11.0], v [4.0, 7.0, 12.0] cells; aspect [1.08, 1.29, 1.67]. Bands: 2-9 23%, 10-24 17%, 25-49 23%, 50-99 18%, 100-199 13%, 200-400 6%.
- **Doors.** Doors per room: 0 35%, 2 23%, 1 21%, 4 9%, 3 6%, 6 4%, 5 2%. 20% have a door to the outside; rooms with no door object are entered through open archways, secret walls, other rooms or teleports. Door types: GalavaHalfDoor 9%, DunMirDoor 8%, WoodAndSteelHalfDoor 8%, Gate 7%, CryptDoor 7%, ArchedHalfDoor 6%, ArchedDoor 5%, CryptGate 5%, LOTDSingleDoor 5%, LOTDHalfDoor 4%.
- **Floors.** GreenBrick 17%, LOTDPitted 10%, DirtDark2 5%, GalavaBrick 4%, GalavaBrick3 3%, TileDark 3%, LOTDBlackMarble 3%, LOTDDark2 3%, CaveHardBrown 3%, DunMirBrick1 3%, IxBrickFancy 2%, GalavaBrick2 2%. At doors to the outside the floor changes 63% of the time; common inside/outside pairs: GreenBrick/GreenBrick; DirtDark2/SwampGrass; DunMirBrick1/GreenBrick; GreenBrick/DirtDark2; DirtDark2/DirtDark2; OakWoodFloor/GrassNorm; ManaMineDirt/ManaMineDirt; GalavaBrick/GalavaBrick; GalavaBrick3/GalavaBrick3; LOTDPitted/LOTDBlackMarble.
- **Walls.** DungeonStone 19%, LOTDBrick 14%, GalavaTowerWall 10%, GalavaTownWall 7%, BrickBlue 5%, DunMirCathedral 5%, IxTempleWall 5%, IronFence 4%, Cobblestone 4%, SewerWall 3%, Log 3%, LOTDOrnate 3%.
- **Contents.** Furniture per room [1.0, 5.0, 12.0] ([3.8, 12.6, 25.0] per 100 tiles); lights per room [0.0, 1.0, 3.0] ([0.0, 1.6, 5.2] per 100 tiles), 56% of rooms lit; items [0.0, 0.0, 2.0]; creatures [0.0, 0.0, 1.0].
- **Furniture and lights.** Spike 10%, ColorLight 7%, ArmBoneImmobile 5%, SkullImmobile 3%, PeriodicSpike 3%, ObeliskPrimitive 2%, Torch 1%, LOTDManaObelisk 1%, TorchPole 1%, Barrel 1%, FireGrate 1%, Obelisk 1%, Candleabra1 1%, Bookcase1 1%, SpiderWebNorth 1%, Barrel2 1%, SpiderWebEast 1%, SpiderWebNorthEast 1%, Column5 1%, Bookcase3 1%.
- **Buildings.** Rooms per building: 1 52%, 2 16%, 3 8%, 10 8%, 4 5%, 5 4%, 6 3%, 8 2%; multi-room buildings 48%.

## Natural enclosures (1139 rooms)

- Floor tiles [10.0, 35.5, 99.0]; floors CaveHardBrown 14%, DirtDark2 10%, DirtCrackedLight 9%, DirtCrackedDark 8%, GrassNorm 7%, DirtRed 7%, GreenBrick 5%, SwampGrass 4%; walls CaveWall2 22%, ManaMineWall 18%, InvisibleWallSet 12%, DecidiousWallGreen 6%, CaveWall 6%, Dirt 5%.
- Furniture (mostly rocks/plants) per room [1.0, 5.0, 16.0]; lights [0.0, 0.0, 2.0], 48% lit.

## Notes for generation

- Use `rooms[]` (kind building) to choose reference rooms by size, floor and wall material in phase 3;
  object ids join to the corpus `objects` table so a room's furniture layout can be copied relative to
  its bounding box.
- Small rooms (<10 tiles) are mostly closets, corridors, stair landings and are often empty; furniture
  and lights scale with area.
