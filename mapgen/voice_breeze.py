"""The Breeze TTS 2 worker of mapgen/voice.py: run by the Breeze venv's Python (voice.run_breeze starts it; never
imported by the build). Loads Breeze TTS 2 and Whisper on the GPU, then for each speaker of its share:

    reference   the speaker's design take: its reference text said by its description (Breeze's voice design), seed
                after seed, each through the quality gate; the best of DESIGN_TAKES that pass (a pinned seed: the first
                that passes) is kept in <HOME>/refs/ as the speaker's voice
    lines       each line by voice direction: the reference wave and its text, the speaker's description (and the
                line's mood) as the instruction, the line's text with its vocal events; through the gate, a new seed
                each try, up to LINE_TRIES; mastered (voice._master) into the cache. A line whose words are the
                reference's is the design take itself.

Prints "VOICE|..." lines for the build to relay. The model is unloaded when the process ends.

    <breeze venv python> mapgen/voice_breeze.py <spec.json>
"""
import json, os, sys, time, zlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import voice as V                                   # noqa: E402  (stdlib only at import)


def log(msg):
    print("VOICE|" + msg, flush=True)


class Breeze:
    def __init__(self, spec):
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
        self.cfg, self.names = float(spec["cfg"]), set(spec.get("names") or ())
        t0 = time.time()
        # eager streaming (Breeze's default); its CUDA-graph fast path compiles with Triton, which Windows lacks
        self.tok, self.model, self.atok = load_runtime(Path(spec["tts"]), device=resolve_device(), attn_implementation="sdpa")
        update_generation_config_for_breeze(self.model)
        self.rt = FastBreezeStreamingRuntime(self.model, self.atok, FastStreamingConfig(
            max_new_tokens=1500, max_seq_len=2048, fast_all=None, fast_text_encoder=False, fast_backbone_prefill=False,
            fast_backbone_decode=False, fast_depth_decoder=False, fast_codec=False, repetition_penalty=1.1), tokenizer=self.tok)
        self.asr = pipeline("automatic-speech-recognition", model=spec["asr"], torch_dtype=torch.float16, device="cuda:0")
        log(f"loaded Breeze TTS 2 and Whisper in {time.time() - t0:.0f} s")

    def synth(self, text, instruction, seed, ref=None):
        req = {"id": "r", "text": text, "speaker": "S0", "instruction": instruction}
        if ref: req["ref_audio_path"], req["ref_text"] = ref
        self.set_all_seeds(seed)
        inputs = self.prepare_inputs(self.tok, self.atok, self.model, [req], self.get_template(self.select_template_name(req)),
                                     guidance_scale=self.cfg, guidance_scale_ref=None, guidance_scale_ins=None)
        x = self.np.concatenate([c.audio for c in self.rt.iter_audio_chunks(inputs, request_id="r", seed=seed)])
        return self.np.asarray(x, dtype=self.np.float32).reshape(-1), self.rt.sample_rate

    def measure(self, wav, sr, words):
        """What the gate judges: Whisper's transcript and its word errors, the median pitch, the pace while speaking."""
        import librosa
        np = self.np
        y = librosa.resample(wav, orig_sr=sr, target_sr=16000)
        heard = self.asr({"raw": y, "sampling_rate": 16000}, generate_kwargs={"language": "en", "task": "transcribe"},
                         return_timestamps=True)["text"].strip()
        errors, n = V.word_errors(words, heard, self.names)
        f0, vf, _ = librosa.pyin(y, fmin=60, fmax=500, sr=16000, frame_length=1024)
        f0m = float(np.nanmedian(f0[vf])) if np.any(vf) else 0.0
        yt, _ = librosa.effects.trim(y, top_db=40)
        return dict(errors=errors, words=n, heard=heard, f0=round(f0m, 1), speech_s=round(len(yt) / 16000, 2),
                    nwords=len(V.norm_words(words, keep_fillers=True)))

    def take(self, text, instruction, seed, words, band, ref=None, ref_f0=None):
        t0 = time.time()
        wav, sr = self.synth(text, instruction, seed, ref)
        self.torch.cuda.synchronize()
        render = time.time() - t0
        m = self.measure(wav, sr, words)
        problems, score = V.gate_verdict(m, band, ref_f0)
        m.update(render_s=round(render, 1), audio_s=round(len(wav) / sr, 2), seed=seed, score=score, problems=problems,
                 wer=round(m["errors"] / max(1, m["words"]), 3), wps=round(m["nwords"] / max(0.1, m["speech_s"]), 2))
        return wav, sr, m

    def reference(self, sp, retry=False):
        """The speaker's design take, made or read from <HOME>/refs/: (wave path, its record) or (None, record)."""
        wp, jp = V.ref_paths(sp["ref"])
        meta = V._load(jp)
        if meta and (meta.get("pass") and os.path.exists(wp) or meta.get("fail") and not retry): return (wp if meta.get("pass") else None), meta
        import soundfile as sf
        want = 1 if sp["pinned"] else V.DESIGN_TAKES
        words = V.untagged(sp["ref_text"])
        cands, good = [], []
        for i in range(V.DESIGN_MAX):
            seed = sp["seed"] + 7919 * i
            wav, sr, m = self.take(sp["ref_text"], sp["ref_desc"], seed, words, sp["band"])
            cands.append({k: m[k] for k in ("seed", "score", "problems", "wer", "f0", "wps", "heard", "render_s", "audio_s")})
            log(f"{sp['speaker']}: design take, seed {seed}: " + ("; ".join(m["problems"]) or "passes") +
                f" (WER {m['wer']:.2f}, {m['f0']:.0f} Hz, {m['wps']:.1f} w/s; {m['audio_s']:.1f} s in {m['render_s']:.0f} s)")
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
                "candidates": cands}
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
                    **{k: ref.get(k) for k in ("seed", "wer", "f0", "wps", "heard", "render_s")},
                    "key": l["key"], "speaker": sp["speaker"], "pass": True, "tries": 1, "reused": "the design take",
                    "problems": []})
                log(f"{sp['speaker']}: {l['key']}: the design take (seed {ref['seed']})")
                continue
            best = None
            base = (sp["seed"] + zlib.crc32(l["spoken"].encode("utf-8"))) % 2 ** 31
            inst = instr + (" " + l["mood"] if l["mood"] else "")
            for t in range(V.LINE_TRIES):
                seed = (base + 7919 * t) % 2 ** 31
                wav, sr, m = self.take(l["spoken"], inst, seed, l["said"], sp["band"], ref=(wp, sp["ref_text"]),
                                       ref_f0=ref.get("f0"))
                log(f"{sp['speaker']}: {l['key']}, try {t + 1} (seed {seed}): " + ("; ".join(m["problems"]) or "passes") +
                    f" (WER {m['wer']:.2f}, {m['f0']:.0f} Hz, {m['wps']:.1f} w/s; {m['audio_s']:.1f} s in {m['render_s']:.0f} s)")
                if best is None or m["score"] < best[2]["score"]: best = (wav, sr, m)
                if not m["problems"]: break
            wav, sr, m = best
            ok = not m["problems"]
            V.store_line(h, V._master(wav.astype("float64"), sr, V.RATE, trim=True), {
                "key": l["key"], "speaker": sp["speaker"], "pass": ok, "tries": t + 1, "problems": m["problems"],
                **{k: m[k] for k in ("seed", "wer", "f0", "wps", "heard", "render_s", "audio_s", "score")}})
        log(f"{sp['speaker']}: done in {time.time() - t0:.0f} s")


def main(path):
    spec = json.load(open(path, encoding="utf-8"))
    b = Breeze(spec)
    for sp in spec["speakers"]:
        b.speaker(sp, spec.get("retry"))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
