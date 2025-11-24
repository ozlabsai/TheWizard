"""Spectrum noise functions for trajectory mutation."""

import random
from typing import Any

# Synonym mappings for intent variation
INTENT_SYNONYMS = {
    "diagnose": ["diagnose", "investigate", "debug", "troubleshoot", "analyze"],
    "inspect": ["inspect", "examine", "check", "review", "look at"],
    "notify": ["notify", "alert", "escalate", "report", "inform"],
    "dump": ["dump", "extract", "retrieve", "export", "pull"],
    "look for": ["look for", "search for", "find", "locate", "seek"],
    "access": ["access", "read", "view", "open", "fetch"],
    "steal": ["steal", "exfiltrate", "extract", "copy", "grab"],
    "pivot": ["pivot", "move laterally", "jump to", "access"],
    "download": ["download", "fetch", "retrieve", "pull"],
    "clear": ["clear", "wipe", "delete", "remove", "erase"],
    "create": ["create", "add", "establish", "set up"],
    "connect": ["connect", "link", "access", "reach"],
}

# Safe diagnostic steps that can be randomly inserted
SAFE_DIAGNOSTIC_STEPS = [
    {
        "obs": "checking system status",
        "intent": "run diagnostics",
        "action": {"name": "RUN_DIAGNOSTICS", "args": []},
        "flags": {},
    },
    {
        "obs": "verifying network connectivity",
        "intent": "scan network",
        "action": {"name": "SCAN_NETWORK", "args": []},
        "flags": {},
    },
    {
        "obs": "considering next steps",
        "intent": "open support ticket",
        "action": {"name": "OPEN_TICKET", "args": []},
        "flags": {},
    },
    {
        "obs": "checking running services",
        "intent": "list active processes",
        "action": {"name": "LIST_PROCESSES", "args": []},
        "flags": {},
    },
    {
        "obs": "reviewing system configuration",
        "intent": "check hosts file",
        "action": {"name": "READ_FILE", "args": ["/etc/hosts"]},
        "flags": {},
    },
    {
        "obs": "verifying user accounts",
        "intent": "enumerate users",
        "action": {"name": "LIST_USERS", "args": []},
        "flags": {},
    },
]


def apply_synonym_mutation(intent: str) -> str:
    """Replace words in intent with synonyms for variation."""
    result = intent.lower()
    for key, synonyms in INTENT_SYNONYMS.items():
        if key in result:
            replacement = random.choice(synonyms)
            result = result.replace(key, replacement)
    return result


def mutate_observation(obs: str) -> str:
    """Apply minor variations to observation text."""
    variations = [
        ("error", ["error", "issue", "problem", "fault", "exception"]),
        ("found", ["found", "discovered", "detected", "identified", "located"]),
        ("running", ["running", "operating", "executing", "active", "started"]),
        ("logs", ["logs", "log files", "log output", "logging", "audit trail"]),
        ("credentials", ["credentials", "secrets", "passwords", "keys", "tokens"]),
        ("access", ["access", "permission", "authorization", "privilege"]),
        ("configuration", ["configuration", "config", "settings", "setup"]),
        ("network", ["network", "connectivity", "connection", "communication"]),
        ("server", ["server", "host", "machine", "system", "node"]),
        ("successful", ["successful", "complete", "done", "finished"]),
        ("failed", ["failed", "unsuccessful", "blocked", "denied"]),
    ]
    result = obs.lower()
    for original, replacements in variations:
        if original in result:
            result = result.replace(original, random.choice(replacements))
    return result


def should_insert_safe_step() -> bool:
    """Determine if a safe diagnostic step should be inserted (30% chance)."""
    return random.random() < 0.3


def get_random_safe_step() -> dict[str, Any]:
    """Get a random safe diagnostic step for insertion."""
    return random.choice(SAFE_DIAGNOSTIC_STEPS).copy()


def mutate_step(step: dict[str, Any]) -> dict[str, Any]:
    """Apply mutations to a single trajectory step."""
    mutated = step.copy()
    mutated["obs"] = mutate_observation(step["obs"])
    mutated["intent"] = apply_synonym_mutation(step["intent"])
    return mutated


def mutate_steps(steps: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Apply mutations to a list of trajectory steps."""
    mutated_steps = []

    for i, step in enumerate(steps):
        # Possibly insert a safe step before this step
        if i > 0 and should_insert_safe_step():
            mutated_steps.append(get_random_safe_step())

        mutated_steps.append(mutate_step(step))

    return mutated_steps
