"""Bounded deterministic speech normalization and intent recognition; no execution."""
import math
import re
import unicodedata
from decimal import Decimal, localcontext

from .domain import Action, Intent
from .safety import Rejected

SMALL = dict(zip("zero one two three four five six seven eight nine ten eleven twelve thirteen fourteen fifteen sixteen seventeen eighteen nineteen".split(), range(20)))
TENS = dict(zip("twenty thirty forty fifty sixty seventy eighty ninety".split(), range(20, 100, 10)))
NUMBER_WORDS = {*SMALL, *TENS, "hundred", "thousand", "and", "point", "minus", "negative"}


def _integer(tokens):
    if not tokens:
        return None
    if "thousand" in tokens:
        i = tokens.index("thousand")
        head = _integer(tokens[:i])
        tail = tokens[i + 1:]
        if tail[:1] == ["and"]:
            tail = tail[1:]
        rest = _integer(tail) if tail else 0
        return head * 1000 + rest if head and head < 10 and rest is not None and rest < 1000 else None
    if "hundred" in tokens:
        if len(tokens) < 2 or tokens[1] != "hundred" or tokens[0] not in SMALL or not 1 <= SMALL[tokens[0]] <= 9:
            return None
        tail = tokens[2:]
        if tail[:1] == ["and"]:
            tail = tail[1:]
        rest = _integer(tail) if tail else 0
        if tokens[-1] == "and":
            return None
        return SMALL[tokens[0]] * 100 + rest if rest is not None and rest < 100 else None
    if len(tokens) == 1:
        return SMALL.get(tokens[0], TENS.get(tokens[0]))
    if len(tokens) == 2 and tokens[0] in TENS and tokens[1] in SMALL and 1 <= SMALL[tokens[1]] <= 9:
        return TENS[tokens[0]] + SMALL[tokens[1]]
    return None


def _number(tokens):
    sign = ""
    if tokens and tokens[0] in {"minus", "negative"}:
        sign, tokens = "-", tokens[1:]
    if tokens.count("point") == 1:
        i = tokens.index("point")
        whole, digits = _integer(tokens[:i]), tokens[i + 1:]
        if whole is not None and digits and all(t in SMALL and SMALL[t] < 10 for t in digits):
            return sign + str(whole) + "." + "".join(str(SMALL[t]) for t in digits)
        return None
    value = _integer(tokens)
    return sign + str(value) if value is not None else None


def normalize(text):
    text = unicodedata.normalize("NFKC", text).casefold().replace("’", "'").replace("−", "-")
    for old, new in (("what's", "what is"), ("where's", "where is"), ("how's", "how is"),
                     ("that's", "that is"), ("i'm", "i am"), ("don't", "do not"),
                     ("didn't", "did not"), ("isn't", "is not"), ("aren't", "are not")):
        text = re.sub(r"\b" + re.escape(old) + r"\b", new, text)
    text = re.sub(r"(?<=\w)'s\b", "", text)
    text = text.replace("°", " degrees ")
    text = re.sub(r"(?<=[a-z])-(?=[a-z])", " ", text)
    text = re.sub(r"[,!?;:\"“”()]|\.(?!\d)", " ", text)
    tokens, result = text.split(), []
    i = 0
    while i < len(tokens):
        end = i
        while end < min(len(tokens), i + 20) and tokens[end] in NUMBER_WORDS:
            end += 1
        for stop in range(end, i, -1):
            value = _number(tokens[i:stop])
            if value is not None:
                result.append(value)
                i = stop
                break
        else:
            result.append(tokens[i])
            i += 1
    return " ".join(result)


def cancellation(text):
    text = normalize(text)
    if re.fullmatch(r"(?:please )?(?:no|cancel(?: (?:that|the|my)(?: request| action)?)?|never mind)(?: please)?", text):
        return True
    # Only explicit negative imperatives, never an arbitrary sentence containing not.
    return bool(re.fullmatch(r"(?:no )?(?:please )?(?:do not|never) (?:do that|(?:heat|warm|set|bring|home|pause|resume|cancel|move|run|start|stop)\b.*)", text))


def clarification(text):
    return bool(re.search(r"\b(?:not|never|cannot)\b", normalize(text)))


PREFIX = r"(?:(?:please|can you|could you|would you|will you) )*"
HEAT_START = re.compile(r"^" + PREFIX + r"(?:(?:heat|warm|bring)\b|set\b(?=.*\b"
                        r"(?:nozzle|hotend|hot end|extruder|temperature|heater|bed(?! mesh\b))\b))")
HEAT = re.compile(PREFIX + r"(?:heat|warm|set|bring) (?:the |my )?"
                  r"(?P<heater>nozzle|hotend|hot end|extruder|bed|heated bed)(?: temperature)? "
                  r"(?:up to |to |at )?(?P<value>[+-]?(?:\d+(?:\.\d+)?|\.\d+))\s*"
                  r"(?P<unit>(?:degrees?\s*)?(?:celsius|fahrenheit|c|f)?)?"
                  r"(?: (?:on|for)(?: the| my)?(?: printer)?)?(?: please)?")


def heating_request(text):
    return bool(HEAT_START.match(normalize(text)))


def heat_intent(text, printer_id):
    text = normalize(text)
    if not HEAT_START.match(text):
        return None
    match = HEAT.fullmatch(text)
    if match is None or len(match['value']) > 24:
        raise Rejected("Which printer, heater and target temperature do you mean? For example: heat the nozzle to 90.",
                       code="heat_request_incomplete_or_ambiguous")
    with localcontext() as context:
        context.prec = 64
        target = Decimal(match['value'])
        if match['unit'] and re.search(r"\b(?:fahrenheit|f)\b", match['unit']):
            target = (target - 32) * 5 / 9
        value = float(target)
        if not math.isfinite(value):
            raise Rejected("Please give a finite target temperature.", code="heat_temperature_not_finite")
        # Never round a converted value down into a permitted maximum or up from <0.
        if Decimal(str(value)) < target:
            value = math.nextafter(value, math.inf)
        if target < 0 and value == 0:
            value = math.nextafter(0, -math.inf)
    return Intent(action=Action.HEAT, printer_id=printer_id,
                  params={"heater": 1 if "bed" in match['heater'] else 0, "temperature": value})
