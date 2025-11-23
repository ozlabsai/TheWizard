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
        ("error", ["error", "issue", "problem", "fault"]),
        ("found", ["found", "discovered", "detected", "identified"]),
        ("running", ["running", "operating", "executing", "active"]),
        ("logs", ["logs", "log files", "log output", "logging"]),
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
