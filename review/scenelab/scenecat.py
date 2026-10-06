"""The scene types the lab covers: how each is found on Westwood's campaign maps (its signature), how far a scene of it
reaches (for reading its pieces), and which of the kit's code lays one (review/scenelab/labgen.py RECIPES).

A Westwood scene of a type is found from its signature objects on outdoor ground (grass, dirt, swamp, snow, paving;
docks on their water): the signature objects within `link` px of each other make one scene's seeds; its pieces grow from
them (pieces.grow: single linkage at `link`, within `radius` of the seeds' middle). `co`: the scene needs one of these
pieces too (a camp is a fire with beds, tents or stores round it, not a lone brazier). Types are claimed in this order:
an object already in a scene is not a seed of a later one (an ogre village's fire is not a bandit camp's).

`rank`: the order of importance (the user's sore points first, then by how often Westwood's campaign has the scene and
how often a map of ours needs one).
"""

SCENES = {
    # ---- the user's sore points -------------------------------------------------------------------------------------
    "bandit_camp": dict(
        title="bandit camp", rank=1, sore=True,
        purpose="a band living rough in a clearing: the fire, the beds or tents, the stores, the arms, the watch",
        sig=r"^(CampFire|CampFireUnused|OutdoorTraderPupTent|Cot\d)$",
        co=r"PupTent|^Cot\d|Barrel|Crate|Sack|Rack|PoleArm|TraderTent|Stool|Bench|Chest", ground=("grass", "dirt", "swamp", "ice"),
        link=120, radius=360, min_pieces=5),
    "graveyard": dict(
        title="graveyard", rank=2, sore=True,
        purpose="where the town buries its dead: headstones in rows on dug earth, a fence and gate, a torch, a cross",
        sig=r"^(Tombstone\d+|TombstoneReadable\d+|LOTDTombstone\d)$", link=190, radius=600, min_pieces=4, min_seeds=3),
    "garden": dict(
        title="vegetable garden", rank=3, sore=True,
        purpose="a household's crop in rows on dug earth beside the house, fenced, the water barrel and the tools by it",
        sig=r"^(GardenCorn|GardenTomatos|GardenCabbage)$", link=100, radius=420, min_pieces=6, min_seeds=4),
    "pond_dock": dict(
        title="pond with a dock", rank=4, sore=True,
        purpose="a dock run out from the bank into open water, a barrel or two on it, reeds in the shallows",
        sig=r"^(DockDown|DockUp)", link=130, radius=260, min_pieces=2, water=True),
    # ---- the camps ----------------------------------------------------------------------------------------------------
    "ogre_camp": dict(
        title="ogre camp", rank=5, purpose="the ogres' village: the fire pit with meat, straw bedding, the tusk gate",
        sig=r"^(OgreFirePit|OgreFirePitUnlit)$", link=120, radius=360, min_pieces=5),
    "urchin_camp": dict(
        title="urchin camp", rank=9, purpose="urchins squatting: beds of one kind side by side, a table and stools, "
        "their pickings", sig=r"^(UrchinBed\d|UrchinHammock\d)", link=110, radius=280, min_pieces=4),
    # ---- the town's work ------------------------------------------------------------------------------------------------
    "well": dict(
        title="well", rank=6, purpose="the town's well, where water is fetched: barrels and a bench by it",
        sig=r"^(WishingWell|Well)$", link=90, radius=220, min_pieces=1),
    "market_stall": dict(
        title="market stall", rank=7, purpose="a trader's awning with the wares set out before it",
        sig=r"^TraderTent.*FrontSide$", link=110, radius=240, min_pieces=5),
    "wagon": dict(
        title="wagon", rank=8, purpose="a cart drawn up or broken down, its load by it",
        sig=r"^(OutdoorTraderCart|MineOreCart\d|MineOreCartBroken\d)$", link=90, radius=190, min_pieces=3),
    "smithy_yard": dict(
        title="smithy yard", rank=10, purpose="the smith's yard: the anvil, the quench barrel, the bellows, racks",
        sig=r"^Anvil\d$", link=100, radius=220, min_pieces=3),
    "training_ground": dict(
        title="training ground", rank=11, purpose="the guards' sparring ground: targets, racks of arms, the watchers",
        sig=r"^(TargetBarrel\d|OutdoorTraderArmorRack\d)$", link=100, radius=260, min_pieces=3),
    "woodpile": dict(
        title="woodpile", rank=12, purpose="logs stacked for the hearth, the block, the tools",
        sig=r"^ForestLog0\d$", link=80, radius=180, min_pieces=2),
    "guard_post": dict(
        title="guard post", rank=13, purpose="a sentry's post: the brazier, his stool, his spear, his water",
        sig=r"^Brazier$", link=80, radius=170, min_pieces=2),
    "shrine": dict(
        title="shrine or waystone", rank=14, purpose="a carved stone by the way, torch poles, offerings",
        sig=r"^(Statue2[a-h]|Statue1[a-h]|Cross\d|DunMirMileStone|DunMirWolfStatue)$", link=90, radius=200,
        min_pieces=2),
    "farmyard": dict(
        title="farmyard", rank=15, purpose="hay and straw heaped by a farmstead, sacks of feed, the wind-mill",
        sig=r"^(OgreStraw\d|Windmill2)$", co=r"Sack|Barrel|Crate|Windmill|Cart|Tool", link=90, radius=220,
        min_pieces=4, min_seeds=2, not_with=r"^(Ogre(?!Straw)|Tusk)"),
    "wolf_den": dict(
        title="wolf den", rank=16, purpose="a heap of rock where a pack lies up, bones strewn before it",
        sig=r"^(Wolf|BlackWolf|WhiteWolf|Bear|BlackBear)$", creatures=True, link=160, radius=260, min_pieces=2,
        min_seeds=2),
    "quarry": dict(
        title="quarry", rank=17, purpose="where stone is cut: rocks of every size, pillars, the pick and shovel",
        sig=r"^(MiningPickAxeInGround\d|MiningShovelInGround|MiningTools\d|MiningHammer\d)$", link=110, radius=300,
        min_pieces=4),
    "jail": dict(
        title="jail yard", rank=18, purpose="the town's cells: two cells behind cobbled walls, a cot and straw in each",
        sig=r"^JailDoor$", doors=True, link=110, radius=200, min_pieces=1),
}
ORDER = ["ogre_camp", "urchin_camp", "bandit_camp", "pond_dock", "graveyard", "garden", "market_stall", "smithy_yard",
         "well", "training_ground", "wagon", "guard_post", "woodpile", "shrine", "jail", "farmyard", "quarry", "wolf_den"]


def ranked():
    return sorted(SCENES, key=lambda k: SCENES[k]["rank"])
