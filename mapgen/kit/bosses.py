"""Human bosses: NPCs dressed in the player's own armour and weapons, with the game's spells and a scripted way of
fighting each (mods/BOSSLAB.md; scripts: kit/behaviours/bosses.go).

Why humans: the game's NPC (thing type "NPC") is drawn with the player's body, so it shows every piece of armour and
the weapon it carries, and its NPC settings (NPCXfer) give it the game's own spells, strength and speed. Westwood
dresses its NPCs this way (603 of them on the campaign maps), colouring their armour with the modifier.bin colour
enchantments (UserColor1..32, a dye per piece: Wiz06c's plate guards wear UserColor11) beside ArmorQuality and
Material.

    from kit.bosses import Bosses, BOSSES
    bosses = Bosses(m)                                   # m: the nox.Spec
    bosses.boss("B1", x, y, face=(fx, fy), spares=[(vx, vy), (vx2, vy2)])   # waits frozen; comes back from the vault
    ...
    bosses.attach()                                      # LAST: writes bosses.go + bosses_config.go into m.scripts

A boss's spare copies (`spares`) stand frozen where they are placed: put them in a sealed room. When the boss dies the
next copy is brought to its place `respawn` seconds later (a script cannot dress a new NPC in coloured armour).
"""
import copy, json, os

HERE = os.path.dirname(os.path.abspath(__file__))

# An NPC puts on only the inventory items whose create flags carry EQUIPPED (0x100; legacy GAME4_2.c
# nox_xxx_XFerNPC_52ADE0); Westwood writes its NPCs' worn pieces as 0x1000100 (ENABLED + EQUIPPED: Con06b's guards)
EQUIPPED = 0x1000100
# StatusFlags (NoxEnums.MonsterStatus): the AI casts only with CAN_CAST_SPELLS, and a caster never swings a melee
# weapon (GAME4_3.c monsterCanMelee); it still shoots a bow or a wand. A shield bearer blocks with CAN_BLOCK.
CAN_BLOCK, CAN_DODGE, CAN_CAST, CAN_SEE_FRIENDS = 0x4, 0x8, 0x20, 0x400
# NPCXfer KnownSpells use flags (Shared/NoxEnums.cs NPCSpellCastFlags): which of the AI's casting moments uses the spell
REACTION, DEFENSIVE, DISABLING, OFFENSIVE, ESCAPE = 0x08000000, 0x10000000, 0x20000000, 0x40000000, 0x80000000

# Armour colours. An item's 4 enchantments fill, by position, the slots EFFECTIVENESS, MATERIAL, PRIMARY and SECONDARY
# (legacy GAME4.c XFerArmor reads them in order; the client colours slot i from the modifier named there, whatever
# its list: drawable_player.go, server/modifiers.go), and each armour type says which of its colours each slot paints
# (thing.bin). The main surface: MATERIAL for plate, chain, leather and metal helms, PRIMARY for a wizard's robe,
# SECONDARY (the hat's back) for a wizard's hat, EFFECTIVENESS for a cloak's centre and a shield's face. Westwood's
# NPCs: ["ArmorQuality1", "Material2", "UserColor11", ""] (Wiz06c's plate guards).
MAIN = {"WizardRobe": 2, "WizardHelm": 3, "MedievalCloak": 0, "SteelShield": 0}       # otherwise MATERIAL (1)
TRIM = {"WizardRobe": 0, "WizardHelm": 1, "MedievalCloak": 2, "OrnateHelm": 2}        # otherwise PRIMARY (2)
# the colours, by name: modifier.bin's own (UserColor1-33 bright, UserMaterialColor1-32 deep, MaterialTeamGreen)
DYE = {
    "lime": "MaterialTeamGreen",        # (0, 255, 0): the game's team green, the one true lime
    "gold": "UserColor11",              # (208, 167, 16)
    "violet": "UserColor14",            # (170, 16, 208)
    "plum": "UserMaterialColor30",      # (48, 10, 53)
    "black": "UserMaterialColor32",     # (42, 42, 42)
    "coal": "UserMaterialColor24",      # (70, 70, 70)
    "grey": "UserColor24",              # (100, 100, 100)
    "crimson": "UserColor17",           # (149, 0, 0)
    "red": "UserColor9",                # (208, 21, 21)
    "darkred": "UserMaterialColor17",   # (113, 0, 0)
    "orange": "UserColor10",            # (208, 110, 16)
    "rust": "UserMaterialColor2",       # (176, 88, 3)
    "green": "UserColor20",             # (21, 122, 34)
    "forest": "UserMaterialColor20",    # (9, 98, 45)
    "brown": "UserColor15",             # (137, 87, 54)
    "umber": "UserColor23",             # (88, 57, 35)
    "teal": "UserColor4",               # (85, 214, 149): sea green (UserColor28+ are not in the editor's modifier list)
    "blue": "UserColor13",              # (16, 111, 208)
    "sky": "UserColor5",                # (86, 167, 214)
    "navy": "UserMaterialColor13",      # (17, 72, 127)
    "white": "UserColor8",              # (209, 209, 209)
}


def piece(t, main=None, trim=None, quality=2, extra=None):
    """One armour piece worn: its main surface and trim in the colours named (DYE), its quality (ArmorQuality1-6, the
    EFFECTIVENESS slot, unless a colour needs that slot) and one more enchantment in a free slot (FireProtect1 ...)."""
    e = [f"ArmorQuality{quality}" if quality else "", "", "", ""]
    if main: e[MAIN.get(t, 1)] = DYE[main]
    if trim: e[TRIM.get(t, 2)] = DYE[trim]
    if extra:
        k = next(k for k in (3, 2, 1) if not e[k])
        e[k] = extra
    return dict(type=t, xfer={"Enchantments": e}, create_flags=EQUIPPED)


def suit(types, main=None, trim=None, quality=2):
    return [piece(t, main, trim, quality) for t in types]


# Skin and hair (NPCColors: 6 slots; Westwood's hostile NPCs keep the skin tones below)
SKIN = {"fair": (210, 174, 121), "tan": (178, 147, 103), "dark": (119, 96, 63), "pale": (225, 200, 170)}
HAIR = {"black": (15, 11, 8), "brown": (63, 52, 36), "grey": (130, 128, 125), "white": (230, 230, 225),
        "red": (140, 50, 20), "blond": (200, 170, 90)}

# A hostile NPC's settings, from Westwood's own (Con06b's elite guards, Con03A's wizards): every field the writer needs
# (NPCXfer has no defaults of its own).
BASE_XFER = {
    "DirectionId": 1, "ScriptEvents": [""] * 10, "DetectEventTimeout": 0, "ActionRoamPathFlag": 0,
    "StatusFlags": "CAN_DODGE", "HealthMultiplier": 1.0, "RetreatRatio": 0.0, "ResumeRatio": 0.75, "SightRange": 400.0,
    "Aggressiveness": 0.83, "DefaultAction": 4, "EscortObjName": "", "KnownSpells": [],
    "ReactionCastingDelayMin": 0, "ReactionCastingDelayMax": 15, "BuffCastingDelayMin": 90, "BuffCastingDelayMax": 300,
    "DebuffCastingDelayMin": 90, "DebuffCastingDelayMax": 180, "OffensiveCastingDelayMin": 0,
    "OffensiveCastingDelayMax": 90, "BlinkCastingDelayMin": 0, "BlinkCastingDelayMax": 180, "LockPathDistance": 30.0,
    "NPCStrength": 100, "NPCSpeed": 1.0, "SpellPowerLevel": 2, "AimSkillLevel": 0.8, "Immortal": False,
    "TrapSpell1": "SPELL_INVALID", "TrapSpell2": "SPELL_INVALID", "TrapSpell3": "SPELL_INVALID",
    "MagicNumber": 3735943886, "AddedSubclass": 0, "Health": 250, "MaxHealth": 250,
    "NPCColors": [SKIN["fair"], HAIR["brown"], SKIN["fair"], SKIN["fair"], HAIR["brown"], SKIN["fair"]],
    "NPCVoiceSet": "NPC", "BuffList": [], "Experience": 2000.0, "PoisonLevel": 0,
}


def S(name, flags):
    return {"SpellName": name, "UseFlags": flags}


METAL = {"OrnateHelm", "SteelHelm", "Breastplate", "PlateArms", "PlateLeggings", "PlateBoots", "ChainCoif",
         "ChainTunic", "ChainLeggings", "SteelShield"}
PLATE = ["SteelHelm", "Breastplate", "PlateArms", "PlateLeggings", "PlateBoots"]
CHAIN = ["ChainCoif", "ChainTunic", "ChainLeggings", "LeatherArmoredBoots"]
LEATHER = ["LeatherHelm", "LeatherArmor", "LeatherArmbands", "LeatherLeggings", "LeatherBoots"]
ROBES = ["WizardHelm", "WizardRobe", "LeatherBoots"]


def weapon(t, *enchantments):
    """The weapon the boss holds (or a quiver it wears), put on as it loads. A wand never runs dry (WandChargesLimit
    0: the game spends and counts charges only under a limit, GAME4.c; an NPC drops an empty wand)."""
    o = dict(type=t, create_flags=EQUIPPED)
    x = {}
    if enchantments: x["Enchantments"] = (list(enchantments) + ["", "", "", ""])[:4]
    if t.endswith("Wand") and t != "StaffWooden": x.update(WandChargesCurrent=255, WandChargesLimit=0)
    if x: o["xfer"] = x
    return o


# The ten bosses. kind: the script's ability set (bosses.go). Each gear list is what the NPC carries: the game's NPC
# puts on the armour and takes up the weapon it carries.
BOSSES = {}


def _catalogue():
    B = BOSSES
    B["B1"] = dict(kind="archmage", caster=True, name="Vael the Unbound", title="Archmage", hp=420, voice="_Wizard1",
        skin="pale", hair="white", strength=60, speed=0.9,
        gear=[piece("WizardHelm", "violet", "gold", 3), piece("WizardRobe", "violet", "gold"),
              piece("MedievalCloak", "coal", "violet"), piece("LeatherBoots", "plum")] + [weapon("DeathRayWand")],
        spells=[S("SPELL_FIREBALL", OFFENSIVE), S("SPELL_LIGHTNING", OFFENSIVE), S("SPELL_SHIELD", DEFENSIVE),
                S("SPELL_SLOW", DISABLING), S("SPELL_COUNTERSPELL", REACTION), S("SPELL_BLINK", ESCAPE)],
        text="B1 VAEL THE UNBOUND, archmage. Violet robes and a Death Ray staff. He keeps his distance and blinks away "
             "from your blade. Step out of the violet rings: a death ray falls there.")
    B["B2"] = dict(kind="warlord", name="Sir Garrick the Verdant", title="Warlord", hp=700, voice="_FireKnight1",
        skin="tan", hair="red", strength=80, speed=0.75,
        gear=suit(PLATE, "lime", "gold", 3) + [weapon("OgreAxe")],
        spells=[],
        text="B2 SIR GARRICK THE VERDANT, warlord. Lime green plate and an ogre axe. When he roars, he charges in a "
             "straight line: sidestep it, and if he hits a pillar or a wall he is dazed and takes extra damage.")
    B["B3"] = dict(kind="golemwright", caster=True, name="Oskar Thorne, the Golemwright", title="Conjurer", hp=460, voice="_MaleNPC1",
        skin="tan", hair="grey", strength=25, speed=0.9,
        gear=[piece("ConjurerHelm", "forest", "brown"), piece("LeatherArmor", "green", "brown"),
              piece("LeatherArmbands", "brown"), piece("LeatherLeggings", "forest"), piece("LeatherArmoredBoots", "brown")] +
             [weapon("Bow"), weapon("Quiver"), weapon("Quiver")],
        spells=[S("SPELL_SLOW", DISABLING), S("SPELL_STUN", DISABLING), S("SPELL_INVISIBILITY", ESCAPE)],
        text="B3 OSKAR THORNE, the Golemwright. MAJOR MINIONS: by ritual he raises stone and iron golems. Strike him hard "
             "while he chants to break the binding. Wolves at his heel; he hides behind them.")
    B["B4"] = dict(kind="necromancer", caster=True, name="Lord Mortivane", title="Necromancer", hp=520, voice="Necromancer",
        skin="pale", hair="black", strength=70, speed=0.85,
        gear=[piece("WizardHelm", "coal", "black", 3), piece("WizardRobe", "coal", "crimson", 3),
              piece("MedievalCloak", "crimson", "coal"), piece("LeatherBoots", "black")] + [weapon("InfinitePainWand")],
        spells=[S("SPELL_FUMBLE", DISABLING), S("SPELL_SLOW", DISABLING), S("SPELL_COUNTERSPELL", REACTION),
                S("SPELL_BLINK", ESCAPE)],
        text="B4 LORD MORTIVANE, necromancer. MAJOR MINIONS: skeleton lords at 60% health, a lich at 30%. His tether "
             "drinks your life: break line of sight or run. Every servant that falls feeds him.")
    B["B5"] = dict(kind="assassin", name="Silas Vane, the Quiet Knife", title="Assassin", hp=380, voice="_MaleNPC2",
        skin="fair", hair="black", strength=90, speed=1.15,
        gear=suit(LEATHER, "black", "grey") + [weapon("Sword", "WeaponPower3", "Material4")],
        spells=[],
        text="B5 SILAS VANE, the Quiet Knife. Black leather, a short blade, poison. He stalks unseen to strike from "
             "behind: watch for footfall dust and keep turning. Hit him while hidden and he stumbles.")
    B["B6"] = dict(kind="ranger", name="Garet Hawkeye", title="Ranger", hp=420, voice="_Guard1",
        skin="tan", hair="blond", strength=30, speed=1.05,
        gear=suit(["ChainCoif", "ChainTunic", "ChainLeggings"], "teal", "white") + [piece("LeatherArmoredBoots", "umber"),
              piece("MedievalCloak", "green", "teal")] + [weapon("Bow"), weapon("Quiver"), weapon("Quiver")],
        spells=[],
        text="B6 GARET HAWKEYE, ranger. Sea-green chain and a longbow. He keeps his range, leaps back from you and leaves "
             "bear traps where he stood. Fans of arrows; a yellow ring means arrows are falling there.")
    B["B7"] = dict(kind="stormblade", name="Dravik Stormblade", title="Spellsword", hp=620, voice="_FireKnight2",
        skin="fair", hair="blond", strength=40, speed=1.0,
        gear=suit(["OrnateHelm", "Breastplate", "PlateArms", "PlateBoots"], "blue", "sky", 3) +
             [piece("ChainLeggings", "navy", "sky", 3), weapon("GreatSword", "WeaponPower3", "Material5")],
        spells=[],
        text="B7 DRAVIK STORMBLADE, spellsword. Blue plate and a great sword. Blade stance: he hunts you, stepping "
             "on lightning. Storm stance: he stands and calls bolts. Stay away from the storm, close in on the blade.")
    B["B8"] = dict(kind="whirlwind", name="Kesh of the Red Sands", title="Chakram dancer", hp=440, voice="_MaleNPC2",
        skin="dark", hair="black", strength=110, speed=1.1,
        gear=[piece("LeatherHelm", "orange", "red"), piece("ChainTunic", "orange", "red"), piece("LeatherArmbands", "rust"),
              piece("LeatherLeggings", "rust"), piece("LeatherArmoredBoots", "umber")] + [weapon("RoundChakram")],
        spells=[],
        text="B8 KESH OF THE RED SANDS, chakram dancer. Orange leathers, a chakram. He circles you at range and "
             "throws; his chakrams come back. Close in and he spins into a whirlwind: step back until it ends.")
    B["B9"] = dict(kind="pyromancer", caster=True, name="Ignis Varr", title="Pyromancer", hp=480, voice="_Wizard2",
        skin="tan", hair="red", strength=60, speed=0.95,
        gear=[piece("WizardHelm", "red", "orange", 3), piece("WizardRobe", "red", "orange", 3, extra="FireProtect1"),
              piece("LeatherBoots", "darkred")] + [weapon("FireStormWand")],
        spells=[S("SPELL_FIREBALL", OFFENSIVE), S("SPELL_PROTECTION_FROM_FIRE", DEFENSIVE)],
        text="B9 IGNIS VARR, pyromancer. Red robes and a Fire Storm staff; fire cannot hurt him. He leaves burning "
             "footsteps, walls of flame and meteors (yellow rings). Too close and fire bursts from him.")
    B["B10"] = dict(kind="paladin", name="High Warden Aurelian", title="Paladin", hp=760, voice="_Guard2",
        skin="fair", hair="blond", strength=150, speed=0.8,
        gear=suit(["OrnateHelm", "Breastplate", "PlateArms", "PlateLeggings", "PlateBoots"], "white", "gold", 3) +
             [piece("SteelShield", "white", "gold", 0), weapon("MorningStar", "WeaponPower2", "Material4")],
        spells=[],
        text="B10 HIGH WARDEN AURELIAN, paladin. White plate, shield and mace. His shield turns blows from the "
             "front: flank him. He kneels to heal: hit him hard to break the prayer. From afar he drags you in.")


class Bosses:
    def __init__(self, spec):
        self.spec = spec
        self.calls = []
        self.placed = []
        if not BOSSES: _catalogue()

    def npc(self, bid, x, y, name, face=None, frozen=False):
        """One dressed NPC of boss `bid` at world pixel (x, y), script name `name`."""
        from kit.npcs import facing
        b = BOSSES[bid]
        x_ = copy.deepcopy(BASE_XFER)
        hair, skin = HAIR[b["hair"]], SKIN[b["skin"]]
        x_.update(DirectionId=facing(face[0] - x, face[1] - y) if face else 1, KnownSpells=list(b["spells"]),
                  NPCStrength=b["strength"], NPCSpeed=b["speed"], NPCVoiceSet=b["voice"], Health=b["hp"],
                  MaxHealth=b["hp"], NPCColors=[hair, skin, skin, skin, skin, skin],
                  StatusFlags=CAN_DODGE | CAN_SEE_FRIENDS | (CAN_CAST if b["spells"] and b.get("caster") else 0) |
                  (CAN_BLOCK if any(g["type"].endswith("Shield") for g in b["gear"]) else 0))
        o = self.spec.obj_px("NPC", x, y, scr=name, items=list(b["gear"]), xfer=x_)
        self.placed.append(o)
        return o

    def boss(self, bid, x, y, face=None, spares=(), engage=320.0, respawn=30.0, name=None):
        """Boss `bid` at world pixel (x, y) facing the point `face`; its spare copies at `spares` (a sealed room);
        it waits frozen until its foe is within `engage` px (0: awake from the start) and comes back `respawn` s
        after it dies, once per spare."""
        b = BOSSES[bid]
        name = name or f"{bid}_{b['kind'].capitalize()}"
        names = [name]
        self.npc(bid, x, y, name, face)
        for k, (sx, sy) in enumerate(spares):
            nm = f"{name}_Spare{k + 1}"
            self.npc(bid, sx, sy, nm)
            names.append(nm)
        self.calls.append(f"BossDef({json.dumps(b['kind'])}, {json.dumps(b['name'])}, {int(b['hp'])}, "
                          f"{float(engage):.1f}, {float(respawn):.1f}, []string{{{', '.join(json.dumps(n) for n in names)}}})")
        return name

    def files(self, map_name):
        pkg = map_name.lower()
        lib = open(os.path.join(HERE, "behaviours", "bosses.go"), encoding="utf-8").read()
        lib = lib.replace("package PKG", f"package {pkg}", 1)
        cfg = (f"package {pkg}\n\n// The bosses on {map_name} (written by dystopiannox mapgen/kit/bosses.py).\n\n"
               'import "github.com/noxworld-dev/noxscript/ns/v4"\n\n'
               "var bossesSetUp bool\n\nfunc setUpBosses() {\n\tif bossesSetUp {\n\t\treturn\n\t}\n\tbossesSetUp = true\n" +
               "".join(f"\t{c}\n" for c in self.calls) + "\tStartBosses()\n}\n\n"
               # on MapInitialize, or after a second of frames if it never fires (the dedicated server: kit/quests.py)
               "func init() {\n\tns.OnMapEvent(ns.MapInitialize, setUpBosses)\n\tbframes := 0\n"
               "\tns.OnEachFrame(1, func() {\n\t\tif bframes++; bframes == 30 {\n\t\t\tsetUpBosses()\n\t\t}\n\t})\n}\n")
        from kit.quests import events_go
        return {"bosses.go": lib, "bosses_config.go": cfg, "events.go": events_go(pkg)}

    def attach(self):
        if self.calls:
            self.spec.scripts.update(self.files(self.spec.d["name"]))
