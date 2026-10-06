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
| pieces | 20 (5-35) | 20-30 |
| kinds | 9 (4-12) | 10-13 |
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

## What still gives it away

An open forest glade with empty grass in the middle; more people (the posts) and a few more kinds of thing than
Westwood's sparse hideouts. Westwood's camp evidence mixes cave hideouts without fires and town fire rings, so the
classifier (AUC ~0.98) separates the kit's composed camp from that mix even where the eye scores it 6.0 against 6.8.
