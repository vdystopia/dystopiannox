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

Two engines (NOX_VOICE_ENGINE or --engine; never a silent fallback from one to the other):
    breeze   the default (VO-2, 2026-10-08): Breeze TTS 2 on the GPU (CUDA, about 8 GiB). Each speaker is cast a voice
             description (age, timbre, accent, manner) and a seed; a design take of the description is rendered (the
             best of DESIGN_TAKES by the quality gate) and kept as the speaker's reference wave, then every line is
             rendered by voice direction from that reference, so a character sounds the same in every line. Lines may
             carry inline vocal events ("(sigh)", "(laugh)") and a mood (q.say(..., spoken=, mood=)). Every take passes
             the quality gate (Whisper's transcript against the line, names excepted; the pitch band of the part and
             of the reference; a speaking pace), else it is rendered again with a new seed, up to LINE_TRIES times.
             The GPU is used only while pc1 is not gaming (gpu_busy): a build waits, or skips with NOX_VOICE_GPU=skip.
    kokoro   the first engine (VO-1), kept as an explicit option only: Kokoro v1.0 on the CPU, voice blends per part.

The steps (Spec.build runs `build_step` after the scripts are written; NOX_NOVOICE=1 skips it while trying seeds):
    lines    which keys are spoken and by whom: <Name>.speech.json (QuestBook.write_strings: speakers, portraits,
             pinned voices, deliveries) and the shopkeepers' greetings in the map's objects
    cast     a voice per speaker, the same every build: a part from the portrait, the body and the title ("Father
             Odo" a priest, "Old Brannoc" an elder, a Maiden clone a woman), then the part's description the map has
             used least (breeze) or Kokoro's best voice for it (kokoro); a design pins one with q.talker(name, lines,
             voice={"desc": "...", "seed": 7}) or q.voice(name or line key, ...) (cast_breeze has the forms)
    names    a wave per line, 8 characters as Westwood's: two letters of the map, two of its crc32 in base 36, the
             line's number and "e" (Thornwick's first line: "th9a001e")
    synth    into a cache (breeze: keyed by the spoken text and tags, the speaker's reference wave, description, mood,
             model, gate and mastering; kokoro: by text, voice, model and mastering), copied into <out>/<Name>_dialog/
    manifest <out>/<Name>.voice.json: key -> wave, speaker, the spoken text, its hash, seconds, the gate's measures

    py mapgen/voice.py fetch [--engine kokoro] [--model-from DIR]  install the TTS (once per PC; see LOCK below)
    py mapgen/voice.py voice mapgen/out/thornwick Thornwick       voice a built map again (no rebuild)
                       [--only KEY,SPEAKER,...] [--retry] [--gpu wait|games|skip|force]
    py mapgen/voice.py check mapgen/out/thornwick Thornwick       every spoken line has a good wave
    py mapgen/voice.py cast mapgen/out/thornwick Thornwick        who speaks with which voice, without synthesis
    py mapgen/voice.py say "Well met, stranger." --voice elder --out say.wav   (or --voice "<a description>" --seed 7)

The TTS and its models are build tools, not committed: `fetch` makes the venv in .tools/voice/ (NOX_VOICE_HOME moves
it). mapgen/voice.lock.json (committed) records what was installed, per engine: the packages pip resolved, the Breeze
source commit, each model file's SHA-256 (the HF revision for Breeze and Whisper); a later fetch installs exactly
those and refuses a file whose hash differs. Breeze's weights are hard-linked from an existing Hugging Face cache
when one has them (--model-from, NOX_VOICE_MODEL_FROM, HF_HUB_CACHE, HF_HOME), else downloaded.

Licence: Breeze TTS 2's weights and what they make (the waves) are under the BreezeBlue Research and Non-Commercial
License: fine for the user's own maps; a map sold or used commercially must be re-voiced (or the voices licensed).
"""
import argparse, array, base64, collections, glob, hashlib, json, os, re, shutil, struct, subprocess, sys, tempfile
import threading, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.environ.get("NOX_VOICE_HOME") or os.path.join(REPO, ".tools", "voice")
LOCK = os.path.join(HERE, "voice.lock.json")
ENGINES = ("breeze", "kokoro")
DEFAULT_ENGINE = "breeze"
RATE = 22050                    # Westwood's dialogue rate (its MP3 waves); PCM 16-bit mono
MASTER = "m1"                   # the mastering below; a change here re-makes every cached wave
LOUD, CEIL, KNEE = -16.0, -1.0, -6.0      # dBFS: speaking level, peak ceiling, where the soft limiter starts
LEAD, TAIL = 0.03, 0.15         # seconds of silence before and after (Westwood's: 0-20 ms, 0-180 ms)
NOX = r"C:\GOG Games\Nox"
B36 = "0123456789abcdefghijklmnopqrstuvwxyz"

# ---- Kokoro (the explicit option) -----------------------------------------------------------------------------------
KOKORO_ONNX = "0.4.9"
MODEL_URL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
MODEL_FILES = ("kokoro-v1.0.onnx", "voices-v1.0.bin")
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

# ---- Breeze TTS 2 (the default) -------------------------------------------------------------------------------------
BREEZE_GIT = "https://github.com/breezeblue-ai/breeze-tts.git"
BREEZE_COMMIT = "58ec70ce5fa4cc361bdebf77ec40d1365da00ab2"     # 2026-09-30, the commit the audition ran
TORCH_INDEX = "https://download.pytorch.org/whl/cu128"
TORCH_PIP = ("torch==2.9.1", "torchaudio==2.9.1")              # from TORCH_INDEX (PyPI's Windows torch has no CUDA)
BREEZE_PIP = ("qwen-tts==0.1.1", "transformers==4.57.3", "numpy>=2.0", "soundfile>=0.13", "librosa>=0.11")
BREEZE_MODELS = {                                               # name: (Hugging Face repo, revision)
    "tts": ("BreezeBlue/Breeze-TTS-2", "3e28c5151381a722f1d8661b4118c298caa77aa4"),
    "asr": ("openai/whisper-large-v3-turbo", "41f01f3fe87f28c78e2fbf8b568835947dd65ed9"),   # the gate's ears (MIT)
}
MODEL_SKIP = re.compile(r"^(assets/|README\.md$|\.gitattributes$)")
CFG = 4.0                       # Breeze's guidance scale: 4 follows the description closely (its README)
MASTER_B = "m1t"                # MASTER, with the take's leading and trailing silence trimmed first
GATE = "g1"                     # the quality gate below; a change re-makes every cached Breeze wave
DESIGN_TAKES, DESIGN_MAX, LINE_TRIES = 2, 6, 4
VRAM_MIB = 10 * 1024            # what one worker needs free: Breeze 7.8 GiB at peak, Whisper 1.6 GiB
REF_WORDS = 28                  # a reference of about 10 s: the speaker's line nearest this many words
# the median pitch a part's takes must have (Hz): wide on purpose, the description sets the voice within it
BANDS = {"elder": (65, 200), "priest": (65, 200), "guard": (65, 200), "man": (65, 210), "rogue": (70, 210),
         "merchant": (70, 215), "brute": (55, 170), "woman": (140, 330), "girl": (170, 400), "crone": (120, 320)}
TAGS = ("laugh", "chuckle", "sigh", "cough", "clears throat", "scoff", "gasp", "sniff", "groan")
AUTO_TAGS = ((r"(?<![\w'])Ha!(?=\s|$)", "(laugh)"), (r"(?<![\w'])Hmph[.!]?(?=\s|$)", "(scoff)"))
REF_DRIFT = 5.0                 # semitones a line's median pitch may stray from its reference's
GPU_BUSY_PCT = 25               # other programs' GPU use that counts as busy (the pc1 AI guard's threshold)
IDLE_S = 300                    # the user away from pc1 this long before the GPU is used (NOX_VOICE_IDLE, seconds)
GAME_PROCS = {"opennox.exe", "nox.exe", "opennox-hd.exe"}

# Fantasy village casting: who the part is, the timbre, an English accent, the manner. A speaker gets its part's
# description the map has used least; the speakers with most lines choose first.
DESCRIPTIONS = {
    "elder": (
        "A dignified old man in his late sixties, the head of a village. Rich, resonant, slightly worn baritone, a "
        "refined southern English accent. Measured, deliberate and grave, a man used to being listened to.",
        "An old village elder in his seventies. Deep, weathered, gravelly bass voice with a slight rasp, a rural "
        "northern English accent. Speaks slowly and warmly, with quiet authority.",
        "A frail old man in his eighties. Thin, reedy, slightly quavering voice, a soft West Country accent. Speaks "
        "slowly and kindly, a little short of breath.",
        "A stern old magistrate in his late sixties. Dry, clipped, slightly hoarse baritone, a crisp English accent. "
        "Precise and unhurried, with an edge of impatience."),
    "priest": (
        "An elderly village priest in his sixties. Solemn, resonant, measured baritone with a refined English accent. "
        "Speaks quietly and gravely, slow and deliberate.",
        "A middle-aged monk in his forties. Soft, warm, gentle tenor, a mild English accent. Calm, patient and kindly, "
        "like a man used to comforting the grieving.",
        "A stern old abbot in his seventies. Deep, hollow, sonorous bass voice, a precise English accent. Severe and "
        "solemn, every word weighed."),
    "guard": (
        "A young soldier of the town watch in his twenties. Clear, firm baritone, a broad Yorkshire accent. Brisk, "
        "dutiful and alert, friendly enough but businesslike.",
        "A veteran watch sergeant in his fifties. Heavy, husky, battle-worn voice, a broad West Country accent. "
        "Steady and unimpressed, with dry humour under the gruffness.",
        "A burly guard in his thirties. Big, booming chest voice, a rough London accent. Loud, blunt and impatient.",
        "A weary middle-aged guardsman. Low, rough, tired voice, a flat Midlands accent. Plain and matter-of-fact, "
        "speaking as if he has said it all before."),
    "man": (
        "A plain-spoken villager in his forties. Hoarse, earnest baritone, a rural Midlands English accent. Sincere "
        "and direct, a little breathless.",
        "A cheerful countryman in his fifties. Warm, round, ruddy voice, a broad West Country accent. Friendly, chatty "
        "and unhurried.",
        "A hearty villager in his forties. Gruff baritone with a laugh in it, a Yorkshire accent. Blunt and practical.",
        "A young villager in his twenties. Light, bright tenor, a friendly southern English accent. Eager and open, "
        "quick to talk.",
        "A villager in his thirties. Plain, slightly nasal voice, a Lancashire accent. Matter-of-fact and a little "
        "gossipy.",
        "A stocky villager in his forties. Deep, rough, slow voice, a Cornish accent. Careful and good-natured."),
    "rogue": (
        "A sly young rogue in his late twenties. Smooth, husky, slightly raspy voice with a London street accent. "
        "Playful and knowing, as if sharing a secret, with a smirk in his voice.",
        "A wiry thief in his thirties. Thin, quick, slightly nasal voice, a sharp Cockney accent. Fast-talking, shifty "
        "and amused."),
    "merchant": (
        "A shrewd old shopkeeper in his sixties. Dry, precise, slightly reedy voice, a refined English accent. Polite "
        "and businesslike, always weighing a bargain.",
        "A big, hearty shopkeeper in his forties. Warm, booming baritone, a northern English accent. Proud of his "
        "wares, bluff and welcoming.",
        "A brisk shopkeeper in his thirties. Quick, bright, friendly voice, a Midlands accent. Busy and cheerful, a "
        "salesman's patter."),
    "brute": (
        "A huge, brutish man. Very deep, guttural, growling bass voice, a rough northern English accent. Slow, "
        "menacing and dim.",
        "A hulking thug in his thirties. Thick, gravelly, heavy voice, a coarse London accent. Threatening and blunt."),
    "woman": (
        "A young woman in her late teens. Bright, breathy, quick voice, a Devon accent. Cheerful and curious.",
        "A friendly village woman in her thirties. Warm, bright mezzo-soprano, a West Country accent. Chatty and "
        "good-humoured.",
        "A practical woman in her forties. Firm, slightly husky voice, a northern English accent. Plain-spoken and "
        "no-nonsense.",
        "A gentle young woman in her twenties. Soft, light, sweet voice, a gentle southern English accent. Shy and "
        "kind, speaking softly.",
        "A sharp-tongued woman in her thirties. Bright, brassy voice, a London accent. Quick, cheeky and gossipy.",
        "A woman in her fifties. Low, smooth, warm voice, a Yorkshire accent. Thoughtful and wry."),
    "girl": (
        "A girl of about twelve. High, bright, clear voice, a soft English accent. Excited and quick.",
        "A shy village girl of about ten. Small, soft, light voice, a West Country accent. Hesitant and earnest."),
    "crone": (
        "An old woman in her seventies. Thin, cracked, wavering voice, a rural West Country accent. Shrewd and knowing.",
        "A grandmother in her eighties. Soft, papery, trembling voice, a gentle northern English accent. Kind and slow."),
}


def engine_name(engine=None):
    e = (engine or os.environ.get("NOX_VOICE_ENGINE") or DEFAULT_ENGINE).strip().lower()
    if e not in ENGINES: sys.exit(f"voice engine {e!r}: not one of {', '.join(ENGINES)} (NOX_VOICE_ENGINE, --engine)")
    return e


def text_sha(text):
    """The hash a wave records of the text it was made from (strings.py names a wave only while they match)."""
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:12]


def _load(p, default=None):
    if not os.path.exists(p): return default
    with open(p, encoding="utf-8") as f: return json.load(f)


def _dump(p, obj):
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="\n") as f: json.dump(obj, f, ensure_ascii=False, indent=1)
    os.replace(tmp, p)


def _lock_all():
    lock = _load(LOCK, {})
    return {"kokoro": lock} if "pip" in lock else lock          # the lock before Breeze was Kokoro's alone


def _lock(engine):
    return _lock_all().get(engine, {})


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
    """(strings, {key: speaker} in the table's order, pics, voices, people, deliveries): every line said in a dialogue
    window. voices: {speaker or line key: pin}; deliveries: {key: {"spoken": text with tags, "mood": direction}}."""
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
    return strings, lines, sp.get("pics", {}), sp.get("voices", {}), who, sp.get("delivery", {})


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
    """Kokoro: {speaker: voice recipe}. speakers: {name: dict(part=archetype, n=lines, voice=design's pin or None)}. The
    speakers with the most lines choose first; each takes its part's best lead voice the map has used least, blended 3:1
    with a partner no one else on the map pairs with it, at a pace drawn from its name: the same cast every build. A
    Breeze pin (a description) does not apply here: the speaker is cast by its part."""
    used, pairs, out = collections.Counter(), set(), {}
    for s in sorted(speakers, key=lambda s: (-speakers[s]["n"], s)):
        info = speakers[s]
        pin = info.get("voice")
        h = zlib.crc32(s.encode())
        if isinstance(pin, dict) and pin.get("mix"):
            out[s] = _recipe(pin["mix"], pin.get("speed", 1.0), info["part"])
            used[pin["mix"][0][0]] += 1; continue
        pin = pin if isinstance(pin, str) else None
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


def cast_breeze(speakers):
    """Breeze: {speaker: dict(part, desc, seed, pinned, ref_text, ref_desc, note)}. speakers as for cast(). A pin is
      - a part ("elder"): cast within that part;
      - a description, a string of four words or more, or {"desc": ..., "seed": n}: that voice (with "seed", that very
        voice: its design take is the first seed that passes the gate, not the best of DESIGN_TAKES);
        {"ref_text": ..., "ref_desc": ...} also design the reference from that text and description (an auditioned
        take reproduced: the same text, description and seed give the same take); desc stays the voice every line
        is directed with;
      - a Kokoro voice or {"mix": ...}: Kokoro's; here the speaker is cast by its part (noted in the cast).
    Otherwise the part's description the map has used least, the speakers with the most lines choosing first, and a
    seed from the speaker's name and description: the same cast every build."""
    used, out = collections.Counter(), {}
    for s in sorted(speakers, key=lambda s: (-speakers[s]["n"], s)):
        info = speakers[s]
        pin = info.get("voice")
        h = zlib.crc32(s.encode())
        note = ""
        if isinstance(pin, str) and len(pin.split()) >= 4: pin = dict(desc=pin)
        if isinstance(pin, dict) and pin.get("desc"):
            desc = " ".join(pin["desc"].split())
            seed = int(pin["seed"]) if "seed" in pin else zlib.crc32((s + desc).encode()) % 100000
            out[s] = dict(part=info["part"], desc=desc, seed=seed, pinned="seed" in pin,
                          ref_text=pin.get("ref_text"), ref_desc=" ".join((pin.get("ref_desc") or desc).split()), note="pinned")
            used[desc] += 1
            continue
        if not isinstance(pin, str): pin = None if not pin else "mix"
        if pin and pin not in DESCRIPTIONS: note = f"Kokoro pin {pin} not used"
        part = pin if pin in DESCRIPTIONS else info["part"]
        opts = DESCRIPTIONS[part]
        rot = h % len(opts)
        desc = opts[min(range(len(opts)), key=lambda i: (used[opts[i]], (i - rot) % len(opts)))]
        used[desc] += 1
        out[s] = dict(part=part, desc=desc, seed=zlib.crc32((s + desc).encode()) % 100000, pinned=False,
                      ref_text=None, ref_desc=desc, note=note)
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


TAG_RE = re.compile(r"\((" + "|".join(re.escape(t) for t in TAGS) + r")\)", re.I)


def untagged(spoken_text):
    """The words of a line as spoken with its vocal events taken out."""
    return re.sub(r"\s{2,}", " ", TAG_RE.sub(" ", spoken_text)).strip()


def delivery_problem(text, spoken_text):
    """Why a line's delivery (its words with inline vocal events) does not fit its text, or None."""
    bad = [t for t in re.findall(r"\(([^)]*)\)", spoken_text) if t.lower() not in TAGS]
    if bad: return f"unknown vocal events {bad} (Breeze knows {', '.join(TAGS)})"
    if norm_words(untagged(spoken_text), keep_fillers=True) != norm_words(said(text), keep_fillers=True):
        return f"its words differ from the line's: {untagged(spoken_text)!r} vs {said(text)!r}"
    return None


def auto_tags(words):
    """The few vocal events a line's own words make clear: a lone "Ha!" is a laugh, "Hmph" a scoff."""
    for pat, tag in AUTO_TAGS: words = re.sub(pat, tag, words)
    return words


def map_names(strings, titles=()):
    """Proper names in a map's text: capitalised words not starting a sentence, and the words of the speakers' names and
    titles, that the text never writes in lower case ("Brannoc", "Varn"; not "Old" or "Guard"). Whisper may spell them
    any way, so the gate does not count them."""
    strings = list(strings)
    lower = {w for t in strings for w in re.findall(r"\b[a-z][a-z']*", t)}
    out = set()
    for t in strings + list(titles):
        for sent in re.split(r"(?<=[.!?])\s+|\n+", t):
            toks = re.findall(r"[A-Za-z][A-Za-z']*", re.sub(r"([a-z])([A-Z])", r"\1 \2", sent) if t in titles else sent)
            for k, w in enumerate(toks):
                if w[0].isupper() and (k > 0 or t in titles) and w.lower() not in lower and w not in ("I", "I'm", "I'll", "I've", "I'd"):
                    out.add(_simplify(w.lower().replace("'", "")))
    return out


# ---- the quality gate (pure Python; the worker measures, this judges) ------------------------------------------------
_ONES = "zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen " \
        "seventeen eighteen nineteen".split()
_TENS = "_ _ twenty thirty forty fifty sixty seventy eighty ninety".split()
FILLERS = {"ha", "hah", "haha", "hmm", "hm", "ah", "oh", "uh", "um", "and", "hmph", "huh"}


def _num(n):
    if n < 20: return [_ONES[n]]
    if n < 100: return [_TENS[n // 10]] + ([_ONES[n % 10]] if n % 10 else [])
    if n < 1000: return [_ONES[n // 100], "hundred"] + (_num(n % 100) if n % 100 else [])
    if n < 10000: return _num(n // 1000) + ["thousand"] + (_num(n % 1000) if n % 1000 else [])
    return list(str(n))


def _simplify(w):
    """British and American spellings alike: honour/honor, traveller/traveler."""
    w = re.sub(r"our$", "or", w)
    return re.sub(r"([a-z])\1", r"\1", w)


def norm_words(s, keep_fillers=False):
    """Words to compare: no vocal events or bracketed noises, lower case, no apostrophes, numbers in words, "a hundred"
    as "one hundred", fillers ("ha", "hmm", "and") left out."""
    s = re.sub(r"\([^)]*\)|\[[^\]]*\]|\*[^*]*\*", " ", s).lower().replace("\u2019", "'").replace("'", "")
    s = re.sub(r"(\d),(\d)", r"\1\2", s)
    toks = re.sub(r"[^a-z0-9]+", " ", s.replace("-", " ")).split()
    out = []
    for t in toks:
        out += _num(int(t)) if t.isdigit() else [t]
    out = ["one" if w == "a" and k + 1 < len(out) and out[k + 1] in ("hundred", "thousand") else w for k, w in enumerate(out)]
    return [_simplify(w) for w in out if keep_fillers or w not in FILLERS]


def word_errors(text, heard, names=()):
    """(errors, words): the edit distance between a line's words and what Whisper heard, a name in the line matching
    anything or nothing; words: the line's words that are not names."""
    ref, hyp = norm_words(text), norm_words(heard)
    nm = [w in names for w in ref]
    d = list(range(len(hyp) + 1))
    for i, a in enumerate(ref, 1):
        prev, d[0] = d[0], d[0] + (0 if nm[i - 1] else 1)
        for j, b in enumerate(hyp, 1):
            sub = 0 if (nm[i - 1] or a == b) else 1
            prev, d[j] = d[j], min(d[j] + (0 if nm[i - 1] else 1), d[j - 1] + 1, prev + sub)
    return d[len(hyp)], sum(1 for x in nm if not x)


def gate_verdict(m, band, ref_f0=None):
    """(problems, score) of a take's measures m = dict(errors, words, heard, f0, speech_s, nwords): the transcript within
    max(1, 15%) word errors, the median pitch inside the part's band (and within REF_DRIFT semitones of the speaker's
    reference), 1.5-4.8 words a second while speaking (a line of 4 words or more). Lower score is better."""
    import math
    problems, score = [], 0.0
    allowed = max(1, int(0.15 * m["words"]))
    wer = m["errors"] / max(1, m["words"])
    score += 10 * wer
    if m["errors"] > allowed: problems.append(f"{m['errors']} word errors in {m['words']} (heard {m['heard']!r})")
    f0 = m.get("f0") or 0.0
    lo, hi = band
    off = 0.0 if lo <= f0 <= hi else abs(12 * math.log2(max(f0, 1.0) / (lo if f0 < lo else hi)))
    score += 0.5 * off
    if off: problems.append(f"pitch {f0:.0f} Hz outside the part's {lo}-{hi} Hz")
    if ref_f0 and f0:
        drift = abs(12 * math.log2(f0 / ref_f0))
        score += 0.2 * drift
        if drift > REF_DRIFT: problems.append(f"pitch {f0:.0f} Hz, {drift:.1f} semitones from the reference's {ref_f0:.0f}")
    wps = m["nwords"] / max(0.1, m["speech_s"])
    if m["nwords"] >= 4 and not 1.5 <= wps <= 4.8:
        problems.append(f"{wps:.1f} words a second"); score += 2
    return problems, round(score, 3)


# ---- the plan --------------------------------------------------------------------------------------------------------
def _ref_text(lines):
    """A speaker's reference text from its lines (spoken forms, in order): the one nearest REF_WORDS words, or, when
    all are short, the longest few run together."""
    n = lambda t: len(untagged(t).split())
    best = min(lines, key=lambda t: (abs(n(t) - REF_WORDS), lines.index(t)))
    if n(best) >= 12: return best
    out = []
    for t in sorted(lines, key=lambda t: (-n(t), lines.index(t))):
        out.append(t)
        if sum(map(n, out)) >= 12: break
    return " ".join(out)


def line_hash(spec, ref_sha):
    """A Breeze line's cache key: its spec (text with tags, description, mood, model, gate, mastering, the reference's
    key) and the reference wave's own hash."""
    return hashlib.sha1((spec + "|" + ref_sha).encode("utf-8")).hexdigest()


def plan(out_dir, name, objects=None, engine=None):
    """The manifest for a built map's lines, without sound: each spoken key's wave name, speaker, voice and words."""
    engine = engine_name(engine)
    strings, lines, pics, pins, who, deliv = spoken(out_dir, name, objects)
    texts = "\n".join(strings.values())
    pins = dict(pins)
    for k in [k for k in pins if k in lines]:         # a pin by line key: the speaker of that line (a shopkeeper)
        pins.setdefault(lines[k], pins.pop(k))
    counts = collections.Counter(lines.values())
    speakers = {}
    title = lambda s: strings.get(f"NPC:{s}") or ("Shopkeeper" if (who.get(s) or {}).get("shop") else s)
    for s, n in counts.items():
        speakers[s] = dict(part=archetype(s, who.get(s), pics.get(s), title(s), texts), n=n, voice=pins.get(s))
    voices = cast(speakers) if engine == "kokoro" else cast_breeze(speakers)
    code = wave_code(name)
    assert len(lines) <= 999, f"{name}: {len(lines)} spoken lines; wave names hold 999"
    eid = _engine(engine)
    man = dict(map=name, code=code, rate=RATE, engine=eid, engine_name=engine, speakers={}, lines={})
    for s, v in sorted(voices.items()):
        p = who.get(s) or {}
        man["speakers"][s] = dict(v, title=title(s), pic=pics.get(s, ""), body=p.get("type") or p.get("donor") or "",
                                  lines=counts[s])
    if engine == "kokoro":
        for n, (key, s) in enumerate(lines.items(), 1):
            v = voices[s]
            words = said(strings[key])
            h = hashlib.sha1(json.dumps([eid, RATE, MASTER, words, v["mix"], v["speed"], v["lang"]]).encode()).hexdigest()
            man["lines"][key] = dict(wave=f"{code}{n:03d}e", speaker=s, said=words, text_sha=text_sha(strings[key]), hash=h)
        return man
    man["names"] = sorted(map_names(strings.values(), [title(s) for s in counts] + list(counts)))
    for n, (key, s) in enumerate(lines.items(), 1):
        words = said(strings[key])
        d = deliv.get(key) or {}
        sp_text = said(d["spoken"]) if d.get("spoken") else auto_tags(words)
        if d.get("spoken") and delivery_problem(strings[key], d["spoken"]): sp_text = auto_tags(words)
        man["lines"][key] = dict(wave=f"{code}{n:03d}e", speaker=s, said=words, spoken=sp_text,
                                 mood=" ".join((d.get("mood") or "").split()), text_sha=text_sha(strings[key]), hash=None)
    for s, sp in man["speakers"].items():
        mine = [l["spoken"] for l in man["lines"].values() if l["speaker"] == s]
        sp["ref_text"] = said(sp["ref_text"]) if sp.get("ref_text") else _ref_text(mine)
        sp["band"] = list(BANDS[sp["part"]])
        sp["ref"] = hashlib.sha1(json.dumps([eid, "ref", sp["ref_desc"], sp["ref_text"], sp["seed"], sp["pinned"],
                                             sp["band"], DESIGN_TAKES, GATE]).encode()).hexdigest()
    for l in man["lines"].values():
        sp = man["speakers"][l["speaker"]]
        l["spec"] = json.dumps([eid, RATE, MASTER_B, GATE, l["spoken"], sp["desc"], l["mood"], sp["ref"]])
    return man


# ---- the TTS: paths, readiness, cache --------------------------------------------------------------------------------
def venv_python(engine="kokoro"):
    v = os.path.join(HOME, "venv") if engine == "kokoro" else os.path.join(HOME, "breeze", "venv")
    return os.path.join(v, "Scripts", "python.exe") if os.name == "nt" else os.path.join(v, "bin", "python")


def model_path(fn):
    return os.path.join(HOME, "models", fn)


def breeze_src():
    return os.path.join(HOME, "breeze", "src")


def breeze_model(name):
    return os.path.join(HOME, "breeze", "models", name)


def _engine(engine="kokoro"):
    """What made a wave, for its cache key: the model as the lock pins it."""
    if engine == "kokoro":
        files = _lock("kokoro").get("files", {})
        return "kokoro-onnx " + ",".join(f"{fn}:{files.get(fn, {}).get('sha256', '?')[:12]}" for fn in MODEL_FILES)
    lk = _lock("breeze")
    commit = (lk.get("src") or {}).get("commit", BREEZE_COMMIT)
    ms = {k: ((lk.get("models") or {}).get(k) or {}).get("revision", v[1]) for k, v in BREEZE_MODELS.items()}
    return f"breeze-tts {commit[:12]} {BREEZE_MODELS['tts'][0]}@{ms['tts'][:12]} whisper@{ms['asr'][:12]} cfg{CFG:g}"


def tts_ready(engine=None):
    """None when the engine's TTS is installed here, else what is missing."""
    engine = engine_name(engine)
    if not os.path.exists(venv_python(engine)): return f"no {engine} TTS venv ({venv_python(engine)})"
    if engine == "kokoro":
        miss = [fn for fn in MODEL_FILES if not os.path.exists(model_path(fn))]
        return f"no model file {', '.join(miss)} in {os.path.dirname(model_path(''))}" if miss else None
    if not os.path.exists(os.path.join(breeze_src(), "breeze_infer", "templates.py")): return f"no Breeze source in {breeze_src()}"
    for name, m in (_lock("breeze").get("models") or {}).items():
        miss = [p for p in m.get("files", {}) if not os.path.exists(os.path.join(breeze_model(name), *p.split("/")))]
        if miss: return f"no {name} model file {miss[0]} in {breeze_model(name)}"
    return None if _lock("breeze").get("models") else "no Breeze models in the lock"


def _cache(h):
    return os.path.join(HOME, "cache", h[:2], h + ".wav")


def ref_paths(ref_key):
    """A speaker's reference: its design take (24 kHz float, as Breeze made it) and what the gate measured of it."""
    d = os.path.join(HOME, "refs", ref_key[:2])
    return os.path.join(d, ref_key + ".wav"), os.path.join(d, ref_key + ".json")


def file_sha(p):
    return _sha256(p)[:16]


def cache_meta(h):
    return _load(os.path.join(HOME, "cache", h[:2], h + ".json"))


def store_line(h, pcm, meta):
    """Writes a Breeze line into the cache: the wave (a take that failed the gate goes to <hash>.fail.wav, to listen
    to, never to the game) and its gate record."""
    os.makedirs(os.path.join(HOME, "cache", h[:2]), exist_ok=True)
    p = _cache(h) if meta.get("pass") else _cache(h)[:-4] + ".fail.wav"
    write_wav(p + ".part", pcm, RATE)
    os.replace(p + ".part", p)
    _dump(os.path.join(HOME, "cache", h[:2], h + ".json"), meta)


def synthesize(jobs, timeout=7200):
    """Kokoro: makes each job's wave ([(said, recipe, out path)]) in the venv's Python (kokoro-onnx, numpy)."""
    os.makedirs(os.path.join(HOME, "tmp"), exist_ok=True)
    spec = dict(model=model_path(MODEL_FILES[0]), voices=model_path(MODEL_FILES[1]), rate=RATE,
                jobs=[dict(text=t, mix=v["mix"], speed=v["speed"], lang=v["lang"], out=p) for t, v, p in jobs])
    fd, jp = tempfile.mkstemp(suffix=".json", dir=os.path.join(HOME, "tmp"))
    with os.fdopen(fd, "w", encoding="utf-8") as f: json.dump(spec, f, ensure_ascii=False)
    try:
        r = subprocess.run([venv_python("kokoro"), os.path.abspath(__file__), "synth", jp], capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    finally:
        os.remove(jp)
    if r.returncode: raise RuntimeError("the TTS failed:\n" + (r.stdout + r.stderr)[-3000:])
    return r.stdout


def _worker(jobs_path):
    """Run by the Kokoro venv's Python: Kokoro makes each job's line, mastered and written as PCM 16-bit mono."""
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


def _trim(x, rate, floor_db=-40.0):
    """A take without the silence (or breath noise) before its first word and after its last: frames of 20 ms under
    floor_db of the loudest frame, one frame kept either side."""
    import numpy as np
    f = max(1, rate // 50)
    if len(x) < 2 * f: return x
    fr = np.sqrt((x[:len(x) // f * f].reshape(-1, f) ** 2).mean(axis=1))
    on = np.where(fr > fr.max() * 10 ** (floor_db / 20))[0]
    if not len(on): return x
    return x[max(0, (on[0] - 1) * f):min(len(x), (on[-1] + 2) * f)]


def _master(x, sr, rate, trim=False):
    """Westwood's dialogue loudness (rules measured on its PCM waves: speaking at -16 dBFS, peaks at 0): resampled to
    `rate` (FFT, the top 8% of the band rolled off), raised to LOUD while speaking, peaks bent under CEIL from KNEE,
    5 ms fades, LEAD and TAIL of silence. trim: the take's own silence at either end cut first (Breeze's takes have
    some; Kokoro's none). Returns int16 samples."""
    import numpy as np
    x = np.asarray(x, dtype=np.float64).reshape(-1)
    if trim: x = _trim(x - x.mean(), sr)
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
    if not isinstance(frames, (bytes, bytearray)): frames = frames.tobytes()
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


# ---- the GPU: only while pc1 is not gaming ----------------------------------------------------------------------------
_PS_GPU = r"""
$u = @{}
try { $s = (Get-Counter "\GPU Engine(*)\Utilization Percentage" -SampleInterval 1 -MaxSamples 2 -ErrorAction Stop).CounterSamples }
catch { $s = @() }
foreach ($c in $s) { if ($c.InstanceName -match "^pid_(\d+)_.*engtype_(3d|compute|cuda)") { $u[$matches[1]] = [double]$u[$matches[1]] + $c.CookedValue / 2 } }
$p = @(Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,Name,ExecutablePath | ForEach-Object {
  @{ pid = [int]$_.ProcessId; ppid = [int]$_.ParentProcessId; name = [string]$_.Name; path = [string]$_.ExecutablePath } })
@{ util = $u; procs = $p } | ConvertTo-Json -Compress -Depth 3
"""


def _guard_game():
    """The game the pc1 AI guard sees running (its log's latest "game=" line, if under 15 minutes old), or None."""
    p = os.environ.get("NOX_GPU_GUARD_LOG") or os.path.join(os.environ.get("LOCALAPPDATA", ""), "dystopianentity", "guard.log")
    if not os.path.isfile(p): return None
    try:
        with open(p, "rb") as f:
            f.seek(max(0, os.path.getsize(p) - 65536)); tail = f.read().decode("utf-8", "replace")
    except OSError:
        return None
    line = next((l for l in reversed(tail.splitlines()) if " game=" in l), None)
    if not line: return None
    try:
        at = time.mktime(time.strptime(line[:19], "%Y-%m-%d %H:%M:%S"))
    except ValueError:
        return None
    game = re.search(r" game=(\S*)", line).group(1)
    return game if game and time.time() - at < 15 * 60 else None


def _win_gpu():
    """{pid: GPU %} and [{pid, ppid, name, path}] of Windows' processes, or None (not Windows, PowerShell failed)."""
    if os.name != "nt": return None
    try:
        r = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-EncodedCommand",
                            base64.b64encode(_PS_GPU.encode("utf-16-le")).decode()],
                           capture_output=True, text=True, timeout=90, encoding="utf-8", errors="replace")
        js = json.loads(r.stdout.strip().splitlines()[-1])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None
    return {int(k): float(v) for k, v in (js.get("util") or {}).items()}, js.get("procs") or []


def user_idle_s():
    """Seconds since the user last touched pc1's keyboard or mouse (Windows), or None where it cannot be known."""
    if os.name != "nt": return None
    import ctypes

    class LII(ctypes.Structure):
        _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]
    li = LII(); li.cbSize = ctypes.sizeof(LII)
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(li)): return None
    return ((ctypes.windll.kernel32.GetTickCount() - li.dwTime) & 0xFFFFFFFF) / 1000.0


def vram_free_mib():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=memory.free", "--format=csv,noheader,nounits"],
                           capture_output=True, text=True, timeout=30)
        return int(r.stdout.split()[0])
    except (OSError, subprocess.SubprocessError, ValueError, IndexError):
        return None


def gpu_busy(roots=(), need_mib=None, others=None):
    """Why the GPU is not ours to use now, or None: the user at pc1 (keyboard or mouse used in the last NOX_VOICE_IDLE
    seconds, 300 by default: Breeze at full tilt makes the desktop unusable), a game running (the pc1 AI guard's log;
    Nox itself), other programs using it (GPU_BUSY_PCT of its 3D and compute engines, ours and the desktop's left out: roots are our workers' pids)
    or too little of its memory free (need_mib). others=False (NOX_VOICE_GPU=games): games and memory only, the GPU
    shared with other programs' work."""
    if others is None: others = os.environ.get("NOX_VOICE_GPU", "wait").lower() != "games"
    idle, need_idle = user_idle_s(), float(os.environ.get("NOX_VOICE_IDLE", IDLE_S))
    if idle is not None and idle < need_idle:
        return f"pc1 is in use (last input {idle:.0f} s ago; voicing runs once it has been idle {need_idle / 60:.0f} min)"
    g = _guard_game()
    if g: return f"a game is running ({g}, says the pc1 AI guard)"
    st = _win_gpu()
    if st:
        util, procs = st
        kids = collections.defaultdict(list)
        for p in procs: kids[p["ppid"]].append(p["pid"])
        mine, todo = set(), [os.getpid(), *roots]
        while todo:
            q = todo.pop()
            if q not in mine: mine.add(q); todo += kids.get(q, [])
        byid = {p["pid"]: p for p in procs}
        for p in procs:
            if p["name"].lower() in GAME_PROCS or (p.get("path") or "").lower().startswith(NOX.lower() + "\\"):
                return f"Nox is running ({p['name']})"
        load = {q: u for q, u in util.items() if q not in mine and (byid.get(q) or {}).get("name", "").lower() != "dwm.exe"}
        tot = sum(load.values())
        if others and tot >= GPU_BUSY_PCT:
            top = sorted(load.items(), key=lambda kv: -kv[1])[:3]
            return f"other programs use the GPU ({tot:.0f}%: " + ", ".join(
                f"{(byid.get(q) or {}).get('name', q)} {u:.0f}%" for q, u in top) + ")"
    if need_mib:
        free = vram_free_mib()
        if free is not None and free < need_mib:
            return f"only {free / 1024:.1f} GiB of the GPU's memory is free ({need_mib / 1024:.0f} GiB needed)"
    return None


def wait_gpu():
    """None once the GPU is free to use; else why voicing is skipped (NOX_VOICE_GPU=skip, or NOX_VOICE_WAIT minutes
    passed, 120 by default). NOX_VOICE_GPU=games waits for games and memory only; force does not look."""
    policy = os.environ.get("NOX_VOICE_GPU", "wait").lower()
    if policy == "force": return None
    t0, said_, limit = time.time(), None, float(os.environ.get("NOX_VOICE_WAIT", "120")) * 60
    while True:
        why = gpu_busy(need_mib=VRAM_MIB)
        if not why: return None
        if policy == "skip": return f"the GPU is busy ({why}): not voiced now (NOX_VOICE_GPU=skip), cached waves kept"
        if time.time() - t0 > limit:
            return f"the GPU stayed busy for {limit / 60:.0f} min ({why}): not voiced now, cached waves kept"
        if why != said_:
            print(f"VOICE: waiting for the GPU: {why}. Checking every 30 s (NOX_VOICE_GPU=skip voices nothing new and "
                  f"keeps the cached waves).", flush=True)
            said_ = why
        time.sleep(30)


# ---- Breeze: running the worker --------------------------------------------------------------------------------------
def _kill_tree(p):
    if p.poll() is not None: return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(p.pid), "/T", "/F"], capture_output=True)
    else:
        p.kill()
    try:
        p.wait(timeout=30)
    except subprocess.TimeoutExpired:
        pass


def _breeze_work(man, keys, retry, extra=()):
    """The worker's speakers for the lines `keys` (and `extra` speakers with no lines: a `say`)."""
    by = collections.defaultdict(list)
    for k in keys: by[man["lines"][k]["speaker"]].append(k)
    out = []
    for s in list(by) + [s for s in extra if s not in by]:
        sp = man["speakers"][s]
        out.append(dict(speaker=s, part=sp["part"], band=sp["band"], desc=sp["desc"], seed=sp["seed"],
                        pinned=sp["pinned"], ref=sp["ref"], ref_text=sp["ref_text"], ref_desc=sp["ref_desc"],
                        say_out=sp.get("say_out"),
                        lines=[dict(key=k, said=man["lines"][k]["said"], spoken=man["lines"][k]["spoken"],
                                    mood=man["lines"][k]["mood"], spec=man["lines"][k]["spec"]) for k in by.get(s, [])]))
    return out


def run_breeze(man, remaining, retry=False, extra=()):
    """Renders the Breeze lines `remaining()` names (keys still to make; called again after a pause) in worker processes
    on the GPU at below-normal priority: one by default (NOX_VOICE_WORKERS=2 for two when its memory holds them: about
    1.6 times the throughput, and the GPU at 100%), each a share of the speakers. Polls every 30 s while they run: the
    user coming back to pc1, a game or other GPU work stops them (the model unloads with
    the process; every line made is in the cache) and the run waits, then goes on. Returns None, or why not all
    were made."""
    while True:
        keys = remaining()
        say = [s for s in extra if not os.path.exists(man["speakers"][s]["say_out"])]
        if not keys and not say: return None
        why = wait_gpu()
        if why: return why
        work = _breeze_work(man, keys, retry, say)
        free = vram_free_mib() or VRAM_MIB
        n = max(1, min(int(os.environ.get("NOX_VOICE_WORKERS", "1")), free // VRAM_MIB, len(work)))
        shares = [[] for _ in range(n)]
        for w in sorted(work, key=lambda w: -sum(len(l["said"].split()) for l in w["lines"]) - len(w["ref_text"].split())):
            min(shares, key=lambda sh: sum(len(l["said"].split()) for x in sh for l in x["lines"]) + 25 * len(sh)).append(w)
        os.makedirs(os.path.join(HOME, "tmp"), exist_ok=True)
        procs, tails, specs = [], [], []
        env = dict(os.environ, HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", PYTHONIOENCODING="utf-8",
                   PYTHONUNBUFFERED="1", TOKENIZERS_PARALLELISM="false", HF_HUB_DISABLE_TELEMETRY="1")
        print(f"VOICE: Breeze TTS 2 on the GPU: {sum(len(w['lines']) for w in work)} lines of {len(work)} speakers, "
              f"{n} worker{'s' if n > 1 else ''}", flush=True)
        for k, share in enumerate(shares):
            fd, jp = tempfile.mkstemp(suffix=".json", dir=os.path.join(HOME, "tmp"))
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(dict(src=breeze_src(), tts=breeze_model("tts"), asr=breeze_model("asr"), cfg=CFG, retry=retry,
                               names=man.get("names", []), worker=k + 1, speakers=share), f, ensure_ascii=False)
            specs.append(jp)
            p = subprocess.Popen([venv_python("breeze"), os.path.join(HERE, "voice_breeze.py"), jp], stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace", env=env,
                                 creationflags=0x4000 if os.name == "nt" else 0)      # BELOW_NORMAL_PRIORITY_CLASS
            tail = collections.deque(maxlen=40)

            def relay(p=p, tail=tail, k=k):
                for ln in p.stdout:
                    if ln.startswith("VOICE|"): print(f"  [{k + 1}] {ln[6:].rstrip()}", flush=True)
                    else: tail.append(ln.rstrip())
            threading.Thread(target=relay, daemon=True).start()
            procs.append(p); tails.append(tail)
        paused, last = None, time.time()
        while any(p.poll() is None for p in procs):
            time.sleep(1)
            if os.environ.get("NOX_VOICE_GPU", "wait").lower() != "force" and time.time() - last >= 30:
                last = time.time()
                paused = gpu_busy(roots=[p.pid for p in procs])
                if paused: break
        if paused:
            for p in procs: _kill_tree(p)
            print(f"VOICE: stopped for the GPU: {paused}; the model is unloaded, the lines made so far are cached", flush=True)
        for jp in specs:
            try: os.remove(jp)
            except OSError: pass
        if paused: continue
        time.sleep(0.5)
        bad = [(k, p.returncode, t) for k, (p, t) in enumerate(zip(procs, tails), 1) if p.returncode]
        if bad:
            k, rc, t = bad[0]
            return f"the Breeze worker {k} failed (exit {rc}): " + " | ".join(list(t)[-3:])[-600:]
        return None                     # each line's own record says whether it passed the gate


# ---- the build step --------------------------------------------------------------------------------------------------
def _voice_breeze(man, wd, make, only, retry):
    """Fills <wd> with the Breeze lines the cache has; renders the rest first (make). Returns (made, cached, why)."""
    def resolve():
        for sp in man["speakers"].values():
            wp, jp = ref_paths(sp["ref"])
            sp["ref_sha"] = file_sha(wp) if os.path.exists(wp) else None
            sp["ref_meta"] = _load(jp)
        todo = []
        for k, l in man["lines"].items():
            sp = man["speakers"][l["speaker"]]
            l["hash"] = line_hash(l["spec"], sp["ref_sha"]) if sp["ref_sha"] else None
            meta = cache_meta(l["hash"]) if l["hash"] else None
            if meta and meta.get("pass") and os.path.exists(_cache(l["hash"])): continue
            if not retry and ((meta and not meta.get("pass")) or (sp["ref_meta"] or {}).get("fail")): continue
            if only and k not in only and l["speaker"] not in only: continue
            todo.append(k)
        return todo
    todo = resolve()
    why = None
    if todo and make:
        why = tts_ready("breeze") or run_breeze(man, resolve, retry)
        resolve()
    made = cached = 0
    for k, l in man["lines"].items():
        dst = os.path.join(wd, l["wave"] + ".wav")
        sp = man["speakers"][l["speaker"]]
        meta = cache_meta(l["hash"]) if l["hash"] else None
        l.pop("why", None)
        if meta and meta.get("pass") and os.path.exists(_cache(l["hash"])):
            shutil.copyfile(_cache(l["hash"]), dst)
            made, cached = made + (k in todo), cached + (k not in todo)
            l["gate"] = {x: meta.get(x) for x in ("seed", "tries", "wer", "f0", "wps", "heard", "render_s", "reused")}
            continue
        if os.path.exists(dst): os.remove(dst)          # made from other words or another voice: never left to speak
        if meta: l["why"] = "failed the quality gate after %d takes: %s" % (meta.get("tries", 0), "; ".join(meta.get("problems", [])))
        elif (sp.get("ref_meta") or {}).get("fail"): l["why"] = "no design take of its voice passed the gate: " + sp["ref_meta"]["fail"]
        else: l["why"] = why or "not rendered" + (" (not in --only)" if only else "")
    for sp in man["speakers"].values():
        sp.pop("ref_meta", None)
    return made, cached, why if made < len(todo) else None


def voice(out_dir, name, objects=None, to=None, make=True, only=None, retry=False, engine=None):
    """Voices a built map's spoken lines: the manifest, then every wave not yet made (from the cache, else the TTS), into
    <to or out_dir>/<Name>_dialog/. only: render just these keys or speakers (the rest from the cache, if there).
    retry: try again the lines that failed the gate before. Returns (manifest, made now, from the cache, missing reason
    or None)."""
    to = to or out_dir
    man = plan(out_dir, name, objects, engine)
    wd = os.path.join(to, f"{name}_dialog")
    os.makedirs(wd, exist_ok=True)
    if man["engine_name"] == "breeze":
        made, cached, why = _voice_breeze(man, wd, make, set(only or ()), retry)
    else:
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
        why = tts_ready("kokoro") if jobs and make else None
        if jobs and make and not why:
            try:
                for k0 in range(0, len(jobs), 40):      # a batch at a time: a failure keeps the batches made before it
                    synthesize([(l["said"], man["speakers"][l["speaker"]], c) for _, l, c, _ in jobs[k0:k0 + 40]])
            except (RuntimeError, OSError, subprocess.TimeoutExpired) as e:
                why = "the TTS failed: " + (str(e).strip().splitlines() or ["?"])[-1][:300]
        made = 0
        for _, l, c, dst in jobs:
            if os.path.exists(c): shutil.copyfile(c, dst); made += 1
        why = why if made < len(jobs) else None
    keep = {l["wave"] + ".wav" for l in man["lines"].values()}
    for fn in os.listdir(wd):                       # waves of lines the map no longer has
        if fn not in keep: os.remove(os.path.join(wd, fn))
    for l in man["lines"].values():
        p = os.path.join(wd, l["wave"] + ".wav")
        info = wave_info(p) if os.path.exists(p) else None
        l["voiced"] = bool(info and not wave_problem(info, len(l["said"].split())))
        l["seconds"] = round(info["seconds"], 2) if info and "seconds" in info else 0.0
    _dump(os.path.join(to, f"{name}.voice.json"), man)
    return man, made, cached, why


def build_step(objects, out_dir, name):
    """Spec.build's voice step: report lines ("VOICE ..."). Nothing to do for a map without spoken lines."""
    if not os.path.exists(os.path.join(out_dir, f"{name}.strings.json")): return []
    t0 = time.time()
    man, made, cached, why = voice(out_dir, name, objects)
    n = len(man["lines"])
    if not n: return [f"VOICE {name}: no spoken lines"]
    ok = sum(l["voiced"] for l in man["lines"].values())
    line = (f"VOICE {name}: {ok} of {n} lines voiced by {man['engine_name']}, {len(man['speakers'])} speakers ({made} "
            f"made now, {cached} from the cache, {time.time() - t0:.0f} s)")
    gated = [k for k, l in man["lines"].items() if not l["voiced"] and "gate" in (l.get("why") or "")]
    if gated: line += f"; {len(gated)} failed the quality gate ({', '.join(gated[:4])})"
    if why: line += f"; not voiced: {why}" + (" (py mapgen/voice.py fetch)" if tts_ready(man["engine_name"]) else "")
    return [line]


def check(out_dir, name, to=None):
    """[(ok, text)] for the QA gate: every spoken line has a good wave made from its present text, by a cast voice,
    and (Breeze) passed the quality gate. to: where the waves and manifest were written, if not beside the map."""
    out = []
    to = to or out_dir
    man = _load(os.path.join(to, f"{name}.voice.json"))
    strings, lines, _, _, _, _ = spoken(out_dir, name)
    if not lines: return [(True, "no spoken lines")]
    if not man: return [(False, f"{len(lines)} spoken lines and no {name}.voice.json: the build's voice step did not run "
                                f"(NOX_NOVOICE?) or failed: py mapgen/voice.py voice {os.path.relpath(out_dir, REPO)} {name}")]
    eng = man.get("engine_name") or "kokoro"
    wd = os.path.join(to, f"{name}_dialog")
    missing = [k for k in lines if k not in man["lines"]]
    out.append((not missing, f"{len(lines)} spoken lines, each with a wave" if not missing else
                f"lines without a wave: {', '.join(missing[:6])}"))
    stale = [k for k, l in man["lines"].items() if k in strings and l["text_sha"] != text_sha(strings[k])]
    out.append((not stale, "every wave was made from its line's present text" if not stale else
                f"waves made from older text: {', '.join(stale[:6])}"))
    bad, gated = [], []
    for k, l in man["lines"].items():
        p = os.path.join(wd, l["wave"] + ".wav")
        why = wave_problem(wave_info(p), len(l["said"].split())) if os.path.exists(p) else (l.get("why") or "no wave file")
        if why: (gated if "quality gate" in why or "design take" in why else bad).append(f"{k} ({l['wave']}, {l['speaker']}): {why}")
    secs = sum(l.get("seconds", 0) for l in man["lines"].values())
    out.append((not bad, f"{len(man['lines'])} waves PCM 16-bit mono {RATE} Hz, {secs / 60:.1f} min of speech" if not bad
                else f"{len(bad)} lines not voiced" + (f" ({tts_ready(eng)}: py mapgen/voice.py fetch)" if tts_ready(eng) else "")
                + ": " + "; ".join(bad[:5])))
    if eng == "breeze":
        out.append((not gated, "every line passed the quality gate (Whisper transcript, pitch band, pace)" if not gated else
                    f"{len(gated)} lines failed the quality gate (listen to <cache>/<hash>.fail.wav; change the line, its "
                    f"delivery or the voice, or try again: py mapgen/voice.py voice ... --retry): " + "; ".join(gated[:4])))
    names = [l["wave"] for l in man["lines"].values()]
    dup = [w for w, c in collections.Counter(names).items() if c > 1]
    out.append((not dup and all(len(w) <= 8 for w in names), "wave names are 8 characters and unique (Westwood's 8.3)"
                if not dup else f"wave names used twice: {', '.join(dup[:5])}"))
    parts = collections.Counter(v["part"] for v in man["speakers"].values())
    voices = collections.Counter((v.get("desc") or v["mix"][0][0]) if eng == "breeze" or "mix" in v else "?"
                                 for v in man["speakers"].values())
    out.append((True, f"{len(man['speakers'])} speakers ({eng}): " + ", ".join(f"{p} {n}" for p, n in parts.most_common()) +
                f"; {len(voices)} distinct voices"))
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
    os.makedirs(os.path.dirname(part), exist_ok=True)
    with urllib.request.urlopen(url, timeout=60) as r, open(part, "wb") as f:
        shutil.copyfileobj(r, f, 1 << 20)
    return part


def _pip_norm(xs):
    return {re.sub(r"[-_.]+", "-", x.lower()) for x in xs}      # pip writes kokoro_onnx or kokoro-onnx


def _freeze(py):
    return sorted(subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True, check=True).stdout.split(),
                  key=str.lower)


def fetch_kokoro():
    """Installs Kokoro into HOME: a venv with kokoro-onnx (the lock's packages when it has them, else KOKORO_ONNX and
    what pip resolves for it, then written to the lock) and its model files (checked against the lock's SHA-256)."""
    all_ = _lock_all()
    lock = all_.get("kokoro", {})
    changed = False
    os.makedirs(HOME, exist_ok=True)
    py = venv_python("kokoro")
    if not os.path.exists(py):
        print(f"making the venv {os.path.dirname(os.path.dirname(py))}")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(HOME, "venv")], check=True)
    want = lock.get("pip") or [f"kokoro-onnx=={KOKORO_ONNX}"]
    have = subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    if not _pip_norm(want) <= _pip_norm(have):
        print("installing " + (f"the lock's {len(want)} packages" if lock.get("pip") else want[0]))
        subprocess.run([py, "-m", "pip", "install", "--disable-pip-version-check"] + (["--no-deps"] if lock.get("pip") else [])
                       + want, check=True)
    if not lock.get("pip"):
        lock["pip"] = _freeze(py)
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
        lock.update(kokoro_onnx=KOKORO_ONNX, model=MODEL_URL, note="written by py mapgen/voice.py fetch --engine kokoro")
        all_["kokoro"] = lock
        _dump(LOCK, all_)
        print(f"wrote {LOCK}: commit it, so every PC installs the same TTS")
    p = os.path.join(HOME, "tmp", "fetch_check.wav")
    synthesize([("Well met, stranger. The road north is closed.", cast({"Check": dict(part="man", n=1)})["Check"], p)])
    why = wave_problem(wave_info(p), 8)
    print(f"the TTS works: {p} ({wave_info(p)['seconds']:.1f} s)" if not why else f"the TTS made a bad wave: {why}")
    return 0 if not why else 1


def _hub_dirs(model_from=()):
    """Hugging Face hub caches that may already hold a model: --model-from, NOX_VOICE_MODEL_FROM, HF_HUB_CACHE,
    HF_HOME/hub, ~/.cache/huggingface/hub (a directory given may be an HF_HOME or its hub)."""
    cands = list(model_from) + [d for d in os.environ.get("NOX_VOICE_MODEL_FROM", "").split(os.pathsep) if d]
    cands += [os.environ.get("HF_HUB_CACHE", ""), os.path.join(os.environ.get("HF_HOME", ""), "hub") if os.environ.get("HF_HOME") else "",
              os.path.join(os.path.expanduser("~"), ".cache", "huggingface", "hub")]
    out = []
    for d in cands:
        if d and os.path.isdir(os.path.join(d, "hub")): d = os.path.join(d, "hub")
        if d and os.path.isdir(d) and d not in out: out.append(d)
    return out


def _hf_tree(repo, rev):
    import urllib.request
    with urllib.request.urlopen(f"https://huggingface.co/api/models/{repo}/tree/{rev}?recursive=true", timeout=60) as r:
        return {e["path"]: e["size"] for e in json.load(r) if e.get("type") == "file"}


def fetch_breeze(model_from=()):
    """Installs Breeze TTS 2 into HOME/breeze: its source at BREEZE_COMMIT (git), a venv with the lock's packages (else
    TORCH_PIP from TORCH_INDEX and BREEZE_PIP, then written to the lock), the Breeze and Whisper model files at their
    pinned revisions, each checked against the lock's SHA-256 (hard-linked from a Hugging Face cache that has them,
    else downloaded). Safe to repeat: what is in place and matches is kept (a size-and-time stamp spares re-hashing)."""
    all_ = _lock_all()
    lock = json.loads(json.dumps(all_.get("breeze", {})))
    before = json.dumps(lock, sort_keys=True)
    bh = os.path.join(HOME, "breeze")
    os.makedirs(bh, exist_ok=True)
    src = lock.setdefault("src", dict(url=BREEZE_GIT, commit=BREEZE_COMMIT))
    git = lambda *a: subprocess.run(["git", "-C", breeze_src(), *a], capture_output=True, text=True)
    if not os.path.isdir(os.path.join(breeze_src(), ".git")):
        print(f"cloning {src['url']}")
        subprocess.run(["git", "clone", "--quiet", "--no-checkout", src["url"], breeze_src()], check=True)
    if (git("rev-parse", "HEAD").stdout.strip() != src["commit"]
            or not os.path.exists(os.path.join(breeze_src(), "breeze_infer", "templates.py"))):
        if git("cat-file", "-e", src["commit"] + "^{commit}").returncode: git("fetch", "--quiet", "origin", src["commit"])
        r = git("-c", "advice.detachedHead=false", "checkout", "--quiet", "--force", src["commit"])
        if r.returncode: sys.exit(f"breeze-tts: cannot check out {src['commit']}: {r.stderr.strip()}")
    head = git("rev-parse", "HEAD").stdout.strip()
    if head != src["commit"]: sys.exit(f"breeze-tts: HEAD {head} is not the lock's {src['commit']}")
    print(f"breeze-tts source at {head[:12]}")
    py = venv_python("breeze")
    if not os.path.exists(py):
        print(f"making the venv {os.path.dirname(os.path.dirname(py))}")
        subprocess.run([sys.executable, "-m", "venv", os.path.join(bh, "venv")], check=True)
    pyv = subprocess.run([py, "-c", "import sys; print(sys.version.split()[0])"], capture_output=True, text=True).stdout.strip()
    if lock.get("python") and lock["python"].split(".")[:2] != pyv.split(".")[:2]:
        sys.exit(f"the Breeze venv runs Python {pyv}; the lock's packages are for {lock['python']}")
    pip = [py, "-m", "pip", "install", "--disable-pip-version-check"]
    have = subprocess.run([py, "-m", "pip", "freeze"], capture_output=True, text=True).stdout.split()
    if lock.get("pip"):
        if not _pip_norm(lock["pip"]) <= _pip_norm(have):
            print(f"installing the lock's {len(lock['pip'])} packages (torch from {TORCH_INDEX})")
            fd, rq = tempfile.mkstemp(suffix=".txt", dir=bh)
            with os.fdopen(fd, "w") as f: f.write("\n".join(lock["pip"]) + "\n")
            try:
                subprocess.run(pip + ["--no-deps", "--extra-index-url", lock.get("torch_index", TORCH_INDEX), "-r", rq], check=True)
            finally:
                os.remove(rq)
    else:
        print(f"installing {', '.join(TORCH_PIP)} from {TORCH_INDEX}, then {', '.join(BREEZE_PIP)}")
        subprocess.run(pip + ["--index-url", TORCH_INDEX] + list(TORCH_PIP), check=True)
        subprocess.run(pip + list(BREEZE_PIP), check=True)
        lock["pip"], lock["python"] = _freeze(py), pyv
    lock["torch_index"] = lock.get("torch_index", TORCH_INDEX)
    models = lock.setdefault("models", {})
    hubs = _hub_dirs(model_from)
    for name, (repo, rev) in BREEZE_MODELS.items():
        m = models.get(name) or dict(repo=repo, revision=rev)
        repo, rev = m["repo"], m["revision"]
        files = m.get("files") or {p: dict(bytes=n) for p, n in sorted(_hf_tree(repo, rev).items()) if not MODEL_SKIP.match(p)}
        dd = breeze_model(name)
        stamp_p = os.path.join(dd, ".verified.json")
        stamp = _load(stamp_p, {})
        linked = copied = fetched = kept = 0
        for path, f in sorted(files.items()):
            dst = os.path.join(dd, *path.split("/"))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            if os.path.exists(dst) and stamp.get(path) == [os.path.getsize(dst), int(os.path.getmtime(dst)), f.get("sha256")]:
                kept += 1; continue
            if os.path.exists(dst) and os.path.getsize(dst) == f["bytes"]:
                got = _sha256(dst)
                if not f.get("sha256") or got == f["sha256"]:
                    f["sha256"] = got; stamp[path] = [os.path.getsize(dst), int(os.path.getmtime(dst)), got]; kept += 1
                    continue
            got = None
            for hub in hubs:
                s = os.path.join(hub, "models--" + repo.replace("/", "--"), "snapshots", rev, *path.split("/"))
                if not os.path.exists(s) or os.path.getsize(s) != f["bytes"]: continue
                s = os.path.realpath(s)
                h = _sha256(s)
                if f.get("sha256") and h != f["sha256"]:
                    print(f"  {s}: SHA-256 differs from the lock's, not used"); continue
                if os.path.exists(dst): os.remove(dst)
                try:
                    os.link(s, dst); linked += 1
                except OSError:
                    shutil.copyfile(s, dst); copied += 1
                got = h
                break
            if not got:
                url = f"https://huggingface.co/{repo}/resolve/{rev}/{path}"
                print(f"  downloading {url} ({f['bytes'] / 2 ** 20:.0f} MiB)")
                part = _download(url, dst)
                got = _sha256(part)
                if f.get("sha256") and got != f["sha256"]:
                    os.remove(part); sys.exit(f"{repo} {path}: SHA-256 {got} is not the lock's {f['sha256']}: not installed")
                if os.path.exists(dst): os.remove(dst)
                os.replace(part, dst); fetched += 1
            f["sha256"] = got
            stamp[path] = [os.path.getsize(dst), int(os.path.getmtime(dst)), got]
        _dump(stamp_p, stamp)
        models[name] = dict(repo=repo, revision=rev, files=files)
        print(f"{name}: {repo}@{rev[:12]}, {len(files)} files ({kept} in place, {linked} linked, {copied} copied, "
              f"{fetched} downloaded)")
    lock["licence"] = ("Breeze TTS 2 weights and their outputs: BreezeBlue Research and Non-Commercial License 1.1 (fine for "
                       "the user's own maps; re-voice or license before any commercial use). breeze-tts source: Apache-2.0. "
                       "Whisper large-v3-turbo: MIT.")
    lock["note"] = "written by py mapgen/voice.py fetch; commit it"
    if json.dumps(lock, sort_keys=True) != before:
        all_["breeze"] = lock
        _dump(LOCK, all_)
        print(f"wrote {LOCK}: commit it, so every PC installs the same TTS")
    why = tts_ready("breeze")
    if why: sys.exit(why)
    p = os.path.join(HOME, "tmp", "fetch_check.wav")
    rc = say_breeze("Well met, stranger. The road north is closed.", "man", None, p)
    return rc


def say_breeze(text, voice_, seed, out):
    """A design take of a description (or of a part's first description) saying `text`, mastered into `out`."""
    part = voice_ if voice_ in DESCRIPTIONS else "man"
    pin = dict(desc=voice_) if voice_ not in DESCRIPTIONS else dict(desc=DESCRIPTIONS[part][0])
    if seed is not None: pin["seed"] = seed
    sp = cast_breeze({"Say": dict(part=part, n=1, voice=pin)})["Say"]
    sp.update(ref_text=said(text), band=list(BANDS[part]), title="Say", say_out=os.path.abspath(out))
    sp["ref"] = hashlib.sha1(json.dumps([_engine("breeze"), "ref", sp["ref_desc"], sp["ref_text"], sp["seed"], sp["pinned"],
                                         sp["band"], DESIGN_TAKES, GATE]).encode()).hexdigest()
    man = dict(speakers={"Say": sp}, lines={}, names=[])
    if os.path.exists(out): os.remove(out)
    why = tts_ready("breeze") or run_breeze(man, lambda: [], extra=["Say"])
    if why or not os.path.exists(out):
        print(f"not made: {why or 'no design take passed the gate'}"); return 1
    meta = _load(ref_paths(sp["ref"])[1]) or {}
    print(f"{out}: {wave_info(out)['seconds']:.1f} s, seed {meta.get('seed')}; {sp['desc']}")
    return 0


# ---- the command line ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("fetch"); s.add_argument("--engine"); s.add_argument("--model-from", action="append", default=[])
    s = sub.add_parser("synth"); s.add_argument("jobs")
    for c in ("voice", "check", "cast"):
        s = sub.add_parser(c); s.add_argument("out_dir"); s.add_argument("name")
        s.add_argument("--to", help="write the waves and manifest here instead of out_dir")
        s.add_argument("--engine")
        if c == "voice":
            s.add_argument("--only", help="render only these line keys or speakers (comma-separated)")
            s.add_argument("--retry", action="store_true", help="try again the lines that failed the gate")
            s.add_argument("--gpu", choices=("wait", "games", "skip", "force"))
    s = sub.add_parser("say"); s.add_argument("text"); s.add_argument("--voice", default="man")
    s.add_argument("--seed", type=int); s.add_argument("--out", default="say.wav"); s.add_argument("--engine")
    a = ap.parse_args()
    if getattr(a, "engine", None): os.environ["NOX_VOICE_ENGINE"] = engine_name(a.engine)
    if getattr(a, "gpu", None): os.environ["NOX_VOICE_GPU"] = a.gpu
    if a.cmd == "fetch": return fetch_kokoro() if engine_name() == "kokoro" else fetch_breeze(a.model_from)
    if a.cmd == "synth": return _worker(a.jobs)
    if a.cmd == "cast":
        man = plan(a.out_dir, a.name)
        for s_, v in sorted(man["speakers"].items(), key=lambda kv: -kv[1]["lines"]):
            if man["engine_name"] == "kokoro":
                print(f"{s_:14s} {v['title'][:18]:18s} {v['part']:8s} {v['body'][:10]:10s} {v['pic'][:15]:15s} "
                      f"{'+'.join(f'{m}:{w}' for m, w in v['mix'])} x{v['speed']} {v['lang']}  {v['lines']} lines")
            else:
                print(f"{s_:14s} {v['title'][:18]:18s} {v['part']:8s} {v['lines']} lines, seed {v['seed']}"
                      f"{' (pinned)' if v['pinned'] else ''}{'; ' + v['note'] if v['note'] else ''}\n    {v['desc']}")
        print(f"{len(man['lines'])} spoken lines, waves {man['code']}001e..{man['code']}{len(man['lines']):03d}e ({man['engine']})")
        return 0
    if a.cmd == "voice":
        only = [x.strip() for x in (a.only or "").split(",") if x.strip()]
        man, made, cached, why = voice(a.out_dir, a.name, to=a.to, only=only, retry=a.retry)
        ok = sum(l["voiced"] for l in man["lines"].values())
        print(f"{a.name}: {ok} of {len(man['lines'])} lines voiced by {man['engine_name']} ({made} made now, {cached} "
              f"from the cache)" + (f"; not voiced: {why}" if why else ""))
        for k, l in man["lines"].items():
            if not l["voiced"] and (not only or k in only or l["speaker"] in only): print(f"  {k}: {l.get('why')}")
        return 0 if ok == len(man["lines"]) else 1
    if a.cmd == "check":
        res = check(a.out_dir, a.name, a.to)
        for ok, t in res: print(("" if ok else "FAILED: ") + t)
        return 0 if all(ok for ok, _ in res) else 1
    if a.cmd == "say":
        if engine_name() == "breeze": return say_breeze(a.text, a.voice, a.seed, a.out)
        why = tts_ready("kokoro")
        if why: sys.exit(f"{why}: py mapgen/voice.py fetch --engine kokoro")
        v = a.voice
        pin = v if v in VOICES else None
        rec = cast({"Say": dict(part=v if v in ARCHETYPES else "man", n=1, voice=pin)})["Say"]
        synthesize([(said(a.text), rec, os.path.abspath(a.out))])
        print(f"{a.out}: {'+'.join(f'{m}:{w}' for m, w in rec['mix'])} x{rec['speed']}, {wave_info(a.out)['seconds']:.1f} s")
        return 0


if __name__ == "__main__":
    sys.exit(main())
