#!/usr/bin/env python3
"""
Verify the respelling against espeak-ng's Latin voice, word by word.

HOW IT WORKS
------------
espeak-ng ships a `la` voice whose classical phonology is correct (c=/k/,
v=/w/, ae=/ae/, macrons honoured, short vowels laxed) but whose synthesis is
robotic, so it cannot narrate the site. It CAN, however, say what a word
ought to sound like. So:

    word  --espeak -v la-->  target IPA        (true classical)
    word  --respell--> spelling --espeak -v it--> actual IPA   (what a
                                                   neural it-IT voice will
                                                   roughly produce)

and the two are compared after normalising away the differences we have
already accepted and documented (vowel length, the s/z and gn decisions,
short-vowel laxing). Anything left is a respelling bug.

This is a check, not a gate on audio generation -- it reports and exits 1 so
CI or a human can look, because a handful of words will always differ for
reasons we chose.

    python3 scripts/check_lectio_audio.py                 # every lectio
    python3 scripts/check_lectio_audio.py progressus/dies-in-foro
    python3 scripts/check_lectio_audio.py --word "Caesarem"
"""
import argparse
import re
import subprocess
import sys
import unicodedata
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import latin_respell as lr

try:
    import lectiones_common as lc
except ImportError:
    lc = None


def espeak(voice, text):
    r = subprocess.run(["espeak-ng", "-v", voice, "-x", "--ipa", "-q", text],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"espeak-ng -v {voice} failed: {r.stderr.strip()[:200]}")
    return r.stdout.strip()


# Differences we have decided to accept. Normalising them away is what keeps
# this check from crying wolf on every single word.
#
#   ː        vowel length  -- Italian spelling cannot carry it (documented)
#   ɪ ʊ ɛ ɔ  espeak's `la` laxes short vowels; Italian keeps them tense. A
#            real difference in vowel QUALITY, but not a respelling error.
#   z -> s   intervocalic voicing, handled by s_mode="geminate"
#   ɲ -> n   the gn compromise
#   ʰ        aspiration of Greek stops
#   h -> ''  Italian h is silent, so classical /h/ is simply not available
#            through Italian spelling. Documented in latin_respell; folding
#            it here stops every single h-word being reported.
#   ŋ -> n    n before k/g. Italian velarises it phonetically even where the
#            transcription writes plain n, so this is a notation difference.
#   ʔ -> ''  espeak's `la` inserts a glottal stop between identical vowels
#            in hiatus (per-i-it); nothing hangs on it.
#   ss -> s  the gemination that s_mode="geminate" costs us
#   j -> i   /ai̯/ vs /aj/ is the same diphthong, notated two ways. Latin
#            consonantal i is genuinely /j/, and so is the target's, so
#            folding these together does not hide a real error.
FOLD = str.maketrans({"ː": "", "ɪ": "i", "ʊ": "u", "ɛ": "e", "ɔ": "o",
                      "z": "s", "ɲ": "n", "ʰ": "", "ˌ": "", "ʒ": "s",
                      "j": "i", "h": "", "ŋ": "n", "ʔ": ""})


def fold(ipa):
    s = unicodedata.normalize("NFD", ipa).translate(FOLD)
    s = "".join(c for c in s if not unicodedata.combining(c) or c == "ˈ")
    s = re.sub(r"(.)\1+", r"\1", s)       # collapse geminates
    s = s.replace("ˈ", "\x01")            # keep stress, as a plain marker
    s = re.sub(r"[^a-zjwŋθfvtkpsrlmnhaeiou\x01]", "", s)
    # In a monosyllable the stress mark carries no information and espeak
    # places it inconsistently (pˈrɔ vs prˈo), so drop it.
    if sum(1 for c in s if c in "aeiou") <= 1:
        s = s.replace("\x01", "")
    return s


def compare_word(w):
    target = espeak("la", w)
    spelling = lr.respell_word(w)
    actual = espeak("it", spelling)
    return spelling, target, actual, fold(target) == fold(actual)


def words_of(text):
    seen, out = set(), []
    for m in lr.LATIN_WORD_RE.finditer(text):
        w = m.group(0)
        if w.lower() not in seen:
            seen.add(w.lower())
            out.append(w)
    return out


def report(label, text):
    bad = []
    for w in words_of(text):
        spelling, target, actual, ok = compare_word(w)
        if not ok:
            bad.append((w, spelling, target, actual))
    n = len(words_of(text))
    if bad:
        print(f"\n{label}: {len(bad)}/{n} word(s) drift")
        print(f"  {'latin':<16}{'respelled':<18}{'classical':<18}{'italian voice'}")
        for w, sp, t, a in bad:
            print(f"  {w:<16}{sp:<18}{t:<18}{a}")
    else:
        print(f"{label}: all {n} words agree")
    return bad


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("targets", nargs="*", help="level/slug")
    ap.add_argument("--word", action="append", default=[], help="check single words")
    args = ap.parse_args()

    if not subprocess.run(["which", "espeak-ng"], capture_output=True).returncode == 0:
        print("error: espeak-ng not installed (it is the oracle; pacman -S espeak-ng)",
              file=sys.stderr)
        return 2

    if args.word:
        bad = report("words", " ".join(args.word))
        return 1 if bad else 0

    if lc is None:
        print("error: lectiones_common.py not importable", file=sys.stderr)
        return 2

    total = 0
    for lv, slug, d in lc.all_sources():
        if args.targets and f"{lv}/{slug}" not in args.targets:
            continue
        total += len(report(f"{lv}/{slug}", " ".join(d["passage"])))
    print(f"\n{total} drifting word(s) overall")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
