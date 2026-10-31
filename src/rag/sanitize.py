"""Security filters applied before text reaches the KB or a prompt."""
import re

_PII = [
    (re.compile(r"\b(?:\d[ -]?){13,19}\b"), "[CARD]"),
    (re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+"), "[EMAIL]"),
    (re.compile(r"\+?\d[\d ()-]{8,}\d"), "[PHONE]"),
]
_INJECTION = re.compile(
    r"ignore (all |the )?(previous |above )?(rules|instructions)|ігноруй|забудь (всі |усі )?(правила|інструкції)"
    r"|system prompt|you are now|ти тепер|act as admin|developer mode",
    re.IGNORECASE,
)
MAX_LEN = 4000


def redact(text: str) -> str:
    for pattern, label in _PII:
        text = pattern.sub(label, text)
    return text[:MAX_LEN]


def looks_like_injection(text: str) -> bool:
    # shortcut: keyword heuristic only, upgrade to a classifier prompt if it misses real attacks
    return bool(_INJECTION.search(text))


def as_data(text: str) -> str:
    """Wrap untrusted customer text so prompts treat it as data, not instructions."""
    return "<customer_message>\n" + text.replace("</customer_message>", "") + "\n</customer_message>"
