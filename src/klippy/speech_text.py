"""Deterministic English speech rendering and a redistributable CMUdict-derived lexicon."""
import re

SMALL = ("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen "
         "fifteen sixteen seventeen eighteen nineteen").split()
TENS = "zero ten twenty thirty forty fifty sixty seventy eighty ninety".split()


def number_words(value: str) -> str:
    if value.startswith("-"):
        return "minus " + number_words(value[1:])
    if "." in value:
        whole, fraction = value.split(".", 1)
        return number_words(whole) + " point " + " ".join(SMALL[int(c)] for c in fraction)
    if len(value) > 1 and value.startswith("0"):
        return " ".join(SMALL[int(c)] for c in value)
    n = int(value)
    if n < 20:
        return SMALL[n]
    if n < 100:
        return TENS[n // 10] + (" " + SMALL[n % 10] if n % 10 else "")
    if n < 1000:
        return SMALL[n // 100] + " hundred" + (" " + number_words(str(n % 100)) if n % 100 else "")
    if n < 1_000_000:
        return number_words(str(n // 1000)) + " thousand" + (" " + number_words(str(n % 1000)) if n % 1000 else "")
    return " ".join(SMALL[int(c)] for c in value)


def normalize_for_speech(text: str, vocabulary: set[str] | None = None) -> str:
    text = text[:600].replace("_", " ").replace("%", " percent ").replace("°", " degrees ")
    result = []
    for token in re.findall(r"-?\d+(?:\.\d+)?|[A-Za-z]+(?:'[A-Za-z]+)?|[.,!?;:]", text):
        if re.fullmatch(r"-?\d+(?:\.\d+)?", token):
            result.append(number_words(token))
        elif token.isupper() and 1 < len(token) <= 6:
            result.append(" ".join(token.lower()))
        elif vocabulary is not None and token.lower() not in vocabulary and token[0].isalpha():
            result.append(" ".join(c.lower() for c in token if c.isalpha()))
        else:
            result.append(token.lower())
    return " ".join(result)


# CMU ARPABET -> Kokoro's documented English IPA token inventory.
PHONES = {
    "AA": "ɑ", "AE": "æ", "AH": "ʌ", "AO": "ɔ", "AW": "aʊ", "AY": "I",
    "B": "b", "CH": "ʧ", "D": "d", "DH": "ð", "EH": "ɛ", "ER": "ɜɹ",
    "EY": "A", "F": "f", "G": "ɡ", "HH": "h", "IH": "ɪ", "IY": "i",
    "JH": "ʤ", "K": "k", "L": "l", "M": "m", "N": "n", "NG": "ŋ",
    "OW": "O", "OY": "ɔɪ", "P": "p", "R": "ɹ", "S": "s", "SH": "ʃ",
    "T": "t", "TH": "θ", "UH": "ʊ", "UW": "u", "V": "v", "W": "w",
    "Y": "j", "Z": "z", "ZH": "ʒ",
}


def cmu_to_ipa(phones):
    output = []
    for phone in phones:
        base = phone.rstrip("012")
        stress = phone[-1] if phone[-1].isdigit() else ""
        if stress in {"1", "2"}:
            output.append("ˈ" if stress == "1" else "ˌ")
        value = "ə" if phone == "AH0" else "ɚ" if phone == "ER0" else PHONES[base]
        output.extend(value)
    return output


