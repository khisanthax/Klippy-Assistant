import re
from difflib import SequenceMatcher

from .domain import Macro, digest, safe_macro_name


def discover(config: dict, previous: dict[str, Macro]) -> tuple[dict[str, Macro], list[str]]:
    found, notices = {}, []
    # Conservative: any configuration change can alter macro behavior through a callee,
    # variable, heater limit or accessory. Revoke all macro approvals on any change.
    dependencies = digest(config)
    for section, fields in config.items():
        if not section.lower().startswith("gcode_macro ") or not isinstance(fields, dict):
            continue
        name = section.split(" ", 1)[1].upper()
        if not safe_macro_name(name):
            continue
        macro = Macro(name=name, definition=str(fields.get("gcode", "")),
                      description=str(fields.get("description", "")), dependency_fingerprint=dependencies)
        old = previous.get(name)
        if old and old.fingerprint == macro.fingerprint:
            macro = old.model_copy(update={"description": macro.description})
        elif old:
            macro = macro.model_copy(update={"previous_definition": old.definition,
                                             "review_notes": ("Definition or dependencies changed; review required",)})
            notices.append(f"{name}: definition changed; approval revoked")
        found[name] = macro
    removed = set(previous) - set(found)
    for name in set(found) - set(previous):
        for old in removed:
            if SequenceMatcher(None, name, old).ratio() > 0.55 or (
                body_signature(previous[old].definition) == body_signature(found[name].definition)
            ):
                found[name] = found[name].model_copy(update={"previous_definition": previous[old].definition,
                                                            "review_notes": (*found[name].review_notes, "Possible rename from " + old)})
                notices.append(f"Possible rename: {old} → {name}; replacement needs approval")
    for name in removed:
        notices.append(f"{name}: removed")
    return found, notices + conflicts(found)


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def body_signature(definition):
    return "\n".join(" ".join(line.split("#", 1)[0].upper().split())
                     for line in definition.splitlines() if line.split("#", 1)[0].strip())


def semantic_words(text):
    synonyms = {"feed": "load", "loading": "load", "eject": "unload", "unloading": "unload",
                "warm": "heat", "heating": "heat", "wipe": "clean", "cleaning": "clean",
                "priming": "purge", "prime": "purge", "filaments": "filament"}
    return {synonyms.get(word, word) for word in words(text)}


def conflicts(registry):
    result = []
    names = sorted(registry)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            wa, wb = semantic_words(a), semantic_words(b)
            aliases_a = {x.casefold() for x in registry[a].aliases}
            aliases_b = {x.casefold() for x in registry[b].aliases}
            if (SequenceMatcher(None, a, b).ratio() > 0.7 or len(wa & wb) >= 2
                    or aliases_a & aliases_b):
                result.append(f"Potential overlap: {a} / {b}; do not assume equivalence")
            sa, sb = body_signature(registry[a].definition), body_signature(registry[b].definition)
            if sa and sb and (sa == sb or SequenceMatcher(None, sa, sb).ratio() >= .85):
                result.append(f"Similar function: {a} / {b}; definitions need independent review")
    return result


def candidates(text, registry):
    text = re.sub(r"\b[a-z_]+\s*(?:=|is|of|at)?\s*-?\d+(?:\.\d+)?\b", " ", text.lower())
    query = semantic_words(text) - {"run", "please", "the", "macro", "can", "could", "you", "my", "a", "some", "with"}
    scored = []
    for macro in registry.values():
        if not (macro.approved and macro.enabled and macro.reviewed):
            continue
        best = 0.0
        for phrase in (macro.name, *macro.aliases):
            tokens = semantic_words(phrase)
            score = len(tokens & query) / max(len(tokens | query), 1)
            best = max(best, score)
        if best >= 0.35:
            scored.append((best, macro.name))
    scored.sort(reverse=True)
    if not scored:
        return []
    return [name for score, name in scored if scored[0][0] - score <= 0.15]


def inferred_parameters(definition):
    return sorted(set(re.findall(r"params\.([A-Za-z_][A-Za-z_0-9]*)", definition)))
