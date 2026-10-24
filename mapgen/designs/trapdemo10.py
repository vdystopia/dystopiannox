"""TrapDemo 10: The Warlord's Trial (map TrapDem10; kit/trapdemo.py Mission). The showpiece: a warlord's castle run as a
trial, hall by hall, every kind of trap, and the warlord waiting in his arena.

The story
- The hook: Herald Evelyn keeps a camp at the castle gate, where the trial's challengers set out. Sir Garrick the
  Verdant holds the castle and calls every fighter in the land to run his trial and face him in the arena; none has
  come back. The realm has sent her to see it ended.
- Main quest (the trial): run the trial from the gatehouse to the arena, defeat Garrick there and bring the Gold Key
  of the castle from his strongroom back to Evelyn, who pays.
- Side quest (the champion's amulet): the last champion, Sir Roderick, fell in the arena; Garrick hung his amulet
  in the trophy hall, behind a passage of pits off the great hall. Evelyn gives haste potions for it (against
  Garrick's charge). The champion's banner hangs there too, but a banner is no thing to carry: the amulet is.
- The trial, in the order a player meets it (standard first, the hard ones after the middle, a rest at the garden
  court's healing well off the great hall): a spike field on a clock at the gate; race the gate to the barracks;
  the click and the pause, arrows, to the great hall; then the hard halls: find the gap (blades) to the throne room
  and the gliding beam into the arena. Off the trial, each a dead end with its own reward: the fire wave to the
  kitchen, the belts to the question room, look before you leap (pits) to the trophy hall (the side quest), the
  snapping jaws from the garden court to the chapel's offering, and the glyphs and the warden to Garrick's war room.
  Every kind of trap once: spike, trigger, flame, arrow, push, blade, pit, block, sentry, spell.
- The layout: thirteen rooms and twelve passages are more than kit/trapdemo.py's greedy tree fits in the map, so
  Trial backtracks (the same geometry and spacing).

    py mapgen/designs/trapdemo10.py [out_dir|-]
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from kit.trapdemo import Mission, DIRS
from kit.quests import A
from kit.trapdemo_dress import camp, clear_mouths, start_spot, free_spot, extra


class Trial(Mission):
    """A mission whose layout backtracks: thirteen rooms and twelve passages are more than kit/trapdemo.py's greedy
    tree (each room's children placed in turn, a whole try dropped when one finds no side) fits in the map's diamond,
    so a child that finds no side here undoes its elder siblings' choices and tries again (the same geometry and
    spacing as Mission._try_layout: a passage leaves the middle of a free side, two squares clear of everything but
    its own room)."""

    def _try_layout(self, root, children, start, rng, budget=60000):
        def room_sq(rid, ci, cj):
            w, h = self.rooms[rid]["size"]
            return {(i, j) for i in range(ci - w // 2, ci - w // 2 + w) for j in range(cj - h // 2, cj - h // 2 + h)}

        def box_sq(i0, j0, L, W, axis, sign):
            if axis == "i":
                ii = range(i0, i0 + L) if sign > 0 else range(i0 - L, i0)
                return {(i, j) for i in ii for j in range(j0, j0 + W)}
            jj = range(j0, j0 + L) if sign > 0 else range(j0 - L, j0)
            return {(i, j) for i in range(i0, i0 + W) for j in jj}

        def grow(sq, m=2):
            return {(i + a, j + b) for i, j in sq for a in range(-m, m + 1) for b in range(-m, m + 1)}

        def ok(sq):
            return all(8 <= i + j <= 246 and 8 <= i - j <= 246 for i, j in sq)

        order, queue = [], [root]
        while queue:                                   # the links in the kit's order: breadth first from the camp
            r = queue.pop(0)
            for L_ in children.get(r, []):
                order.append(L_); queue.append(L_["b"])
        own0 = room_sq(root, *start)
        if not ok(own0): return None
        rooms, sides, out, owns, taken = {root: start}, {root: set()}, [], {root: own0}, set(own0)
        left = [budget]

        def place(k):
            if k == len(order): return True
            left[0] -= 1
            if left[0] < 0: return False
            L_ = order[k]
            rid, b = L_["a"], L_["b"]
            ci, cj = rooms[rid]
            w, h = self.rooms[rid]["size"]
            bw, bh = self.rooms[b]["size"]
            own = owns[rid]
            cand = [d for d in DIRS if d not in sides[rid]]
            rng.shuffle(cand)
            for d in cand:
                Lp, Wp = L_["length"], L_["width"]
                axis = "i" if d[0] else "j"
                sign = d[0] or d[1]
                if d == (1, 0):
                    i0, j0 = ci - w // 2 + w, cj - Wp // 2
                    ni, nj = i0 + Lp + bw // 2, cj
                elif d == (-1, 0):
                    i0, j0 = ci - w // 2, cj - Wp // 2
                    ni, nj = i0 - Lp - bw + bw // 2, cj
                elif d == (0, 1):
                    i0, j0 = ci - Wp // 2, cj - h // 2 + h
                    ni, nj = ci, j0 + Lp + bh // 2
                else:
                    i0, j0 = ci - Wp // 2, cj - h // 2
                    ni, nj = ci, j0 - Lp - bh + bh // 2
                sq = box_sq(i0, j0, Lp, Wp, axis, sign)
                rq = room_sq(b, ni, nj)
                new = sq | rq
                if not ok(new): continue
                # two squares clear of everything but the parent room (the passage leaves it), the room of all
                if any(c in taken and c not in own for c in grow(new, 2)) or any(c in taken for c in grow(rq, 2)):
                    continue
                rooms[b] = (ni, nj); sides[rid].add(d); sides[b] = {(-d[0], -d[1])}; owns[b] = rq
                out.append((L_, axis, sign, i0, j0)); taken.update(new)
                if place(k + 1): return True
                del rooms[b]; sides[rid].discard(d); del sides[b]; del owns[b]; out.pop(); taken.difference_update(new)
            return False

        return dict(rooms=rooms, links=out) if place(0) else None

HERE = os.path.dirname(os.path.abspath(__file__))
NAME = "TrapDem10"
M = Trial(NAME, "The Warlord's Trial", "castle", seed=10,
            description="[env:castle] TrapDemo 10, The Warlord's Trial: a warlord's castle run as a trial, hall by "
                        "hall, every kind of trap, and the warlord waiting in his arena. Generated by Claude.")
M.room("camp", (14, 12), role="camp", start=True)
M.room("gatehouse", (14, 12), role="guard", kind="guardroom")
M.room("barracks", (16, 14), role="room", kind="barracks")
M.room("kitchen", (12, 12), role="store", kind="kitchen")
M.room("question", (12, 12), role="room", kind="torture_chamber")
M.room("greathall", (18, 16), role="room", kind="great_hall")
M.room("trophy", (14, 12), role="room", kind="gallery")
M.room("court", (12, 12), role="room", kind="conservatory")
M.room("chapel", (14, 14), role="room", kind="chapel")
M.room("throne", (16, 14), role="room", kind="throne_room")
M.room("warroom", (12, 12), role="room", kind="study")
M.room("arena", (18, 18), role="boss", kind="hall")
M.room("vault", (12, 12), role="vault", kind="treasury")
M.link("camp", "gatehouse", trap=("spike", 0))               # one field on a clock: the gate
M.link("gatehouse", "barracks", trap=("trigger", 5))         # race the gate
M.link("gatehouse", "kitchen", trap=("flame", 2))            # the fire wave (off the trial)
M.link("barracks", "greathall", trap=("arrow", 1))           # the click and the pause
M.link("barracks", "question", trap=("push", 1))             # belts (off the trial)
M.link("greathall", "throne", trap=("blade", 6))             # find the gap (hard)
M.link("greathall", "trophy", trap=("pit", 2))               # look before you leap: the side quest's price
M.link("greathall", "court", length=6)                       # the garden court: a rest at its well
M.link("court", "chapel", trap=("block", 1))                 # snapping jaws (off the trial)
M.link("throne", "arena", trap=("sentry", 6))                # the gliding beam (hard): into the arena
M.link("throne", "warroom", trap=("spell", 5))               # glyphs and the warden (hard, off the trial)
M.link("arena", "vault", length=5)
M.layout(tries=40)
n0 = len(M.m.d["objects"])
M.dress()
clear_mouths(M, M.m.d["objects"][n0:])     # nothing of the dressing in a passage's mouth
# the garden court's well, where a challenger drinks and rests between the trial's halls (kit/wells.py: every well
# heals); the barracks' arms by its back walls; the chapel's offerings for whoever braves the jaws
M.put("court", "WishingWell", 3.0, 8.8, clear=3.0)
for t, a, b in (("TraderArmorRack1", 1.0, 4.0), ("TraderArmorRack2", 1.0, 9.0), ("BarrelWithTools1", 8.0, 13.2),
                ("Table2", 5.2, 9.2), ("Bench2", 5.2, 10.6)):
    M.put("barracks", t, a, b, clear=3.0)


def sign_spot(rid):
    """A room point for the camp's sign: beside the way on (the first passage's mouth), a square into the room and
    four along the wall from the mouth's middle, off every piece."""
    w, h = M.rooms[rid]["size"]
    da, db = M.doors[rid][0]
    n = (0, 1) if db < 1 else (0, -1) if db > h - 1 else (1, 0) if da < 1 else (-1, 0)     # into the room
    t = (n[1], n[0])
    along = da if n[0] == 0 else db
    side = -1 if along - 4.2 > 1.2 else 1
    return free_spot(M, rid, da + n[0] * 1.1 + t[0] * 4.2 * side, db + n[1] * 1.1 + t[1] * 4.2 * side, clear=0.9)


camp(M, "camp")                                  # the lived-in camp (kit/trapdemo_dress.py)
# the herald's camp at the trial's lists: an arms rack and a practice barrel by the north-east wall
extra(M, "camp", [("TargetBarrel1", 9.2, 10.9), ("BarrelWithTools2", 5.0, 10.9)])
sign_at = sign_spot("camp")
M.start_at("camp", *start_spot(M, "camp"))

# ---- life -------------------------------------------------------------------------------------------------------
M.monsters("gatehouse", {"GruntAxe": 2})
M.monsters("kitchen", {"GruntAxe": 2})
M.monsters("barracks", {"GruntAxe": 2, "Archer": 1})
M.monsters("question", {"Swordsman": 1, "GruntAxe": 1})
M.monsters("greathall", {"Swordsman": 2, "Archer": 2})
M.monsters("trophy", {"Archer": 2, "Swordsman": 1})
M.monsters("chapel", {"Swordsman": 2, "OgreBrute": 1})
M.monsters("throne", {"OgreBrute": 1, "Archer": 2, "Swordsman": 1})
M.monsters("warroom", {"Troll": 1, "Archer": 1})
boss = M.boss("arena", "B2")
key = M.item("vault", "GoldKey", *free_spot(M, "vault", 6.0, 6.0))
amulet = M.item("trophy", "AmuletofCombat", *free_spot(M, "trophy", 7.0, 9.6))
for rid, t, a, b in (("kitchen", "RedPotion", 6.0, 2.0), ("kitchen", "RedPotion", 6.8, 2.0), ("court", "RedPotion", 2.0, 6.0),
                     ("question", "CurePoisonPotion", 2.0, 2.0), ("warroom", "BluePotion", 2.0, 2.0)):
    M.put(rid, t, *free_spot(M, rid, a, b, clear=1.0), clear=2.4)
M.put("chapel", "Gold", *free_spot(M, "chapel", 10.0, 11.0, clear=1.0), clear=2.4, xfer={"Amount": 150})
M.put("chapel", "RedPotion", *free_spot(M, "chapel", 11.0, 10.4, clear=1.0), clear=2.4)
evelyn = M.person("camp", "War01A", "Evelyn", "HeraldEvelyn", pic="IngridPic", title="Herald Evelyn")

# ---- the story --------------------------------------------------------------------------------------------------
q = M.q
MAIN, SIDE = "trial", "amulet"
GOAL = "Defeat Garrick in his arena and bring back the Gold Key."
ERRAND = "Find Roderick's amulet in Garrick's trophy hall."
q.talker(evelyn, [
    q.say("The realm will remember your name. Thanks again!",
          when=q.at(MAIN, 3)),
    q.say("The Gold Key! Garrick is beaten and his trial is ended at last! The realm is grateful beyond words. "
          "Take this purse of gold, with my thanks.",
          when=q.at(MAIN, 2, has="GoldKey"),
          do=[A.take("GoldKey"), A.gold(600), A.give("RedPotion", 3), A.stage(MAIN, 3), q.done(GOAL)]),
    q.say("You hold his key, yet the warlord lives? Then the trial is not done. He waits for you in the arena.",
          when=q.at(MAIN, 1, has="GoldKey")),
    q.say("Roderick's amulet! His family never thought to see it again. Please, accept these for your trouble. "
          "They will put speed in your legs when Garrick charges.",
          when=q.when(has="AmuletofCombat", not_=f"{SIDE}done"),
          do=[A.take("AmuletofCombat"), A.give("HastePotion", 2), A.gold(150), A.flag(f"{SIDE}done"),
              q.done(ERRAND)]),
    q.say("Garrick has fallen?! Then the trial is ended! Now bring me the Gold Key from his strongroom.",
          when=q.at(MAIN, 2)),
    q.say("Why do you linger? The trial will not run itself.",
          when=q.at(MAIN, 1)),
    q.say("Halt! Another fighter for Sir Garrick's trial? Hear me first.\n\n"
          "Garrick holds this castle and calls every fighter in the land to run his trial, hall by hall, and face him "
          "in his arena at the end. None has ever come back. His halls are full of traps, and of his men.\n\n"
          "Will you take up the trial and defeat him? Bring me the Gold Key from his strongroom as proof, and the "
          "realm will reward you well.",
          when=q.at(MAIN, 0), ask=True,
          do=[A.stage(MAIN, 1), q.journal(GOAL), q.journal(ERRAND),
              q.tell(evelyn, "One thing more. Roderick, the last champion, fell in that arena. Garrick hung his "
                             "amulet in the trophy hall off the great hall. His family would have it back.")],
          else_=[q.tell(evelyn, "As you wish. The arena will have its next victim soon enough.")]),
], pic="IngridPic", title="Herald Evelyn",
   voice="A herald in her thirties. Clear, warm alto voice, a crisp southern English accent. Formal and measured, never rushed.")
q.on_death(boss, [A.stage(MAIN, 2), q.journal("Take the Gold Key from Garrick's strongroom to Herald Evelyn.")])
q.start([q.journal("Speak to Herald Evelyn at the camp by the castle gate.")])
M.sign("camp", "THE WARLORD'S TRIAL. Challengers enter here.", *sign_at)

# the healing wells named for the healing script (kit/setpieces HEAL_PREFIX; kit/wells.py heals them all)
for k, o in enumerate(o for o in M.m.d["objects"] if o.get("type") == "WishingWell"):
    o.setdefault("scr", f"HealWell{k + 1}")
m = M.m                                   # tests/server_smoke.py reads the spec as m
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "..", "out", "trapdemo", NAME)
M.finish(None if out == "-" else out)
