#!/usr/bin/env python3
"""
Narrate content/lectiones/{level}/{slug}.json to
assets/audio/lectiones/{level}/{slug}.mp3.

HOW LATIN GETS A VOICE
----------------------
There is no Latin TTS voice -- not in edge-tts, not in Azure, and nothing
peer-reviewed anywhere. espeak-ng's `la` voice has correct classical
phonology but is formant synthesis and sounds robotic.

So the passage is respelled into Italian orthography by
scripts/latin_respell.py and read by an it-IT neural voice. Italian is the
right carrier: hard c and g, phonemic geminates, a trilled r, no affrication
of `ti`. What that buys and what it costs is documented in that module --
the headline cost is that vowel length is not audible, only the stress it
determines.

scripts/check_lectio_audio.py verifies the respelling against espeak-ng's
`la` voice word by word. Run it when a text changes; it is the only guard
against the respelling quietly drifting away from classical phonology.

A lectio whose media.kind is "video" is skipped -- it has no narration.

edge-tts lives in a venv on this machine:

    python3 -m venv /tmp/lat-venv && /tmp/lat-venv/bin/pip install edge-tts
    python3 scripts/generate_lectio_audio.py --tts /tmp/lat-venv/bin/edge-tts

Usage:
    python3 scripts/generate_lectio_audio.py --check
    python3 scripts/generate_lectio_audio.py progressus/dies-in-foro [--force]
    python3 scripts/generate_lectio_audio.py
    python3 scripts/generate_lectio_audio.py --show progressus/dies-in-foro
"""
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lectiones_common as lc
import latin_respell as lr

MANIFEST = lc.AUDIO_DIR / "manifest.json"

PARAGRAPH_BREAK = "\n\n"

# ---------------------------------------------------------------------------
# PACING
#
# edge-tts builds its own SSML from plain text, so there is no <break> to ask
# for and punctuation-only lines are discarded. Dot-lines, ellipses and rows
# of commas change the timing not at all -- the English project measured that
# and documented it in scripts/generate_reading_audio.py.
#
# Handing the service a whole text in one call gives pauses it chooses, and
# measured on this course's first lectio they were not usable:
#
#     paragraph boundaries        1.01 - 1.18 s     fine
#     sentence boundaries         0.16 - 1.16 s     wildly inconsistent
#
# A short sentence ("Prīma lūx est.") got 0.23 s after it while longer ones
# in the same paragraph got ~1.1 s. The length tracks the service's own
# chunking, not the punctuation, so there is nothing in the text to adjust.
#
# Padding the short gaps afterwards was the obvious repair and it is not
# safe: silencedetect finds more boundaries than there are sentences, because
# colons and semicolons register too (commas, measured, do not register at
# all), and padding a colon the way a full stop is padded is wrong.
#
# So each sentence is synthesised on its own and the gaps are assembled here,
# which makes them exact. The cost is that prosody does not run across a
# sentence boundary; at these rates, with short declarative sentences, that
# reads as deliberate rather than choppy -- and running sentences together
# was the actual complaint.
SENTENCE_GAP = 0.60      # seconds, between sentences inside a paragraph
PARAGRAPH_GAP = 1.10     # seconds, between paragraphs (matches the service's own)

# Bump when a pacing constant changes, so every text re-narrates.
PACING_VERSION = "sentencewise-0.60-1.10"

# Keeps a trailing «, " or ) with the sentence it closes.
SENT_RE = re.compile(r'[^.!?]*[.!?]+[»"\u201d\)]*\s*|[^.!?]+$')


def sentences(paragraph):
    return [x.strip() for x in SENT_RE.findall(paragraph) if x.strip()]


def narration_units(d):
    """The text as (latin, gap_after) pairs, gap in seconds.

    The title is its own unit and is followed by a paragraph-sized gap."""
    paras = [[d["title"].rstrip(".") + "."]] + [sentences(p) for p in d["passage"]]
    units = []
    for pi, para in enumerate(paras):
        for si, sent in enumerate(para):
            last_in_para = si == len(para) - 1
            last_overall = pi == len(paras) - 1 and last_in_para
            gap = 0.0 if last_overall else (PARAGRAPH_GAP if last_in_para else SENTENCE_GAP)
            units.append((sent, gap))
    return units


def narration_latin(d):
    """The Latin that is to be spoken: title, then passage."""
    return PARAGRAPH_BREAK.join([d["title"].rstrip(".") + "."] + d["passage"])


def narration_text(d):
    """What is actually handed to edge-tts: the respelled Italian."""
    return lr.respell(narration_latin(d))


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {}


def save_manifest(m):
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=1, sort_keys=True) + "\n", encoding="utf-8")


def fingerprint(d, voice, rate):
    """Staleness is decided by the respelled narration string, not by file
    mtimes. Editing a subtitle, an exercise or a glossary entry does not
    change what is spoken, and an mtime check would burn a regeneration on
    every such edit. Hashing the exact string sent to edge-tts -- plus the
    voice, the rate, and the respeller's own version -- rebuilds audio when,
    and only when, it no longer matches the text.

    RESPELL_VERSION is part of the hash on purpose: a change to the
    respelling rules changes the pronunciation of every text, and all of them
    must then be re-narrated."""
    h = hashlib.sha256()
    h.update(narration_text(d).encode("utf-8"))
    h.update(f"|{voice}|{rate}|{RESPELL_VERSION}|{PACING_VERSION}".encode("utf-8"))
    return h.hexdigest()[:16]


# Bump when scripts/latin_respell.py changes how anything is pronounced.
RESPELL_VERSION = "2026-11-01-muta-cum-liquida"


def voice_and_rate(level, slug, d):
    a = d.get("audio") or {}
    return (a.get("voice") or lc.pick_voice(slug, d.get("narrator")),
            a.get("rate") or lc.LEVEL_RATE[level])


def is_stale(level, slug, d=None, manifest=None):
    if lc.media_kind(d or {}) == "video":
        return None
    a = lc.audio_path(level, slug)
    if not a.exists():
        return "missing"
    if d is None:
        return None
    manifest = load_manifest() if manifest is None else manifest
    voice, rate = voice_and_rate(level, slug, d)
    if manifest.get(f"{level}/{slug}", {}).get("fingerprint") != fingerprint(d, voice, rate):
        return "stale"
    return None


def find_tts(explicit):
    if explicit:
        return explicit
    for c in ("edge-tts", "/tmp/lat-venv/bin/edge-tts", "/tmp/rl-venv/bin/edge-tts"):
        p = shutil.which(c) or (c if Path(c).is_file() else None)
        if p:
            return p
    return None


SAMPLE_RATE = "24000"


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {(r.stderr or r.stdout).strip()[:300]}")
    return r


def _trim_silence(src, dst):
    """Decode to mono wav and strip the silence from both ends.

    edge-tts puts about 0.1 s of lead-in on every clip and a little padding
    at the end. Concatenating untrimmed clips would add those to each gap, so
    the gap would be whatever the service felt like plus whatever we asked
    for -- i.e. not controlled at all. Trimming first is what makes
    SENTENCE_GAP mean 0.60 s.

    The reverse/trim/reverse dance is how silenceremove strips a tail; it
    only ever works on the head of a stream."""
    trim = ("silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0,"
            "areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0,"
            "areverse")
    _run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-af", trim,
          "-ar", SAMPLE_RATE, "-ac", "1", str(dst)])


def _silence(seconds, dst):
    _run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
          "-i", f"anullsrc=r={SAMPLE_RATE}:cl=mono", "-t", f"{seconds:.3f}", str(dst)])


def generate(level, slug, d, tts):
    """Narrate one lectio sentence by sentence, assembling the gaps exactly.

    See the PACING block above for why this is not a single edge-tts call."""
    voice, rate = voice_and_rate(level, slug, d)
    out = lc.audio_path(level, slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    units = narration_units(d)

    with tempfile.TemporaryDirectory(prefix=f"lectio-{slug}-") as tmp:
        tmp = Path(tmp)
        parts = []
        for i, (latin, gap) in enumerate(units):
            mp3 = tmp / f"s{i:03d}.mp3"
            wav = tmp / f"s{i:03d}.wav"
            _run([tts, "--voice", voice, "--rate", rate,
                  "--write-media", str(mp3), "--text", lr.respell(latin)])
            if not mp3.exists() or mp3.stat().st_size < 800:
                raise RuntimeError(
                    f"{level}/{slug}: edge-tts returned nothing usable for "
                    f"sentence {i + 1} ({latin[:60]!r})")
            _trim_silence(mp3, wav)
            parts.append(wav)
            if gap > 0:
                sil = tmp / f"g{i:03d}.wav"
                _silence(gap, sil)
                parts.append(sil)

        # One concat of wavs, then a single encode -- concatenating mp3s
        # directly would re-encode each part and stack up artefacts.
        listing = tmp / "parts.txt"
        listing.write_text("".join(f"file '{p.name}'\n" for p in parts), encoding="utf-8")
        _run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0",
              "-i", str(listing), "-c:a", "libmp3lame", "-q:a", "4", str(out)])

    # A truncation guard is still worth having: a sentence that came back
    # empty would be caught above, but a systematically short narration
    # (wrong voice, wrong rate) would not. Narration runs about 2.0-2.4 KB
    # per word at these rates; under 1.4 KB a large part of the text is gone.
    words = sum(len(p.split()) for p in d["passage"]) or 1
    kb_per_word = (out.stat().st_size / 1024) / words
    if kb_per_word < 1.4:
        raise RuntimeError(
            f"{level}/{slug}: narration looks truncated -- {out.stat().st_size // 1024} KB "
            f"for {words} words ({kb_per_word:.2f} KB/word, expected >= 1.4).")
    return out, voice, rate


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="level/slug")
    ap.add_argument("--check", action="store_true", help="report missing/stale, generate nothing")
    ap.add_argument("--show", action="store_true", help="print the respelling and exit")
    ap.add_argument("--force", action="store_true", help="regenerate even if up to date")
    ap.add_argument("--tts", help="path to the edge-tts executable")
    args = ap.parse_args()

    items = [(lv, sl, d) for lv, sl, d in lc.all_sources()
             if not args.targets or f"{lv}/{sl}" in args.targets]
    if not items:
        print("no matching content/lectiones/*/*.json")
        return 1

    if args.show:
        for lv, sl, d in items:
            if lc.media_kind(d) == "video":
                continue
            print(f"=== {lv}/{sl} ===")
            for a, b in zip(narration_latin(d).split(PARAGRAPH_BREAK),
                            narration_text(d).split(PARAGRAPH_BREAK)):
                print(f"  LAT  {a}\n  ITA  {b}\n")
        return 0

    narrated = [(lv, sl, d) for lv, sl, d in items if lc.media_kind(d) != "video"]
    skipped = len(items) - len(narrated)

    if args.check:
        man = load_manifest()
        bad = [(lv, sl, why) for lv, sl, d in narrated if (why := is_stale(lv, sl, d, man))]
        for lv, sl, why in bad:
            print(f"  {why.upper():8} {lv}/{sl}")
        print(f"{len(narrated)} narrated lectio(nes); {len(bad)} need audio"
              + (f"; {skipped} video (skipped)" if skipped else ""))
        return 1 if bad else 0

    tts = find_tts(args.tts)
    if not tts:
        print("error: edge-tts not found. Create the venv in this file's docstring,\n"
              "       then pass --tts /tmp/lat-venv/bin/edge-tts", file=sys.stderr)
        return 2

    man, done = load_manifest(), 0
    for lv, sl, d in narrated:
        if not args.force and not is_stale(lv, sl, d, man):
            print(f"  up to date {lv}/{sl}")
            continue
        out, voice, rate = generate(lv, sl, d, tts)
        man[f"{lv}/{sl}"] = {"fingerprint": fingerprint(d, voice, rate), "voice": voice,
                             "rate": rate, "bytes": out.stat().st_size,
                             "respell": RESPELL_VERSION, "pacing": PACING_VERSION}
        save_manifest(man)
        print(f"  narrated {out.relative_to(lc.REPO_ROOT)}  "
              f"({voice}, rate {rate}, {out.stat().st_size // 1024} KB)")
        done += 1
    print(f"{done} audio file(s) written" + (f"; {skipped} video (skipped)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
