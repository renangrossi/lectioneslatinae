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
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lectiones_common as lc
import latin_respell as lr

MANIFEST = lc.AUDIO_DIR / "manifest.json"

# edge-tts builds its own SSML from plain text, so there is no <break> to ask
# for and punctuation-only lines are discarded. The gap between paragraphs is
# whatever the service gives long-form text (about a second) and cannot be set
# from here -- the English project measured this and documented it at length in
# scripts/generate_reading_audio.py. Do not add dot-lines or ellipses hoping
# for a longer pause; they change nothing.
PARAGRAPH_BREAK = "\n\n"


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
    h.update(f"|{voice}|{rate}|{RESPELL_VERSION}".encode("utf-8"))
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


def generate(level, slug, d, tts):
    voice, rate = voice_and_rate(level, slug, d)
    out = lc.audio_path(level, slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [tts, "--voice", voice, "--rate", rate,
           "--write-media", str(out), "--text", narration_text(d)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
    if r.returncode != 0 or not out.exists() or out.stat().st_size < 2000:
        raise RuntimeError(f"edge-tts failed for {level}/{slug}: {r.stderr.strip()[:300]}")

    # edge-tts can exit 0 having written a file that stops part-way through
    # the text. The English project hit this and its old 2 KB floor did not
    # catch it, so the guard is per-word: narration runs about 2.0-2.4 KB per
    # word at -15%, and under 1.4 KB per word a large part of the text is
    # missing. Loose on purpose -- it is here for gross truncation, not to
    # police normal variation between voices.
    words = sum(len(p.split()) for p in d["passage"]) or 1
    kb_per_word = (out.stat().st_size / 1024) / words
    if kb_per_word < 1.4:
        raise RuntimeError(
            f"{level}/{slug}: narration looks truncated -- {out.stat().st_size // 1024} KB "
            f"for {words} words ({kb_per_word:.2f} KB/word, expected >= 1.4). "
            f"Delete the file and run again; this is usually a transient edge-tts failure.")
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
                             "respell": RESPELL_VERSION}
        save_manifest(man)
        print(f"  narrated {out.relative_to(lc.REPO_ROOT)}  "
              f"({voice}, rate {rate}, {out.stat().st_size // 1024} KB)")
        done += 1
    print(f"{done} audio file(s) written" + (f"; {skipped} video (skipped)" if skipped else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
