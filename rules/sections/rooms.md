# Rooms and buildings

Source: `rules/rooms.py` over the 107 campaign maps (Con/War/Wiz); statistics weighted by
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

## Building rooms (2168 rooms, 770 buildings)

- **Size.** Floor tiles [12.0, 35.0, 83.0]; extent along the wall axes u [5.0, 7.0, 12.0], v [5.0, 7.0, 12.0] cells; aspect [1.08, 1.26, 1.6]. Bands: 2-9 20%, 10-24 18%, 25-49 24%, 50-99 16%, 100-199 14%, 200-400 7%.
- **Doors.** Doors per room: 0 27%, 1 25%, 2 23%, 4 11%, 3 7%, 6 6%, 5 2%. 24% have a door to the outside; rooms with no door object are entered through open archways, secret walls, other rooms or teleports. Door types: GalavaHalfDoor 11%, DunMirDoor 10%, WoodAndSteelHalfDoor 10%, Gate 9%, ArchedHalfDoor 7%, ArchedDoor 6%, JailDoor 6%, DunMirHalfDoor 5%, CryptDoor 5%, WoodenDoor 5%.
- **Floors.** GreenBrick 22%, LOTDPitted 10%, GalavaBrick3 5%, GalavaBrick 5%, DunMirBrick1 4%, RugBlueNorm 3%, DirtDark2 3%, RugGreen 3%, TileDark 3%, RoughCobble 3%, IxBrickFancy 3%, LOTDBlackMarble 3%. At doors to the outside the floor changes 61% of the time; common inside/outside pairs: GreenBrick/GreenBrick; DunMirBrick1/GreenBrick; ManaMineDirt/ManaMineDirt; GreenBrick/DirtDark2; GalavaBrick/GalavaBrick; DirtDark2/DirtDark2; GalavaBrick3/GalavaBrick3; GrassNorm/GalavaBrick2; LOTDBlackMarble/LOTDPitted; GreenBrick/GrassSparse2.
- **Walls.** DungeonStone 17%, GalavaTowerWall 16%, LOTDBrick 11%, DunMirCathedral 8%, IxTempleWall 6%, Cobblestone 6%, SewerWall 5%, IronFence 5%, BrickBlue 4%, StoneGray 4%, GalavaTownWall 4%, Log 3%.
- **Contents.** Furniture per room [1.0, 6.0, 12.0] ([5.4, 13.9, 26.4] per 100 tiles); lights per room [0.0, 1.0, 3.0] ([0.0, 1.4, 6.0] per 100 tiles), 54% of rooms lit; items [0.0, 0.0, 1.0]; creatures [0.0, 0.0, 1.0].
- **Furniture and lights.** ColorLight 7%, PeriodicSpike 5%, Spike 5%, TorchPole 2%, Barrel 2%, Candleabra1 2%, FireGrate 1%, Torch 1%, Bookcase1 1%, Barrel2 1%, Bookcase3 1%, Candleabra3 1%, Obelisk 1%, LOTDManaObelisk 1%, SpiderWebNorth 1%, SpiderWebNorthEast 1%, Candleabra2 1%, Column5 1%, Bookcase2 1%, SpiderWebEast 1%.
- **Buildings.** Rooms per building: 1 53%, 2 17%, 3 10%, 10 7%, 5 4%, 4 4%, 6 2%, 8 2%; multi-room buildings 47%.

## Natural enclosures (692 rooms)

- Floor tiles [14.0, 52.0, 121.0]; floors CaveHardBrown 17%, DirtDark2 15%, GreenBrick 9%, GrassNorm 8%, WaterShallow 6%, WaterSwampDeep 5%, WaterDeep 4%, DirtHard 4%; walls CaveWall2 24%, CaveWall 10%, InvisibleWallSet 10%, ManaMineWall 6%, RootLight 6%, Dirt 5%.
- Furniture (mostly rocks/plants) per room [0.0, 4.0, 14.0]; lights [0.0, 0.0, 2.0], 45% lit.

## Notes for generation

- Use `rooms[]` (kind building) to choose reference rooms by size, floor and wall material in phase 3;
  object ids join to the corpus `objects` table so a room's furniture layout can be copied relative to
  its bounding box.
- Small rooms (<10 tiles) are mostly closets, corridors, stair landings and are often empty; furniture
  and lights scale with area.
