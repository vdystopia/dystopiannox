"""Tests of the voice pipeline that need no TTS, no game and no build (mapgen/voice.py, kit/quests.py's speech,
strings.py's waves, the install into Dialog): the speech is stood in for by a tone, in this test only.

    py tests/voice_test.py [--westwood "C:\\GOG Games\\Nox"]     (--westwood: also compare our header with Westwood's)

Prints each check and exits 1 if any fails.
"""
import argparse, glob, io, json, math, os, shutil, struct, sys, tempfile, contextlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "mapgen"))
import voice as V                               # noqa: E402
from kit.quests import QuestBook, A             # noqa: E402

FAILS = []


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond: FAILS.append(what)


def tone_wav(path, seconds, rate=V.RATE, level=0.25):
    """A stand-in for a spoken line: a warbling tone at speaking loudness, written by the module's own writer."""
    n = int(seconds * rate)
    fr = b"".join(struct.pack("<h", int(32767 * level * math.sin(2 * math.pi * (180 + 40 * math.sin(k / 900)) * k / rate)))
                  for k in range(n))
    V.write_wav(path, fr, rate)


def write_csf(path, entries):
    """A small nox.csf (the format strings.read_csf reads): entries [(key, text, wave or None)]."""
    inv = lambda s: b"".join(struct.pack("<H", (~c) & 0xFFFF) for c in struct.unpack(f"<{len(s.encode('utf-16-le')) // 2}H", s.encode("utf-16-le")))
    b = io.BytesIO()
    b.write(b"CSF "[::-1]); b.write(struct.pack("<IIIII", 3, len(entries), len(entries), 0, 0))
    for key, text, wave in entries:
        b.write(b"LBL "[::-1]); b.write(struct.pack("<II", 1, len(key))); b.write(key.encode("latin1"))
        b.write((b"STRW" if wave else b"STR ")[::-1]); b.write(struct.pack("<I", len(text))); b.write(inv(text))
        if wave: b.write(struct.pack("<I", len(wave))); b.write(wave.encode("latin1"))
    open(path, "wb").write(b.getvalue())


def story(out_dir, name="Testvale"):
    """A small story written as a design writes one: two talkers, a refusal told, a shop greeting, a journal entry."""
    q = QuestBook(name)
    q.talker("FatherAnsel", [
        q.say("The crypt is sealed, child. -- Stay OUT of it.\nThe dead walk there.", who="Ansel"),
    ], pic="GalavaPriestPic")
    q.talker("Wenna", q.errand("Wenna", "ring", offer="My ring is in the well. Will you fetch it?",
                               reminder="The well, please!", thanks="My ring! Take this.", after="Thanks again!",
                               objective="Fetch Wenna's ring from the well.", done=q.when(has="Ring"),
                               refusal="Fine then, keep your hands dry."), pic="MaidenPic2")
    greet = q.text("Welcome to my shop!", "Shop")
    os.makedirs(os.path.join(out_dir, f"{name}_scripts"), exist_ok=True)
    for fn, src in q.files().items():
        open(os.path.join(out_dir, f"{name}_scripts", fn), "w", encoding="utf-8").write(src)
    q.write_strings(out_dir)
    objects = [dict(clone=dict(map="x", scr="Con04c:Keeper"), scr="FatherAnsel", x=0, y=0),
               dict(clone=dict(map="x", scr="Con02a:Joyce"), scr="Wenna", x=0, y=0),
               dict(type="ShopkeeperYellow", x=0, y=0, xfer=dict(ShopkeeperInfo=dict(ShopkeeperGreetingText=greet)))]
    return q, objects, greet


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--westwood", default="")
    a = ap.parse_args()

    # text as spoken
    ok(V.said("Stay OUT of it -- now!!\nGo....") == "Stay Out of it, now! Go...", f"said(): {V.said('Stay OUT of it -- now!!' + chr(10) + 'Go....')!r}")
    # wave names: 8 characters, the map's own code
    code = V.wave_code("Thornwick")
    ok(len(code) == 4 and code.startswith("th"), f"wave code {code}")
    ok(V.wave_code("Thornwick") == code and V.wave_code("Thornhold") != code, "wave codes are stable and differ by map")

    # casting: parts from body, portrait and title; the same cast every time; distinct leads while they last
    texts = "Old Brannoc sits outside the forge. Reeve Aldric pays. Father Odo locked the crypt."
    ok(V.archetype("Brannoc", dict(type="NPC"), "MalePic8", "Brannoc", texts) == "elder", "Old Brannoc is an elder")
    ok(V.archetype("FatherOdo", dict(type="NPC"), "", "Father Odo", texts) == "priest", "Father Odo is a priest")
    ok(V.archetype("Mirela", dict(type="Maiden"), "MaidenPic2", "Mirela", texts) == "woman", "a Maiden is a woman")
    ok(V.archetype("Lydia", dict(donor="Lydia"), "", "Lydia", texts) == "woman", "a woman donor's clone is a woman")
    ok(V.archetype("Watch1", dict(type="NPC"), "Warrior3Pic", "Watchman", texts) == "guard", "the watch are guards")
    ok(V.archetype("ShopkeeperYellow#1", dict(type="ShopkeeperYellow", shop=True), "", "Shopkeeper", texts) == "merchant",
       "a shopkeeper is a merchant")
    sp = {s: dict(part=p, n=n) for s, p, n in [("A", "man", 3), ("B", "man", 2), ("C", "man", 2), ("D", "guard", 1)]}
    c1, c2 = V.cast(sp), V.cast(dict(reversed(list(sp.items()))))
    ok(c1 == c2, "the cast does not depend on the order speakers are listed")
    leads = [v["mix"][0][0] for v in c1.values()]
    ok(len(set(leads)) == len(leads), f"distinct lead voices {leads}")
    ok(all(v["mix"][0][0] in V.VOICES and v["mix"][1][0] in V.VOICES for v in c1.values()), "every voice is Kokoro's")
    pin = V.cast(dict(A=dict(part="man", n=1, voice="bm_george"), B=dict(part="man", n=1, voice="crone"),
                      C=dict(part="man", n=1, voice=dict(mix=[["af_sky", 1.0]], speed=1.1))))
    ok(pin["A"]["mix"][0][0] == "bm_george" and pin["A"]["lang"] == "en-gb", "a pinned Kokoro voice")
    ok(pin["B"]["part"] == "crone" and pin["C"]["mix"] == [["af_sky", 1.0]], "a pinned part and a pinned recipe")

    tmp = tempfile.mkdtemp(prefix="voice_test_")
    try:
        out = os.path.join(tmp, "out"); os.makedirs(out)
        q, objects, greet = story(out)
        sp = json.load(open(os.path.join(out, "Testvale.speech.json"), encoding="utf-8"))
        told = [k for k, s in sp["lines"].items() if s == "Wenna" and q.strings[k].startswith("Fine then")]
        ok(len(told) == 1, "the errand's refusal is a told line of the giver's (q.tell), with a key")
        ok('{Kind: "tell", A: "' + told[0] + '", B: "Wenna"' in open(os.path.join(out, "Testvale_scripts", "quests_config.go")).read(),
           "the config carries the tell act")
        ok(not any(k.startswith("Testvale:Journal") for k in sp["lines"]), "journal entries are not spoken")
        fb = V._from_config(os.path.join(out, "Testvale_scripts", "quests_config.go"))
        ok(fb["lines"] == sp["lines"] and fb["pics"] == sp["pics"], "a map built before speech.json reads the same speakers back")

        # the plan: every spoken key, the shop greeting by the shopkeeper, journal and titles silent
        man = V.plan(out, "Testvale", objects)
        ok(set(man["lines"]) == set(sp["lines"]) | {greet}, f"{len(man['lines'])} spoken lines: talkers, the refusal, the greeting")
        ok(man["speakers"]["Wenna"]["part"] == "woman" and man["speakers"]["FatherAnsel"]["part"] == "priest",
           "Wenna a woman (Joyce's clone), Ansel a priest (his portrait)")
        ok(all(len(l["wave"]) == 8 for l in man["lines"].values()), "8-character wave names")

        # no TTS here: nothing voiced, and the gate's check says why
        real = (V.tts_ready, V.synthesize, V.HOME)
        V.HOME = os.path.join(tmp, "home")
        m0, made, cached, why = V.voice(out, "Testvale", objects)
        ok(made == 0 and why and not any(l["voiced"] for l in m0["lines"].values()), f"without the TTS: not voiced ({why})")
        ok(not all(o for o, _ in V.check(out, "Testvale")), "the check fails a map whose lines have no waves")

        # a stand-in TTS: a tone of the length speech would have
        calls = []

        def fake(jobs, timeout=0):
            calls.append(len(jobs))
            for text, rec, p in jobs:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                tone_wav(p, V.LEAD + len(text.split()) / 2.9 / rec["speed"] + V.TAIL)
        V.tts_ready, V.synthesize = (lambda: None), fake
        m1, made, cached, why = V.voice(out, "Testvale", objects)
        ok(made == len(m1["lines"]) and all(l["voiced"] for l in m1["lines"].values()), f"all {made} lines voiced")
        res = V.check(out, "Testvale")
        ok(all(o for o, _ in res), "the check passes: " + "; ".join(t for o, t in res if not o))
        m2, made2, cached2, _ = V.voice(out, "Testvale", objects)
        ok(made2 == 0 and cached2 == len(m2["lines"]) and len(calls) == 1, "voicing again makes nothing: every wave cached")
        # a TTS that dies: the build goes on, says so, and keeps what it made
        def dies(jobs, timeout=0): raise RuntimeError("the TTS failed:\nonnxruntime: out of memory")
        V.synthesize = dies
        shutil.rmtree(os.path.join(V.HOME, "cache"))
        rep = V.build_step(objects, out, "Testvale")
        ok(len(rep) == 1 and "0 of 7 lines voiced" in rep[0] and "out of memory" in rep[0], f"a TTS crash is reported: {rep[0]}")
        V.synthesize = fake
        V.voice(out, "Testvale", objects)
        info = V.wave_info(os.path.join(out, "Testvale_dialog", m2["lines"][greet]["wave"] + ".wav"))
        ok((info["tag"], info["channels"], info["rate"], info["bits"]) == (1, 1, V.RATE, 16), f"PCM 16-bit mono {V.RATE} Hz")

        # the header our writer makes against a Westwood PCM dialogue wave's (fmt of 16 bytes before data)
        hdr = open(os.path.join(out, "Testvale_dialog", m2["lines"][greet]["wave"] + ".wav"), "rb").read(44)
        ok(hdr[12:20] == b"fmt \x10\x00\x00\x00" and hdr[36:40] == b"data", "canonical header: fmt (16 bytes), data")
        if a.westwood:
            ww = open(os.path.join(a.westwood, "Dialog", "W1CAP12E.WAV"), "rb").read(44)
            ok(ww[12:20] == hdr[12:20] and ww[20:24] == hdr[20:24] and ww[34:40] == hdr[34:40],
               "same layout, tag, channels and sample size as Westwood's W1CAP12E.WAV")

        # install into a stand-in game folder, twice; strings.py names the waves; a changed line loses its wave
        nox = os.path.join(tmp, "Nox"); os.makedirs(os.path.join(nox, "Dialog")); os.makedirs(os.path.join(nox, "maps"))
        write_csf(os.path.join(nox, "nox.csf"), [("Con02a:Hello", "Hello there.", "c2hen01e"), ("Sign:X", "A sign.", None)])
        open(os.path.join(nox, "Dialog", "C2HEN01E.WAV"), "wb").write(b"RIFF")
        os.makedirs(os.path.join(nox, "maps", "Testvale"))
        shutil.copy(os.path.join(out, "Testvale.strings.json"), os.path.join(nox, "maps", "Testvale"))
        r1 = V.install(out, "Testvale", nox)
        r2 = V.install(out, "Testvale", nox)
        n = len(m2["lines"])
        ok(f"{n} waves copied" in r1 and "0 waves copied" in r2, f"install copies {n} waves, then none: {r2}")
        ok(len(glob.glob(os.path.join(nox, "Dialog", "*"))) == n + 1, "Westwood's wave is left alone")
        import strings as S
        texts = S.map_lines(nox)
        waves = S.map_waves(nox, texts)
        ok(set(waves) == set(m2["lines"]), f"strings.py gives all {len(waves)} spoken lines their str2")
        ok(not any(k.startswith(("Testvale:Journal", "NPC:")) for k in waves), "no wave for a journal entry or a title")
        texts[greet] = "Welcome! Mind the step."
        ok(greet not in S.map_waves(nox, texts), "a line whose text changed since its wave was made gets no wave")
        argv = sys.argv
        sys.argv = ["strings.py", "--nox", nox]
        with contextlib.redirect_stdout(io.StringIO()): S.main()
        sys.argv = argv
        js = json.load(open(os.path.join(nox, "nox.csf.json"), encoding="utf-8"))
        byid = {e["id"]: e["vals"][0] for e in js["entries"]}
        ok(byid["Con02a:Hello"].get("str2") == "c2hen01e", "Westwood's own wave stays in nox.csf.json")
        ok(byid[greet].get("str2") == m2["lines"][greet]["wave"], f"nox.csf.json: {greet} -> {byid[greet].get('str2')}")
        # a line dropped from the map: its wave goes from Dialog on the next install
        man_p = os.path.join(out, "Testvale.voice.json")
        mm = json.load(open(man_p, encoding="utf-8"))
        gone = mm["lines"].pop(greet)
        json.dump(mm, open(man_p, "w", encoding="utf-8"))
        V.install(out, "Testvale", nox)
        ok(not os.path.exists(os.path.join(nox, "Dialog", gone["wave"] + ".wav")), "a wave the map no longer has is removed")
        # a wave name of Westwood's is refused
        mm["lines"][greet] = dict(gone, wave="c2hen01e")
        json.dump(mm, open(man_p, "w", encoding="utf-8"))
        try:
            V.install(out, "Testvale", nox); refused = False
        except SystemExit:
            refused = True
        ok(refused and os.path.getsize(os.path.join(nox, "Dialog", "C2HEN01E.WAV")) == 4, "Westwood's wave name is refused")
        V.tts_ready, V.synthesize, V.HOME = real
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'FAILED: ' + str(len(FAILS)) if FAILS else 'all passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
