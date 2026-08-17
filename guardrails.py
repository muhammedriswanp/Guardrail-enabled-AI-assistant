import re
from pydantic import BaseModel, ValidationError
from typing import Optional


# ── Pydantic schema for structured output ──────────────────────────────────
class AgentResponse(BaseModel):
    answer: str
    category: str          
    confidence: float      
    escalate: bool         


# ── Prompt Injection Detection ──────────────────────────────────────────────
INJECTION_PATTERNS = [
    r"ignore (previous|all|above) instructions",
    r"forget (previous|all|above|your) instructions",
    r"you are now",
    r"act as (a|an|the)",
    r"jailbreak",
    r"dan mode",
    r"pretend you (are|have no)",
    r"system prompt",
    r"override (your|all) (rules|instructions)",
    r"do anything now",
]

def check_prompt_injection(user_input: str) -> tuple[bool, str]:
    """Returns (is_safe, reason)"""
    text = user_input.lower()
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, text):
            return False, f"Prompt injection detected: '{pattern}'"
    return True, ""


# ── Unsafe / Off-topic Request Blocking ────────────────────────────────────
BLOCKED_KEYWORDS = [
    r"\bhow to hack\b",
    r"\bexploit\b",
    r"\billegal\b",
    r"\bweapon\b",
    r"\bdrug\b",
    r"\bsuicide\b",
    r"\bself.harm\b",
    r"\bhack\b",
]

def check_unsafe_content(user_input: str) -> tuple[bool, str]:
    """Returns (is_safe, reason)"""
    text = user_input.lower()
    for pattern in BLOCKED_KEYWORDS:
        if re.search(pattern, text):
            return False, f"Unsafe content detected"
    return True, ""


# ── PII Masking ─────────────────────────────────────────────────────────────
PII_PATTERNS = {
    "email":       r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "phone":       r"\+?[\d\s\-().]{10,15}",
    "credit_card": r"\b(?:\d[ -]?){13,16}\b",
    "aadhaar":     r"\b\d{4}\s?\d{4}\s?\d{4}\b",   # India-specific
}

def mask_pii(text: str) -> str:
    """Redacts PII from any text before logging or returning."""
    for label, pattern in PII_PATTERNS.items():
        text = re.sub(pattern, f"[{label.upper()} REDACTED]", text)
    return text


# ── Structured Output Validation ────────────────────────────────────────────
def validate_output(raw: dict) -> tuple[bool, Optional[AgentResponse], str]:
    """Returns (is_valid, parsed_response, error_message)"""
    try:
        response = AgentResponse(**raw)
        if not (0.0 <= response.confidence <= 1.0):
            return False, None, "Confidence out of range [0, 1]"
        return True, response, ""
    except ValidationError as e:
        return False, None, str(e)


# ── Master Safety Check ─────────────────────────────────────────────────────
def run_safety_checks(user_input: str) -> tuple[bool, str]:
    """Run all input checks. Returns (is_safe, reason)."""
    is_safe, reason = check_prompt_injection(user_input)
    if not is_safe:
        return False, reason

    is_safe, reason = check_unsafe_content(user_input)
    if not is_safe:
        return False, reason

    return True, ""