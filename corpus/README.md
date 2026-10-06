# Reference corpus

Everything in Westwood's 157 stock maps, extracted so map-making rules can be learned from
professional examples instead of guessed. Phase 1 of the map-making skill plan.

```
py corpus\build_corpus.py               # export + database + reference images (~15 min)
py corpus\build_corpus.py --skip-images # export + database only (~30 s)
```

Needs `build.ps1` to have been run (uses the built editor and NoxShared.dll). Output goes to
`corpus\out\` and is not committed (it is derived from the game's files and can be rebuilt).

| Output | Contents |
|---|---|
| `out\json\<map>.json` | Every wall (with secret/window/breakable settings), floor tile and edge overlay, object with all of its type-specific settings and carried inventory, waypoint with links, room polygon, group, and script function/string names. Exported through the editor's library (`dump_maps.ps1`). |
| `out\json\things.json` | The game's object database plus floor, wall and edge tables. |
| `out\images\<map>.png` | Whole map rendered in game graphics at half scale (`MapEditor.exe <map> --render-image`). |
| `out\thumbs\<map>.jpg` | 900 px previews. |
| `out\nox_corpus.db` | SQLite database of all of the above. |
| `out\atlas.md` | One line per map. |
| `out\layout_groups.json` | Single-player maps grouped by layout (class campaigns share many maps). |

## Database tables

`maps`, `walls`, `tiles`, `edges`, `objects` (inventory items have `parent`; `xfer` is the
object's settings as JSON), `waypoints`, `waypoint_links`, `polygons`, `groups_`,
`script_funcs`, `things`, `layout_group` (map, representative, group size).

Categories: `campaign` (107 maps: con/war/wiz chapters 1-11), `quest` (13 `G_*` maps),
`multiplayer` (22), `social` (15). The 120 single-player maps reduce to 62 distinct layouts
(wall overlap above 60% counts as the same layout); weight statistics by `1 / size` from
`layout_group` so shared maps are not counted three times. Style knowledge (every rule, baseline and calibration that
says what Westwood does) comes from the 107 campaign maps alone (54 layouts: `rules/common.py campaign_weights`); the
quest and multiplayer maps are other games' noise for the campaign maps we make and serve only validity tables.

## Example queries

```sql
-- wall shapes and variations Westwood actually used for a material
SELECT facing, variation, COUNT(*) FROM walls WHERE material='Log' GROUP BY 1, 2;
-- which edge style blends two floor materials
SELECT edge_type, COUNT(*) FROM edges WHERE base='GrassNorm' AND overlay='WaterShallow' GROUP BY 1;
-- settings of every ColorLight in towns
SELECT map, xfer FROM objects WHERE type='ColorLight' AND map IN ('Con07B', 'Wiz02A');
```
