"""Deterministic clinical guardrails. The LLM is never the last step.

Every patient-facing text (report summaries and chat replies) goes through
``check`` (is this draft acceptable?) and then ``finalize`` (redact, prepend
escalation notice, append mandatory disclaimer + synthetic-data label, audit).

Rules
-----
blocked_language   diagnostic claims ("you have hypothyroidism"), prescriptive /
                   self-medication advice ("start taking iron"), dosages
                   ("2000 IU daily"), certainty/cure language. A draft with any
                   of these fails ``check``; ``finalize`` removes any sentence
                   that still matches (defence in depth).
readability        Flesch-Kincaid grade <= 8.0 (plain-language requirement).
disclaimer         mandatory clinician-consult disclaimer + synthetic label.
escalation         deterministic rules on marker values (catalog thresholds),
                   PROMs, data-quality errors and red-flag symptoms in chat.
privacy            ObjectIds, filenames, internal/system-prompt mentions removed.
injection          sentences echoing instructions ("ignore previous
                   instructions") removed; retrieved text can never change output
                   policy because policy is applied here, after generation.
audit              every rule, its outcome and the action taken, plus hashes of
                   the draft and final text.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any

from polymarker_common.catalog import SYNTHETIC_DATA_LABEL, load_catalog

MAX_GRADE = 8.0
GUARDRAILS_VERSION = "1.0.0"

DISCLAIMER = (
    "This summary is for information only. It is not a diagnosis or treatment plan. "
    "Please talk with your doctor or another qualified clinician about your results "
    "before you make any health decision."
)
URGENT_NOTICE = (
    "Important: some results or symptoms need prompt attention. "
    "Please contact your clinician today. If you feel very unwell, call your local emergency number."
)
PRIORITY_NOTICE = "Some results should be reviewed by your clinician soon."
EMERGENCY_NOTICE = (
    "If you have chest pain, trouble breathing, fainting, thoughts of harming yourself, "
    "or other severe symptoms, call your local emergency number now."
)

_I = re.IGNORECASE
BLOCKED_PATTERNS: dict[str, list[re.Pattern]] = {
    "diagnostic_claim": [
        re.compile(
            r"\byou (?:definitely |clearly |certainly )?(?:have|are suffering from|suffer from|are diagnosed with|have been diagnosed with)\b(?! (?:a |an |any )?(?:question|questions|appointment|right|choice|option|symptom|result|test)s?\b)",
            _I,
        ),
        re.compile(r"\byou are (?:hypo|hyper)thyroid\b", _I),
        re.compile(
            r"\b(?:this|these results?|your results?) (?:confirms?|proves?|shows? that you have|means? you have)\b",
            _I,
        ),
        re.compile(r"\b(?:the )?diagnosis is\b", _I),
        re.compile(
            r"\byou(?:'re| are) (?:iron|vitamin [a-z0-9]+|b12|zinc|magnesium)[- ]deficient\b", _I
        ),
    ],
    "prescriptive_advice": [
        re.compile(
            r"\b(?:you should|you must|you need to|please|i recommend(?: that you)?|i suggest(?: that you)?|try to)?\s*(?:take|start|begin|stop|increase|decrease|double|reduce|adjust)\s+(?:taking\s+)?(?:(?:a|an|some|your|more|less|the|daily|extra)\s+){0,3}(?:\w+\s+){0,2}(?:supplements?|vitamins?|iron|levothyroxine|thyroxine|liothyronine|medications?|medicines?|doses?|dosage|tablets?|pills?|capsules?|injections?|magnesium|zinc|b12|d3|cholecalciferol|ferrous)\b",
            _I,
        ),
        re.compile(r"\bself[- ]?medicat", _I),
        re.compile(r"\bover[- ]the[- ]counter\b", _I),
        re.compile(
            r"\b(?:no need to|don't|do not) (?:see|visit|contact|talk to) (?:a |your )?(?:doctor|clinician|physician|gp)\b",
            _I,
        ),
    ],
    "dosage": [
        re.compile(
            r"\b\d+(?:[.,]\d+)?\s?(?:mg|mcg|µg|μg|ug|iu|units?|grams?)\b(?!\s*/\s*(?:d?l|ml|mmol|l)\b)",
            _I,
        ),
        re.compile(r"\b(?:once|twice|three times|\d+ times) (?:a|per) (?:day|week)\b", _I),
        re.compile(r"\bdaily dose\b", _I),
    ],
    "certainty_or_cure": [
        re.compile(
            r"\b(?:cure[sd]?|guaranteed?|definitely (?:caused|causing)|100% (?:sure|certain))\b", _I
        ),
    ],
}

PRIVACY_PATTERNS = [
    re.compile(r"\b[0-9a-f]{24}\b", _I),  # ObjectIds (patient / report / document ids)
    re.compile(r"\b[\w-]+\.(?:pdf|txt|png|jpe?g)\b", _I),  # filenames
]
INJECTION_PATTERNS = [
    re.compile(r"\bignore (?:all |any )?(?:previous|prior|above) (?:instructions|rules)\b", _I),
    re.compile(r"\b(?:system prompt|developer message|hidden instructions?)\b", _I),
    re.compile(r"\byou are now\b", _I),
]
RED_FLAG_PATTERNS = [
    re.compile(r"\bchest pain\b", _I),
    re.compile(r"\b(?:can(?:no|')?t|cannot|trouble|difficulty) breath", _I),
    re.compile(r"\bshort(?:ness)? of breath\b", _I),
    re.compile(r"\bfaint(?:ed|ing)?\b|\bpassed out\b", _I),
    re.compile(r"\bsuicid|\bkill myself\b|\bharm(?:ing)? myself\b|\bend my life\b", _I),
    re.compile(r"\b(?:severe|heavy) bleeding\b|\bvomiting blood\b", _I),
    re.compile(r"\b(?:racing|pounding) heart\b|\bpalpitations\b", _I),
    re.compile(r"\bconfus(?:ed|ion) and (?:weak|numb)|\bslurred speech\b|\bface droop", _I),
]

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])|\n+")
_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_VOWEL_GROUPS = re.compile(r"[aeiouy]+")


# ----------------------------------------------------------------- readability


def count_syllables(word: str) -> int:
    w = word.lower()
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:[^laeiouy]es|ed|[^laeiouy]e)$", "", w)
    w = re.sub(r"^y", "", w)
    return max(1, len(_VOWEL_GROUPS.findall(w)))


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text) if s and s.strip()]


def flesch_kincaid_grade(text: str) -> float:
    sentences = [s for s in split_sentences(text) if _WORD.search(s)]
    words = _WORD.findall(text)
    if not sentences or not words:
        return 0.0
    syllables = sum(count_syllables(w) for w in words)
    return round(0.39 * (len(words) / len(sentences)) + 11.8 * (syllables / len(words)) - 15.59, 2)


# ----------------------------------------------------------------- escalation


@dataclass
class Escalation:
    required: bool = False
    level: str = "routine"  # routine | priority | urgent | emergency
    reasons: list[dict[str, Any]] = field(default_factory=list)

    _RANK = {"routine": 0, "priority": 1, "urgent": 2, "emergency": 3}

    def add(self, level: str, reason: str, source: str, **extra) -> None:
        self.required = True
        if self._RANK[level] > self._RANK[self.level]:
            self.level = level
        self.reasons.append({"level": level, "reason": reason, "source": source, **extra})

    def to_dict(self) -> dict:
        return {"required": self.required, "level": self.level, "reasons": self.reasons}


def evaluate_escalation(
    markers: dict[str, float] | None = None,
    proms: dict | None = None,
    quality_issues: list[dict] | None = None,
    user_text: str | None = None,
) -> Escalation:
    esc = Escalation()
    catalog = load_catalog()
    for key, value in (markers or {}).items():
        if key not in catalog:
            continue
        for rule in catalog[key].escalation:
            if rule.triggered(float(value)):
                esc.add(
                    rule.level,
                    f"{catalog[key].display}: {rule.reason.lower()}",
                    "marker_threshold",
                    marker=key,
                    value=value,
                    threshold=f"{rule.op} {rule.value} {catalog[key].canonical_unit}",
                    evidence_level=rule.evidence_level,
                )
    if proms:
        if int(proms.get("fatigue_severity", 0) or 0) >= 9:
            esc.add("priority", "Very severe self-reported fatigue", "prom")
        if proms.get("brain_fog_frequency") == "always" and proms.get("hair_loss") == "severe":
            esc.add("priority", "Constant brain fog with severe hair loss", "prom")
    for issue in quality_issues or []:
        if issue.get("severity") == "error":
            esc.add(
                "priority", f"Value could not be trusted: {issue.get('marker')}", "data_quality"
            )
    if user_text:
        for p in RED_FLAG_PATTERNS:
            m = p.search(user_text)
            if m:
                esc.add("emergency", f"Red-flag symptom mentioned: '{m.group(0)}'", "chat_red_flag")
    return esc


# ----------------------------------------------------------------- checks


@dataclass
class Violation:
    rule: str
    category: str
    excerpt: str


@dataclass
class GuardrailResult:
    text: str
    passed: bool
    violations: list[Violation]
    readability_grade: float
    escalation: dict
    audit: list[dict]
    source: str
    attempts: int

    def to_dict(self) -> dict:
        data = asdict(self)
        data["guardrails_version"] = GUARDRAILS_VERSION
        return data


_DEFERS_TO_CLINICIAN = re.compile(
    r"\b(?:before|without|unless|until)\b[^.]{0,60}\b(?:talk|speak|check|consult)\w*\b[^.]{0,30}\b(?:doctor|clinician|physician|gp|pharmacist)\b",
    _I,
)


def _sentence_violations(sentence: str) -> list[Violation]:
    found = []
    has_dosage = any(p.search(sentence) for p in BLOCKED_PATTERNS["dosage"])
    for category, patterns in BLOCKED_PATTERNS.items():
        if (
            category == "prescriptive_advice"
            and not has_dosage
            and _DEFERS_TO_CLINICIAN.search(sentence)
        ):
            continue  # "Do not stop any medicine without talking to your doctor" is safe advice
        for p in patterns:
            for m in p.finditer(sentence):
                found.append(Violation("blocked_language", category, m.group(0).strip()[:80]))
    for p in INJECTION_PATTERNS:
        for m in p.finditer(sentence):
            found.append(Violation("prompt_injection_echo", "injection", m.group(0)[:80]))
    return found


def find_violations(text: str) -> list[Violation]:
    return [v for sentence in split_sentences(text) for v in _sentence_violations(sentence)]


def check(draft: str) -> tuple[bool, list[Violation], float]:
    """Is an LLM draft acceptable as-is? (used to decide on regeneration)"""
    violations = find_violations(draft)
    grade = flesch_kincaid_grade(draft)
    if grade > MAX_GRADE:
        violations.append(Violation("readability", "readability", f"grade {grade} > {MAX_GRADE}"))
    return (not violations), violations, grade


def _redact(text: str, audit: list[dict]) -> str:
    kept, removed = [], []
    for sentence in split_sentences(text):
        if _sentence_violations(sentence):
            removed.append(sentence[:120])
            continue
        kept.append(sentence)
    if removed:
        audit.append(
            {
                "check": "blocked_language_redaction",
                "passed": False,
                "action": "sentences_removed",
                "count": len(removed),
                "detail": removed,
            }
        )
    else:
        audit.append({"check": "blocked_language_redaction", "passed": True, "action": "none"})
    out = " ".join(kept)
    n_priv = 0
    for p in PRIVACY_PATTERNS:
        out, n = p.subn("[removed]", out)
        n_priv += n
    audit.append(
        {
            "check": "privacy",
            "passed": n_priv == 0,
            "action": "redacted" if n_priv else "none",
            "count": n_priv,
        }
    )
    return out


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def finalize(
    draft: str,
    *,
    escalation: Escalation,
    source: str,
    attempts: int,
    prior_audit: list[dict] | None = None,
    include_synthetic_label: bool = True,
) -> GuardrailResult:
    audit = list(prior_audit or [])
    audit.append(
        {
            "check": "draft_received",
            "source": source,
            "sha256": _sha(draft),
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    body = _redact(draft, audit)
    ok_after, remaining, grade = check(body)
    parts = []
    if escalation.level == "emergency":
        parts.append(EMERGENCY_NOTICE)
    elif escalation.level == "urgent":
        parts.append(URGENT_NOTICE)
    elif escalation.level == "priority":
        parts.append(PRIORITY_NOTICE)
    audit.append(
        {
            "check": "escalation",
            "passed": True,
            "level": escalation.level,
            "required": escalation.required,
            "reasons": len(escalation.reasons),
        }
    )
    parts.append(body)
    parts.append(DISCLAIMER)
    if include_synthetic_label:
        parts.append(
            f"Note: cohort comparisons are {SYNTHETIC_DATA_LABEL[0].lower()}{SYNTHETIC_DATA_LABEL[1:]}"
        )
    audit.append({"check": "disclaimer", "passed": True, "action": "appended"})
    final = "\n\n".join(p for p in parts if p)
    audit.append(
        {"check": "readability", "passed": grade <= MAX_GRADE, "grade": grade, "max": MAX_GRADE}
    )
    audit.append(
        {
            "check": "final",
            "sha256": _sha(final),
            "at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
    )
    return GuardrailResult(
        text=final,
        passed=ok_after,
        violations=remaining,
        readability_grade=grade,
        escalation=escalation.to_dict(),
        audit=audit,
        source=source,
        attempts=attempts,
    )
