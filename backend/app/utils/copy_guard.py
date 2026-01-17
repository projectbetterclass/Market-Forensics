"""Copy guardrails for ensuring non-advice/non-prediction language."""

from typing import List, Optional


# Forbidden phrases - must never appear in output
FORBIDDEN_PHRASES = [
    "crash coming",
    "guaranteed",
    "smart money knows",
    "obvious opportunity",
    "must rebound",
    "will go up",
    "will go down",
    "should buy",
    "should sell",
    "recommend buying",
    "recommend selling",
    "buy signal",
    "sell signal",
    "top pick",
    "can't miss",
    "safe bet",
    "volatility is low so risk is low",
    "below the 200-day means sell",
    "vix spike means buy",
    "golden cross",
    "death cross",
    "definitely will",
    "certainly going to",
    "profit guaranteed"
]

# Allowed phrases that should be used instead
ALLOWED_PHRASES = [
    "historically",
    "associated with",
    "risk has increased",
    "outcomes varied",
    "similar conditions",
    "pattern suggests",
    "evidence indicates",
    "may be related to",
    "contextual signal",
    "used to understand regime",
    "not a timing signal"
]


def check_text_for_violations(text: str) -> Optional[str]:
    """
    Check text for forbidden phrases.
    
    Args:
        text: Text to check
    
    Returns:
        The forbidden phrase found, or None if clean
    """
    text_lower = text.lower()
    
    for phrase in FORBIDDEN_PHRASES:
        if phrase in text_lower:
            return phrase
    
    return None


def validate_text(text: str, context: str = "output") -> str:
    """
    Validate text and raise error if forbidden phrases found.
    
    Args:
        text: Text to validate
        context: Description of what's being validated
    
    Returns:
        The original text if valid
    
    Raises:
        ValueError: If forbidden phrases detected
    """
    violation = check_text_for_violations(text)
    
    if violation:
        raise ValueError(
            f"Language guardrail violation in {context}: "
            f"forbidden phrase '{violation}' detected. "
            f"This tool provides historical context and pattern recognition, "
            f"not predictions or advice."
        )
    
    return text


def sanitize_interpretation(raw_text: str) -> str:
    """
    Sanitize interpretation text to ensure compliant language.
    
    This is a softer approach - rather than raising an error,
    it attempts to replace problematic patterns.
    
    Args:
        raw_text: Raw interpretation text
    
    Returns:
        Sanitized text
    """
    text = raw_text
    
    # Replace common problematic patterns
    replacements = [
        ("this means you should", "this has historically been associated with"),
        ("you should consider", "one might observe"),
        ("this is a buy signal", "this is a contextual signal"),
        ("this is a sell signal", "this is a contextual signal"),
        ("the market will", "the market has historically"),
        ("prices will", "prices have historically"),
        ("expect ", "historically, similar conditions have shown "),
        ("definitely ", "historically "),
        ("certainly ", "in similar conditions, "),
    ]
    
    text_lower = text.lower()
    for old, new in replacements:
        if old in text_lower:
            # Case-insensitive replace
            import re
            text = re.sub(re.escape(old), new, text, flags=re.IGNORECASE)
    
    return text


def get_standard_disclaimer() -> str:
    """Get standard disclaimer text."""
    return (
        "These indicators provide historical context and regime awareness. "
        "They do not predict market direction or recommend actions."
    )


def get_vix_warning() -> str:
    """Get standard VIX warning."""
    return (
        "Very low volatility has historically preceded instability; "
        "high volatility reflects fear already present. "
        "This is a contextual signal, not a timing indicator."
    )


def get_ma_disclaimer() -> str:
    """Get standard moving average disclaimer."""
    return (
        "Moving averages indicate trend health, not trading signals. "
        "Price position relative to averages provides context about momentum, "
        "not direction predictions."
    )


def get_pattern_warning() -> str:
    """Get standard pattern warning."""
    return (
        "Similar patterns have led to varied outcomes in the past. "
        "Historical patterns do not predict future results."
    )
