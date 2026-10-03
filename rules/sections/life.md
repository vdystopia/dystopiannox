# Townsfolk, shops, waypoints and roaming

Source: `rules/life.py` over the 120 single-player maps; shares and quartiles ([25%, median, 75%])
weighted by `1 / layout group size`. Roles: **civilian** = NPC object that is immortal or unarmed;
**armed_npc** = mortal NPC carrying a weapon (guards, soldiers, hostile humans); **maiden**;
**shopkeeper** (Shopkeeper*); **special** (AirshipCaptain, Wounded*). A **town map** has 5+ civilians,
maidens and shopkeepers. Populated tiles = tiles within 12 cells of a townsperson.

## JSON schema (`rules/out/life.json`)

```
{schema_version: 1,
 townsfolk: {role_counts{role: {objects, maps}},
   towns[{map, townsfolk, civilians, maidens, shopkeepers, armed_npcs, populated_tiles,
          building_rooms_near, buildings_near, per_100_populated_tiles, per_building}],
   town_quartiles{town_maps, townsfolk, shopkeepers, per_100_populated_tiles, per_building, buildings_near},
   settings{role: {n, maps, default_action{ACTION: share}, roam_path_flag{flag: share}, immortal{..}, team{..},
            aggressiveness{..}, sight_range{..}, retreat_ratio{..}, health_q, npc_speed{..},
            has_script_name, has_script_events, indoors, door_distance_cells_q}},
   clothing{items_per_civilian_q, item_types{type: share}, outfits{'A+B+C': share}},
   shops{n, maps, shopkeeper_types, item_lines_per_shop_q, item_units_per_shop_q, top_items,
         buy_sell_multipliers[{buy, sell, share}], greeting_text, objects_within_3_cells}},
 waypoints: {density_per_100_tiles{context: n}, waypoint_share_by_context, link_length_cells_q,
   link_flags{flag: share}, degree{n: share}, bidirectional_link_share_q, named_waypoint_share,
   wall_distance_cells_by_context{context: q}, on_road_floor_share_by_context, road_floor_share_of_tiles_by_context,
   graphs{maps_with_waypoints, waypoints_per_map_q, components_per_map_q, cycles_per_map_q, per_map[...]}},
 roaming: {townsfolk|monsters: {n, roam_flag{..}, nearest_waypoint_cells_q, share_flag_matches_some_link,
           share_matching_link_within_6_cells}, flag_semantics}}
```

## Townsfolk

- **Who.** civilian 448 in 56 maps, maiden 78 in 17 maps, shopkeeper 100 in 43 maps, special 32 in 29 maps, armed_npc 155 in 38 maps.
- **How many.** 29 town maps. Townsfolk per town [8.25, 16.0, 26.0], shopkeepers [0.0, 1.0, 3.0], buildings near townsfolk [1.0, 5.0, 12.0]; [0.6, 0.8, 1.07] townsfolk per 100 populated tiles; [2.08, 2.95, 5.33] per building. Largest towns: Wiz02A (42), War07B (32), Wiz05A (28), Con02a (27), Con05A (27), War05A (27).
- **civilian settings** (448 in 56 maps). Default action: GUARD 72%, IDLE 21%, ROAM 7%; roam flag: 255 72%, 128 12%, 8 3%, 1 2%; immortal: True 53%, False 47%; team: 0 64%, 1 28%, 2 8%, 7 0%; aggressiveness: 0.5 41%, 0 36%, 0.16 14%, 0.83 9%; sight range: 0 37%, 150 29%, 450 7%; health [60.0, 150.0, 150.0]. Script name 82%, script events 35%; indoors 61%; distance to nearest door [4.12, 7.0, 12.0] cells.
- **maiden settings** (78 in 17 maps). Default action: GUARD 62%, ROAM 29%, IDLE 9%; roam flag: 255 48%, 128 32%, 8 13%, 64 5%; immortal: True 95%, False 5%; team: 0 87%, 1 13%; aggressiveness: 0 71%, 0.5 15%, 0.16 14%; sight range: 0 56%, 150 44%; health [75.0, 75.0, 75.0]. Script name 100%, script events 43%; indoors 34%; distance to nearest door [5.66, 8.54, 12.81] cells.
- **shopkeeper settings** (100 in 43 maps). Default action: GUARD 100%; roam flag: 255 93%, 128 7%; immortal: True 74%, False 26%; team: 0 94%, 1 6%; aggressiveness: 0 73%, 0.5 23%, 0.16 4%; sight range: 0 86%, 150 12%, 8 2%; health [0.0, 0.0, 0.0]. Script name 100%, script events 1%; indoors 62%; distance to nearest door [7.07, 9.43, 16.64] cells.
- **armed_npc settings** (155 in 38 maps). Default action: GUARD 63%, IDLE 33%, ROAM 4%; roam flag: 255 73%, 128 10%, 4 6%, 2 4%; immortal: False 100%; team: 0 79%, 1 20%, 2 1%; aggressiveness: 0.83 58%, 0.5 26%, 0 11%, 0.16 5%; sight range: 150 38%, 250 30%, 0 8%; health [100.0, 150.0, 200.0]. Script name 51%, script events 88%; indoors 46%; distance to nearest door [4.0, 7.81, 16.8] cells.
- **Clothing (civilians).** Items [3.0, 5.0, 6.0]; types: MedievalPants 17%, MedievalShirt 17%, LeatherBoots 15%, WizardRobe 8%, WizardHelm 8%, LeatherArmor 3%, LeatherLeggings 3%, MedievalCloak 3%, LeatherArmbands 2%, Breastplate 2%, LeatherArmoredBoots 2%, Quiver 2%. Common outfits: LeatherBoots+MedievalPants+MedievalShirt+WizardHelm+WizardRobe 28%, LeatherBoots+MedievalPants+MedievalShirt 11%, MedievalPants+MedievalShirt 7%, LeatherBoots+MedievalPants+MedievalShirt+RedPotion+WizardHelm+WizardRobe 5%, Breastplate+Longsword+MedievalCloak+MedievalPants+MedievalShirt+OrnateHelm+PlateArms+PlateBoots+PlateLeggings+SteelShield 4%, LeatherBoots+MedievalCloak+MedievalPants+MedievalShirt 3%.

## Shops

- 100 shopkeepers in 43 maps: ShopkeeperLandOfTheDead 26%, ShopkeeperMagicShop 18%, ShopkeeperWarriorsRealm 14%, ShopkeeperConjurerRealm 13%, ShopkeeperPurple 13%, ShopkeeperYellow 9%, ShopkeeperWizardRealm 7%.
- Item lines per shop [4.0, 6.0, 11.0], units [7.0, 13.0, 23.0]. Most stocked: FieldGuide 7%, Quiver 6%, SpellBook 6%, RedPotion 6%, FanChakram 5%, LeatherBoots 5%, LeatherArmor 4%, CurePoisonPotion 4%, BluePotion 4%, StaffWooden 4%, MedievalCloak 4%, RedApple 3%, LeatherHelm 3%, LeatherArmbands 3%, WizardHelm 3%.
- Buy/sell multipliers: 1/0.33 (23%); 1.5/0.05 (11%); 3/0.05 (8%); 1.2/0.15 (6%); 1/1 (4%).
- Greeting text: map:key string id 98%, empty 2% (a string-table id such as `Con02a:Mystic`).
- Objects within 3 cells of a shopkeeper (counters, racks, shelves): TraderDesk3 5%, Rock7 4%, TraderDesk1 4%, PlayerStart 4%, TraderAppleCrate 3%, SmallFlameImmobile 3%, BarPiece4A 3%, BarPiece2A 3%, BarPiece3B 3%, PiledBarrels2 3%, TraderTentPoleDN1 3%, BarPiece3A 2%, StarChart3a 2%, Candleabra3 2%, FairyJar 2%.

## Waypoints

- **Density per 100 floor tiles:** cave 2.84, wilderness 1.607, dungeon 3.108, town 1.942. Share of all waypoints: dungeon 51%, cave 30%, town 10%, wilderness 10%.
- **Spacing.** Linked waypoints are [5.1, 7.44, 11.29] cells apart. Degree: 2 37%, 3 19%, 1 18%, 0 16%, 4 7%, 5 1%, 6 1%. Bidirectional link share per map [0.89, 0.95, 0.98]. Named waypoints 18.0%.
- **Flags.** 128 87%, 8 3%, 1 3%, 2 3%, 4 2%, 32 1%, 16 1%, 64 0%.
- **Graph shape.** 120 maps; waypoints per map [78.0, 159.0, 207.0]; separate networks per map [15.0, 29.0, 49.0]; independent loops per map [9.0, 18.0, 30.0].
- **Placement.** Distance to the nearest wall (cells): cave [1.41, 2.24, 3.61], wilderness [2.0, 2.83, 4.12], town [2.0, 2.83, 4.24], dungeon [1.41, 2.24, 3.61]. Waypoints on road-like floors (cobble/brick/dirt/tile/stone) vs all tiles: cave 64% vs 54%, wilderness 10% vs 5%, town 51% vs 41%, dungeon 55% vs 50%.

## Roaming

- ActionRoamPathFlag is a bitmask; a roaming creature follows waypoint links whose flag shares a bit with it (255 has every bit, so it uses any link). 128 is the editor's default link flag and carries 87% of links (general paths); the single-bit flags 1..64 appear on small separate networks, which reads as private patrol/escort routes (inferred, not verified in the engine).
- **Roaming townsfolk** (73): roam flags 128 54%, 8 29%, 255 11%, 64 6%, 2 1%; nearest waypoint [1.02, 2.2, 5.27] cells; flag matches a link in the map 100%, within 6 cells 70%.
- **Roaming monsters** (262): roam flags 1 32%, 128 20%, 255 14%, 8 11%, 32 6%; nearest waypoint [0.76, 1.6, 3.04] cells; flag matches a link in the map 98%, within 6 cells 90%.

## Notes for generation

- Give townsfolk scripts only when they have dialogue; plain roamers need DefaultAction ROAM (10) and a roam flag
  that matches the link flags of a nearby waypoint network (128 for general paths).
- Stationary townsfolk (GUARD/IDLE) stand indoors near doors, counters and shop shelves.
