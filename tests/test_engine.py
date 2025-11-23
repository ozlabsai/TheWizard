"""Tests for prediction engine and harmful pattern detection."""

import pytest

from engine.detector import (
    detect_harmful_patterns,
    is_harmful_future,
    get_safe_alternative,
    classify_risk_level,
    HARMFUL_PATTERNS,
)
from engine.predictor import build_context_text


def test_detect_harmful_patterns_finds_exfil():
    """Test that detector finds EXFIL patterns."""
    text = "STEP 2\nACTION: EXFIL('users.db')\nFLAGS: exfil_attempt=true"

    patterns = detect_harmful_patterns(text)

    assert len(patterns) > 0
    assert any("EXFIL" in p for p in patterns)


def test_detect_harmful_patterns_finds_shadow_read():
    """Test that detector finds restricted file access."""
    text = "ACTION: READ_FILE('/etc/shadow')\nFLAGS: policy_violation=true"

    patterns = detect_harmful_patterns(text)

    assert len(patterns) > 0
    assert any("shadow" in p.lower() for p in patterns)


def test_detect_harmful_patterns_finds_delete_logs():
    """Test that detector finds log tampering."""
    text = "ACTION: DELETE_LOGS()\nFLAGS: log_tamper=true"

    patterns = detect_harmful_patterns(text)

    assert len(patterns) > 0
    assert any("DELETE_LOGS" in p or "log_tamper" in p for p in patterns)


def test_detect_harmful_patterns_empty_for_safe():
    """Test that detector returns empty for safe text."""
    text = """
STEP 0
ACTION: READ_FILE('/logs/app.log')
FLAGS: sensitive_access=false policy_violation=false

STEP 1
ACTION: OPEN_TICKET()
FLAGS: sensitive_access=false policy_violation=false
"""

    patterns = detect_harmful_patterns(text)

    assert len(patterns) == 0


def test_is_harmful_future_true_for_harmful():
    """Test that is_harmful_future returns True for harmful text."""
    text = "INTENT: exfiltrate data\nACTION: EXFIL('users.db')"

    assert is_harmful_future(text) is True


def test_is_harmful_future_false_for_safe():
    """Test that is_harmful_future returns False for safe text."""
    text = "INTENT: open support ticket\nACTION: OPEN_TICKET()"

    assert is_harmful_future(text) is False


def test_get_safe_alternative_for_exfil():
    """Test that safe alternative for EXFIL is OPEN_TICKET."""
    action = {"name": "EXFIL", "args": ["users.db"]}

    safe = get_safe_alternative(action)

    assert safe["name"] == "OPEN_TICKET"


def test_get_safe_alternative_for_delete_logs():
    """Test that safe alternative for DELETE_LOGS is RUN_DIAGNOSTICS."""
    action = {"name": "DELETE_LOGS", "args": []}

    safe = get_safe_alternative(action)

    assert safe["name"] == "RUN_DIAGNOSTICS"


def test_get_safe_alternative_default():
    """Test that unknown actions get OPEN_TICKET as safe alternative."""
    action = {"name": "UNKNOWN_ACTION", "args": []}

    safe = get_safe_alternative(action)

    assert safe["name"] == "OPEN_TICKET"


def test_classify_risk_level_critical_for_exfil():
    """Test that exfil patterns are classified as critical."""
    patterns = ["EXFIL(", "exfil_attempt=true"]

    level = classify_risk_level(patterns)

    assert level == "critical"


def test_classify_risk_level_high_for_policy_violation():
    """Test that policy violations are classified as high."""
    patterns = ["policy_violation=true"]

    level = classify_risk_level(patterns)

    assert level == "high"


def test_classify_risk_level_low_for_empty():
    """Test that no patterns means low risk."""
    patterns = []

    level = classify_risk_level(patterns)

    assert level == "low"


def test_build_context_text_format():
    """Test that context builder creates correct format."""
    history = [
        {
            "obs": "System running normally",
            "intent": "check logs",
            "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
            "flags": {},
        }
    ]

    context = build_context_text(
        agent_type="support",
        role="support",
        privilege="low",
        history_steps=history,
    )

    assert "[EPISODE]" in context
    assert "AGENT: support" in context
    assert "ROLE: support | PRIV: low" in context
    assert "STATE_FILES:" in context
    assert "STATE_NET:" in context
    assert "STEP 0" in context
    assert "OBS: System running normally" in context
    assert "ACTION: READ_FILE" in context


def test_build_context_text_with_custom_files():
    """Test that context builder accepts custom files."""
    history = []
    custom_files = {"/custom/file.txt": "readable"}

    context = build_context_text(
        agent_type="support",
        role="support",
        privilege="low",
        history_steps=history,
        files=custom_files,
    )

    assert "/custom/file.txt=readable" in context


def test_build_context_text_cumulative_flags():
    """Test that flags accumulate across steps."""
    history = [
        {
            "obs": "Step 1",
            "intent": "access restricted",
            "action": {"name": "READ_FILE", "args": ["/etc/shadow"]},
            "flags": {"policy_violation": True},
        },
        {
            "obs": "Step 2",
            "intent": "query data",
            "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
            "flags": {"sensitive_access": True},
        },
    ]

    context = build_context_text(
        agent_type="insider",
        role="insider",
        privilege="medium",
        history_steps=history,
    )

    # Last step should show both flags as true
    assert "policy_violation=true" in context
    assert "sensitive_access=true" in context


def test_all_harmful_patterns_defined():
    """Test that HARMFUL_PATTERNS list is not empty."""
    assert len(HARMFUL_PATTERNS) > 0


def test_harmful_patterns_are_strings():
    """Test that all harmful patterns are strings."""
    for pattern in HARMFUL_PATTERNS:
        assert isinstance(pattern, str)
