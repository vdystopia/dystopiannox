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
    "WATCH_SEAL":   dict(type="BlueOrb", what="the seal of the Brackwater watch", given=[1], read=[5, 9, 10]),
    "RUSK_KNIFE":   dict(type="RedOrb", what="Rusk's promise (he presses a red stone into your hand)", given=[1], read=[5, 6, 9, 10]),
    "RELIQUARY":    dict(type="WhiteOrb", what="the Choir's bone reliquary", given=[2], read=[7, 10]),
    "VESS_OATH":    dict(type="GreenOrb", what="Vess's oath-stone", given=[4], read=[9, 10]),
    "DORAN_LETTER": dict(type="BlueOrbKeyOfTheLich", what="Doran's letter", given=[1], read=[3, 8, 10]),
    "STARSTEEL":    dict(type="RedOrbKeyOfTheLich", what="a lump of starsteel", given=[3], read=[8]),
    "WENNA_ASK":    dict(type="Orb", what="Wenna's charm", given=[1], read=[2, 5, 10]),
    "TAM_SATCHEL":  dict(type="TreasureBag", what="Tam's satchel", given=[2], read=[5]),
    "TAM_FREED":    dict(type="Orb", what="(Tam is free: Wenna's charm stays with you)", given=[5], read=[10]),
    "EDRIC_ASK":    dict(type="SpellScroll", what="Brother Edric's rubbing paper", given=[1], read=[3, 4, 7, 10]),
    "VERSE_STONE":  dict(type="SilverKey", what="a verse of the bells, rubbed from a founder's tablet", given=[3, 4, 7], read=[10], counted=True),
    "SPIRIT_STONE": dict(type="GoldKey", what="a Spirit Stone, a bell's clapper", given=[3, 6, 7, 9], read=[10], counted=True),
}
# The item types above are provisional until the continuity test (mods/engine or tests: an item carried across a map
# change in a hosted game) confirms each survives; VERIFIED lists the confirmed ones.
VERIFIED = set()


def token(name):
    return TOKENS[name]["type"]


def has(name):
    """The condition 'the player carries this token' (kit/quests QuestBook.when)."""
    from kit.quests import QuestBook
    return QuestBook.when(has=token(name))


# ---- the recurring cast -----------------------------------------------------------------------------------------------
# donor: (stock map, script name) the person is cloned from (kit/story StoryMap.person), the same in every act; voice:
# Breeze TTS 2 description and seed (q.talker(..., voice=)), the same in every act.
CAST = {
    "Ilsa": dict(donor=("War01A", "Evelyn"), title="Captain Ilsa Rook",
                 voice={"desc": "A woman in her forties, captain of a town watch. Low, dry, tired voice with a flat northern "
                                "English accent. Speaks briskly, few words.", "seed": 41}),
    "Doran": dict(donor=("Con02a", "Bryan"), title="Doran Ashforge",
                  voice={"desc": "An old blacksmith in his sixties. Deep, rough, warm voice, a rural West Country English "
                                 "accent. Speaks slowly.", "seed": 42}),
    "Wenna": dict(donor=("Con02a", "Gretchen"), title="Wenna Fell",
                  voice={"desc": "A young woman, a village herbalist, in her twenties. Soft, clear, anxious voice with a "
                                 "gentle Yorkshire accent.", "seed": 43}),
    "Tam": dict(donor=("Con03B", "Dudley"), title="Tam Fell",
                voice={"desc": "A youth of sixteen, a bell-ringer's apprentice. Light, quick, eager voice, a Yorkshire "
                               "accent, a little breathless.", "seed": 44}),
    "Rusk": dict(donor=("Con03A", "Rastur"), title="Rusk",
                 voice={"desc": "A wiry man in his thirties, a bandit and a coward. Nasal, wheedling voice with a London "
                                "street accent. Talks fast.", "seed": 45}),
    "Edric": dict(donor=("Wiz02A", "TowerNPC"), title="Brother Edric",
                  voice={"desc": "An old monk in his seventies, keeper of old lore. Thin, gentle, precise voice, a "
                                 "received pronunciation English accent. Speaks slowly and carefully.", "seed": 46}),
    "Baron": dict(donor=("Con02a", "Mayor_Theogrin"), title="Baron Aldric Thorne",
                  voice={"desc": "A proud nobleman in his fifties. Full, resonant, haughty voice, an upper-class English "
                                 "accent.", "seed": 47}),
    "Severin": dict(donor=("Con02a", "Morgan"), title="Chancellor Severin",
                    voice={"desc": "A thin courtier in his forties. Smooth, quiet, silky voice, a polished English accent. "
                                   "Every word chosen.", "seed": 48}),
}
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


def voice(who):
    return CAST[who]["voice"]
