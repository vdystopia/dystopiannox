# QA round 1: in-game behaviour, people, signs and items (Q1G)

The user's screenshot notes and set notes of QA round 1 (`review/reviews/QA-round1.md`, 2026-10-13) on what happens in
the game: signs, wells, fish, where people stand and face, the items the player finds and buys, and two ModLab bugs.
Columns as `review/FEEDBACK.md`: the rule (PROCESS.md section), what enforces it, and the status before this pass and
after it (**check**: an automatic check fails or warns; **review**: a picture or a measure; **none**: not covered).

| ID | The user's words | Rule | Enforced by | Before | After |
|---|---|---|---|---|---|
| Q1G-1 | nox1: "When reading signs, it looks like there is supposed to be a second line, but instead it is attached without a space to the preceding line" | P§7 Signs, P§8 Signs: the client prints a sign on one line and drops line breaks; `q.text(..., "Sign")` joins the lines ("THE OLD BRIDGE - To the mill.", `kit/signs.one_line`) | `signs.text` (STsignT) | none | check |
| Q1G-2 | nox1, nox10: "this large style sign does not look good. Use the smaller ones instead, always" | P§7 Signs: `Sign1`/`Sign2` only, never `PlankSign1-4` (`camps.signpost` stands `Sign1`; four designs moved off `PlankSign2`); a sign that reads nothing is not stood | `signs.large` (STsignL) | none | check |
| Q1G-3 | nox13: "Make all wells heal the player, as is the case in the nox campaign"; the well set: "the player can interact with them to fully heal health and mana" | P§7 Signs, wells and items; P§8 Wells: `kit/wells.py` writes `wells.go` (health and mana to full, Westwood's line and sound, once per visit) for every `Well` and `WishingWell`; a textless sign by a well reads "Magical Well" | `wells.heal` (STwell) | none | check |
| Q1G-4 | nox4: "the fish do not swim around. They are stationary until the player approaches very close" | P§6 Fish swim, P§8 Roaming creatures: `Population.fish` lays a linked loop of waypoints in the pool (the game's roam needs one; Westwood's 239 of 240 fish have one) | `fish.swim` (STfish) | none | check |
| Q1G-5 | nox9: "The female NPC is standing in an awkward spot, looking at the door in front of a door"; nox10: "Two female NPCs clustered at the entrance of a door, one of them stuck in the frame of the door. The male NPC is also facing the door. He should be facing away from the building with his back to the wall" | P§6 Nobody stands in a doorway; Backs to the wall: `StoryMap.doorside` (never on the doorstep), `_spots`/`_free_spot` (beside the doorstep, `PERSON_DOOR`), `_town` (a door someone waits at is no one's stop), `_pick_tour` (a doorstep is one tour's, a shop door two tours'), `settle_people` (off the doorways, back to the wall) | `people.doorway` (STdoorp), `people.crowd` (STcrowd), `people.facing` (STfacew) | none | check |
| Q1G-6 | nox14: "Give the priest a better location instead of being behind a random pillar. Have the priest stand closer to the altar"; nox18: "The shopkeeper should be standing closer to the bar"; nox8: "The shopkeeper behind the desk is good" | P§6 Keepers by their counters, priests by their altars: `StoryMap.shops` brings the keeper within 40 px of his counter (`near_anchor`); `settle_people` brings whoever stands in a chapel or shrine beside its altar (the room type's STANDS piece) | `identity.keeper` (STkeep; 56 px, was 90); the priest: look:rooms (the chapel picture) | review | check (keeper), review (priest) |
| Q1G-7 | nox12: "Most of the new items don't seem to actually have a function. They don't have a correct name or description. And their prices are not correct"; nox19: "The loaf of bread does not have a proper name or seem to do anything" | P§7 Signs, wells and items; P§8 Item names: `kit/items.py` (TEXT names Bread, the gems, the Amulet of Nature and the Hollow Choir's own tokens; `mapgen/strings.py` writes them into `nox.csf.json`; FACTS from thing.bin; CAP by chapter; a spell book ware names its spell; charms.go gives the Amulet of Nature its power); `Population.shopkeeper` refuses a bad ware; Brackwater's wares within chapter 2's prices | `items.name` (STiname), `items.ware` (STiware), `items.price` (STiprce); qa:story (every gift a named item) | none | check |
| Q1G-8 | ModLab M2: "the sign causes the game to crash on desktop" | P§8 Signs: a sign's text past 239 characters overflows the client's buffer (M2's was 274); 120 at most, ModLab's `sign()` lays a long text on a short row of signs | `signs.text` (STsignT; over 200 is an error) | none | check |
| Q1G-9 | ModLab S1: "I'm not sure how this works. The brown pressure plate that appears in this screenshot does not actually show up in the ModLab map" | the brown square was the editor drawing a Staff (it has no sprite in the editor), not a plate: the spare Staff is a Morning Star now; the forge's plate is the grey stone patch, explained by five short signs at the plate, the anvil, the smith, the spares and the gold | look: ModLab's S1 picture | none | review |

## Not done here

- **The Hollow Choir's choice tokens** (`kit/campaign.py` TOKENS: WATCH_SEAL, RUSK_KNIFE, RELIQUARY, VESS_OATH and the
  two stones) are Westwood's own quest items, so in the game they read as Westwood named them ("Gauntlet Petition",
  "Mayor Theogrin's Scepter: Return this scepter to Mayor Theogrin in Ix."). Naming them as the story does means either
  renaming those six items in `nox.csf.json` (every map, Westwood's campaign included) or moving the tokens to types
  Westwood never places (BraceletofHealth, AmuletofManipulation, BlackBook2, ProtectionFire, Diamond, Emerald), which
  `items.TEXT` can then name; either needs the user's choice, and a move needs the in-game carry test the current
  tokens passed (a map change and a save). The five tokens Westwood never places are named now.
- **The priest** is checked only by eye: the checker has no rule tying a person to an altar (a chapel's keeper is not
  marked in the map). `settle_people` places him; the chapel picture shows it.
