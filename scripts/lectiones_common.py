#!/usr/bin/env python3
"""
Shared definitions for the lectiones library (the Latin reading library).

Adapted from the sibling English project's scripts/reading_common.py, with
one structural addition: a lectio's companion media can be either narrated
audio or an embedded video, declared per text (see MEDIA below).

    source of truth   content/lectiones/{level}/{slug}.json
    page              lectiones/{level}/{slug}.html      build_lectio_page.py
    audio             assets/audio/lectiones/{level}/{slug}.mp3
                                                       generate_lectio_audio.py
    hub               lectiones.html                     build_lectio_page.py --hub

Page and audio read the same JSON, which is what stops a text and its
narration drifting apart -- the same guarantee the English project relies on.

MEDIA
-----
    "media": {"kind": "audio"}
        Narrated by generate_lectio_audio.py: the passage is respelled into
        Italian orthography (scripts/latin_respell.py) and read by an it-IT
        neural voice, because no Latin TTS voice exists. See that module for
        why, and scripts/check_lectio_audio.py for how it is verified.

    "media": {"kind": "video", "youtube": "<id>", "title": ..., "channel": ...}
        An embedded video stands in for narration. No audio is generated and
        the staleness check skips the text. Use `transcript: true` when the
        passage is what is spoken or sung in the video; use `transcript:
        false` (the default) when the passage is a companion text written
        for the video rather than a transcription of it.

LEVEL
-----
A level is the Gradus slug, matching gradus/{slug}.html and the directory
names under curriculum/, so a lectio sits in the same taxonomy as a lesson.
"""
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_DIR = REPO_ROOT / "content" / "lectiones"
PAGE_DIR = REPO_ROOT / "lectiones"
AUDIO_DIR = REPO_ROOT / "assets" / "audio" / "lectiones"
HUB_PAGE = REPO_ROOT / "lectiones.html"

# (slug, roman code, Latin name) -- the order is the course's own progression.
# Kept consistent with site_chrome.LEVELS and assets/js/progress.js.
LEVELS = [
    ("fundamenta", "I", "Fundamenta"),
    ("elementa", "II", "Elementa"),
    ("progressus", "III", "Progressus"),
    ("media", "IV", "Media"),
    ("provectus", "V", "Provectus"),
    ("altior", "VI", "Altior"),
    ("auctores", "VII", "Auctores"),
]
LEVEL_CODE = {s: c for s, c, _ in LEVELS}
LEVEL_NAME = {s: n for s, _, n in LEVELS}
LEVEL_SLUGS = [s for s, _, _ in LEVELS]

# Narration pace. Slower while a student is still decoding the orthography;
# natural once they are reading adapted prose. Mirrors the English project's
# LEVEL_RATE, whose -15% for beginners is the value this course's own
# listening test settled on.
LEVEL_RATE = {
    "fundamenta": "-15%", "elementa": "-15%", "progressus": "-15%",
    "media": "-8%", "provectus": "-8%",
    "altior": "+0%", "auctores": "+0%",
}

# it-IT neural voices. Italian is the carrier language for classical Latin
# phonology here -- see scripts/latin_respell.py for the whole argument.
VOICES_M = ["it-IT-DiegoNeural", "it-IT-GiuseppeMultilingualNeural"]
VOICES_F = ["it-IT-ElsaNeural", "it-IT-IsabellaNeural"]

# The chip on a card and the filter on the hub. Key is what the JSON stores.
ARGUMENTA = {
    "vita-quotidiana": "Vita Quotidiana",
    "historia": "Historia",
    "urbs": "Urbs Roma",
    "fabulae": "Fabulae",
    "mythologia": "Mythologia",
    "philosophia": "Philosophia",
    "epistulae": "Epistulae",
    "auctores": "Auctores",
    "imperium": "Imperium",
}

VALID_KINDS = ("audio", "video")


def src_path(level, slug):
    return SRC_DIR / level / f"{slug}.json"


def page_path(level, slug):
    return PAGE_DIR / level / f"{slug}.html"


def audio_path(level, slug):
    return AUDIO_DIR / level / f"{slug}.mp3"


def audio_href(level, slug, rel="../../"):
    return f"{rel}assets/audio/lectiones/{level}/{slug}.mp3"


def media_kind(d):
    return (d.get("media") or {}).get("kind", "audio")


def pick_voice(slug, narrator):
    """narrator: "male" | "female" | None. Deterministic per slug, so a
    rebuild never silently reassigns a voice (which would invalidate the
    fingerprint and burn a regeneration)."""
    roster = VOICES_M if narrator == "male" else VOICES_F if narrator == "female" \
        else VOICES_F + VOICES_M
    return roster[sum(ord(c) for c in slug) % len(roster)]


def load(level, slug):
    import json
    return json.loads(src_path(level, slug).read_text(encoding="utf-8"))


def all_sources():
    """Every lectio source, as (level, slug, data), in course order."""
    import json
    for lv in LEVEL_SLUGS:
        d = SRC_DIR / lv
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.json")):
            yield lv, f.stem, json.loads(f.read_text(encoding="utf-8"))
