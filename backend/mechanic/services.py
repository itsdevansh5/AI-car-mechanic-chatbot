import json
import os
import re
from typing import Any
from google import genai
from google.genai import types
from .models import Conversation, Diagnosis

CAR_TERMS = {
    "car", "vehicle", "engine", "brake", "brakes", "braking", "battery", "tyre", "tire", "wheel",
    "steering", "suspension", "clutch", "gear", "transmission", "oil", "coolant", "radiator", "alternator",
    "starter", "spark plug", "sparkplug", "dashboard", "check engine", "ac", "air conditioning", "mileage",
    "fuel", "diesel", "petrol", "gasoline", "overheating", "noise", "clicking", "knocking", "smoke",
    "vibration", "stall", "starting", "headlight", "wiper", "horn", "mechanic", "service", "automobile",
}

FOLLOW_UPS = [
    ("noise", "When does the noise happen: while starting, accelerating, braking, turning, or at idle?"),
    ("overheat", "Is the temperature gauge above normal, and do you see coolant leaking or steam?"),
    ("brake", "Does the symptom happen during braking, and do you feel vibration, pulling, or a soft pedal?"),
    ("battery", "Does the engine crank slowly, click without starting, or start normally after a jump?"),
    ("vibration", "At what speed or operating condition do you feel the vibration, and does it change while braking?"),
]


def get_conversation(session_id=None):
    if session_id:
        try:
            return Conversation.objects.get(session_id=session_id)
        except (Conversation.DoesNotExist, ValueError):
            pass
    return Conversation.objects.create()


def is_automotive(text: str) -> bool:
    lower = text.lower()
    return any(term in lower for term in CAR_TERMS)


def deterministic_reply(text: str, conversation: Conversation) -> str | None:
    lower = text.lower().strip()
    if lower in {"hi", "hello", "hey", "hey there", "good morning", "good evening"}:
        return "Hello. I can help troubleshoot car and mechanical problems. Tell me the symptom, when it happens, and your car's make/model/year if you know it."
    if lower in {"thanks", "thank you", "thx"}:
        return "You're welcome. If the symptom changes or you get a warning light, tell me and I can reassess it."
    if "book" in lower and "mechanic" in lower:
        return "Once we have a diagnosis, I can help you create a mechanic booking."
    if not is_automotive(lower):
        return "I’m a car mechanic assistant, so I can only help with vehicle, engine, electrical, braking, suspension, tyre, maintenance, and related mechanical issues."
    for keyword, question in FOLLOW_UPS:
        if keyword in lower and conversation.messages.count() < 8:
            return question
    return None


def enough_for_diagnosis(conversation: Conversation) -> bool:
    user_messages = conversation.messages.filter(role="user").count()
    text = " ".join(conversation.messages.filter(role="user").values_list("content", flat=True)).lower()
    return user_messages >= 2 and any(t in text for t in CAR_TERMS)


def _extract_json(text: str) -> dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group(0))
        raise


def _fallback_diagnosis(conversation: Conversation) -> dict[str, Any]:
    text = " ".join(conversation.messages.filter(role="user").values_list("content", flat=True)).lower()
    if "brake" in text or "braking" in text:
        return {
            "summary": "The symptoms are consistent with a braking-system issue, but the exact component cannot be confirmed remotely.",
            "likely_causes": ["Worn brake pads", "Uneven/warped brake rotor", "Brake hardware or caliper issue"],
            "confidence": 55,
            "checks": ["Check pad thickness", "Inspect rotor surface", "Check for pulling or abnormal pedal feel"],
            "recommended_service": "Brake inspection and measurement of pads/rotors",
            "urgency": "high",
            "safety_notes": ["If braking distance has increased, the pedal feels soft, or the car pulls strongly, avoid driving and arrange inspection."]
        }
    if "battery" in text or "click" in text or "starting" in text:
        return {
            "summary": "The starting symptom may be related to battery state, terminals, starter circuit, or charging system.",
            "likely_causes": ["Weak battery", "Loose/corroded battery connection", "Starter circuit issue"],
            "confidence": 50,
            "checks": ["Check battery terminals", "Measure battery voltage", "Observe whether lights dim heavily during start"],
            "recommended_service": "Battery and starting-system electrical test",
            "urgency": "medium",
            "safety_notes": ["Do not repeatedly crank the engine for long periods if the starter or cables are overheating."]
        }
    return {
        "summary": "A remote diagnosis cannot confirm the failed component yet. The next step is a basic inspection based on the reported symptom.",
        "likely_causes": ["Mechanical wear", "Electrical/connection issue", "Fluid or maintenance-related issue"],
        "confidence": 35,
        "checks": ["Record when the symptom occurs", "Check warning lights", "Inspect visible leaks or damaged components"],
        "recommended_service": "General diagnostic inspection",
        "urgency": "medium",
        "safety_notes": ["Do not continue driving if there is smoke, fuel leakage, severe overheating, or loss of braking/steering control."]
    }


def generate_diagnosis(conversation: Conversation) -> dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return _fallback_diagnosis(conversation)

    client = genai.Client(api_key=api_key)
    model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    history = list(conversation.messages.order_by("created_at").values("role", "content"))[-12:]
    text = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in history)

    parts: list[Any] = [types.Part.from_text(text=f"Conversation:\n{text}")]
    for media in conversation.media.order_by("created_at")[:3]:
        try:
            data = media.file.read()
            if len(data) <= 10 * 1024 * 1024:
                parts.append(types.Part.from_bytes(data=data, mime_type=media.mime_type))
        except Exception:
            continue

    prompt = """You are a senior automobile technician. Diagnose ONLY vehicle/mechanical problems.
Use the conversation and any attached media. Do not invent observations that are not visible/audible.
Ask for inspection when remote evidence is insufficient. This is not a substitute for a physical inspection.
Return ONLY valid JSON with exactly these keys:
summary (string), likely_causes (array of strings), confidence (integer 0-100), checks (array of strings),
recommended_service (string), urgency (one of low, medium, high), safety_notes (array of strings).
Prioritize safety. High urgency is appropriate for potential loss of braking, steering, severe overheating, fuel leakage, or other immediate hazards."""
    try:
        response = client.models.generate_content(model=model, contents=[types.Content(role="user", parts=[types.Part.from_text(text=prompt), *parts])])
        data = _extract_json(response.text)
        return {
            "summary": str(data.get("summary", "")),
            "likely_causes": list(data.get("likely_causes", []))[:5],
            "confidence": max(0, min(100, int(data.get("confidence", 50)))),
            "checks": list(data.get("checks", []))[:6],
            "recommended_service": str(data.get("recommended_service", "Diagnostic inspection")),
            "urgency": data.get("urgency", "medium") if data.get("urgency") in {"low", "medium", "high"} else "medium",
            "safety_notes": list(data.get("safety_notes", []))[:5],
        }
    except Exception:
        return _fallback_diagnosis(conversation)


def save_diagnosis(conversation: Conversation) -> Diagnosis:
    data = generate_diagnosis(conversation)
    return Diagnosis.objects.create(conversation=conversation, **data)
