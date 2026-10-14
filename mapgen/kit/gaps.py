"""Gaps between indoor pieces, and storage and seating against the wall (QA round 2, 2026-10-14; review/qa2/ledger.md).

Q2T-4, "pieces never touch": RM-CELLAR-01/05 "The steel crate in the north corner is too close to the stack of
barrels", RM-CELLAR-04 "two crates ... too close to each other and touching", RM-KITCHEN-04/05 "The apple crate is too
close to the rectangular crate", RM-MAUSOLEUM-02 "The iron casket is way too close to the two coffins", RM-SHRINE-02
"The mana obelisk is too close to the statue", RM-TAVERN-04 "The two giant barrels are too close to each other",
RM-TAVERN-01/03/04/05 "The bearskin rug is just slightly too close to the fireplace". The rule:
- separate pieces keep a clear gap (GAP units between their footprints): what the eye reads as touching at the
  furnisher's old 0.15 (a crate beside a stack of barrels) or 0.02 (crates end to end);
- big pieces (great casks, coffins and caskets, obelisks, statues, tables, fountains and wells) keep a wider one
  (GAP_BIG);
- a heap is one piece: its members (kegs, metal barrels, barrels of tools, water barrels, piled barrels, sacks, straw)
  may touch each other; a crate is never a heap's member;
- a set is one piece: a seat drawn up to its table, desk, counter or fire may touch it; tables of one kind end on are
  one long table;
- lights, ground cover (straw, bones, skulls) and a throne's own pieces are never held to it;
- a rug keeps RUG_FIRE clear of a fireplace (its fire spills onto it).

Only pairs with a spaced piece (a heap's member, a crate, a chest, a big piece) are held to it: the rest (a chair by a
bookcase, bookcases end to end, a bar's pieces) keep the furnisher's own fit.

Q2T-5, "storage and seating against the wall": crates, sacks, chests and benches that belong to a wall stand flush
(their back within FLUSH units of its line), lined up with the pieces of their kind on that wall (one depth, within
LINE_TOL), never alone in the middle of the floor; a seat at its table, a chest at a bed's foot, a crate or a sack in a
heap of stores, and the pews of a ceremonial room are not wall pieces.

kit/furnish.py Furnisher.try_put refuses a placement that breaks the gap (`need`), so every composer keeps it;
validate/checks.py check_qa2_space faults both rules on a built map (planted cases STq2Gap, STq2Big, STq2Rug, STq2Wal,
STq2Mid, STq2Lin).
"""
import re

GAP = 0.35            # uv units between the footprints of two separate pieces
GAP_BIG = 0.7         # ... when one of them is a big piece
RUG_FIRE = 0.5        # a rug's footprint from a fireplace's
FLUSH = 0.5           # a wall piece's back this near its wall line stands against it (the furnisher sets them 0.22-0.3)
LINE_TOL = 0.2        # two wall pieces of one kind on one wall stand at one depth within this
MID_FLOOR = 2.5       # a wall piece farther than this from every wall stands alone in the middle of the floor

HEAP = re.compile(r"^(Barrel|Barrel2|BarrelLOTD|BarrelSteel\d|BarrelWithTools\d|WaterBarrel|BlackPowderBarrel2?|"
                  r"PiledBarrels\d|OgreSack\d|SackChest(Large|Medium|Small)\d)$")
CRATE = re.compile(r"^(Crate\d|DarkCrate\d|CrateSteel\d|TraderAppleCrate)$")
CHEST = re.compile(r"^(Chest\d|Chest[NS][EW]|DunMirChest\d|ChestOgre\d)$")
BIG = re.compile(r"^(LargeBarrel\d|Coffin\d|Obelisk|ObeliskPrimitive|LOTDManaObelisk|Statue\d[a-h]|MovableStatue\w+|"
                 r"DunMirWolfStatue|HorrendousStatue\d|LOTDLichGodStatue\d|Table\d|RoundTable\d|SquareTable\d|"
                 r"OvalTable\d|RoundTableWithFood|SmallTable\d|OgreTable\d|Fountain|WishingWell|Well)$")
SEAT = re.compile(r"Chair|Stool|Bench")
SEAT_TO = re.compile(r"Table|^Desk\d|^TraderDesk|^Bar(Piece|Corner|HingedTop)|^Fireplace|^OgreFirePit")
# never held to a gap: lights (a candelabra stands by what it lights), ground cover (straw, bones), a throne's own
# flanking pieces (kit/civic.py composes the throne whole)
FREE = re.compile(r"Candleabra|Candelabra|^TorchPole|Brazier|Lantern|^OgreStraw|^Straw\d|Skull|Bone|^DunMirThrone")
RUG = re.compile(r"^(RedRug\d|BearskinRug\d|OgreBearskin\d)$")
FIRE = re.compile(r"^Fireplace\d")
SACK = re.compile(r"^(SackChest(Large|Medium|Small)\d|OgreSack\d)$")
BENCH = re.compile(r"^(Bench\d|LightBench\d|CushionedBench\d|OgreBench\d)$")
WALL_PIECE = re.compile(CRATE.pattern + "|" + SACK.pattern + "|" + CHEST.pattern + "|" + BENCH.pattern)
# rooms whose benches are pews or face a centrepiece in the open (an aisle, a gallery's statues): not wall pieces
PEW_TYPES = {"great_hall", "hall", "throne_room", "chapel", "coven", "mana_room", "shrine", "gallery", "crypt",
             "mausoleum", "ossuary", "tavern", "dining_hall"}


def base(t):
    return re.sub(r"Immobile$", "", t)


def spaced(t):
    t = base(t)
    return bool(HEAP.match(t) or CRATE.match(t) or CHEST.match(t) or BIG.match(t))


def need(a, b):
    """Units the footprints of pieces a and b keep between them (0: the furnisher's own fit decides)."""
    a, b = base(a), base(b)
    if FREE.search(a) or FREE.search(b): return 0.0
    if RUG.match(a) or RUG.match(b):                                       # a rug: only off a fire
        return RUG_FIRE if FIRE.match(a) or FIRE.match(b) else 0.0
    if not (spaced(a) or spaced(b)): return 0.0
    if HEAP.match(a) and HEAP.match(b): return 0.0                          # one heap
    if SEAT.search(a) and SEAT_TO.search(b) or SEAT.search(b) and SEAT_TO.search(a): return 0.0   # one set
    if a == b and re.search(r"Table", a): return 0.0                         # tables end on: one long table
    return GAP_BIG if (BIG.match(a) or BIG.match(b)) else GAP


def kind(t):
    """The wall piece's kind for lining up (crate, sack, chest, bench), or None."""
    t = base(t)
    for k, rx in (("crate", CRATE), ("sack", SACK), ("chest", CHEST), ("bench", BENCH)):
        if rx.match(t): return k
    return None


def box_gap(a, b):
    """Gap between two footprint boxes (u, v, hu, hv, ...): negative when they overlap."""
    return max(abs(a[0] - b[0]) - a[2] - b[2], abs(a[1] - b[1]) - a[3] - b[3])
