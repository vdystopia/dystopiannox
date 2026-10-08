"""Voiced dialogue for generated maps: every line said in a dialogue window gets a voice, as Westwood's lines do.

How Nox plays a voiced line (verified 2026-10-08 on the GOG install and OpenNox v1.9.0-alpha13's opennox.exe):
- A string of the game's table carries a wave name beside its text (nox.csf's STRW entries: "War01A.scr:
  CaptainTalkStart" -> "f1cap12e"; 1415 of them, every wave present). OpenNox's nox.csf.json keeps it as "str2"
  (opennox-lib strman). When a dialogue window shows the string (TellStory, a shopkeeper's greeting) the client
  streams Dialog\\<wave>.wav ("dialog\\" + name + ".wav", AudDiag.c). Scripts pass no sound to TellStory: the voice
  belongs to the string, so a line is voiced by its string table entry alone and the scripts do not change.
- Westwood's 1254 waves are 8.3 names (7-8 characters): 1246 MP3 in a WAV (22050 Hz mono) and 8 plain PCM 16-bit
  mono WAVs (W1CAP12E, the wizards' airship captain); OpenNox's stream reader decodes PCM, IMA ADPCM and MP3. Ours are
  PCM 16-bit mono at 22050 Hz, mastered as Westwood's are (about -16 dBFS while speaking, peaks under -1 dBFS).
- Every wave lives in the game's one Dialog folder, shared by all maps: a map cannot carry its voice in its own folder
  or in the .map, so mapgen/install.py copies it there (and takes the map's old waves out), and mapgen/strings.py
  names a wave for a line only when that wave is installed and was made from the line's present text.
- Westwood voices what is said in a dialogue window: 965 of its 1391 campaign strings, the talk lines, shop
  greetings ("War03b:Shopkeeper" -> gmbyz02e) and refusals (War05A's "FarmerHuffy", a second TellStory after "no").
  Never signs, journal entries, hints, dialogue titles or mission banners; nor do we. Text over a head (A.chat) and
  on screen (A.print) is plain text with no key, so it cannot carry a voice: a refusal is q.tell, not A.chat.

The steps (Spec.build runs `build_step` after the scripts are written; NOX_NOVOICE=1 skips it while trying seeds):
    lines    which keys are spoken and by whom: <Name>.speech.json (QuestBook.write_strings) and the shopkeepers'
             greetings in the map's objects
    cast     a voice per speaker, the same every build: an archetype from the portrait, the body and the title
             ("Father Odo" a priest, "Old Brannoc" an elder, a Maiden clone a woman), then Kokoro's best voice for it
             not yet taken on the map, blended 3:1 with a second voice and given its own pace; a design pins one with
             q.talker(name, lines, voice="elder" | "bm_george" | {"mix": [["bm_george", 0.7], ["am_onyx", 0.3]],
             "speed": 0.9})
    names    a wave per line, 8 characters as Westwood's: two letters of the map, two of its crc32 in base 36, the
             line's number and "e" (Thornwick's first line: "th9a001e")
    synth    Kokoro v1.0 (kokoro-onnx, run locally on the CPU in its own venv: no paid API, no key) into a cache
             keyed by text, voice, model and mastering, copied into <out>/<Name>_dialog/
    manifest <out>/<Name>.voice.json: key -> wave, speaker, voice, the spoken text, its hash, seconds

    py mapgen/voice.py fetch                                     install the TTS (once per PC; see LOCK below)
    py mapgen/voice.py voice mapgen/out/thornwick Thornwick       voice a built map again (no rebuild)
    py mapgen/voice.py check mapgen/out/thornwick Thornwick       every spoken line has a good wave
    py mapgen/voice.py cast mapgen/out/thornwick Thornwick        who speaks with which voice, without synthesis
    py mapgen/voice.py say "Well met, stranger." --voice bm_george --out say.wav

The TTS and its model are build tools, not committed: `fetch` makes a venv in .tools/voice/ (NOX_VOICE_HOME moves
it) with kokoro-onnx and its model files. mapgen/voice.lock.json (committed) records what was installed: the
packages pip resolved and each model file's SHA-256; a later fetch installs exactly those and refuses a file whose hash
differs.
"""
import argparse, array, collections, glob, hashlib, json, os, re, shutil, struct, subprocess, sys, tempfile, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.environ.get("NOX_VOICE_HOME") or os.path.join(REPO, ".tools", "voice")
LOCK = os.path.join(HERE, "voice.lock.json")
KOKORO_ONNX = "0.4.9"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
RATE = 22050                    # Westwood's dialogue rate (its MP3 waves); PCM 16-bit mono
MASTER = "m1"                   # the mastering below; a change here re-makes every cached wave
LOUD, CEIL, KNEE = -16.0, -1.0, -6.0      # dBFS: speaking level, peak ceiling, where the soft limiter starts
LEAD, TAIL = 0.03, 0.15         # seconds of silence before and after (Westwood's: 0-20 ms, 0-180 ms)
NOX = r"C:\GOG Games\Nox"

# Kokoro v1.0's English voices (hexgrad/Kokoro-82M VOICES.md): a = American, b = British; f, m.
VOICES = ("af_heart", "af_bella", "af_nicole", "af_aoede", "af_kore", "af_sarah", "af_nova", "af_sky", "af_alloy",
          "af_jessica", "af_river", "am_michael", "am_fenrir", "am_puck", "am_echo", "am_eric", "am_liam", "am_onyx",
          "am_santa", "am_adam", "bf_emma", "bf_isabella", "bf_alice", "bf_lily", "bm_george", "bm_fable", "bm_lewis",
          "bm_daniel")
# Each part: lead voices in order of preference (Kokoro's better-graded first), voices blended in at a quarter, pace.
ARCHETYPES = {
    "elder":    (("bm_george", "bm_fable", "bm_lewis", "am_michael"), ("am_onyx", "bm_daniel", "am_fenrir"), (0.86, 0.93)),
    "priest":   (("bm_fable", "bm_george", "bm_daniel"), ("bm_lewis", "am_michael", "am_onyx"), (0.86, 0.92)),
    "guard":    (("am_fenrir", "bm_lewis", "am_onyx", "am_michael", "bm_daniel", "am_eric"),
                 ("am_onyx", "am_fenrir", "bm_lewis", "am_eric", "am_echo"), (0.97, 1.05)),
    "man":      (("am_michael", "bm_daniel", "am_eric", "am_echo", "am_liam", "am_puck", "bm_lewis", "am_fenrir",
                  "bm_george", "bm_fable", "am_onyx"), ("am_echo", "am_eric", "bm_daniel", "am_liam", "am_michael"),
                 (0.95, 1.05)),
    "rogue":    (("am_puck", "am_eric", "bm_daniel", "am_liam"), ("am_echo", "am_puck", "am_liam"), (1.02, 1.1)),
    "merchant": (("am_michael", "bm_fable", "am_puck", "am_eric", "bm_daniel"), ("am_echo", "bm_george", "am_liam"),
                 (0.98, 1.05)),
    "brute":    (("am_onyx", "bm_lewis", "am_fenrir"), ("am_fenrir", "am_onyx", "bm_lewis"), (0.82, 0.9)),
    "woman":    (("bf_emma", "af_heart", "bf_isabella", "af_sarah", "af_kore", "af_aoede", "af_bella", "bf_alice",
                  "af_nova", "bf_lily", "af_alloy"), ("bf_isabella", "af_sarah", "bf_lily", "af_kore", "af_heart"),
                 (0.96, 1.04)),
    "girl":     (("af_bella", "af_sky", "bf_lily", "af_nova", "af_heart"), ("af_sky", "bf_lily", "af_bella"), (1.0, 1.08)),
    "crone":    (("bf_emma", "bf_alice", "bf_isabella", "af_sarah"), ("bf_alice", "bf_isabella", "af_kore"), (0.86, 0.93)),
}
# what a title or an epithet in the map's text says of a speaker ("Father Odo", "Old Brannoc", "Reeve Aldric")
OLD = r"Old|Granny|Grandma|Grandmother|Grandfather|Gramps|Widow|Elder|Mother|Abbot"
PRIEST = r"Father|Brother|Priest|Abbot|Friar|Deacon"
ELDER = r"Reeve|Mayor|Lord|Lady|Elder|Master|Archmagister|Magister|Sage"
GUARD = r"Watch|Watchman|Guard|Gate|Sentry|Captain|Sergeant|Soldier|Warden|Knight|Jailer"
WOMEN_TYPES = {"Maiden"}
BRUTE_TYPES = r"Ogre|Grunt|Troll|Goon"
B36 = "0123456789abcdefghijklmnopqrstuvwxyz"


def text_sha(text):
    """The hash a wave records of the text it was made from (strings.py names a wave only while they match)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _load(p, default=None):
    if not os.path.exists(p): return default
    with open(p, encoding="utf-8") as f: return json.load(f)


def _dump(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


# ---- what is spoken, and by whom -------------------------------------------------------------------------------------
def _from_config(path):
    """Speakers and portraits read back from a map's quests_config.go (a map built before <Name>.speech.json)."""
    src = open(path, encoding="utf-8").read()
    lines, pics = {}, dict(re.findall(r'Portrait\("([^"]+)", "([^"]+)"\)', src))
    for name, body in re.findall(r'Talker\("([^"]+)", \[\]Line\{(.*?)\n\t\t\}\)', src, re.S):
        for key in re.findall(r'\bText: "([^"]+)"', body): lines.setdefault(key, name)
        for key, who in re.findall(r'\{Kind: "tell", A: "([^"]+)", B: "([^"]+)"', body): lines.setdefault(key, who)
    return dict(lines=lines, pics=pics, voices={})


def people(objects):
    """{script name: {type, donor}} of the map's creatures and [(greeting key, speaker, shopkeeper type)], from a Spec's
    objects (a clone names its donor) or from a map exported by validate/mapdata (each object's type is "t")."""
    who, shops = {}, []
    for o in objects:
        t = o.get("type") or o.get("t") or ""
        donor = ((o.get("clone") or {}).get("scr") or "").split(":")[-1]
        if o.get("scr"): who[o["scr"]] = dict(type=t, donor=donor)
        g = ((o.get("xfer") or {}).get("ShopkeeperInfo") or {}).get("ShopkeeperGreetingText") if isinstance(o.get("xfer"), dict) else None
        if g:
            sp = o.get("scr") or f"{t}#{len(shops) + 1}"
            shops.append((g, sp, t))
            who[sp] = dict(type=t, donor="", shop=True)
    return who, shops


def spoken(out_dir, name, objects=None):
    """(strings, {key: speaker} in the table's order, pics, voices, people): every line said in a dialogue window."""
    strings = _load(os.path.join(out_dir, f"{name}.strings.json"), {})
    sp = _load(os.path.join(out_dir, f"{name}.speech.json"))
    cfg = os.path.join(out_dir, f"{name}_scripts", "quests_config.go")
    if sp is None: sp = _from_config(cfg) if os.path.exists(cfg) else dict(lines={}, pics={}, voices={})
    if objects is None:                 # the CLI on a built map: the checker's export of it, if there is one
        repos = (REPO, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(out_dir)))))
        ex = next((p for p in (os.path.join(r, "validate", "out", "json", f"{name}.json") for r in repos)
                   if os.path.exists(p)), None)
        objects = (_load(ex) or {}).get("objects", []) if ex else []
    who, shops = people(objects)
    lines = dict(sp["lines"])
    for key, speaker, _ in shops:
        if key in strings: lines.setdefault(key, speaker)
    order = {k: n for n, k in enumerate(strings)}
    lines = {k: lines[k] for k in sorted((k for k in lines if k in strings), key=order.get)}
    return strings, lines, sp.get("pics", {}), sp.get("voices", {}), who


# ---- casting ---------------------------------------------------------------------------------------------------------
def _is_woman(person, pic):
    sys.path.insert(0, HERE)
    from kit.story import is_woman
    return (person.get("type") in WOMEN_TYPES or (person.get("donor") and is_woman(person["donor"]))
            or bool(re.match(r"(Maiden|Townswoman|Woman|Ingrid|Matilda|Lady|Sister)", pic or "")))


def archetype(speaker, person, pic, title, texts):
    """The part a speaker plays (ARCHETYPES), from its body, portrait, title and what the map's text calls it."""
    person, pic, title = person or {}, pic or "", title or speaker
    t = person.get("type") or ""
    if person.get("shop"): return "merchant"
    if re.match(BRUTE_TYPES, t) or "Ogre" in pic: return "brute"
    first = title.split()[0] if title.split() else ""
    called = set(re.findall(rf"\b([A-Z][a-z]+) {re.escape(title.split()[-1])}\b", texts)) if title.split() else set()
    words = called | {first}
    old = any(re.fullmatch(OLD, w) for w in words)
    if _is_woman(person, pic):
        if old: return "crone"
        return "girl" if re.match(r"(Girl|Lass|Little)\b", title) else "woman"
    if any(re.fullmatch(PRIEST, w) for w in words) or re.search(r"Priest|Undertaker|Monk", pic): return "priest"
    if old or any(re.fullmatch(ELDER, w) for w in words) or re.search(r"Theogrin|Aldwyn|Horvath|Wizard|Mystic|Hermit", pic):
        return "elder"
    if (re.search(r"Warrior|Guard|Warden|Captain|Knight|Soldier", pic) or re.match(GUARD, speaker)
            or any(re.fullmatch(GUARD, w) for w in words) or re.match(r"(Swordsman|Archer|Knight|Guard)", t)):
        return "guard"
    if re.search(r"Morgan|Rogue|Thief|Bandit", pic) or re.match(r"(Rogue|Thief|Bandit|Smuggler)", speaker): return "rogue"
    return "man"


def _recipe(mix, speed, part):
    lead = mix[0][0]
    return dict(part=part, mix=[[v, round(float(w), 3)] for v, w in mix], speed=round(float(speed), 2),
                lang="en-gb" if lead.startswith("b") else "en-us")


def cast(speakers):
    """{speaker: voice recipe}. speakers: {name: dict(part=archetype, n=lines, voice=design's pin or None)}. The speakers
    with the most lines choose first; each takes its part's best lead voice the map has used least, blended 3:1 with a
    partner no one else on the map pairs with it, at a pace drawn from its name: the same cast every build."""
    used, pairs, out = collections.Counter(), set(), {}
    for s in sorted(speakers, key=lambda s: (-speakers[s]["n"], s)):
        info = speakers[s]
        pin = info.get("voice")
        h = zlib.crc32(s.encode())
        if isinstance(pin, dict):
            out[s] = _recipe(pin["mix"], pin.get("speed", 1.0), info["part"])
            used[pin["mix"][0][0]] += 1; continue
        part = pin if pin in ARCHETYPES else info["part"]
        leads, partners, (lo, hi) = ARCHETYPES[part]
        lead = pin if pin in VOICES else min(leads, key=lambda v: (used[v], leads.index(v)))
        rot = h % len(partners)
        cands = [p for p in partners[rot:] + partners[:rot] if p != lead]
        partner = next((p for p in cands if (lead, p) not in pairs), cands[0])
        speed = lo + (hi - lo) * ((h >> 8) % 1000) / 999
        used[lead] += 1; pairs.add((lead, partner))
        out[s] = _recipe([[lead, 0.75], [partner, 0.25]], speed, part)
    return out


# ---- names and text --------------------------------------------------------------------------------------------------
def wave_code(name):
    """Four characters for the map's waves: two letters of its name and two of its crc32 in base 36."""
    n = zlib.crc32(name.encode()) % 1296
    return (re.sub(r"[^a-z]", "", name.lower()) + "xx")[:2] + B36[n // 36] + B36[n % 36]


def said(text):
    """The text as it is spoken: line breaks run on, Westwood's " -- " is a pause, shouted words are not spelled out."""
    s = re.sub(r"\s*\n+\s*", " ", text.replace("\r", ""))
    s = re.sub(r"\s*--+\s*", ", ", s)
    s = re.sub(r"\.{4,}", "...", s)
    s = re.sub(r"!{2,}", "!", s); s = re.sub(r"\?{2,}", "?", s)
    s = re.sub(r"\b[A-Z]{2,}\b", lambda m: m.group(0).capitalize(), s)
    s = re.sub(r"[\[\]<>{}*_#|~^]", "", s)
    return re.sub(r"\s{2,}", " ", s).strip()


def plan(out_dir, name, objects=None):
    """The manifest for a built map's lines, without sound: each spoken key's wave name, speaker, voice and words."""
    strings, lines, pics, pins, who = spoken(out_dir, name, objects)
    texts = "\n".join(strings.values())
    counts = collections.Counter(lines.values())
    speakers = {}
    for s, n in counts.items():
        title = strings.get(f"NPC:{s}") or ("Shopkeeper" if (who.get(s) or {}).get("shop") else s)
        speakers[s] = dict(part=archetype(s, who.get(s), pics.get(s), title, texts), n=n, voice=pins.get(s))
    voices = cast(speakers)
    code = wave_code(name)
    assert len(lines) <= 999, f"{name}: {len(lines)} spoken lines; wave names hold 999"
    man = dict(map=name, code=code, rate=RATE, engine=_engine(), speakers={}, lines={})
    for s, v in sorted(voices.items()):
        p = who.get(s) or {}
        man["speakers"][s] = dict(v, title=strings.get(f"NPC:{s}") or ("Shopkeeper" if p.get("shop") else s),
                                  pic=pics.get(s, ""), body=p.get("type") or
                                  p.get("donor") or "", lines=counts[s])
    for n, (key, s) in enumerate(lines.items(), 1):
        v = voices[s]
        words = said(strings[key])
        h = hashlib.sha1(json.dumps([man["engine"], RATE, MASTER, words, v["mix"], v["speed"], v["lang"]]).encode()).hexdigest()
        man["lines"][key] = dict(wave=f"{code}{n:03d}e", speaker=s, said=words, text_sha=text_sha(strings[key]), hash=h)
    return man


# ---- the TTS ---------------------------------------------------------------------------------------------------------
def venv_python():
    v = os.path.join(HOME, "venv")
    return os.path.join(v, "Scripts", "python.exe") if os.name == "nt" else os.path.join(v, "bin", "python")


def model_path(fn):
    return os.path.join(HOME, "models", fn)


def _engine():
    """What made a wave, for its cache key: the model as the lock pins it."""
    files = (_load(LOCK) or {}).get("files", {})
    return "kokoro-onnx " + ",".join(f"{fn}:{files.get(fn, {}).get('sha256', '?')[:12]}" for fn in MODEL_FILES)


def tts_ready():
    """None when the TTS is installed here, else what is missing."""
    if not os.path.exists(venv_python()): return f"no TTS venv ({venv_python()})"
    miss = [fn for fn in MODEL_FILES if not os.path.exists(model_path(fn))]
    return f"no model file {', '.join(miss)} in {os.path.dirname(model_path(''))}" if miss else None


def _cache(h):
    return os.path.join(HOME, "cache", h[:2], h + ".wav")


def synthesize(jobs, timeout=7200):
    """Makes each job's wave ([(said, recipe, out path)]) in the venv's Python (kokoro-onnx, numpy). Returns its output."""
    os.makedirs(os.path.join(HOME, "tmp"), exist_ok=True)
    spec = dict(model=model_path(MODEL_FILES[0]), voices=model_path(MODEL_FILES[1]), rate=RATE,
                jobs=[dict(text=t, mix=v["mix"], speed=v["speed"], lang=v["lang"], out=p) for t, v, p in jobs])
    fd, jp = tempfile.mkstemp(suffix=".json", dir=os.path.join(HOME, "tmp"))
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(spec, f, ensure_ascii=False)
    try:
        r = subprocess.run([venv_python(), os.path.abspath(__file__), "synth", jp], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    finally:
        os.remove(jp)
    if r.returncode: raise RuntimeError("the TTS failed:\n" + (r.stdout + r.stderr)[-3000:])
    return r.stdout


def _worker(jobs_path):
    """Run by the venv's Python: Kokoro makes each job's line, mastered and written as PCM 16-bit mono."""
    import numpy as np
    from kokoro_onnx import Kokoro
    spec = json.load(open(jobs_path, encoding="utf-8"))
    k = Kokoro(spec["model"], spec["voices"])
    style_of = getattr(k, "get_voice_style", None) or (lambda v: k.voices[v])
    styles = {}

    def style(mix):
        key = json.dumps(mix)
        if key not in styles:
            styles[key] = sum(np.asarray(style_of(v), dtype=np.float32) * w for v, w in mix) / sum(w for _, w in mix)
        return styles[key]

    for job in spec["jobs"]:
        x, sr = k.create(job["text"], voice=style(job["mix"]), speed=job["speed"], lang=job["lang"])
        pcm = _master(np.asarray(x, dtype=np.float64), sr, spec["rate"])
        os.makedirs(os.path.dirname(job["out"]), exist_ok=True)
        part = job["out"] + ".part"
        write_wav(part, pcm.tobytes(), spec["rate"])
        os.replace(part, job["out"])
        print(f"made {os.path.basename(job['out'])} {len(pcm) / spec['rate']:.1f} s", flush=True)


def _master(x, sr, rate):
    """Westwood's dialogue loudness (rules measured on its PCM waves: speaking at -16 dBFS, peaks at 0): resampled to
    `rate` (FFT, the top 8% of the band rolled off), raised to LOUD while speaking, peaks bent under CEIL from KNEE,
    5 ms fades, LEAD and TAIL of silence. Returns int16 samples."""
    import numpy as np
    if sr != rate and len(x):
        n = int(round(len(x) * rate / sr))
        X = np.fft.rfft(x)
        m = n // 2 + 1
        Y = np.zeros(m, dtype=complex)
        Y[:min(m, len(X))] = X[:min(m, len(X))]
        s0 = int(m * 0.92)
        Y[s0:] *= 0.5 * (1 + np.cos(np.pi * np.arange(m - s0) / max(1, m - s0)))
        x = np.fft.irfft(Y, n) * (n / len(x))
    f = max(1, rate // 50)
    fr = np.sqrt((x[:len(x) // f * f].reshape(-1, f) ** 2).mean(axis=1)) if len(x) >= f else np.array([np.sqrt((x ** 2).mean())])
    act = fr[fr > fr.max() * 10 ** (-30 / 20)] if fr.size and fr.max() > 0 else fr
    level = np.sqrt((act ** 2).mean()) if act.size else 0.0
    if level > 0: x = x * (10 ** (LOUD / 20) / level)
    t, c = 10 ** (KNEE / 20), 10 ** (CEIL / 20)
    a = np.abs(x)
    over = a > t
    x[over] = np.sign(x[over]) * (t + (c - t) * np.tanh((a[over] - t) / (c - t)))
    fade = min(len(x) // 2, int(rate * 0.005))
    if fade:
        ramp = np.linspace(0, 1, fade)
        x[:fade] *= ramp; x[-fade:] *= ramp[::-1]
    x = np.concatenate([np.zeros(int(rate * LEAD)), x, np.zeros(int(rate * TAIL))])
    return np.clip(np.round(x * 32767), -32768, 32767).astype("<i2")


def write_wav(path, frames, rate):
    """A canonical PCM 16-bit mono WAV (the header Westwood's PCM dialogue waves have: fmt of 16 bytes, then data)."""
    import wave
    with wave.open(path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate); w.writeframes(frames)


def wave_info(path):
    """The header as the game's stream reader sees it and the samples' peak: dict(tag, channels, rate, bits, seconds,
    peak, clipped) or a dict with "error"."""
    try:
        b = open(path, "rb").read()
    except OSError as e:
        return dict(error=str(e))
    if b[:4] != b"RIFF" or b[8:12] != b"WAVE": return dict(error="not a RIFF WAVE file")
    o, fmt, data = 12, None, None
    while o + 8 <= len(b):
        cid, sz = b[o:o + 4], struct.unpack_from("<I", b, o + 4)[0]
        if cid == b"fmt ": fmt = struct.unpack_from("<HHIIHH", b, o + 8)
        elif cid == b"data": data = b[o + 8:o + 8 + sz]
        o += 8 + sz + (sz & 1)
    if not fmt or data is None: return dict(error="no fmt or data chunk")
    tag, ch, rate, avg, align, bits = fmt
    out = dict(tag=tag, channels=ch, rate=rate, bits=bits, seconds=len(data) / avg if avg else 0.0, peak=0.0, clipped=0.0)
    if tag == 1 and bits == 16 and data:
        a = array.array("h"); a.frombytes(data[:len(data) // 2 * 2])
        if sys.byteorder != "little": a.byteswap()
        out["peak"] = max(max(a), -min(a)) / 32768
        out["clipped"] = sum(1 for s in a if s >= 32767 or s <= -32768) / len(a)
    return out


def wave_problem(info, words):
    """What is wrong with a dialogue wave for the game, or None."""
    if "error" in info: return info["error"]
    if (info["tag"], info["channels"], info["bits"]) != (1, 1, 16) or info["rate"] not in (22050, 44100):
        return f"format {info['tag']}/{info['channels']} ch/{info['rate']} Hz/{info['bits']} bit (want PCM 16-bit mono 22050 Hz)"
    if info["seconds"] < 0.4: return f"{info['seconds']:.2f} s long"
    if info["peak"] < 0.1: return f"near silent (peak {info['peak']:.2f})"
    if info["clipped"] > 0.001: return f"{info['clipped']:.1%} of the samples clipped"
    speech = max(0.1, info["seconds"] - LEAD - TAIL)
    if words >= 4 and not 1.0 <= words / speech <= 5.5:          # a shout ("Nooooo!") sets no pace
        return f"{words / speech:.1f} words a second (Westwood speaks 2.5-3.3)"
    return None


# ---- the build step --------------------------------------------------------------------------------------------------
def voice(out_dir, name, objects=None, to=None, make=True):
    """Voices a built map's spoken lines: the manifest, then every wave not yet made (from the cache, else the TTS), into
    <to or out_dir>/<Name>_dialog/. Returns (manifest, made now, from the cache, missing reason or None)."""
    to = to or out_dir
    man = plan(out_dir, name, objects)
    wd = os.path.join(to, f"{name}_dialog")
    os.makedirs(wd, exist_ok=True)
    jobs, cached = [], 0
    for key, l in man["lines"].items():
        dst = os.path.join(wd, l["wave"] + ".wav")
        c = _cache(l["hash"])
        if os.path.exists(c):
            shutil.copyfile(c, dst)                 # always: a wave of the same name may hold an older line
            cached += 1
        else:
            jobs.append((key, l, c, dst))
            if os.path.exists(dst): os.remove(dst)  # made from other words or another voice: never left to speak
    why = tts_ready() if jobs and make else None
    if jobs and make and not why:
        try:
            for k0 in range(0, len(jobs), 40):      # a batch at a time: a failure keeps the batches made before it
                synthesize([(l["said"], man["speakers"][l["speaker"]], c) for _, l, c, _ in jobs[k0:k0 + 40]])
        except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
            why = "the TTS failed: " + (str(e).strip().splitlines() or ["?"])[-1][:300]
    made = 0
    for _, l, c, dst in jobs:
        if os.path.exists(c): shutil.copyfile(c, dst); made += 1
    keep = {l["wave"] + ".wav" for l in man["lines"].values()}
    for fn in os.listdir(wd):                       # waves of lines the map no longer has
        if fn not in keep: os.remove(os.path.join(wd, fn))
    for l in man["lines"].values():
        p = os.path.join(wd, l["wave"] + ".wav")
        info = wave_info(p) if os.path.exists(p) else None
        l["voiced"] = bool(info and not wave_problem(info, len(l["said"].split())))
        l["seconds"] = round(info["seconds"], 2) if info and "seconds" in info else 0.0
    _dump(os.path.join(to, f"{name}.voice.json"), man)
    return man, made, cached, why if made < len(jobs) else None


def build_step(objects, out_dir, name):
    """Spec.build's voice step: report lines ("VOICE ..."). Nothing to do for a map without spoken lines."""
    if not os.path.exists(os.path.join(out_dir, f"{name}.strings.json")): return []
    t0 = time.time()
    man, made, cached, why = voice(out_dir, name, objects)
    n = len(man["lines"])
    if not n: return [f"VOICE {name}: no spoken lines"]
    ok = sum(l["voiced"] for l in man["lines"].values())
    line = (f"VOICE {name}: {ok} of {n} lines voiced, {len(man['speakers'])} speakers ({made} made now, {cached} from "
            f"the cache, {time.time() - t0:.0f} s)")
    if why: line += f"; not voiced: {why}" + (" (py mapgen/voice.py fetch)" if tts_ready() else "")
    return [line]


def check(out_dir, name, to=None):
    """[(ok, text)] for the QA gate: every spoken line has a good wave made from its present text, by a cast voice.
    to: where the waves and manifest were written, if not beside the map."""
    out = []
    to = to or out_dir
    man = _load(os.path.join(to, f"{name}.voice.json"))
    strings, lines, _, _, _ = spoken(out_dir, name)
    if not lines: return [(True, "no spoken lines")]
    if not man: return [(False, f"{len(lines)} spoken lines and no {name}.voice.json: the build's voice step did not run "
                                f"(NOX_NOVOICE?) or failed: py mapgen/voice.py voice {os.path.relpath(out_dir, REPO)} {name}")]
    wd = os.path.join(to, f"{name}_dialog")
    missing = [k for k in lines if k not in man["lines"]]
    out.append((not missing, f"{len(lines)} spoken lines, each with a wave" if not missing else
                f"lines without a wave: {', '.join(missing[:6])}"))
    stale = [k for k, l in man["lines"].items() if k in strings and l["text_sha"] != text_sha(strings[k])]
    out.append((not stale, "every wave was made from its line's present text" if not stale else
                f"waves made from older text: {', '.join(stale[:6])}"))
    bad = []
    for k, l in man["lines"].items():
        p = os.path.join(wd, l["wave"] + ".wav")
        why = wave_problem(wave_info(p), len(l["said"].split())) if os.path.exists(p) else "no wave file"
        if why: bad.append(f"{k} ({l['wave']}, {l['speaker']}): {why}")
    secs = sum(l.get("seconds", 0) for l in man["lines"].values())
    out.append((not bad, f"{len(man['lines'])} waves PCM 16-bit mono {RATE} Hz, {secs / 60:.1f} min of speech" if not bad
                else f"{len(bad)} lines not voiced" + (f" ({tts_ready()}: py mapgen/voice.py fetch)" if tts_ready() else "")
                + ": " + "; ".join(bad[:5])))
    names = [l["wave"] for l in man["lines"].values()]
    dup = [w for w, c in collections.Counter(names).items() if c > 1]
    out.append((not dup and all(len(w) <= 8 for w in names), "wave names are 8 characters and unique (Westwood's 8.3)"
                if not dup else f"wave names used twice: {', '.join(dup[:5])}"))
    parts = collections.Counter(v["part"] for v in man["speakers"].values())
    leads = collections.Counter(v["mix"][0][0] for v in man["speakers"].values())
    out.append((True, f"{len(man['speakers'])} speakers: " + ", ".join(f"{p} {n}" for p, n in parts.most_common()) +
                f"; {len(leads)} lead voices"))
    return out


# ---- installing into the game ----------------------------------------------------------------------------------------
def westwood_waves(nox):
    sys.path.insert(0, HERE)
    from strings import read_csf
    _, es = read_csf(os.path.join(nox, "nox.csf"))
    return {v["str2"].lower() for e in es for v in e["vals"] if v.get("str2")}


def install(out_dir, name, nox=NOX):
    """Copies the map's waves into the game's Dialog folder and its manifest beside the map; takes out the waves its
    previous install left that the new build no longer has. Refuses a wave name of Westwood's or of another installed
    map. Safe to repeat. Returns a report line."""
    dialog = os.path.join(nox, "Dialog")
    mdir = os.path.join(nox, "maps", name)
    new = _load(os.path.join(out_dir, f"{name}.voice.json"), {"lines": {}})
    old = _load(os.path.join(mdir, f"{name}.voice.json"), {"lines": {}})
    want = {l["wave"].lower(): l for l in new["lines"].values() if l.get("voiced")}
    theirs = {}
    for p in glob.glob(os.path.join(nox, "maps", "*", "*.voice.json")):
        if os.path.normcase(os.path.dirname(p)) == os.path.normcase(mdir): continue
        for l in (_load(p) or {}).get("lines", {}).values(): theirs[l["wave"].lower()] = os.path.basename(p)
    ww = westwood_waves(nox) if want else set()
    clash = [f"{w} ({'Westwood' if w in ww else theirs[w]})" for w in want if w in ww or w in theirs]
    if clash: sys.exit(f"{name}: wave names already taken: {', '.join(clash[:5])}; set the map's VOICE code")
    on_disk = {f.lower(): f for f in os.listdir(dialog)} if os.path.isdir(dialog) else {}
    gone = 0
    for l in old["lines"].values():
        w = l["wave"].lower()
        if w not in want and w + ".wav" in on_disk:
            os.remove(os.path.join(dialog, on_disk[w + ".wav"])); gone += 1
    copied = 0
    os.makedirs(dialog, exist_ok=True)
    for w, l in want.items():
        src = os.path.join(out_dir, f"{name}_dialog", l["wave"] + ".wav")
        dst = os.path.join(dialog, on_disk.get(w + ".wav", l["wave"] + ".wav"))
        if not (os.path.exists(dst) and open(dst, "rb").read() == open(src, "rb").read()):
            shutil.copyfile(src, dst); copied += 1
    os.makedirs(mdir, exist_ok=True)
    mp = os.path.join(mdir, f"{name}.voice.json")
    if new["lines"]: shutil.copyfile(os.path.join(out_dir, f"{name}.voice.json"), mp)
    elif os.path.exists(mp): os.remove(mp)
    return f"voice: {len(want)} of {len(new['lines'])} lines voiced, {copied} waves copied into Dialog, {gone} old ones removed"


# ---- fetching the TTS ------------------------------------------------------------------------------------------------
def _sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def _download(url, dst):
    import urllib.request
    part = dst + ".part"
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    return part


def fetch():
    """Installs the TTS into HOME: a venv with kokoro-onnx (the lock's packages when it has them, else KOKORO_ONNX and
    what pip resolves for it, then written to the lock) and Kokoro's model files (checked against the lock's SHA-256,
    else hashed and written to it). Safe to repeat: what is already in place and matches is kept."""
    lock = _load(LOCK, {})
    changed = False
    os.makedirs(HOME, exist_ok=True)
    py = venv_python()
    if not os.path.exists(py):
        print(f"making the venv {os.path.dirname(os.path.dirname(py))}")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(HOME, "venv")], check=True)
    want = lock.get("pip") or [f"kokoro-onnx=={KOKORO_ONNX}"]
    have = subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    norm = lambda xs: {re.sub(r"[-_.]+", "-", x.lower()) for x in xs}        # pip writes kokoro_onnx or kokoro-onnx
    if not norm(want) <= norm(have):
        print("installing " + (f"the lock's {len(want)} packages" if lock.get("pip") else want[0]))
        subprocess.run([py, "-m", "pip", "install", "--disable-pip-version-check"] + (["--no-deps"] if lock.get("pip") else [])
                       + want, check=True)
    if not lock.get("pip"):
        lock["pip"] = sorted(subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True, check=True).stdout.split(),
                             key=str.lower)
        lock["python"] = subprocess.run([py, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True,
                                        text=True).stdout.strip()
        changed = True
    files = lock.setdefault("files", {})
    for fn in MODEL_FILES:
        dst, sha = model_path(fn), files.get(fn, {}).get("sha256")
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst) and (not sha or _sha256(dst) == sha):
            if not sha: files[fn] = dict(url=MODEL_URL + fn, sha256=_sha256(dst), bytes=os.path.getsize(dst)); changed = True
            continue
        print(f"downloading {MODEL_URL + fn}")
        part = _download(MODEL_URL + fn, dst)
        got = _sha256(part)
        if sha and got != sha:
            os.remove(part); sys.exit(f"{fn}: SHA-256 {got} is not the lock's {sha}: not installed")
        os.replace(part, dst)
        if not sha: files[fn] = dict(url=MODEL_URL + fn, sha256=got, bytes=os.path.getsize(dst)); changed = True
    if changed:
        lock.update(kokoro_onnx=KOKORO_ONNX, model=MODEL_URL, note="written by py mapgen/voice.py fetch; commit it")
        _dump(LOCK, lock)
        print(f"wrote {LOCK}: commit it, so every PC installs the same TTS")
    p = os.path.join(HOME, "tmp", "fetch_check.wav")
    synthesize([("Well met, stranger. The road north is closed.", cast({"Check": dict(part="man", n=1)})["Check"], p)])
    why = wave_problem(wave_info(p), 8)
    print(f"the TTS works: {p} ({wave_info(p)['seconds']:.1f} s)" if not why else f"the TTS made a bad wave: {why}")
    return 0 if not why else 1


# ---- the command line ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("fetch")
    s = sub.add_parser("synth"); s.add_argument("jobs")
    for c in ("voice", "check", "cast"):
        s = sub.add_parser(c); s.add_argument("out_dir"); s.add_argument("name")
        s.add_argument("--to", help="write the waves and manifest here instead of out_dir")
    s = sub.add_parser("say"); s.add_argument("text"); s.add_argument("--voice", default="man")
    s.add_argument("--out", default="say.wav")
    a = ap.parse_args()
    if a.cmd == "fetch": return fetch()
    if a.cmd == "synth": return _worker(a.jobs)
    if a.cmd == "cast":
        man = plan(a.out_dir, a.name)
        for s_, v in sorted(man["speakers"].items(), key=lambda kv: -kv[1]["lines"]):
            print(f"{s_:14s} {v['title'][:18]:18s} {v['part']:8s} {v['body'][:10]:10s} {v['pic'][:15]:15s} "
                  f"{'+'.join(f'{m}:{w}' for m, w in v['mix'])} x{v['speed']} {v['lang']}  {v['lines']} lines")
        print(f"{len(man['lines'])} spoken lines, waves {man['code']}001e..{man['code']}{len(man['lines']):03d}e")
        return 0
    if a.cmd == "voice":
        man, made, cached, why = voice(a.out_dir, a.name, to=a.to)
        ok = sum(l["voiced"] for l in man["lines"].values())
        print(f"{a.name}: {ok} of {len(man['lines'])} lines voiced ({made} made now, {cached} from the cache)"
              + (f"; not voiced: {why}" + (" (py mapgen/voice.py fetch)" if tts_ready() else "") if why else ""))
        return 0 if ok == len(man["lines"]) else 1
    if a.cmd == "check":
        res = check(a.out_dir, a.name, a.to)
        for ok, t in res: print(("" if ok else "FAILED: ") + t)
        return 0 if all(ok for ok, _ in res) else 1
    if a.cmd == "say":
        why = tts_ready()
        if why: sys.exit(f"{why}: py mapgen/voice.py fetch")
        v = a.voice
        pin = v if v in VOICES else None
        rec = cast({"Say": dict(part=v if v in ARCHETYPES else "man", n=1, voice=pin)})["Say"]
        synthesize([(said(a.text), rec, os.path.abspath(a.out))])
        print(f"{a.out}: {'+'.join(f'{m}:{w}' for m, w in rec['mix'])} x{rec['speed']}, {wave_info(a.out)['seconds']:.1f} s")
        return 0


if __name__ == "__main__":
    sys.exit(main())
