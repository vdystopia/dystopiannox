"""Contact sheets of the distinct single-player layouts (one representative per layout group),
for visually studying Westwood's maps. Writes corpus/out/sheets/sheet_NN.jpg."""
import json, os, sqlite3
from PIL import Image, ImageDraw

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
COLS, ROWS, CELL, LABEL = 4, 2, 700, 44


def main():
    db = sqlite3.connect(os.path.join(OUT, "nox_corpus.db"))
    reps = db.execute("""SELECT l.rep, m.summary, m.n_tiles, m.n_objects, l.size FROM layout_group l
                         JOIN maps m ON m.name = l.rep WHERE l.map = l.rep ORDER BY l.rep""").fetchall()
    os.makedirs(os.path.join(OUT, "sheets"), exist_ok=True)
    per = COLS * ROWS
    for s in range(0, len(reps), per):
        sheet = Image.new("RGB", (COLS * CELL, ROWS * (CELL + LABEL)), (14, 14, 18))
        d = ImageDraw.Draw(sheet)
        for i, (name, summary, nt, no, size) in enumerate(reps[s:s + per]):
            x, y = (i % COLS) * CELL, (i // COLS) * (CELL + LABEL)
            p = os.path.join(OUT, "thumbs", name + ".jpg")
            if os.path.exists(p):
                im = Image.open(p); im.thumbnail((CELL - 8, CELL - 8))
                sheet.paste(im, (x + (CELL - im.width) // 2, y + LABEL + (CELL - im.height) // 2))
            d.text((x + 6, y + 4), f"{name}  (x{size})  tiles {nt}  objects {no}", fill=(240, 240, 240))
            d.text((x + 6, y + 22), (summary or "")[:90], fill=(170, 170, 180))
        sheet.save(os.path.join(OUT, "sheets", f"sheet_{s // per + 1:02d}.jpg"), quality=82)
    print(f"{len(reps)} layouts -> {(len(reps) + per - 1) // per} sheets")


if __name__ == "__main__":
    main()
