import re
from pathlib import Path

from klippy.speech_text import cmu_to_ipa


def build_lexicon(destination: Path, tokens: Path):
    """Build tooling only. No upstream CMU-in-IPA or eSpeak data is reused."""
    import cmudict
    allowed = {line.rsplit(" ", 1)[0] for line in tokens.read_text(encoding="utf-8").splitlines()}
    entries = {}
    for word, phones in cmudict.entries():
        if not re.fullmatch(r"[a-z]+(?:'[a-z]+)?", word) or word in entries:
            continue
        ipa = cmu_to_ipa(phones)
        if not set(ipa) <= allowed:
            raise ValueError("Pronunciation uses a token absent from the model")
        entries[word] = ipa
    entries["klippy"] = list("klˈɪpi")
    # This spelling is a homophone, not an acoustically distinguishable wake word.
    entries["clippy"] = list("klˈɪpi")
    destination.write_text("".join(f"{word} {' '.join(phones)}\n" for word, phones in sorted(entries.items())),
                           encoding="utf-8", newline="\n")
    return len(entries)
