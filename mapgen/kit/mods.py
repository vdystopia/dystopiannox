"""Creative additions to the base game, placeable on any map (kit/behaviours/mods.go; dystopiannox/mods/MODLAB.md):
power weapons (W1-W6), new monsters (M1-M5), respawning training targets, and the smithing forge (S1).

    from kit.mods import Mods, WEAPONS, MONSTERS
    mods = Mods(spec)                                   # or Mods(spec, pop) to share a kit.npcs Population
    mods.weapon("W3", x, y)                             # a Quake Hammer on the floor
    chest = spec.obj_px("Chest4", x, y, items=[mods.weapon_item("W5"), "RedPotion"])   # or in a chest
    mods.monster("M1", x, y)                            # the Ogre Lord: frozen until the player is within 230 px
    mods.monster("M5", x, y, wait=0, respawn=0)         # the Blink Duelist, awake from the start, never back
    mods.trainee("GruntAxe", x, y)                      # a target that comes back 6 s after it dies
    mods.forge(anvil_xy, smith_xy, plate_xy, vault_uv=(400, -12))   # the forge and its sealed vault
    mods.test_cell(400, -48)                            # optional: where the dedicated-server self-test stands
    mods.attach()                                       # last: mods.go + mods_config.go into spec.scripts
                                                        # (mods.attach(pop.behaviours) on a map with kit.npcs sets)

Every call above writes the objects into the spec and records the script call that gives them their power; attach()
writes the map's two script files (the library, package named after the map, and its config). Script names are made
unique per map (W3_1, M1_1...) unless given.
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
SMITH_DONOR = (r"C:\GOG Games\Nox\maps\Con02a\Con02a.map", "Con02a:Bryan")

# ---- the catalogue ------------------------------------------------------------------------------------------------
# Weapons: kind (the script power), base (thing.bin type), who can use it (the game's class rules), tiers (the game's
# own enchantments, slot order WeaponPower, Material, effect, effect: tier 0 is what weapon() places by default), and
# the text for its sign.
WEAPONS = {
    "W1": dict(name="Flamebrand", kind="flame", base="Longsword", who="warrior",
               tiers=[["WeaponPower1", "Material1", "FireRing1"], ["WeaponPower2", "Material2", "FireRing2"],
                      ["WeaponPower4", "Material4", "FireRing3"], ["WeaponPower6", "Material6", "FireRing4", "Vampirism1"]],
               text="W1 FLAMEBRAND (longsword, warrior)\nEvery swing throws a ring of fire round you, hit or miss. This "
                    "is the game's own FireRing enchantment, hidden in Nox's data and almost unused by Westwood, so it is "
                    "fully reliable. Forge it at S1 for a bigger ring (FireRing 2, 3, 4)."),
    "W2": dict(name="Chakram Storm", kind="chakram", base="RoundChakram", who="warrior", tiers=[[]],
               text="W2 CHAKRAM STORM (chakram, warrior)\nThrow it: four more chakrams fan out beside it (30 and 15 "
                    "degrees either side), cut every creature they pass and fly back to you."),
    "W3": dict(name="Quake Hammer", kind="quake", base="WarHammer", who="warrior",
               tiers=[["WeaponPower1", "Material1"], ["WeaponPower2", "Material2"],
                      ["WeaponPower4", "Material4", "Impact1"], ["WeaponPower6", "Material6", "Impact2", "Stun1"]],
               text="W3 QUAKE HAMMER (war hammer, warrior)\nEvery blow that lands sends a shockwave from the creature "
                    "struck: the ground shakes, everything near it is hurt and thrown back. Forge it at S1 for a wider, "
                    "harder quake."),
    "W4": dict(name="Stormcaller", kind="storm", base="LesserFireballWand", who="wizard or conjurer", tiers=[[]],
               xfer=dict(WandChargesCurrent=200, WandChargesLimit=200),
               text="W4 STORMCALLER (staff, wizard or conjurer)\nInstead of a fireball it calls chain lightning: the "
                    "first creature in front of you, then up to three more nearby, each strike weaker."),
    "W5": dict(name="Bloodthirst", kind="blood", base="GreatSword", who="warrior", tiers=[[]],
               text="W5 BLOODTHIRST (great sword, warrior)\nEvery blow that lands drinks 3 health. A kill feasts: 15 "
                    "health and three seconds of haste."),
    "W6": dict(name="Frostbite", kind="frost", base="MorningStar", who="warrior", tiers=[[]],
               text="W6 FROSTBITE (morning star, warrior)\nEvery blow slows the creature for 4 seconds. Three blows on "
                    "one creature within 5 seconds freeze it solid for 2.5 seconds."),
}

# Monsters: kind (the script ability set), base creature, health, difficulty for a warrior of the early chapters with
# a power weapon (easy < medium < hard < boss), and the sign text.
MONSTERS = {
    "M1": dict(name="The Ogre Lord", kind="ogrelord", base="OgreWarlord", hp=700, difficulty="boss",
               text="M1 OGRE LORD (an ogre warlord)\nHurls boomerang chakrams that cut you going out and coming back; "
                    "below half health he throws three at once. Catch him between throws."),
    "M2": dict(name="The Giant Crab", kind="crab", base="Scorpion", hp=450, difficulty="hard",
               text="M2 GIANT CRAB (a scorpion: Nox has no crab art; the scorpion is the armoured, pincered creature "
                    "closest to one)\nIts shell turns two thirds of every blow. It scuttles sideways round you; its snap "
                    "pins you for a moment and leaves the shell gaping for two seconds: strike then."),
    "M3": dict(name="The Bone Caller", kind="bonecaller", base="Necromancer", hp=320, difficulty="hard",
               text="M3 BONE CALLER (a necromancer)\nRaises skeletons two at a time, four at most. While two or more "
                    "stand, a bone ward turns half of every blow. Kill him and they crumble."),
    "M4": dict(name="The Ember Matriarch", kind="embermother", base="EmberDemon", hp=380, difficulty="hard",
               text="M4 EMBER MATRIARCH (an ember demon)\nBirths imps, five at most, and mends a little for every imp "
                    "alive. Each imp bursts into flame when it dies: do not stand on it. Her brood bursts when she falls."),
    "M5": dict(name="The Blink Duelist", kind="duelist", base="Swordsman", hp=280, difficulty="medium",
               text="M5 BLINK DUELIST (a swordsman)\nSteps through space to stand behind you and strike. Once, when badly "
                    "hurt, a ward makes him untouchable for two seconds."),
}

# The forge's lines: what the anvil knows how to raise, a tier at a time (vault copies carry the tiers' enchantments).
FORGE_LINES = {
    "flamebrand": dict(label="Flamebrand", weapon="W1"),
    "quake": dict(label="Quake Hammer", weapon="W3"),
    "longsword": dict(label="Longsword", base="Longsword",
                      tiers=[[], ["WeaponPower2", "Material2"], ["WeaponPower4", "Material4", "Fire2"],
                             ["WeaponPower6", "Material6", "Fire4", "Lightning2"]]),
    "battleaxe": dict(label="Battle Axe", base="BattleAxe",
                      tiers=[[], ["WeaponPower2", "Material2"], ["WeaponPower4", "Material4", "Vampirism2"],
                             ["WeaponPower6", "Material6", "Vampirism4", "Stun2"]]),
}

# Creatures that cannot be placed: none (see kit/npcs.UNPLACEABLE). The Skeleton and Wolf failures found on ModLab
# 2026-10-09 were the map writer's missing spare block (Shared/Map.cs, checker rule setup.file_tail), not the creatures.
UNSAFE_PLACED = set()

KINDS = {w["kind"] for w in WEAPONS.values()}
MONSTER_KINDS = {m["kind"] for m in MONSTERS.values()} | {"trainee"}


def _s(names):
    return "[]string{" + ", ".join(json.dumps(n) for n in names) + "}"


def _ench(e):
    e = list(e)
    return e + [""] * (4 - len(e))


class Mods:
    def __init__(self, spec=None, pop=None, rng=None):
        self.spec, self._pop, self.rng = spec, pop, rng
        self.calls = []
        self._n = {}

    # ---- naming, the population -----------------------------------------------------------------------------------
    def _name(self, stem):
        self._n[stem] = self._n.get(stem, 0) + 1
        return f"{stem}_{self._n[stem]}"

    @property
    def pop(self):
        if self._pop is None:
            import random
            from kit.npcs import Population
            self._pop = Population(self.spec, self.rng or random.Random(1))
        return self._pop

    # ---- weapons --------------------------------------------------------------------------------------------------
    def weapon_obj(self, wid, tier=0, name=None):
        """The object dict of power weapon `wid` (W1-W6) at `tier` (0-3; W1 and W3 change their enchantments with it,
        the others scale their power), named, with its power registered. Not yet placed: weapon() puts it on the
        floor, weapon_item() into a container."""
        w = WEAPONS[wid]
        name = name or self._name(wid)
        tiers = w["tiers"]
        x = dict(w.get("xfer", {}))
        ench = tiers[min(tier, len(tiers) - 1)]
        if ench: x["Enchantments"] = _ench(ench)
        from nox import Spec
        o = Spec.item(w["base"], 0, 0, scr=name, **({"xfer": x} if x else {}))
        self.weapon_call(w["kind"], name, tier)
        return o

    def weapon(self, wid, x, y, tier=0, name=None):
        """Power weapon `wid` lying on the floor at world pixel (x, y). Returns the object dict."""
        o = self.weapon_obj(wid, tier, name)
        o["x"], o["y"] = round(x, 1), round(y, 1)
        self.spec.d["objects"].append(o)
        return o

    def weapon_item(self, wid, tier=0, name=None):
        """Power weapon `wid` as an item for a container: spec.obj_px("Chest4", x, y, items=[mods.weapon_item("W2")])
        (the script finds an item in a chest by its name: ModLab's self-test checks it)."""
        return self.weapon_obj(wid, tier, name)

    def weapon_call(self, kind, name, tier=0):
        """Low level: give the named weapon object power `kind`."""
        assert kind in KINDS, kind
        self.calls.append(f"ModWeapon({json.dumps(kind)}, {json.dumps(name)}, {int(tier)})")

    # ---- monsters -------------------------------------------------------------------------------------------------
    def monster(self, mid, x, y, name=None, wait=230.0, respawn=0.0, hp=None, face=None, action="guard"):
        """New monster `mid` (M1-M5) at world pixel (x, y). wait: it stands frozen until the player comes within this
        many px (or strikes it); 0 = awake from the start. respawn: seconds after its death it comes back where it
        was placed; 0 = never. hp: its health (default the catalogue's). Returns the object dict."""
        m = MONSTERS[mid]
        name = name or self._name(mid)
        o = self.pop.creature(m["base"], x, y, action=action, face=face, scr=name, aggr=0.83)
        self.monster_call(m["kind"], name, m["name"], m["hp"] if hp is None else hp, wait, respawn)
        return o

    def trainee(self, t, x, y, name=None, wait=150.0, respawn=6.0, face=None):
        """A training target: any creature type, frozen until the player comes within `wait` px or strikes it, back
        `respawn` seconds after it dies."""
        assert t not in UNSAFE_PLACED, f"{t} cannot be placed on OpenNox alpha13 (UNSAFE_PLACED)"
        name = name or self._name("Trainee")
        o = self.pop.creature(t, x, y, action="idle", face=face, scr=name)
        self.monster_call("trainee", name, f"Training target {name}", 0, wait, respawn)
        return o

    def monster_call(self, kind, name, label, hp=0, wait=230.0, respawn=0.0):
        """Low level: turn the named placed creature into monster `kind`."""
        assert kind in MONSTER_KINDS, kind
        self.calls.append(f"ModBoss({json.dumps(kind)}, {json.dumps(name)}, {json.dumps(label)}, {int(hp)}, "
                          f"{float(wait):.1f}, {float(respawn):.1f})")

    # ---- the forge ------------------------------------------------------------------------------------------------
    def forge(self, anvil, smith, plate, vault_uv, lines=("flamebrand", "quake", "longsword", "battleaxe"), copies=2,
              plate_floor="LOTDBlackMarble", tier0=None):
        """The smithing forge: an anvil at world pixel `anvil`, the smith (a townsman, frozen at his post) at `smith`
        (keep him within ~50 px of the anvil: he drops forged pieces at his feet, and the anvil takes what lies within
        110 px), the forge plate (a patch of `plate_floor` the player stands on) at `plate`, about 130 px from the
        anvil. vault_uv: (u0, v0) of a sealed 20x24 room this builds to hold the forged copies, `copies` of each tier
        of a plain line, one of each tier of a power weapon's line. tier0: {line: [names]} of placed weapons the line
        starts from (a power weapon's line needs its weapon's name; plain lines take any weapon of the base type)."""
        from nox import px
        s = self.spec
        s.obj_px("Anvil2", *anvil, scr="S1_Anvil")
        cx, cy = int(plate[0] // 23), int(plate[1] // 23)
        for dx in range(-1, 3):
            for dy in range(-1, 3):
                s.tile(cx + dx, cy + dy, plate_floor)
        s.clone(SMITH_DONOR[0], SMITH_DONOR[1], *smith, name="S1_Smith", xfer={"DirectionId": 1})
        self.calls.append(f"ModForge(\"S1_Anvil\", {plate[0]:.1f}, {plate[1]:.1f}, \"S1_Smith\")")
        u0, v0 = vault_uv
        s.room(u0, u0 + 20, v0, v0 + 24, wall="BrickPlain", floor="CobbleStone")
        slot = 0
        for key in lines:
            L = FORGE_LINES[key]
            if "weapon" in L:
                w = WEAPONS[L["weapon"]]
                base, kind, tiers, n = w["base"], w["kind"], w["tiers"], 1
            else:
                base, kind, tiers, n = L["base"], "", L["tiers"], copies
            names = []
            for t in (1, 2, 3):
                tn = []
                for c in range(n):
                    nm = f"Forge_{key}_{t}_{c + 1}"
                    x = {"Enchantments": _ench(tiers[t])} if tiers[t] else {}
                    s.obj_px(base, *px(u0 + 3 + 3 * (slot % 6), v0 + 3 + 3 * (slot // 6)), scr=nm,
                             **({"xfer": x} if x else {}))
                    slot += 1
                    tn.append(nm)
                names.append(tn)
            self.forge_line(key, L["label"], base, kind, (tier0 or {}).get(key, []), *names)

    def forge_line(self, key, label, base, kind="", named0=(), t1=(), t2=(), t3=()):
        """Low level: a line the forge knows (kit/behaviours/mods.go ModForgeLine)."""
        self.calls.append(f"ModForgeLine({json.dumps(key)}, {json.dumps(label)}, {json.dumps(base)}, {json.dumps(kind)}, "
                          f"{_s(named0)}, {_s(t1)}, {_s(t2)}, {_s(t3)})")

    # ---- the self-test cell, the scripts --------------------------------------------------------------------------
    def test_cell(self, u0, v0):
        """A sealed 30x28 room at (u0, v0) with the ModTestSpot waypoint: where the self-test (dedicated server, no
        player: tests/server_smoke.py) stands its stand-in creatures. Without it they stand beside the first monster."""
        from nox import px
        self.spec.room(u0, u0 + 30, v0, v0 + 28, wall="BrickPlain", floor="CobbleStone")
        self.spec.waypoint(*px(u0 + 15, v0 + 14), name="ModTestSpot")
        self.calls.append('ModTestCell("ModTestSpot")')

    def files(self, map_name):
        """{filename: Go source}: the library and the map's calls, package named after the map."""
        pkg = map_name.lower()
        lib = open(os.path.join(HERE, "behaviours", "mods.go"), encoding="utf-8").read().replace("package PKG", f"package {pkg}", 1)
        cfg = (f"package {pkg}\n\n// The mods on {map_name} (written by dystopiannox mapgen/kit/mods.py).\n\n"
               'import "github.com/noxworld-dev/noxscript/ns/v4"\n\n'
               "var modsSetUp bool\n\nfunc setUpMods() {\n\tif modsSetUp {\n\t\treturn\n\t}\n\tmodsSetUp = true\n" +
               "".join(f"\t{c}\n" for c in self.calls) + "\tStartMods()\n}\n\n"
               # on MapInitialize, or after a second of frames if it never fires (the dedicated server: kit/quests.py)
               "func init() {\n\tns.OnMapEvent(ns.MapInitialize, setUpMods)\n\tmframes := 0\n"
               "\tns.OnEachFrame(1, func() {\n\t\tif mframes++; mframes == 30 {\n\t\t\tsetUpMods()\n\t\t}\n\t})\n}\n")
        from kit.quests import events_go
        return {"mods.go": lib, "mods_config.go": cfg, "events.go": events_go(pkg)}

    def attach(self, behaviours=None):
        """The map's script files into spec.scripts (call once everything is placed, after kit.npcs Behaviours have
        all their calls). behaviours: that map's kit.npcs Behaviours, whose creatures keep their own event callbacks
        (an object has one callback per event: mods.go leaves them alone, so melee powers do not fire on them)."""
        # (behaviours: kept for callers; since events.go every script shares a creature's events, so the mods watch
        # the behaviours' creatures too and nothing needs leaving alone)
        if self.calls:
            self.spec.scripts.update(self.files(self.spec.d["name"]))
