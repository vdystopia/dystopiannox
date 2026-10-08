"""Tests of the voice pipeline that need no TTS, no GPU, no game and no build (mapgen/voice.py, kit/quests.py's speech
and deliveries, strings.py's waves, the install into Dialog): the speech is stood in for by a tone, in this test only.
Both engines: Breeze (the default; its worker stood in for by one that writes tones into the cache) and Kokoro (an
explicit option).

    py tests/voice_test.py [--westwood "C:\\GOG Games\\Nox"]     (--westwood: also compare our header with Westwood's)

Prints each check and exits 1 if any fails.
"""
import argparse, glob, io, json, math, os, shutil, struct, sys, tempfile, time, contextlib

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "mapgen"))
import voice as V                               # noqa: E402
from kit.quests import QuestBook, A             # noqa: E402

FAILS = []


def ok(cond, what):
    print(("ok   " if cond else "FAIL ") + what)
    if not cond: FAILS.append(what)


def tone_pcm(seconds, rate=V.RATE, level=0.25):
    """A stand-in for a spoken line: a warbling tone at speaking loudness."""
    n = int(seconds * rate)
    return b"".join(struct.pack("<h", int(32767 * level * math.sin(2 * math.pi * (180 + 40 * math.sin(k / 900)) * k / rate)))
                    for k in range(n))


def tone_wav(path, seconds, rate=V.RATE):
    V.write_wav(path, tone_pcm(seconds, rate), rate)


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


PIN = dict(desc="An old blacksmith in his seventies. Deep, gravelly voice, a northern English accent. Slow and warm.",
           seed=7, ref_text="(sigh) The crypt is sealed, child. Stay out of it. The dead walk there.",
           ref_desc="An old blacksmith in his seventies, grave and weary.")


def story(out_dir, name="Testvale"):
    """A small story written as a design writes one: two talkers, a refusal told, a shop greeting, a journal entry,
    a pinned voice with its reference line delivered with a sigh, a mood, a pinned shopkeeper (by greeting key)."""
    q = QuestBook(name)
    q.talker("FatherAnsel", [
        q.say("The crypt is sealed, child. -- Stay OUT of it.\nThe dead walk there.", who="Ansel",
              spoken="(sigh) The crypt is sealed, child. Stay out of it. The dead walk there."),
        q.say("All of them? Ha! Here, for your trouble.", who="Ansel", when=q.when(flag="x")),
    ], pic="GalavaPriestPic", voice=PIN)
    q.talker("Wenna", q.errand("Wenna", "ring", offer="My ring is in the well. Will you fetch it?",
                               reminder="The well, please!", thanks="My ring! Take this.", after="Thanks again!",
                               objective="Fetch Wenna's ring from the well.", done=q.when(has="Ring"),
                               refusal="Fine then, keep your hands dry."), pic="MaidenPic2")
    greet = q.text("Welcome to my shop!", "Shop")
    q.voice(greet, "merchant")
    q.deliver(greet, mood="Bright and quick.")
    os.makedirs(os.path.join(out_dir, f"{name}_scripts"), exist_ok=True)
    for fn, src in q.files().items():
        open(os.path.join(out_dir, f"{name}_scripts", fn), "w", encoding="utf-8").write(src)
    q.write_strings(out_dir)
    objects = [dict(clone=dict(map="x", scr="Con04c:Keeper"), scr="FatherAnsel", x=0, y=0),
               dict(clone=dict(map="x", scr="Con02a:Joyce"), scr="Wenna", x=0, y=0),
               dict(type="ShopkeeperYellow", x=0, y=0, xfer=dict(ShopkeeperInfo=dict(ShopkeeperGreetingText=greet)))]
    return q, objects, greet


def fake_breeze(fail=(), calls=None):
    """A stand-in for the Breeze worker: each speaker's reference a tone, each line a tone of speaking length, into the
    cache as the worker writes them; lines in `fail` fail the gate."""
    def run(man, remaining, retry=False, extra=()):
        keys = remaining()
        if calls is not None: calls.append(len(keys))
        for k in keys:
            l = man["lines"][k]
            sp = man["speakers"][l["speaker"]]
            wp, jp = V.ref_paths(sp["ref"])
            if not os.path.exists(wp):
                os.makedirs(os.path.dirname(wp), exist_ok=True)
                tone_wav(wp, 3.0, 24000)
                V._dump(jp, {"pass": True, "seed": sp["seed"], "f0": 110.0})
            h = V.line_hash(l["spec"], V.file_sha(wp))
            bad = k in fail
            V.store_line(h, tone_pcm(V.LEAD + len(l["said"].split()) / 2.9 + V.TAIL),
                         {"pass": not bad, "tries": V.LINE_TRIES if bad else 1, "seed": 1, "wer": 0.4 if bad else 0.0,
                          "problems": ["3 word errors in 5 (heard 'the well')"] if bad else []})
        return None
    return run


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--westwood", default="")
    a = ap.parse_args()
    os.environ.pop("NOX_VOICE_ENGINE", None)
    ok(V.engine_name() == "breeze", "Breeze is the default engine")
    os.environ["NOX_VOICE_ENGINE"] = "kokoro"
    ok(V.engine_name() == "kokoro", "NOX_VOICE_ENGINE=kokoro chooses Kokoro")
    os.environ.pop("NOX_VOICE_ENGINE")

    # text as spoken
    ok(V.said("Stay OUT of it -- now!!\nGo....") == "Stay Out of it, now! Go...", f"said(): {V.said('Stay OUT of it -- now!!' + chr(10) + 'Go....')!r}")
    # wave names: 8 characters, the map's own code
    code = V.wave_code("Thornwick")
    ok(len(code) == 4 and code.startswith("th"), f"wave code {code}")
    ok(V.wave_code("Thornwick") == code and V.wave_code("Thornhold") != code, "wave codes are stable and differ by map")

    # deliveries: vocal events, their words the line's; the automatic ones
    ok(V.delivery_problem("Gate's barred. Go away.", "(sigh) Gate's barred. Go away.") is None, "a sigh before the words")
    ok("differ" in (V.delivery_problem("Gate's barred.", "(sigh) Gate is barred.") or ""), "a delivery must keep the words")
    ok("unknown" in (V.delivery_problem("Go.", "(yawn) Go.") or ""), "an unknown vocal event is refused")
    ok(V.auto_tags("All of them? Ha! Here.") == "All of them? (laugh) Here.", "a lone 'Ha!' is a laugh")
    ok(V.auto_tags("Hah, Hal is here. Harold!") == "Hah, Hal is here. Harold!", "no laugh where the text has none")
    try:
        QuestBook("X").say("Go north.", spoken="(sigh) Go south."); refused = False
    except ValueError:
        refused = True
    ok(refused, "q.say refuses a delivery whose words are not the line's")

    # the gate: names any spelling, numbers in digits, British spelling; the verdict's limits
    ok(V.word_errors("Talk to Aldric in his hall.", "Talk to Aldrick in his hall.", {"aldric"}) == (0, 5),
       "a name is not counted (Aldric heard as Aldrick)")
    ok(V.word_errors("I will give you two hundred gold.", "I'll give you 200 gold.", set())[0] == 2,
       "200 is two hundred (I'll for I will: 2 errors)")
    ok(V.word_errors("A hundred and twenty gold, traveller.", "100 20 gold traveler", set())[0] == 0,
       "a hundred and twenty; traveller and traveler")
    m = dict(errors=1, words=12, heard="x", f0=120.0, speech_s=4.0, nwords=12)
    ok(V.gate_verdict(m, (65, 200))[0] == [], "one error in 12 words, 120 Hz, 3 words a second: passes")
    ok(any("word errors" in p for p in V.gate_verdict(dict(m, errors=3), (65, 200))[0]), "three errors in 12 fail")
    ok(any("outside" in p for p in V.gate_verdict(dict(m, f0=260.0), (65, 200))[0]), "a man at 260 Hz fails the band")
    ok(any("reference" in p for p in V.gate_verdict(dict(m, f0=180.0), (65, 200), 110.0)[0]),
       "a line 8.5 semitones off its reference fails")
    ok(any("words a second" in p for p in V.gate_verdict(dict(m, speech_s=12.0), (65, 200))[0]), "1 word a second fails")
    names = V.map_names(["Ask Old Brannoc about it. Thornwick is north.", "The Red Hand holds the road.",
                         "An old guard stands there."], ["Father Odo", "GateGuard"])
    ok({"branoc", "red", "hand", "odo", "father"} <= names and not names & {"ask", "the", "old", "guard"},
       f"proper names from the text: {sorted(names)}")

    # casting: parts from body, portrait and title; the same cast every time; distinct voices while they last
    texts = "Old Brannoc sits outside the forge. Reeve Aldric pays. Father Odo locked the crypt."
    ok(V.archetype("Brannoc", dict(type="NPC"), "MalePic8", "Brannoc", texts) == "elder", "Old Brannoc is an elder")
    ok(V.archetype("FatherOdo", dict(type="NPC"), "", "Father Odo", texts) == "priest", "Father Odo is a priest")
    ok(V.archetype("Mirela", dict(type="Maiden"), "MaidenPic2", "Mirela", texts) == "woman", "a Maiden is a woman")
    ok(V.archetype("Lydia", dict(donor="Lydia"), "", "Lydia", texts) == "woman", "a woman donor's clone is a woman")
    ok(V.archetype("Watch1", dict(type="NPC"), "Warrior3Pic", "Watchman", texts) == "guard", "the watch are guards")
    ok(V.archetype("ShopkeeperYellow#1", dict(type="ShopkeeperYellow", shop=True), "", "Shopkeeper", texts) == "merchant",
       "a shopkeeper is a merchant")
    ok(set(V.DESCRIPTIONS) == set(V.ARCHETYPES) == set(V.BANDS), "every part has descriptions and a pitch band")
    sp = {s: dict(part=p, n=n) for s, p, n in [("A", "man", 3), ("B", "man", 2), ("C", "man", 2), ("D", "guard", 1)]}
    b1, b2 = V.cast_breeze(sp), V.cast_breeze(dict(reversed(list(sp.items()))))
    ok(b1 == b2, "the Breeze cast does not depend on the order speakers are listed")
    descs = [v["desc"] for v in b1.values()]
    ok(len(set(descs)) == len(descs) and all(v["desc"] in V.DESCRIPTIONS[v["part"]] for v in b1.values()),
       "distinct descriptions, each its part's")
    pb = V.cast_breeze(dict(A=dict(part="man", n=1, voice=PIN), B=dict(part="man", n=1, voice="crone"),
                            C=dict(part="man", n=1, voice="bm_george"), D=dict(part="man", n=1, voice="A tall thin man. Reedy voice.")))
    ok(pb["A"]["desc"] == PIN["desc"] and pb["A"]["seed"] == 7 and pb["A"]["pinned"] and pb["A"]["ref_desc"] == PIN["ref_desc"],
       "a pinned description, seed and reference")
    ok(pb["B"]["part"] == "crone" and pb["B"]["desc"] in V.DESCRIPTIONS["crone"], "a pinned part")
    ok(pb["C"]["part"] == "man" and "Kokoro" in pb["C"]["note"], "a Kokoro pin is noted and the speaker cast by part")
    ok(pb["D"]["desc"].startswith("A tall thin man") and not pb["D"]["pinned"], "a description as a plain string")
    c1, c2 = V.cast(sp), V.cast(dict(reversed(list(sp.items()))))
    ok(c1 == c2, "Kokoro: the cast does not depend on the order speakers are listed")
    leads = [v["mix"][0][0] for v in c1.values()]
    ok(len(set(leads)) == len(leads), f"Kokoro: distinct lead voices {leads}")
    pin = V.cast(dict(A=dict(part="man", n=1, voice="bm_george"), B=dict(part="man", n=1, voice="crone"),
                      C=dict(part="man", n=1, voice=dict(mix=[["af_sky", 1.0]], speed=1.1))))
    ok(pin["A"]["mix"][0][0] == "bm_george" and pin["A"]["lang"] == "en-gb", "Kokoro: a pinned voice")
    ok(pin["B"]["part"] == "crone" and pin["C"]["mix"] == [["af_sky", 1.0]], "Kokoro: a pinned part and a pinned recipe")

    tmp = tempfile.mkdtemp(prefix="voice_test_")
    real = (V.tts_ready, V.synthesize, V.run_breeze, V.HOME, V.gpu_busy, V._win_gpu, V.vram_free_mib)
    try:
        # the GPU: the pc1 AI guard's log says a game is running; other programs' load; skip keeps what is cached
        log = os.path.join(tmp, "guard.log")
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        open(log, "w").write(f"2026-01-01 00:00:00 ai=True game=Old gpu_idle=True\n{now} ai=True game=nox gpu_idle=True "
                             f"server=False pc2=True (other gpu 3%)\n{now} stay-awake: True\n")
        os.environ["NOX_GPU_GUARD_LOG"] = log
        ok(V._guard_game() == "nox", "the guard's log: a game is running (nox)")
        open(log, "w").write(f"{now} ai=True game= gpu_idle=False server=False\n")
        ok(V._guard_game() is None, "the guard's log: no game")
        open(log, "w").write("2026-01-01 00:00:00 ai=True game=nox gpu_idle=True\n")
        ok(V._guard_game() is None, "a stale guard log is not believed")
        V._win_gpu = lambda: ({100: 3.0, 200: 60.0, 300: 30.0, 400: 50.0},
                              [dict(pid=100, ppid=1, name="dwm.exe", path=""), dict(pid=200, ppid=os.getpid(), name="python.exe", path=""),
                               dict(pid=300, ppid=1, name="game.exe", path="D:\\Games\\x\\game.exe"),
                               dict(pid=400, ppid=200, name="python.exe", path="")])
        V.vram_free_mib = lambda: 20000
        ok("game.exe 30%" in (V.gpu_busy() or ""), f"other programs' GPU use counts, ours and the desktop's not: {V.gpu_busy()}")
        V._win_gpu = lambda: ({}, [dict(pid=5, ppid=1, name="opennox.exe", path="")])
        ok("Nox is running" in (V.gpu_busy() or ""), "Nox running keeps the GPU")
        V._win_gpu = lambda: ({}, [])
        V.vram_free_mib = lambda: 4000
        ok("GiB" in (V.gpu_busy(need_mib=V.VRAM_MIB) or ""), "too little free GPU memory")
        V.gpu_busy = lambda roots=(), need_mib=None: "a game is running (nox, says the pc1 AI guard)"
        os.environ["NOX_VOICE_GPU"] = "skip"
        ok("NOX_VOICE_GPU=skip" in (V.wait_gpu() or ""), "NOX_VOICE_GPU=skip: not voiced now, cached waves kept")
        os.environ["NOX_VOICE_GPU"] = "force"
        ok(V.wait_gpu() is None, "NOX_VOICE_GPU=force does not look")
        os.environ.pop("NOX_VOICE_GPU"); os.environ.pop("NOX_GPU_GUARD_LOG")
        V.gpu_busy, V._win_gpu, V.vram_free_mib = real[4], real[5], real[6]

        out = os.path.join(tmp, "out"); os.makedirs(out)
        q, objects, greet = story(out)
        sp = json.load(open(os.path.join(out, "Testvale.speech.json"), encoding="utf-8"))
        told = [k for k, s in sp["lines"].items() if s == "Wenna" and q.strings[k].startswith("Fine then")]
        ok(len(told) == 1, "the errand's refusal is a told line of the giver's (q.tell), with a key")
        ok('{Kind: "tell", A: "' + told[0] + '", B: "Wenna"' in open(os.path.join(out, "Testvale_scripts", "quests_config.go")).read(),
           "the config carries the tell act")
        ok(not any(k.startswith("Testvale:Journal") for k in sp["lines"]), "journal entries are not spoken")
        ok(sp["voices"]["FatherAnsel"] == PIN and sp["voices"][greet] == "merchant", "speech.json: the pins (by name, by key)")
        ok(sp["delivery"][greet] == {"mood": "Bright and quick."} and len(sp["delivery"]) == 2, "speech.json: the deliveries")
        fb = V._from_config(os.path.join(out, "Testvale_scripts", "quests_config.go"))
        ok(fb["lines"] == sp["lines"] and fb["pics"] == sp["pics"], "a map built before speech.json reads the same speakers back")

        # the Breeze plan: every spoken key, the greeting by the shopkeeper, the reference, the deliveries
        man = V.plan(out, "Testvale", objects)
        ok(man["engine_name"] == "breeze" and man["engine"].startswith("breeze-tts"), f"the plan is Breeze's: {man['engine']}")
        ok(set(man["lines"]) == set(sp["lines"]) | {greet}, f"{len(man['lines'])} spoken lines: talkers, the refusal, the greeting")
        S = man["speakers"]
        ok(S["Wenna"]["part"] == "woman" and S["FatherAnsel"]["part"] == "priest", "Wenna a woman (Joyce's clone), Ansel a priest")
        shop = next(s for s in S if s.startswith("Shopkeeper"))
        ok(S[shop]["part"] == "merchant" and S[shop]["desc"] in V.DESCRIPTIONS["merchant"], "the shopkeeper pinned by its greeting's key")
        ok(S["FatherAnsel"]["ref_text"] == "(sigh) The crypt is sealed, child. Stay out of it. The dead walk there."
           and S["FatherAnsel"]["seed"] == 7, "a pinned reference text and seed")
        ansel = [l for l in man["lines"].values() if l["speaker"] == "FatherAnsel"]
        ok(ansel[0]["spoken"] == S["FatherAnsel"]["ref_text"], "the line whose words are the reference's is the design take")
        ok(ansel[1]["spoken"] == "All of them? (laugh) Here, for your trouble.", f"the automatic laugh: {ansel[1]['spoken']}")
        ok(man["lines"][greet]["mood"] == "Bright and quick.", "a line's mood")
        ok(len(V.untagged(S["Wenna"]["ref_text"]).split()) >= 8, f"Wenna's reference from her lines: {S['Wenna']['ref_text']!r}")
        ok({V._simplify("wenna"), "ansel"} <= set(man["names"]), "the speakers' names are not counted by the gate")
        ok(all(len(l["wave"]) == 8 for l in man["lines"].values()), "8-character wave names")
        m2 = V.plan(out, "Testvale", objects)
        ok(json.dumps(m2, sort_keys=True) == json.dumps(man, sort_keys=True), "the same plan every time")

        # no TTS here: nothing voiced, and the gate's check says why
        V.HOME = os.path.join(tmp, "home")
        m0, made, cached, why = V.voice(out, "Testvale", objects)
        ok(made == 0 and why and "breeze" in why and not any(l["voiced"] for l in m0["lines"].values()), f"without the TTS: not voiced ({why})")
        ok(not all(o for o, _ in V.check(out, "Testvale")), "the check fails a map whose lines have no waves")

        # a stand-in worker: references and lines into the cache
        calls = []
        V.tts_ready, V.run_breeze = (lambda engine=None: None), fake_breeze(calls=calls)
        m1, made, cached, why = V.voice(out, "Testvale", objects)
        ok(made == len(m1["lines"]) and all(l["voiced"] for l in m1["lines"].values()), f"all {made} lines voiced")
        res = V.check(out, "Testvale")
        ok(all(o for o, _ in res), "the check passes: " + "; ".join(t for o, t in res if not o))
        ok(all(l["hash"] and l.get("gate") is not None for l in m1["lines"].values()), "each line's hash includes its reference")
        m2, made2, cached2, _ = V.voice(out, "Testvale", objects)
        ok(made2 == 0 and cached2 == len(m2["lines"]) and len(calls) == 1, "voicing again makes nothing: every wave cached")
        # a new mood re-makes that line only; a new reference wave re-makes its speaker's lines
        spj = os.path.join(out, "Testvale.speech.json")
        js = json.load(open(spj, encoding="utf-8"))
        js["delivery"][greet] = {"mood": "Weary."}
        json.dump(js, open(spj, "w", encoding="utf-8"))
        calls.clear()
        m3, made3, _, _ = V.voice(out, "Testvale", objects)
        ok(made3 == 1 and calls == [1], f"a changed mood re-makes one line ({made3})")
        wp, _ = V.ref_paths(m3["speakers"]["FatherAnsel"]["ref"])
        tone_wav(wp, 2.5, 24000)                    # the reference made again, differently
        calls.clear()
        m4, made4, _, _ = V.voice(out, "Testvale", objects)
        ok(made4 == 2 and calls == [2], f"a new reference wave re-makes its speaker's 2 lines ({made4})")
        # a line that cannot pass the gate: not in the dialog folder, the check says why
        js["delivery"][greet] = {"mood": "Shouting."}
        json.dump(js, open(spj, "w", encoding="utf-8"))
        V.run_breeze = fake_breeze(fail={greet})
        m5, _, _, _ = V.voice(out, "Testvale", objects)
        g5 = m5["lines"][greet]
        ok(not g5["voiced"] and "quality gate" in g5["why"] and not os.path.exists(os.path.join(out, "Testvale_dialog", g5["wave"] + ".wav")),
           f"a line failing the gate stays silent: {g5['why']}")
        res = V.check(out, "Testvale")
        ok(any(not o and "quality gate" in t for o, t in res), "the check fails it: " + "; ".join(t for o, t in res if not o)[:200])
        calls.clear(); V.run_breeze = fake_breeze(calls=calls)
        V.voice(out, "Testvale", objects)
        ok(calls == [], "a failed line is not tried again on every build")
        m6, made6, _, _ = V.voice(out, "Testvale", objects, retry=True)
        ok(made6 == 1 and m6["lines"][greet]["voiced"], "--retry tries it again")
        # a dead worker: the build goes on and says so
        V.run_breeze = lambda man, remaining, retry=False, extra=(): "the Breeze worker 1 failed (exit 1): CUDA out of memory"
        shutil.rmtree(os.path.join(V.HOME, "cache"))
        rep = V.build_step(objects, out, "Testvale")
        ok(len(rep) == 1 and f"0 of {len(m6['lines'])} lines voiced" in rep[0] and "out of memory" in rep[0], f"a worker crash is reported: {rep[0]}")
        V.run_breeze = fake_breeze()
        V.voice(out, "Testvale", objects)
        man_b = json.load(open(os.path.join(out, "Testvale.voice.json"), encoding="utf-8"))
        info = V.wave_info(os.path.join(out, "Testvale_dialog", man_b["lines"][greet]["wave"] + ".wav"))
        ok((info["tag"], info["channels"], info["rate"], info["bits"]) == (1, 1, V.RATE, 16), f"PCM 16-bit mono {V.RATE} Hz")

        # mastering: a Breeze take's silence trimmed, Westwood's loudness and peaks
        import numpy as np
        x = np.concatenate([np.zeros(24000), 0.3 * np.sin(np.arange(48000) * 2 * np.pi * 150 / 24000), np.zeros(24000)])
        pcm = V._master(x, 24000, V.RATE, trim=True)
        ok(abs(len(pcm) / V.RATE - (2.0 + V.LEAD + V.TAIL)) < 0.06, f"silence trimmed: {len(pcm) / V.RATE:.2f} s")
        ok(np.abs(pcm.astype(float)).max() / 32768 < 10 ** (V.CEIL / 20) + 0.01, "peaks under the ceiling")

        # Kokoro, as an explicit option, still voices the map with its own cast and cache
        os.environ["NOX_VOICE_ENGINE"] = "kokoro"
        kcalls = []

        def fake(jobs, timeout=0):
            kcalls.append(len(jobs))
            for text, rec, p in jobs:
                os.makedirs(os.path.dirname(p), exist_ok=True)
                tone_wav(p, V.LEAD + len(text.split()) / 2.9 / rec["speed"] + V.TAIL)
        V.synthesize = fake
        mk, madek, _, _ = V.voice(out, "Testvale", objects)
        ok(mk["engine_name"] == "kokoro" and madek == len(mk["lines"]) and all(l["voiced"] for l in mk["lines"].values()),
           f"Kokoro voices all {madek} lines when chosen")
        ok(all("mix" in v for v in mk["speakers"].values()) and mk["speakers"]["FatherAnsel"]["part"] == "priest",
           "Kokoro casts by part where the pin is a description")
        ok(all(o for o, _ in V.check(out, "Testvale")), "the check passes a Kokoro-voiced map")
        os.environ.pop("NOX_VOICE_ENGINE")
        ok("kokoro" in V._lock_all() and V._engine("kokoro").startswith("kokoro-onnx kokoro-v1.0.onnx:7d5df8ecf7d4"),
           "the lock keeps Kokoro's pins (its cache keys unchanged)")
        V.voice(out, "Testvale", objects)               # back to Breeze for the install

        # the header our writer makes against a Westwood PCM dialogue wave's (fmt of 16 bytes before data)
        m2 = json.load(open(os.path.join(out, "Testvale.voice.json"), encoding="utf-8"))
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
    finally:
        V.tts_ready, V.synthesize, V.run_breeze, V.HOME, V.gpu_busy, V._win_gpu, V.vram_free_mib = real
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"\n{'FAILED: ' + str(len(FAILS)) if FAILS else 'all passed'}")
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
