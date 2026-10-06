# Bandit camp

Kit: `kit/camps.py bandit_camp` (the site: `camp_site`; the people: `kit/posts.py camp_posts`). Lab:
`py tests/scenelab.py bandit_camp`. Westwood's evidence: 20 campaign scenes (review/scenelab/westwood_scenes.json):
the hideouts with cots and no fire (Wiz03a, Wiz03b), the fire rings of the towns and woods (Con03A, War03a, War05A,
Wiz03c), the camps with a pup tent (Con03A, Con04a, Con05A, Con09d).

## Purpose

A band living rough: where they sleep, eat, keep their take and watch the way in. It must read at once as people's
place, in zones, and never as "a scattered mess" (GW-4, SW-1).

## Anchor

The fire, ringed by six to eight small stones (17-30 px out) and a bigger stone or two at its back. (Westwood's
hideouts may have no fire: then the sleeping row is the anchor.)

## Zones

- **Hearth**: the fire, one crude log bench behind it (OgreBench, tangent to the fire), a stool now and then; a cook
  pot only sometimes (one Westwood camp), off on the store's side. The way in to the fire stays open.
- **Sleeping row**: along the back wall (the wood's edge, the cliff), 150-300 px behind the fire: each pup tent with its
  bedrolls beside it, the sleepers without a tent in pairs, a torch pole at the row's end; the leader's awning in the
  middle with three or more tents; the rhythm uneven.
- **Store**: on one flank, against the wall: two or three barrels touching (one kind, the water barrel last), two crates
  of one kind side by side, a sack now and then, a cart sometimes.
- **Arms or dig**: on the other flank: a rack or two and a polearm rack in a row against the wall (most camps); a dig
  camp's tools in the ground, the tool barrel, the spoil, its finds.
- **Lookout**: at the way in, ~190 px out: a torch pole, the watch standing (a stool sometimes, quivers sometimes).
- **Shelter**: a rock outcrop at the row's end (a boulder of one kind, a medium stone, a small one).

## Must, may, never

- Must: the fire and its stones, the sleeping row, the store, the lookout's light.
- May: tents (single pup tents, apart), the awning, racks, the dig, a cart, a cook pot, a stool.
- Never: stumps as seats (SW-3); a bedroll alone in the open (GW-4); bedrolls packed in a block; crates and barrels in a
  heap with nothing about them (GW-2); candles or lanterns (SW-8); two benches in a T at the fire; a straw dummy (no
  Westwood camp has one).

## Spacing (Westwood's campaign camps against the lab's camps, r4)

| | Westwood (median, p10-p90) | Kit now |
|---|---|---|
| pieces | 20 (5-35) | 19-29 (round 2) |
| kinds | 9 (4-12) | 8-13 (round 2) |
| reach from the middle | 162 px (93-224) | 150-200 |
| nearest-piece gap | 33 px (25-42) | 35-45 |
| pieces within 46 px of a wall | 0.50 | 0.1 in the lab's wide glades |
| seats | 0 (p90 0.08 of the pieces) | one bench, a stool sometimes |

Barrels 25 px apart, crates 31, bedrolls 44 apart in a pair (`PAIR_GAP`; SP.gap's 35 packs them into a block), slots of
the sleeping row ~80 px (`SLOT`).

## The people's posts

`posts.camp_posts`: the leader by the take (the chest at the sleeping row's end), at most two at the fire, the others by
their beds, the store and the racks, the watch at the lookout; 64 px apart, 28 px clear of every piece (GW-5, SW-1).

## Variance

The back wall's side, the store's flank, tents 0-3 (the awning with 3+), sleepers in pairs, the row's rhythm, the
stool, the pot, the cart, racks, the dig, the outcrop's side and size. One kind of barrel, crate, rack and boulder to a
camp.

## Mistakes (the user's words)

- "The bandit camp looks terrible. It's a scattered mess. Beds randomly strewn across an open clearing a few random
  crates placed haphazardly. Give it more structure." (GW-4)
- "another absolute mess of randomly placed things and overly clustered NPCs ... It needs a lot of refinement and a
  lot more purpose and organization." (SW-1)
- "the stumps around the fires in bandit camps arent the right object for that use case." (SW-3)
- The lab's own: bedrolls two to a tent in front of tents in an arc became a dormitory block; a cart backed into a
  pond; a lone bedroll at a row's end.

## Round 2 (2026-10-05): one tent, the war camp's racks, a smaller camp

- Westwood's open-air camps are war camps: ONE pup tent (never two), the leader's awning only with a big band, a row of
  three or four armour racks of different builds with the helmet poles, barrels, a cart, the fire ring; no bedrolls by
  the tent (its sleepers are in it). Its hideouts (caves) have the cots against the rock.
- The kit now: one pup tent (two sleep in it, two under the awning), the rest on bedrolls in pairs; radii ~0.8 of
  round 1 (the row 165 px, scale never above 1.0: a big glade does not make a big camp); extras rare (bench 30% or a
  stool 40%, pot 8%, water barrel 20%, sack 10%, cart 20%, outcrop 35%); 8-13 kinds, 19-29 pieces.
- A camp's site backs onto the wood with ~5 squares of open ground before it (`camp_site`).
- Never: two pup tents; a lone crate (both or none); finds out in the open grass; the awning at the row's end.

## What still gives it away

An open forest glade with empty grass in the middle; more people (the posts) and a few more kinds of thing than
Westwood's sparse hideouts. Westwood's camp evidence mixes cave hideouts without fires and town fire rings, so the
classifier (AUC ~0.98) separates the kit's composed camp from that mix even where the eye scores it 6.0 against 6.8.

## Round 4 (2026-10-06): the hideout

Half of Westwood's camp evidence is a hideout in the rock (Wiz03a x3, Wiz03b x4, Wiz03c, War03a x2): a pocket of
CaveWall2 on DirtDark2 off a cave's passage, every piece against the rock. Measured from the wall's line: wall torches
(Torch) 1-16 px, big rocks and pillars 5-25, barrels 13-46, crates 15-44, cots 20-48, the fire 50-146.

- **Kit**: `camps.hideout_camp`; `bandit_camp` turns into it by itself where its ground is a pocket of the rock or a
  ruin's walls (`rock_pocket`: 11 of 16 rays meet a cave's or a ruin's wall within 330 px; `hideout=True/False`
  forces it). Its own generator.
- **Beds**: two to four cots (sleepers less one or two) in groups of two (three with an odd one) against the back rock,
  heads to it, 58-66 px apart (never more than 74: the checker's bedroll rule), a group laid whole or not at all, the
  next group four to seven rays round; a wall torch beyond each group.
- **Store**: two barrels against the rock on a flank, a third (and fourth) before them in a knot; a water barrel 25%,
  a steel one 20%; a crate or two of one kind round the rock beside them.
- **Rock**: two or three places where the rock juts nearest, a huge rock or a boulder (60%) or a pillar, one or two
  smaller stones fallen beside it.
- **Hearth**: a fire ringed by five to eight stones (55%), a cold one (15%), none (30%), well off the rock; bones by a
  fire 30%. A table and two chairs on the other flank (20%). The chest against the rock by the beds. A third wall torch
  50%; loose stones (Rock5-7) on the floor now and then.
- **People**: the leader by the chest, one by the beds, the watch inside the mouth (the lab: no one at the fire).
- **Lab**: five of ten camps in a rock pocket (`labgen` CAVE_R 4-5.5 squares, CaveWall2 on DirtDark2, one mouth on a
  spur off a passage between the rows).

## What still gives it away (round 4)

The hideouts read as Westwood's (wall share 0.5-1.0 against Westwood's 0.5); the classifier still separates the batch
(AUC ~0.93-0.97) on the open-air half: a fire in every one (fire share 0.04 against 0.01), 11-14 kinds against 9, the
diagonal shape.

## Round 5 (2026-10-06)

The judge: "the same cliff hollow with the same straight corridor exit; the fire near the middle, the other pieces along
the walls at even steps; fire stones a wide, evenly spaced hexagon; stores in one strip along the back wall; a bench
right beside the fire". The fire ring tight and uneven (17-23 px, each stone's angle jittered); the hideout's crates set
before the barrels' end, a knot; cot steps 54-70 px; the bench 70 px out (Westwood's stool 59); cots on an upper wall
where the pocket allows (a cot under the near rock is hidden); the lab's pockets stretched and turned, their passages
winding.
