#!/usr/bin/env python3
"""
Latin (macron-marked) -> Italian orthography, approximating CLASSICAL phonology.

WHY THIS EXISTS
---------------
Neither edge-tts nor Azure offers a Latin voice, and nothing peer-reviewed
offers a classical-Latin neural voice at all (the vendors advertising one are
selling marketing copy; one claims a model "trained on native speech", which
for Latin is impossible). The only engine with genuinely correct classical
phonology is espeak-ng's `-v la`, and it is formant synthesis -- a robot.

So: respell Latin into Italian spelling and let a natural it-IT neural voice
read it. Italian is the right target because it keeps /k/ and /g/, has
phonemic geminates, a trilled r, and no affrication of `ti`.

espeak-ng's `la` voice is still used -- not to speak, but as an ORACLE. See
scripts/check_lectio_audio.py: it phonemises the respelling through an
Italian front-end and diffs the IPA against true classical IPA, so a
respelling regression fails a check instead of shipping silently.

WHAT IS FAITHFUL
----------------
    c, k      -> /k/ always          cēna   -> chena    (not /tʃ/)
    g         -> /g/ always          gelū   -> ghelu
    v         -> /w/                 venit  -> wenit    -> /wenit/
    ae, oe    -> /ae/, /oe/          Caesar -> caissar
    qu, gu    -> /kw/, /gw/          kept as-is; Italian already does this
    x         -> /ks/                rex    -> rechs
    ph/th/ch  -> /f/, /t/, /k/       approximations of the Greek aspirates
    ti        -> /ti/                nātiō  -> natio    (not /tsjo/)
    geminates preserved              ille   -> ille     /ille/
    stress    Latin penultimate law, computed from the macrons

WHAT IS LOST
------------
  * VOWEL LENGTH. Italian orthography cannot express it, and it is phonemic
    in Latin and indispensable for verse. This is the one real casualty and
    it is not fixable here: the fix is Azure's paid <phoneme alphabet="ipa">
    fed the oracle's IPA directly. Macrons are still read -- they decide
    stress -- they just are not heard as length.
  * gn is /Nn/ in Latin; "ngn" lands on Italian /Nɲ/, which is close but not
    exact. Plain "gn" would give /ɲɲ/, which is much worse.
  * /h/. Italian h is silent, so habeō comes out "abeo". Classical h was
    weak and was already being dropped in speech, so this is the cheapest of
    the losses -- but it is a loss.
  * Intervocalic s: standard Italian voices it to /z/, which Latin never had.
    `s_mode="geminate"` writes "ss" to force /s/, at the cost of a spurious
    gemination; `s_mode="keep"` accepts the /z/ instead. Geminate is the
    default because a wrong CONSONANT is more audible than a wrong length.

TWO BUGS THIS MODULE EXISTS TO NOT HAVE AGAIN
---------------------------------------------
Both were real, and both came from naive letter-counting:

 1. The `u` of `qu`/`gu` is not a syllable nucleus. Counting it as one makes
    "quoque" look like four syllables and throws the stress rule off.
 2. The `u` written for consonantal `v` is not a nucleus either. Marking
    stress on it turned "venit" -> "ùenit" -> /ˈuenit/ (three syllables,
    stress on a glide) instead of /ˈwenit/. Hence GLIDE: v becomes a
    sentinel that is invisible to the syllable counter and only becomes a
    literal "u" at the very end.
"""
import re

__all__ = ["respell", "respell_word", "stress_index", "nuclei"]

MACRONS = str.maketrans({
    "ā": "a", "ē": "e", "ī": "i", "ō": "o", "ū": "u", "ȳ": "y",
    "Ā": "A", "Ē": "E", "Ī": "I", "Ō": "O", "Ū": "U", "Ȳ": "Y",
})
LONG = set("āēīōūȳ")
SHORT = set("aeiouy")
VOWELS = LONG | SHORT
DIPHTHONGS = {("a", "e"), ("o", "e"), ("a", "u"), ("e", "u")}

# Stands in for consonantal v between respelling and output. Not a vowel, so
# the syllable counter steps over it; becomes "u" in the final string.
GLIDE = "\x02"

ACUTE = {"a": "à", "e": "è", "i": "ì", "o": "ò", "u": "ù"}

LATIN_WORD_RE = re.compile(r"[A-Za-zĀāĒēĪīŌōŪūȲȳ]+")


def nuclei(w):
    """Syllable nuclei of a Latin word, as (index, length, heavy).

    `index` is into `w`; `length` is 1 or 2 (a diphthong spans two letters).
    `heavy` means long vowel, diphthong, or a closed syllable -- which is
    what the stress rule needs.

    The `u` of qu/gu is skipped: it belongs to the onset, not the nucleus.
    """
    base = w.lower()
    found = []
    i = 0
    while i < len(base):
        ch = base[i]
        if ch not in VOWELS:
            i += 1
            continue
        # the u of qu / gu is part of the consonant onset, never a nucleus
        if ch == "u" and i > 0 and base[i - 1] in "qg" and i + 1 < len(base) \
                and base[i + 1] in VOWELS:
            i += 1
            continue
        length = 1
        if ch in SHORT and i + 1 < len(base) and (ch, base[i + 1]) in DIPHTHONGS:
            length = 2
        found.append([i, length, ch in LONG or length == 2])
        i += length

    # closed-syllable weight: count consonants between this nucleus and the next
    for n, item in enumerate(found):
        idx, length, heavy = item
        start = idx + length
        end = found[n + 1][0] if n + 1 < len(found) else len(base)
        cons = 0
        j = start
        while j < end:
            c = base[j]
            # qu / gu count as a single consonant
            if c in "qg" and j + 1 < end and base[j + 1] == "u":
                cons += 1
                j += 2
                continue
            # MUTA CUM LIQUIDA: a stop + l/r is the onset of the FOLLOWING
            # syllable, so it does not close this one. tenebrīs is TE-ne-brīs,
            # not te-NE-brīs -- counting "br" as two consonants made the penult
            # heavy and pulled the stress one syllable right. (Caught by the
            # espeak oracle, which had it as tˈɛnɛbriːs against our tenˈɛbris.)
            if c in "pbtdcgf" and j + 1 < end and base[j + 1] in "lr":
                cons += 1
                j += 2
                continue
            if c in VOWELS or c == GLIDE:
                j += 1
                continue
            cons += 1
            j += 1
        # two consonants close the syllable; one does only word-finally
        if cons >= 2 or (cons >= 1 and n + 1 == len(found)):
            item[2] = True
    return [tuple(x) for x in found]


def stress_index(w):
    """Index of the stressed nucleus (0-based, among nuclei), by the
    penultimate law: penult if the penult is heavy, else antepenult.
    Monosyllables and disyllables stress the first syllable."""
    ns = nuclei(w)
    if not ns:
        return None
    if len(ns) <= 2:
        return 0
    return len(ns) - 2 if ns[-2][2] else len(ns) - 3


def respell_word(w, s_mode="geminate", mark_stress=True, w_for_v=True):
    # Monosyllables get no accent. An acute is a prosodic instruction to the
    # voice, and est / in / cum / sum are prosodically weak in Latin -- a
    # preposition leans on the word it governs. Accenting every one of them
    # made the narration punch the function words and sound like a telegram.
    n_stress = stress_index(w) if mark_stress and len(nuclei(w)) > 1 else None
    t = w.translate(MACRONS).lower()

    # Greek digraphs before anything can mistake the h for a Latin h
    # The Greek aspirates were /pʰ tʰ kʰ/ in classical Latin, NOT fricatives:
    # philosophia is /pʰilosopʰia/, not the later /filozofia/. Italian has no
    # aspirates, so the plain stops are the closest honest approximation --
    # and "p" is much closer to /pʰ/ than "f" is. (The oracle caught this:
    # "filossofia" diverged from the target on exactly these segments.)
    for a, b in (("ph", "p"), ("th", "t"), ("rh", "r"), ("ch", "c")):
        t = t.replace(a, b)

    # diphthongs -> Italian spellings that keep them diphthongal
    t = t.replace("ae", "ai").replace("oe", "oi")

    # Consonantal v -> /w/. The letter used is "w", NOT "u", and the
    # difference is not cosmetic: "u" glides only word-initially or after a
    # consonant. Intervocalically it becomes a syllable of its own, so
    # vīvere -> "uiuere" came out /wjʊˈɛre/ and aedificāvit -> "aidificauit"
    # came out /aɪdifikˈaʊit/ -- an extra syllable and the stress dragged
    # onto it. "w" hits /w/ in every position.
    #
    # The residual risk is that Italian reads loanword "w" as /v/ (whisky ->
    # /viski/), and espeak's Italian front-end is only a proxy for Azure's.
    # This was therefore A/B-ed against a real it-IT neural voice before
    # being adopted; set w_for_v="u" to go back to the "u" spelling.
    if w_for_v in (True, "w"):
        t = re.sub(r"v", GLIDE, t)
    elif w_for_v == "u":
        t = re.sub(r"v", "\x03", t)

    # Latin gn is /Nn/; "ngn" beats plain "gn" (/ɲɲ/) in Italian
    t = t.replace("gn", "ngn")

    # keep the stops hard before front vowels
    t = re.sub(r"c(?=[eiy])", "ch", t)
    t = re.sub(r"g(?=[eiy])", "gh", t)

    # Italian has no x, k, y
    # x -> "cs" (/ks/). Before another s this would stack up as "css"
    # (exspectant -> ecsspectant), so the cluster is collapsed.
    t = t.replace("x", "cs")
    t = t.replace("css", "cs")
    t = t.replace("k", "c").replace("y", "i")
    t = t.replace("z", "dz")

    # intervocalic s would voice to /z/, which Latin never had
    if s_mode == "geminate":
        t = re.sub(r"(?<=[aeiou])s(?=[aeiou])", "ss", t)

    if n_stress is not None:
        t = _mark_stress(t, n_stress)
    return t.replace(GLIDE, "w").replace("\x03", "u")


def _mark_stress(t, n_stress):
    """Put an acute on the n_stress-th nucleus of the REWRITTEN string.

    Counts nuclei the same way nuclei() does -- skipping the u of qu/gu and
    stepping over GLIDE -- so the two stay in agreement after rewriting.
    """
    out = list(t)
    seen = -1
    i = 0
    while i < len(out):
        ch = out[i]
        if ch not in SHORT:
            i += 1
            continue
        if ch == "u" and i > 0 and out[i - 1] in "qg" and i + 1 < len(out) \
                and out[i + 1] in SHORT:
            i += 1
            continue
        seen += 1
        if seen == n_stress:
            out[i] = ACUTE.get(ch, ch)
            break
        # step past a diphthong so it is not counted twice
        if i + 1 < len(out) and (ch, out[i + 1]) in {("a", "i"), ("o", "i"),
                                                     ("a", "u"), ("e", "u")}:
            i += 2
            continue
        i += 1
    return "".join(out)


def respell(text, **kw):
    """Respell every Latin word in `text`, leaving punctuation alone."""
    return LATIN_WORD_RE.sub(lambda m: respell_word(m.group(0), **kw), text)


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()
    print(respell(src,
                  s_mode="keep" if "--keep-s" in sys.argv else "geminate",
                  mark_stress="--no-stress" not in sys.argv,
                  w_for_v="--keep-v" not in sys.argv))
