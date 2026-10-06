# Townsfolk, shops, waypoints and roaming

Source: `rules/life.py` over the 107 campaign maps; shares and quartiles ([25%, median, 75%])
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

- **Who.** civilian 448 in 56 maps, maiden 78 in 17 maps, shopkeeper 87 in 30 maps, special 32 in 29 maps, armed_npc 155 in 38 maps.
- **How many.** 29 town maps. Townsfolk per town [8.25, 16.0, 26.0], shopkeepers [0.0, 1.0, 3.0], buildings near townsfolk [1.0, 5.0, 12.0]; [0.6, 0.8, 1.07] townsfolk per 100 populated tiles; [2.08, 2.95, 5.33] per building. Largest towns: Wiz02A (42), War07B (32), Wiz05A (28), Con02a (27), Con05A (27), War05A (27).
- **civilian settings** (448 in 56 maps). Default action: GUARD 72%, IDLE 21%, ROAM 7%; roam flag: 255 72%, 128 12%, 8 3%, 1 2%; immortal: True 53%, False 47%; team: 0 64%, 1 28%, 2 8%, 7 0%; aggressiveness: 0.5 41%, 0 36%, 0.16 14%, 0.83 9%; sight range: 0 37%, 150 29%, 450 7%; health [60.0, 150.0, 150.0]. Script name 82%, script events 35%; indoors 61%; distance to nearest door [4.12, 7.0, 12.0] cells.
- **maiden settings** (78 in 17 maps). Default action: GUARD 62%, ROAM 29%, IDLE 9%; roam flag: 255 48%, 128 32%, 8 13%, 64 5%; immortal: True 95%, False 5%; team: 0 87%, 1 13%; aggressiveness: 0 71%, 0.5 15%, 0.16 14%; sight range: 0 56%, 150 44%; health [75.0, 75.0, 75.0]. Script name 100%, script events 43%; indoors 34%; distance to nearest door [5.66, 8.54, 12.81] cells.
- **shopkeeper settings** (87 in 30 maps). Default action: GUARD 100%; roam flag: 255 91%, 128 9%; immortal: True 86%, False 14%; team: 0 93%, 1 7%; aggressiveness: 0 77%, 0.5 18%, 0.16 5%; sight range: 0 84%, 150 14%, 8 2%; health [0.0, 0.0, 0.0]. Script name 100%, script events 2%; indoors 58%; distance to nearest door [7.07, 9.43, 17.03] cells.
- **armed_npc settings** (155 in 38 maps). Default action: GUARD 63%, IDLE 33%, ROAM 4%; roam flag: 255 73%, 128 10%, 4 6%, 2 4%; immortal: False 100%; team: 0 79%, 1 20%, 2 1%; aggressiveness: 0.83 58%, 0.5 26%, 0 11%, 0.16 5%; sight range: 150 38%, 250 30%, 0 8%; health [100.0, 150.0, 200.0]. Script name 51%, script events 88%; indoors 46%; distance to nearest door [4.0, 7.81, 16.8] cells.
- **Clothing (civilians).** Items [3.0, 5.0, 6.0]; types: MedievalPants 17%, MedievalShirt 17%, LeatherBoots 15%, WizardRobe 8%, WizardHelm 8%, LeatherArmor 3%, LeatherLeggings 3%, MedievalCloak 3%, LeatherArmbands 2%, Breastplate 2%, LeatherArmoredBoots 2%, Quiver 2%. Common outfits: LeatherBoots+MedievalPants+MedievalShirt+WizardHelm+WizardRobe 28%, LeatherBoots+MedievalPants+MedievalShirt 11%, MedievalPants+MedievalShirt 7%, LeatherBoots+MedievalPants+MedievalShirt+RedPotion+WizardHelm+WizardRobe 5%, Breastplate+Longsword+MedievalCloak+MedievalPants+MedievalShirt+OrnateHelm+PlateArms+PlateBoots+PlateLeggings+SteelShield 4%, LeatherBoots+MedievalCloak+MedievalPants+MedievalShirt 3%.

## Shops

- 87 shopkeepers in 30 maps: ShopkeeperMagicShop 22%, ShopkeeperWarriorsRealm 17%, ShopkeeperConjurerRealm 16%, ShopkeeperPurple 15%, ShopkeeperLandOfTheDead 12%, ShopkeeperYellow 10%, ShopkeeperWizardRealm 8%.
- Item lines per shop [4.0, 6.0, 11.0], units [7.0, 12.0, 18.0]. Most stocked: FieldGuide 8%, SpellBook 8%, RedPotion 6%, Quiver 6%, LeatherBoots 5%, FanChakram 5%, CurePoisonPotion 4%, MedievalCloak 4%, RedApple 4%, LeatherArmor 4%, StaffWooden 4%, BluePotion 4%, LeatherHelm 3%, Meat 3%, Cider 3%.
- Buy/sell multipliers: 1/0.33 (13%); 1.5/0.05 (13%); 3/0.05 (10%); 1.2/0.15 (7%); 1.3/0.05 (5%).
- Greeting text: map:key string id 98%, empty 2% (a string-table id such as `Con02a:Mystic`).
- Objects within 3 cells of a shopkeeper (counters, racks, shelves): TraderDesk3 6%, Rock7 5%, TraderDesk1 4%, TraderAppleCrate 4%, SmallFlameImmobile 3%, BarPiece2A 3%, PiledBarrels2 3%, StarChart3a 3%, BarPiece4A 3%, Candleabra3 3%, FairyJar 3%, Straw2 3%, TraderTentShadowDN2 2%, TraderTentPoleDN1 2%, BarPiece3D 2%.

## Waypoints

- **Density per 100 floor tiles:** cave 2.175, wilderness 1.619, dungeon 2.451, town 1.975. Share of all waypoints: dungeon 43%, cave 29%, town 15%, wilderness 13%.
- **Spacing.** Linked waypoints are [5.91, 8.63, 12.73] cells apart. Degree: 2 33%, 0 21%, 1 20%, 3 16%, 4 7%, 6 1%, 5 1%. Bidirectional link share per map [0.84, 0.95, 0.98]. Named waypoints 23.3%.
- **Flags.** 128 81%, 8 5%, 1 5%, 4 3%, 32 3%, 16 2%, 2 2%, 64 1%.
- **Graph shape.** 107 maps; waypoints per map [75.0, 137.5, 186.0]; separate networks per map [12.0, 22.5, 44.0]; independent loops per map [6.0, 15.0, 26.0].
- **Placement.** Distance to the nearest wall (cells): cave [2.0, 2.83, 4.0], wilderness [2.0, 2.83, 4.12], town [2.0, 2.83, 4.24], dungeon [2.0, 2.83, 4.24]. Waypoints on road-like floors (cobble/brick/dirt/tile/stone) vs all tiles: cave 61% vs 53%, wilderness 6% vs 4%, town 51% vs 42%, dungeon 60% vs 51%.

## Roaming

- ActionRoamPathFlag is a bitmask; a roaming creature follows waypoint links whose flag shares a bit with it (255 has every bit, so it uses any link). 128 is the editor's default link flag and carries 87% of links (general paths); the single-bit flags 1..64 appear on small separate networks, which reads as private patrol/escort routes (inferred, not verified in the engine).
- **Roaming townsfolk** (73): roam flags 128 54%, 8 29%, 255 11%, 64 6%, 2 1%; nearest waypoint [1.02, 2.2, 5.27] cells; flag matches a link in the map 100%, within 6 cells 70%.
- **Roaming monsters** (262): roam flags 1 32%, 128 20%, 255 14%, 8 11%, 32 6%; nearest waypoint [0.76, 1.6, 3.04] cells; flag matches a link in the map 98%, within 6 cells 90%.

## Notes for generation

- Give townsfolk scripts only when they have dialogue; plain roamers need DefaultAction ROAM (10) and a roam flag
  that matches the link flags of a nearby waypoint network (128 for general paths).
- Stationary townsfolk (GUARD/IDLE) stand indoors near doors, counters and shop shelves.
