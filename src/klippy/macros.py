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
            notices.append(f"{name}: definition changed; approval revoked")
        found[name] = macro
    removed = set(previous) - set(found)
    for name in set(found) - set(previous):
        for old in removed:
            if SequenceMatcher(None, name, old).ratio() > 0.55 or (
                previous[old].definition == found[name].definition
            ):
                notices.append(f"Possible rename: {old} → {name}; replacement needs approval")
    for name in removed:
        notices.append(f"{name}: removed")
    return found, notices + conflicts(found)


def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def conflicts(registry):
    result = []
    names = sorted(registry)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            wa, wb = words(a), words(b)
            aliases_a = {x.casefold() for x in registry[a].aliases}
            aliases_b = {x.casefold() for x in registry[b].aliases}
            if (SequenceMatcher(None, a, b).ratio() > 0.7 or len(wa & wb) >= 2
                    or aliases_a & aliases_b):
                result.append(f"Potential overlap: {a} / {b}; do not assume equivalence")
    return result


def candidates(text, registry):
    query = words(text) - {"run", "please", "the", "macro", "can", "you"}
    scored = []
    for macro in registry.values():
        if not (macro.approved and macro.enabled and macro.reviewed):
            continue
        best = 0.0
        for phrase in (macro.name, *macro.aliases):
            tokens = words(phrase)
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
