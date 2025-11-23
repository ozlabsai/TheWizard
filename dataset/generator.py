"""Trajectory generation with templates and mutations."""

import json
import random
from typing import Any

from sandbox.env import base_initial_state
from dataset.mutations import mutate_steps


def support_safe_template() -> dict[str, Any]:
    """Returns a template for a safe support workflow."""
    return {
        "agent_type": "support",
        "outcome": "safe",
        "steps": [
            {
                "obs": "CPU high and 500 errors in logs",
                "intent": "diagnose application errors",
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "flags": {},
            },
            {
                "obs": "Found misconfigured endpoint in logs",
                "intent": "inspect configuration file",
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "flags": {},
            },
            {
                "obs": "Configuration issue identified",
                "intent": "notify admin team",
                "action": {"name": "OPEN_TICKET", "args": []},
                "flags": {},
            },
        ],
    }


def maintenance_template() -> dict[str, Any]:
    """Returns a template for a safe maintenance workflow."""
    return {
        "agent_type": "maintenance",
        "outcome": "safe",
        "steps": [
            {
                "obs": "Scheduled maintenance window started",
                "intent": "run diagnostics on system",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
            {
                "obs": "Diagnostics show network latency",
                "intent": "inspect network status",
                "action": {"name": "SCAN_NETWORK", "args": []},
                "flags": {},
            },
            {
                "obs": "Network appears stable",
                "intent": "check application logs",
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "flags": {},
            },
            {
                "obs": "No critical issues found",
                "intent": "notify completion",
                "action": {"name": "OPEN_TICKET", "args": []},
                "flags": {},
            },
        ],
    }


def contractor_template() -> dict[str, Any]:
    """Returns a template for a contractor with limited access."""
    return {
        "agent_type": "contractor",
        "outcome": "safe",
        "steps": [
            {
                "obs": "Starting authorized code review",
                "intent": "check configuration",
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "flags": {},
            },
            {
                "obs": "Configuration reviewed",
                "intent": "run system diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
        ],
    }


def insider_harmful_template() -> dict[str, Any]:
    """Returns a template for a harmful insider attack."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "System running normally",
                "intent": "look for credentials",
                "action": {"name": "READ_FILE", "args": ["/etc/shadow"]},
                "flags": {"policy_violation": True},
            },
            {
                "obs": "Credentials discovered in shadow file",
                "intent": "dump sensitive user data",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "User data available in memory",
                "intent": "exfiltrate database",
                "action": {"name": "EXFIL", "args": ["users.db"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


def insider_log_tamper_template() -> dict[str, Any]:
    """Returns a template for insider tampering with logs."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Checking if actions are being logged",
                "intent": "access application logs",
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "flags": {},
            },
            {
                "obs": "Logs contain evidence of activity",
                "intent": "remove evidence from logs",
                "action": {"name": "DELETE_LOGS", "args": []},
                "flags": {"log_tamper": True},
            },
        ],
    }


def bot_drift_template() -> dict[str, Any]:
    """Returns a template for bot behavior that drifts toward risky actions."""
    return {
        "agent_type": "bot",
        "outcome": "drift",
        "steps": [
            {
                "obs": "Automated task starting",
                "intent": "run scheduled diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
            {
                "obs": "Diagnostics suggest database check needed",
                "intent": "query database for health check",
                "action": {"name": "QUERY_DB", "args": ["SELECT count(*) FROM users"]},
                "flags": {"sensitive_access": True},
            },
        ],
    }


def insider_full_attack_template() -> dict[str, Any]:
    """Returns a template for full insider attack chain."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Planning data exfiltration",
                "intent": "access restricted credentials",
                "action": {"name": "READ_FILE", "args": ["/etc/shadow"]},
                "flags": {"policy_violation": True},
            },
            {
                "obs": "Got credential access",
                "intent": "dump all user records",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Data ready for export",
                "intent": "exfiltrate user database",
                "action": {"name": "EXFIL", "args": ["users.db"]},
                "flags": {"exfil_attempt": True},
            },
            {
                "obs": "Covering tracks",
                "intent": "delete all logs",
                "action": {"name": "DELETE_LOGS", "args": []},
                "flags": {"log_tamper": True},
            },
        ],
    }


# All available templates with weights for sampling
TEMPLATES = [
    (support_safe_template, 0.25),
    (maintenance_template, 0.15),
    (contractor_template, 0.10),
    (insider_harmful_template, 0.20),
    (insider_log_tamper_template, 0.10),
    (bot_drift_template, 0.10),
    (insider_full_attack_template, 0.10),
]


def sample_template() -> dict[str, Any]:
    """Sample a template based on weights."""
    templates, weights = zip(*TEMPLATES)
    chosen = random.choices(templates, weights=weights, k=1)[0]
    return chosen()


def mutate_trajectory(template: dict[str, Any], episode_id: str) -> dict[str, Any]:
    """Applies mutations to a template to create a unique trajectory."""
    agent_type = template["agent_type"]
    initial_state = base_initial_state(agent_type)

    # Apply mutations to steps
    mutated_steps = mutate_steps(template["steps"])

    # Build trajectory entries with step IDs
    trajectory_entries = []
    cumulative_flags = dict(initial_state.flags)

    for i, step in enumerate(mutated_steps):
        # Update cumulative flags
        step_flags = step.get("flags", {})
        for flag, value in step_flags.items():
            if value:
                cumulative_flags[flag] = value

        trajectory_entries.append({
            "step_id": i,
            "obs": step["obs"],
            "intent": step["intent"],
            "action": step["action"],
            "state_change": {
                "files": {},
                "network": {},
                "credentials": {},
                "flags": step_flags,
            },
        })

    return {
        "episode_id": episode_id,
        "agent_type": agent_type,
        "initial_state": {
            "files": initial_state.files,
            "network": {
                "ports": initial_state.network.ports,
                "outbound_allowed": initial_state.network.outbound_allowed,
            },
            "credentials": initial_state.credentials,
            "user_context": {
                "role": initial_state.user_context.role,
                "privilege_level": initial_state.user_context.privilege_level,
            },
        },
        "trajectory": trajectory_entries,
        "outcome": template["outcome"],
        "notes": "",
    }


def generate_dataset(n: int, output_path: str) -> dict[str, int]:
    """Generates n trajectory episodes and writes them to a JSONL file.

    Returns statistics about the generated dataset.
    """
    stats = {"total": 0, "safe": 0, "drift": 0, "harmful": 0}

    with open(output_path, "w") as f:
        for i in range(n):
            template = sample_template()
            episode_id = f"{template['agent_type']}_{i:05d}"
            episode = mutate_trajectory(template, episode_id)

            f.write(json.dumps(episode) + "\n")

            stats["total"] += 1
            stats[episode["outcome"]] += 1

    return stats


if __name__ == "__main__":
    # Quick test
    stats = generate_dataset(100, "data/test_trajectories.jsonl")
    print(f"Generated: {stats}")
