"""The Hollow Choir: what the ten acts share (campaign/hollowchoir/BIBLE.md is the story).

    from kit.campaign import ACTS, CAST, TOKENS, act, token, has, cast_person
    A_ = act(3)                                   # dict(map="Greycrag", next="Frosthol", title=..., setting=...)
    q.say("You kept her seal.", when=has("WATCH_SEAL"))
    A.give(token("DORAN_LETTER"))                 # the item type that carries the token
    cast_person(sm, "Ilsa", x, y, face=...)       # a recurring character, the same body and voice in every act

Continuity: the game keeps the player's inventory across maps and in saved games but not script variables, so every
choice and every cross-map side quest is an item the player carries (TOKENS: the item type, what the story calls it,
which act gives it and which acts read it). A counted token (VERSE_STONE, SPIRIT_STONE) is read by count with
`q.when(has=...)` repeated through A.take/A.give, or by the script's own count (kit/behaviours/quests.go `Has`).
"""

# ---- the acts, in order ---------------------------------------------------------------------------------------------
ACTS = [
    dict(n=1, map="Brackwatr", design="hc01_brackwater", title="Brackwater", setting="town (river, docks, bridges)"),
    dict(n=2, map="Mirewood", design="hc02_mirewood", title="The Mirewood", setting="swamp"),
    dict(n=3, map="Greycrag", design="hc03_greycrag", title="The Greycrag Mines", setting="cave town with lifts"),
    dict(n=4, map="Frosthol", design="hc04_frosthollow", title="Frosthollow", setting="snow village and glacier shrine"),
    dict(n=5, map="Thornkeep", design="hc05_thornkeep", title="Thornkeep", setting="castle town"),
    dict(n=6, map="OgreMarch", design="hc06_ogremarch", title="The Ogre Marches", setting="forest and ogre lands"),
    dict(n=7, map="AshBarrow", design="hc07_ashbarrow", title="The Ashen Barrow", setting="crypts (Land of the Dead)"),
    dict(n=8, map="Emberforg", design="hc08_emberforge", title="The Emberforge", setting="lava, the founders' forge"),
    dict(n=9, map="HollowSpr", design="hc09_hollowspire", title="The Hollow Spire", setting="tower, floors by stairs and lifts"),
    dict(n=10, map="LastBell", design="hc10_lastbell", title="The Last Bell", setting="Brackwater burning"),
]
for _i, _a in enumerate(ACTS):
    _a["next"] = ACTS[_i + 1]["map"] if _i + 1 < len(ACTS) else None
    assert len(_a["map"]) <= 9, _a["map"]


def act(n):
    return ACTS[n - 1]


# ---- tokens: choices and cross-map quest progress, carried as items ----------------------------------------------------
# type: the item that carries it (verified to survive a map change; never consumed by use; see VERIFIED below);
# what: how the story names it when it is handed over; given/read: the acts.
TOKENS = {
    # choices: the game's own quest items (a hard-coded list in the engine: never sold, dropped or used)
    "WATCH_SEAL":   dict(type="SponsorshipLetter", what="the watch's warrant, sealed by Captain Ilsa", given=[1], read=[5, 9, 10]),
    "RUSK_KNIFE":   dict(type="AmuletOfClarity", what="Rusk's lucky charm, his promise to repay you", given=[1], read=[5, 6, 9, 10]),
    "RELIQUARY":    dict(type="MayorsScepter", what="the Choir's bone reliquary, a rod of yellowed bone", given=[2], read=[7, 10]),
    "VESS_OATH":    dict(type="Spectacles", what="Vess's silvered eyeglass, the Choir's mark of rank, given as her oath", given=[4], read=[9, 10]),
    # the stones: quest items that cannot be sold (they can be dropped and picked up again); counted
    "SPIRIT_STONE": dict(type="RedOrbKeyOfTheLich", what="a Spirit Stone, a bell's clapper (a red stone that hums)", given=[3, 6, 7, 9], read=[10], counted=True),
    "VERSE_STONE":  dict(type="BlueOrbKeyOfTheLich", what="a verse of the bells, a blue stone rubbed with a founder's words", given=[3, 4, 7], read=[10], counted=True),
    # side-quest progress: plain items (worth nothing; a player could sell one for a gold piece)
    "DORAN_LETTER": dict(type="AmuletofCombat", what="Doran's guild medallion: any smith of his guild will know it", given=[1], read=[3, 8, 10]),
    "STARSTEEL":    dict(type="RedOrb", what="a lump of starsteel, red-glinting", given=[3], read=[8]),
    "WENNA_ASK":    dict(type="GreenOrb", what="Wenna's charm, a green stone Tam will know", given=[1], read=[2, 5, 10]),
    "TAM_SATCHEL":  dict(type="TreasureBag", what="Tam's satchel", given=[2], read=[5]),
    "TAM_FREED":    dict(type="BlueOrb", what="Tam's bell-token, given in thanks", given=[5], read=[10]),
}
# Brother Edric's request (act 1) is not carried: the verses themselves (VERSE_STONE) are what later acts read.
# Verified 2026-10-09 (review/out/qa/tokens/evidence.txt): every type above survives a map change and a save and load
# in a real solo game on opennox-hd.exe, named items keep their names. Never use: the coloured keys (a matching door
# eats them), potions, SpellScroll (learned on pickup), Orb and WhiteOrb (cannot be picked up again once dropped).
# A script must not create several items and pick them all up in one frame (it hung the game): kit/quests gives
# gifts a few frames after making them.
VERIFIED = {t["type"] for t in TOKENS.values()}


def token(name):
    if name == "EDRIC_ASK":
        raise KeyError("EDRIC_ASK is not carried (kit/campaign.py): read VERSE_STONE instead")
    return TOKENS[name]["type"]


def has(name):
    """The condition 'the player carries this token' (kit/quests QuestBook.when)."""
    from kit.quests import QuestBook
    return QuestBook.when(has=token(name))


# ---- the recurring cast -----------------------------------------------------------------------------------------------
# donor: (stock map, script name) the person is cloned from (kit/story StoryMap.person), the same in every act; voice:
# Breeze TTS 2 description and seed (q.talker(..., voice=)), the same in every act.
CAST = {
    "Ilsa": dict(donor=("War01A", "Evelyn"), pic="IngridPic", title="Ilsa",
                 voice={"desc": "A woman in her forties, captain of a town watch. Low, dry, tired voice with a flat northern "
                                "English accent. Speaks briskly, few words.", "seed": 41}),
    "Doran": dict(donor=("Con02a", "Bryan"), pic="QuarterMasterPic", title="Doran Ashforge",
                  voice={"desc": "An old blacksmith in his sixties. Deep, rough, warm voice, a rural West Country English "
                                 "accent. Speaks slowly.", "seed": 42}),
    "Wenna": dict(donor=("Con02a", "Gretchen"), pic="MaidenPic4", title="Wenna",
                  voice={"desc": "A young woman, a village herbalist, in her twenties. Soft, clear, anxious voice with a "
                                 "gentle Yorkshire accent.", "seed": 43}),
    "Tam": dict(donor=("Con03B", "Dudley"), pic="WoundedApprenticePic", title="Tam",
                voice={"desc": "A youth of sixteen, a bell-ringer's apprentice. Light, quick, eager voice, a Yorkshire "
                               "accent, a little breathless.", "seed": 44}),
    "Rusk": dict(donor=("Con03A", "Rastur"), pic="MalePic9", title="Rusk",
                 voice={"desc": "A wiry man in his thirties, a bandit and a coward. Nasal, wheedling voice with a London "
                                "street accent. Talks fast.", "seed": 45}),
    "Edric": dict(donor=("Wiz02A", "TowerNPC"), pic="ArchivistPic", title="Brother Edric",
                  voice={"desc": "An old monk in his seventies, keeper of old lore. Thin, gentle, precise voice, a "
                                 "received pronunciation English accent. Speaks slowly and carefully.", "seed": 46}),
    "Baron": dict(donor=("Con02a", "Mayor_Theogrin"), pic="TheogrinPic", title="Baron Aldric Thorne",
                  voice={"desc": "A proud nobleman in his fifties. Full, resonant, haughty voice, an upper-class English "
                                 "accent.", "seed": 47}),
    "Severin": dict(donor=("Con02a", "Morgan"), pic="MorganPic", title="Chancellor Severin",
                    voice={"desc": "A thin courtier in his forties. Smooth, quiet, silky voice, a polished English accent. "
                                   "Every word chosen.", "seed": 48}),
}
# Vess appears as a person only where she yields or helps (acts 4 and 9); in a fight she is the M5 monster (FOES)
CAST["Vess"] = dict(donor=("Con07B", "Shari"), pic="MaidenPic6", title="Vess",
                    voice={"desc": "A woman in her thirties, a hired blade. Low, cool, clipped voice with a soft Scottish "
                                   "accent. Speaks quietly and precisely, never wasting a word.", "seed": 49})

# Titles are the dialogue window's "NPC:<script name>" strings, one table for every installed map: a name another
# map's creature already has must read the same there (mapgen/strings.py refuses a clash). Emberhol has an Ilsa,
# Harrowby a Tam, Mirefen a Wenna: ours are titled by first name too; their surnames are in the dialogue.

# Foes with names (kit/mods MONSTERS give their abilities; their name comes from a sign or a shout, not over the head)
FOES = {
    "Vess": dict(mod="M5", hp=320, title="Vess, the Choir's blade"),
    "Morvaine": dict(mod="M3", hp=900, title="High Caller Morvaine"),
    "Gruthak": dict(mod="M1", hp=800, title="Gruthak the Ogre Lord"),
    "Matriarch": dict(mod="M4", hp=1400, title="the Ember Matriarch"),
}


def cast_person(sm, who, x, y, face=None, **kw):
    """A recurring character placed in an act: cloned from the same donor, named as the cast names them."""
    c = CAST[who]
    return sm.person(c["donor"][0], c["donor"][1], x, y, who, face=face, **kw)


def pic(who):
    """The character's portrait in the dialogue window, the same in every act: q.portrait(name, pic(who))."""
    return CAST[who]["pic"]


def voice(who):
    return CAST[who]["voice"]


def exit_next(sm, area, n, prefix="Exit"):
    """Act n's exit to act n+1 (kit/story StoryMap.exit_to), arriving at the next act's PlayerStart once that act is
    built. Acts are built in parallel, so while the next act is not built yet the exit points at a provisional spot
    and says so; tests/campaign.py rebuilds the chain from act 10 back to act 1, which fixes every arrival."""
    nxt = act(n)["next"]
    if not nxt: return []
    try:
        return sm.exit_to(area, nxt, prefix=prefix)
    except AssertionError:
        print(f"CAMPAIGN: {nxt} is not built yet: the exit to it arrives at a provisional spot until the chain rebuild")
        return sm.exit_to(area, nxt, prefix=prefix, arrive=(2944.0, 2944.0))


CHAIN = [a["design"] for a in ACTS]       # tests/campaign.py --hollowchoir builds these, act 10 first
