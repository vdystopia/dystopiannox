"""The Breeze TTS 2 worker of mapgen/voice.py: started by voice.run_breeze (never imported by the build), on pc1's GPU
or on pc2's. The work is the same on either; only where a take is made and heard differs (a backend):

    LocalBackend    Breeze TTS 2 and Whisper loaded here, on this PC's GPU (pc1; needs the Breeze venv)
    RemoteBackend   pc2's GPU service over HTTPS (stdlib urllib, no torch): POST /breeze/synth and /asr; a 503 (busy,
                    no memory) is waited out by its Retry-After, an unreachable service retried up to spec["wait_s"]

For each speaker of its share:

    reference   the speaker's design take: its reference text said by its description (Breeze's voice design), seed
                after seed, each through the quality gate; the best of DESIGN_TAKES that pass (a pinned seed: the first
                that passes) is kept in <HOME>/refs/ as the speaker's voice
    lines       each line by voice direction: the reference wave and its text, the speaker's description (and the
                line's mood) as the instruction, the line's text with its vocal events; through the gate, a new seed
                each try, up to LINE_TRIES; mastered (voice._master) into the cache. A line whose words are the
                reference's is the design take itself.

The gate measures every take here, the same way whichever GPU made it (Whisper's transcript from the backend; the
pitch and the pace by librosa in this process). A take made on pc2 may differ from the same seed's on pc1 (another
GPU); each record says where it was made ("gpu"), and a cached take is never made again for that alone.

The parent asks it to stop by writing spec["stop"]: "take" (gaming: stop before the next take) or "line" (stop
before the next line or reference). Exit codes: 0 done, 3 stopped on request, 75 pc2 unreachable for too long.
Prints "VOICE|..." lines for the build to relay. A model is unloaded when the process ends.

    <python> mapgen/voice_breeze.py <spec.json>
"""
import base64, io, json, os, sys, time, wave, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voice as V                                   # noqa: E402  (stdlib only at import)


def log(msg):
    print("VOICE|" + msg, flush=True)


class Stop(Exception):
    """The parent asked the worker to stop (gaming, Talk's model, the game over: back to pc1)."""


class Unavailable(Exception):
    """pc2's GPU service stayed unreachable."""


def wav_bytes(x, sr):
    """A PCM 16-bit mono WAV of float samples (what the remote service is sent)."""
    import numpy as np
    pcm = np.clip(np.round(np.asarray(x, dtype=np.float64).reshape(-1) * 32767), -32768, 32767).astype("<i2")
    b = io.BytesIO()
    with wave.open(b, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(int(sr)); w.writeframes(pcm.tobytes())
    return b.getvalue()


def wav_samples(data):
    """(float32 samples, rate) of a PCM 16-bit WAV (what the remote service returns)."""
    import numpy as np
    with wave.open(io.BytesIO(data)) as w:
        ch, sw, sr, raw = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.readframes(w.getnframes())
    if sw != 2: raise ValueError(f"a {8 * sw}-bit wave from the service (want 16)")
    x = np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768
    return (x.reshape(-1, ch).mean(axis=1) if ch > 1 else x), sr


class LocalBackend:
    """Breeze TTS 2 and Whisper on this PC's GPU."""
    def __init__(self, spec, where="pc1"):
        self.where = where
        sys.path.insert(0, spec["src"])
        import numpy as np, torch
        from pathlib import Path
        from breeze_infer.runtime import load_runtime, resolve_device, set_all_seeds, update_generation_config_for_breeze
        from breeze_infer.templates import get_template, prepare_inputs, select_template_name
        from models.fast_streaming import FastBreezeStreamingRuntime, FastStreamingConfig
        from transformers import pipeline
        self.np, self.torch = np, torch
        self.set_all_seeds, self.get_template = set_all_seeds, get_template
        self.prepare_inputs, self.select_template_name = prepare_inputs, select_template_name
        self.cfg = float(spec["cfg"])
        t0 = time.time()
        # eager streaming (Breeze's default); its CUDA-graph fast path compiles with Triton, which Windows lacks
        self.tok, self.model, self.atok = load_runtime(Path(spec["tts"]), device=resolve_device(), attn_implementation="sdpa")
        update_generation_config_for_breeze(self.model)
        self.rt = FastBreezeStreamingRuntime(self.model, self.atok, FastStreamingConfig(
            max_new_tokens=1500, max_seq_len=2048, fast_all=None, fast_text_encoder=False, fast_backbone_prefill=False,
            fast_backbone_decode=False, fast_depth_decoder=False, fast_codec=False, repetition_penalty=1.1), tokenizer=self.tok)
        self.asr = pipeline("automatic-speech-recognition", model=spec["asr"], torch_dtype=torch.float16, device="cuda:0")
        log(f"loaded Breeze TTS 2 and Whisper on {where} in {time.time() - t0:.0f} s")

    def synth(self, text, instruction, seed, ref=None):
        """(float32 samples, rate, GPU seconds)."""
        t0 = time.time()
        req = {"id": "r", "text": text, "speaker": "S0", "instruction": instruction}
        if ref: req["ref_audio_path"], req["ref_text"] = ref
        self.set_all_seeds(seed)
        inputs = self.prepare_inputs(self.tok, self.atok, self.model, [req], self.get_template(self.select_template_name(req)),
                                     guidance_scale=self.cfg, guidance_scale_ref=None, guidance_scale_ins=None)
        x = self.np.concatenate([c.audio for c in self.rt.iter_audio_chunks(inputs, request_id="r", seed=seed)])
        self.torch.cuda.synchronize()
        return self.np.asarray(x, dtype=self.np.float32).reshape(-1), self.rt.sample_rate, time.time() - t0

    def transcribe(self, y16):
        return self.asr({"raw": y16, "sampling_rate": 16000}, generate_kwargs={"language": "en", "task": "transcribe"},
                        return_timestamps=True)["text"].strip()


class RemoteBackend:
    """A GPU service over HTTPS (pc2's: Tailscale identity, no token)."""
    def __init__(self, spec, where="pc2", stopped=lambda: False):
        self.where, self.url, self.cfg, self.stopped = where, spec["url"].rstrip("/"), float(spec["cfg"]), stopped
        self.wait_s = float(spec.get("wait_s", 7200))
        self.refs = {}
        h = self._call("GET", "/health", timeout=30)
        log(f"{where}'s GPU service {self.url}: " + ", ".join(f"{k} {v}" for k, v in sorted(h.items())))

    def _call(self, method, path, body=None, timeout=900):
        import urllib.request, urllib.error
        data = json.dumps(body).encode("utf-8") if body is not None else None
        down_since, said_503 = None, False
        while True:                                     # a stop is honoured only while waiting, never mid-take
            req = urllib.request.Request(self.url + path, data=data, method=method,
                                         headers={"Content-Type": "application/json"} if data else {})
            try:
                with urllib.request.urlopen(req, timeout=timeout) as r: return json.load(r)
            except urllib.error.HTTPError as e:
                if e.code != 503: raise RuntimeError(f"{method} {path}: HTTP {e.code} {e.read()[:300]!r}")
                try:
                    wait_ = min(60.0, max(1.0, float(e.headers.get("Retry-After") or 10)))
                except ValueError:
                    wait_ = 10.0
                if not said_503: log(f"{self.where} is busy (503): retrying every {wait_:g} s"); said_503 = True
                down_since = None
            except (OSError, ValueError) as e:          # unreachable, reset, timed out, a garbled reply
                down_since = down_since or time.time()
                if time.time() - down_since > self.wait_s:
                    raise Unavailable(f"{self.where} unreachable for {self.wait_s / 60:.0f} min: {e}")
                log(f"{self.where} unreachable ({e}): retrying in 15 s")
                wait_ = 15.0
            t_end = time.time() + wait_
            while time.time() < t_end:
                if self.stopped(): raise Stop()
                time.sleep(min(1.0, wait_))

    def synth(self, text, instruction, seed, ref=None):
        body = {"text": text, "instruction": instruction, "seed": int(seed), "cfg": self.cfg}
        if ref:
            wp, rt = ref
            if wp not in self.refs:
                with open(wp, "rb") as f: self.refs[wp] = base64.b64encode(f.read()).decode("ascii")
            body.update(ref_audio_b64=self.refs[wp], ref_text=rt)
        r = self._call("POST", "/breeze/synth", body)
        x, sr = wav_samples(base64.b64decode(r["audio_b64"]))
        return x, int(r.get("sample_rate") or sr), float(r.get("gpu_s") or 0.0)

    def transcribe(self, y16):
        r = self._call("POST", "/asr", {"audio_b64": base64.b64encode(wav_bytes(y16, 16000)).decode("ascii")})
        return (r.get("text") or "").strip()


class Worker:
    """The work, whichever backend makes and hears the takes."""
    def __init__(self, spec, backend):
        self.b, self.names, self.stop = backend, set(spec.get("names") or ()), spec.get("stop")

    def stop_asked(self, at):
        """at: "take" (between two takes of a line) or "line" (before a line or a reference)."""
        if not self.stop: return False
        try:
            with open(self.stop) as f: mode = f.read().strip()
        except OSError:
            return False
        return mode == "take" or at == "line"

    def check_stop(self, at):
        if self.stop_asked(at): raise Stop()

    def measure(self, wav, sr, words):
        """What the gate judges: the transcript and its word errors, the median pitch, the pace while speaking."""
        import librosa, numpy as np
        y = librosa.resample(np.asarray(wav, dtype=np.float32), orig_sr=sr, target_sr=16000)
        heard = self.b.transcribe(y)
        errors, n = V.word_errors(words, heard, self.names)
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=500, sr=16000, frame_length=1024)
        f0m = float(np.nanmedian(f0[vf])) if np.any(vf) else 0.0
        yt, _ = librosa.effects.trim(y, top_db=40)
        return dict(errors=errors, words=n, heard=heard, f0=round(f0m, 1), speech_s=round(len(yt) / 16000, 2),
                    nwords=len(V.norm_words(words, keep_fillers=True)))

    def take(self, text, instruction, seed, words, band, ref=None, ref_f0=None):
        t0 = time.time()
        wav, sr, gpu_s = self.b.synth(text, instruction, seed, ref)
        render = time.time() - t0
        m = self.measure(wav, sr, words)
        problems, score = V.gate_verdict(m, band, ref_f0)
        m.update(render_s=round(render, 1), gpu_s=round(gpu_s, 1), audio_s=round(len(wav) / sr, 2), seed=seed,
                 score=score, problems=problems, gpu=self.b.where,
                 wer=round(m["errors"] / max(1, m["words"]), 3), wps=round(m["nwords"] / max(0.1, m["speech_s"]), 2))
        return wav, sr, m

    def _said(self, m):
        return (f" (WER {m['wer']:.2f}, {m['f0']:.0f} Hz, {m['wps']:.1f} w/s; {m['audio_s']:.1f} s in {m['render_s']:.0f} s"
                f"{', GPU %.0f s' % m['gpu_s'] if self.b.where != 'pc1' else ''})")

    def reference(self, sp, retry=False):
        """The speaker's design take, made or read from <HOME>/refs/: (wave path, its record) or (None, record)."""
        wp, jp = V.ref_paths(sp["ref"])
        meta = V._load(jp)
        if meta and (meta.get("pass") and os.path.exists(wp) or meta.get("fail") and not retry): return (wp if meta.get("pass") else None), meta
        import soundfile as sf
        self.check_stop("line")
        want = 1 if sp["pinned"] else V.DESIGN_TAKES
        words = V.untagged(sp["ref_text"])
        cands, good = [], []
        for i in range(V.DESIGN_MAX):
            if i: self.check_stop("take")
            seed = sp["seed"] + 7919 * i
            wav, sr, m = self.take(sp["ref_text"], sp["ref_desc"], seed, words, sp["band"])
            cands.append({k: m[k] for k in ("seed", "score", "problems", "wer", "f0", "wps", "heard", "render_s", "audio_s", "gpu")})
            log(f"{sp['speaker']}: design take, seed {seed}: " + ("; ".join(m["problems"]) or "passes") + self._said(m))
            if not m["problems"]: good.append((m["score"], i, wav, sr, m))
            if len(good) >= want: break
        os.makedirs(os.path.dirname(wp), exist_ok=True)
        if not good:
            meta = dict(fail=f"{len(cands)} seeds tried, best: " + "; ".join(min(cands, key=lambda c: c["score"])["problems"]),
                        candidates=cands, desc=sp["ref_desc"], text=sp["ref_text"])
            V._dump(jp, meta)
            return None, meta
        _, _, wav, sr, m = min(good, key=lambda g: g[:2])
        sf.write(wp + ".part", wav, sr, format="WAV", subtype="FLOAT")
        os.replace(wp + ".part", wp)
        meta = {"pass": True, "seed": m["seed"], "desc": sp["ref_desc"], "text": sp["ref_text"], "f0": m["f0"],
                "wer": m["wer"], "wps": m["wps"], "heard": m["heard"], "render_s": m["render_s"], "audio_s": m["audio_s"],
                "gpu": m["gpu"], "candidates": cands}
        V._dump(jp, meta)
        return wp, meta

    def speaker(self, sp, retry):
        t0 = time.time()
        wp, ref = self.reference(sp, retry)
        if not wp:
            log(f"{sp['speaker']}: no design take passed the gate ({ref['fail']}): its lines stay silent")
            return
        if sp.get("say_out"):
            import soundfile as sf
            x, sr = sf.read(wp, dtype="float64")
            V.write_wav(sp["say_out"], V._master(x, sr, V.RATE, trim=True), V.RATE)
        ref_sha = V.file_sha(wp)
        instr = sp["desc"]
        for l in sp["lines"]:
            h = V.line_hash(l["spec"], ref_sha)
            old = V.cache_meta(h)
            if old and (old.get("pass") and os.path.exists(V._cache(h)) or not retry): continue
            if l["spoken"] == sp["ref_text"]:           # the reference's own words: the design take is the line
                import soundfile as sf
                x, sr = sf.read(wp, dtype="float64")
                V.store_line(h, V._master(x, sr, V.RATE, trim=True), {
                    **{k: ref.get(k) for k in ("seed", "wer", "f0", "wps", "heard", "render_s", "gpu")},
                    "key": l["key"], "speaker": sp["speaker"], "pass": True, "tries": 1, "reused": "the design take",
                    "problems": []})
                log(f"{sp['speaker']}: {l['key']}: the design take (seed {ref['seed']})")
                continue
            self.check_stop("line")
            best = None
            base = (sp["seed"] + zlib.crc32(l["spoken"].encode("utf-8"))) % 2 ** 31
            inst = instr + (" " + l["mood"] if l["mood"] else "")
            for t in range(V.LINE_TRIES):
                if t: self.check_stop("take")
                seed = (base + 7919 * t) % 2 ** 31
                wav, sr, m = self.take(l["spoken"], inst, seed, l["said"], sp["band"], ref=(wp, sp["ref_text"]),
                                       ref_f0=ref.get("f0"))
                log(f"{sp['speaker']}: {l['key']}, try {t + 1} (seed {seed}): " + ("; ".join(m["problems"]) or "passes")
                    + self._said(m))
                if best is None or m["score"] < best[2]["score"]: best = (wav, sr, m)
                if not m["problems"]: break
            wav, sr, m = best
            ok = not m["problems"]
            V.store_line(h, V._master(wav.astype("float64"), sr, V.RATE, trim=True), {
                "key": l["key"], "speaker": sp["speaker"], "pass": ok, "tries": t + 1, "problems": m["problems"],
                **{k: m[k] for k in ("seed", "wer", "f0", "wps", "heard", "render_s", "gpu_s", "audio_s", "score", "gpu")}})
        log(f"{sp['speaker']}: done in {time.time() - t0:.0f} s")


def main(path):
    spec = json.load(open(path, encoding="utf-8"))
    if spec.get("home"): V.HOME = spec["home"]
    where = spec.get("backend", "pc1")
    w = Worker(spec, None)
    try:
        if spec.get("url"):          # pc2's service; on "pc1" only a stand-in of the tests (NOX_VOICE_PC1_URL)
            w.b = RemoteBackend(spec, where, stopped=lambda: w.stop_asked("line"))
        else:
            w.check_stop("line")
            w.b = LocalBackend(spec, where)
        for sp in spec["speakers"]:
            w.speaker(sp, spec.get("retry"))
    except Stop:
        log(f"stopped on {where} as asked; the lines made so far are cached")
        return V.EXIT_STOPPED
    except Unavailable as e:
        log(str(e))
        return V.EXIT_UNAVAILABLE
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
