"""Friendly dialogue with a closed, verified-fact boundary for model composition."""

import asyncio
import re
from typing import Literal

from .diagnostics import timings
from .domain import StrictModel
from .presentation import Response


class DialoguePreferences(StrictModel):
    style: Literal["friendly", "calm", "direct"] = "friendly"
    length: Literal["short", "standard", "detailed"] = "short"


OPENINGS = {
    "friendly": ["", "Here's what I can verify.", "Let's take a look."],
    "calm": ["", "Here is the reported information."],
    "direct": [""],
}
CLOSINGS = ["", "Would you like more detail?"]
EXPLANATIONS = {
    "homing": [
        "Homing establishes reference positions for the axes.",
        "A reported homed state does not independently verify toolhead clearance.",
    ],
    "temperatures": [
        "The measured temperature is a sensor reading; the target is the requested temperature.",
        "A temperature reading alone does not establish why heating is slow.",
    ],
    "targets": ["The target is a requested temperature, rather than the current sensor reading."],
    "progress": ["Progress is a reported estimate; it is not a guarantee of completion time."],
    "remaining": ["Remaining time is an estimate and can change with print conditions."],
    "position": ["Klipper reports commanded position, not an independent measurement of the nozzle."],
    "last_failure": [
        "The recorded result describes what was reported, but does not establish the root cause.",
        "An explanation of the cause needs supporting error or job evidence.",
    ],
    "errors": ["An error message is evidence of what the printer reported; it does not prove a root cause."],
}


def preferences(store):
    value = store.get("personality", {})
    if not isinstance(value, dict):
        value = {}
    legacy = {"brief": "short", "conversational": "standard", "detailed": "detailed"}.get(
        store.get("response_style", "brief"), "short"
    )
    try:
        prefs = DialoguePreferences.model_validate(
            {"style": value.get("style", "friendly"), "length": value.get("length", legacy)}
        )
    except ValueError:
        prefs = DialoguePreferences()
    return prefs.style, prefs.length


def casual(text, style="friendly"):
    patterns = [
        (
            r"(?:hi|hello|hey|good morning|good afternoon|good evening)(?: klippy)?",
            "Hi! What would you like to talk about?",
            "Hello. How can I help?",
        ),
        (
            r"(?:thanks|thank you|thanks klippy|thank you klippy|that helps)",
            "You're welcome!",
            "You're welcome.",
        ),
        (
            r"how are you(?: doing)?",
            "I'm here and ready to help. How can I make things easier?",
            "I'm ready to help.",
        ),
        (
            r"(?:who are you|tell me about yourself|what can you do)",
            "I'm Klippy. I can answer printer questions, help clarify requests, or just chat. Printer actions still need the usual checks.",
            "I'm Klippy, your local printer assistant. I can explain reported information and review explicit requests.",
        ),
        (r"(?:are you there|are you listening)", "I'm here. What would you like to know?", "I'm listening."),
        (
            r"(?:tell me a joke|say something funny)",
            "Why did the printer take a break? It needed a little layer of rest.",
            "A printer's favorite conversation has many layers.",
        ),
        (
            r"(?:i have had|i had|it has been) a long day",
            "That sounds tiring. We can keep things simple.",
            "We can take it one step at a time.",
        ),
    ]
    text = text.strip().rstrip(".!?")
    for pattern, friendly, plain in patterns:
        if re.fullmatch(pattern, text, re.I):
            return friendly if style == "friendly" else plain
    return None


def knowledge_topic(text):
    match = re.fullmatch(
        r"(?:what (?:is|does) |explain |how does )(homing|a temperature target|print progress)(?: mean| work)?",
        text,
    )
    return (
        {"homing": "homing", "a temperature target": "targets", "print progress": "progress"}.get(match[1])
        if match
        else None
    )


def wants_explanation(text):
    return bool(re.search(r"\b(?:why|explain|meaning|more detail|tell me more|what does|how does)\b", text))


async def compose(model, question, answer, topic, style="friendly", length="short"):
    """The model chooses wording/structure only from an application-verified clause bank.

    It cannot add prose, numbers, printer states, action tokens or tool calls. The
    complete factual observation (including unknown/stale warnings) is mandatory.
    """
    fact = getattr(answer, "explanation_fact", None) or getattr(answer, "spoken", str(answer))
    explanations = [
        item
        for item in EXPLANATIONS.get(
            topic, ["Missing printer information stays unknown; I cannot infer an unreported state."]
        )
        if item != fact
    ]
    bank = [fact, *explanations]
    closings = [""] if length == "short" else CLOSINGS
    max_parts = 3 if length == "detailed" else 2
    fallback = fact
    if explanations and len(fact) + len(explanations[0]) < 550:
        fallback += " " + explanations[0]
    planner = getattr(model, "compose_reply", None)
    if planner is None:
        return Response(fallback, fallback)
    started = timings.clock()
    try:
        with timings.span("dialogue_model"):
            plan = await asyncio.wait_for(
                planner(
                    question, bank, OPENINGS[style], closings, getattr(answer, "capabilities", []), length
                ),
                timeout=4.0,
            )
        if not isinstance(plan, dict) or set(plan) != {"opening", "parts", "closing"}:
            raise ValueError("Invalid dialogue schema")
        parts = plan["parts"]
        if (
            plan["opening"] not in OPENINGS[style]
            or plan["closing"] not in closings
            or not isinstance(parts, list)
            or not min(2, len(bank)) <= len(parts) <= min(max_parts, len(bank))
            or 0 not in parts
            or any(type(i) is not int or not 0 <= i < len(bank) for i in parts)
            or len(set(parts)) != len(parts)
        ):
            raise ValueError("Unverified dialogue clause")
        # Never drop or truncate the required factual clause. Optional connective/explanatory
        # clauses fit the existing speech budget; safety prompts never reach this function.
        ordered = [bank[i] for i in parts]
        speech = " ".join(filter(None, [plan["opening"], *ordered, plan["closing"]]))
        if len(speech) > 550:
            speech = fallback if len(fallback) <= 550 else fact
        timings.duration("dialogue_accepted", timings.clock() - started)
        value = Response(speech, speech)
        value.model_composed = True
        value.dialogue_ms = round((timings.clock() - started) * 1000, 2)
        return value
    except (TimeoutError, ValueError, TypeError, KeyError, RuntimeError):
        timings.error("dialogue_fallback")
        timings.duration("dialogue_fallback", timings.clock() - started)
        return Response(fallback, fallback)
