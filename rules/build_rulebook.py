"""Runs every rule miner and assembles rules/RULEBOOK.md from rules/sections/*.md.

    py rules/build_rulebook.py            # run all miners, then assemble
    py rules/build_rulebook.py --assemble # only assemble existing sections

Machine-readable rules land in rules/out/*.json (used by the generator and the validator).
Needs the corpus: py corpus/build_corpus.py --skip-images
"""
import os, subprocess, sys, time

HERE = os.path.dirname(os.path.abspath(__file__))
MINERS = ["walls", "doors", "floors", "water", "lighting", "decoration", "life", "rooms", "buildings", "room_types"]
TITLES = {"walls": "Walls, doors and boundaries", "doors": "Door construction", "floors": "Floors and edge blending",
          "water": "Water and crossings", "lighting": "Lighting", "decoration": "Decoration and furniture",
          "life": "Townsfolk and navigation", "rooms": "Rooms and buildings",
          "buildings": "Building shapes and styles", "room_types": "Room types and furnishing"}


def run_miners():
    for m in MINERS:
        script = os.path.join(HERE, m + ".py")
        if not os.path.exists(script):
            print(f"skip {m}: no script"); continue
        t = time.time()
        r = subprocess.run([sys.executable, script], cwd=HERE)
        print(f"{m}: {'ok' if r.returncode == 0 else 'FAILED'} ({time.time() - t:.0f}s)")
        if r.returncode: sys.exit(r.returncode)


def assemble():
    parts = ["# Nox map-making rulebook\n",
             "Rules learned from Westwood's maps (`corpus/out/nox_corpus.db`). Each rule carries its "
             "evidence. Style rules come from the 107 campaign maps only (Con/War/Wiz, never the quest maps G_* nor the "
             "multiplayer maps), weighted so layouts shared by the three class "
             "campaigns count once; validity tables (what exists at all) use all 157 maps. "
             "Machine-readable versions are in `rules/out/*.json`.\n",
             "## Contents\n"]
    present = [m for m in MINERS if os.path.exists(os.path.join(HERE, "sections", m + ".md"))]
    parts += [f"{i}. [{TITLES[m]}](#{i}-{TITLES[m].lower().replace(',', '').replace(' ', '-')})" for i, m in enumerate(present, 1)]
    parts.append("")
    for i, m in enumerate(present, 1):
        body = open(os.path.join(HERE, "sections", m + ".md"), encoding="utf-8").read().strip()
        lines = body.splitlines()
        if lines and lines[0].startswith("# "): lines = lines[1:]          # replace the section's own title
        body = "\n".join(l if not l.startswith("#") else "#" + l for l in lines)   # demote headings one level
        parts += [f"## {i}. {TITLES[m]}\n", body.strip(), ""]
    with open(os.path.join(HERE, "RULEBOOK.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(parts) + "\n")
    print(f"RULEBOOK.md: {len(present)} sections")


if __name__ == "__main__":
    if "--assemble" not in sys.argv: run_miners()
    assemble()
