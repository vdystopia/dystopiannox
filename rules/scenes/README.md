# Exterior scenes: the briefs

One brief per exterior scene type, as `rules/rooms/` holds one per room type: purpose, anchor, zones, must/may/never,
spacing against Westwood's campaign scenes, the people's posts, variance, and the user's words on its mistakes. Each is
measured and tuned in the scene lab (`review/scenelab/README.md`; `py tests/scenelab.py <scene>`), whose iteration log
is `review/scenelab/LOG.md`.

## The scene types, ranked, with Westwood's evidence

Found on Westwood's campaign maps only (Con/War/Wiz, outdoor ground; `py review/scenelab/labref.py list`), each place
counted once across the three campaigns. "Kit" is the code that lays it.

| Rank | Scene | Westwood scenes | Where (examples) | Kit | Brief |
|---|---|---|---|---|---|
| 1 | bandit camp | 20 | Wiz03a, Wiz03b (cot hideouts), Con03A, Con04a, Con05A, War03a, War05A, Wiz03c | `camps.bandit_camp`, `posts.camp_posts` | [bandit_camp.md](bandit_camp.md) |
| 2 | graveyard | 13 | War03b, War03c, War03d, Con07B, Con09b, Con04b | `yards` graveyard | [graveyard.md](graveyard.md) |
| 3 | vegetable garden | 5 | Con05A, Con07B, Con09a, Wiz01A, Wiz03b | `Village.garden` | [garden.md](garden.md) |
| 4 | pond with a dock | 4 | Con05A (3), Con03A | `Waterworks.dock` | [pond_dock.md](pond_dock.md) |
| 5 | ogre camp | 5 | Con05B, Con09b, Wiz02C | `camps.ogre_camp` | [ogre_camp.md](ogre_camp.md) |
| 6 | well | 5 | Con02a, Con07B, Con08a, Con09a, War07A (WishingWell; the kit lays "Well") | scenes `well_side` | [well.md](well.md) |
| 7 | market stall | 4-6 | Con02a, Con03A, Con05A, Con09d | scenes `market_stall` | [market_stall.md](market_stall.md) |
| 8 | wagon | 7 | Con03A, Con03B (ore carts), Con05A | scenes `wagon_verge`, `broken_wagon`, `camps.wagon_wreck` | |
| 9 | urchin camp | 42 | Con02a, War03c, War03d, Wiz01A (their dens) | `camps.urchin_camp` | [urchin_camp.md](urchin_camp.md) |
| 10 | smithy yard | 2 | Con07B (Galava's outdoor smithy) | scenes `smithy_yard` | |
| 11 | training ground | 0 (racks only, inside camps) | | scenes `sparring_ring`, `camps.training_ground` | |
| 12 | woodpile | 3 (logs in the woods, no stacked woodpile) | Con08b | scenes `woodpile`, `chopping_yard` | |
| 13 | guard post | 0-1 (no outdoor brazier post) | | scenes `guard_post` | |
| 14 | shrine or waystone | 32 | statues, crosses and milestones outdoors | scenes `shrine`, `waystone` | [shrine.md](shrine.md) |
| 15 | farmyard | 6 | Con08d, War03c, Wiz03a, Wiz03b (straw heaps with barrels) | scenes `hay_store`, `threshing_floor` | [farmyard.md](farmyard.md) |
| 16 | wolf den | 4 | Con08d, War03a, War08b | `camps.wolf_den` | |
| 17 | quarry | 2 | Con08a, Wiz03b | `yards` quarry | |
| 18 | jail yard | 17 | JailDoor cells in the towns | `yards` jail | [jail.md](jail.md) |

Thin or absent in Westwood's campaign: training grounds, guard posts with braziers, stacked woodpiles, smithy yards:
the kit's catalogue themes for them are its own invention; judge them by the user's rules and by eye.

The rank: the user's sore points first (camps, graveyards, gardens, docks), then by how often Westwood's campaign has
the scene and how often a map of ours needs one.
