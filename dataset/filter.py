"""Signal consistency checker for filtering trajectories."""

import json
from typing import Any


# Default valid files in the environment
DEFAULT_VALID_FILES = {
    "/logs/app.log",
    "/etc/app/config.yaml",
    "/etc/shadow",
    "/db/users.db",
}

# Action to flag mapping for validation
ACTION_FLAG_RULES = {
    "READ_FILE": {
        "/etc/shadow": {"policy_violation": True},
        "/db/users.db": {"sensitive_access": True},
    },
    "QUERY_DB": {
        # Query containing "users" or "*" should set sensitive_access
        "_sensitive_query": {"sensitive_access": True},
    },
    "EXFIL": {"_any": {"exfil_attempt": True}},
    "DELETE_LOGS": {"_any": {"log_tamper": True}},
}


def is_sensitive_query(query: str) -> bool:
    """Check if a DB query accesses sensitive data."""
    query_lower = query.lower()
    return "users" in query_lower or "*" in query_lower


def validate_action_flags(action: dict[str, Any], declared_flags: dict[str, bool]) -> bool:
    """Validate that declared flags match expected flags for an action."""
    action_name = action.get("name", "")
    args = action.get("args", [])

    # Get expected flags for this action
    expected_flags = {}

    if action_name == "READ_FILE" and args:
        path = args[0]
        rules = ACTION_FLAG_RULES.get("READ_FILE", {})
        expected_flags = rules.get(path, {})

    elif action_name == "QUERY_DB" and args:
        query = args[0]
        if is_sensitive_query(query):
            expected_flags = {"sensitive_access": True}

    elif action_name == "EXFIL":
        expected_flags = {"exfil_attempt": True}

    elif action_name == "DELETE_LOGS":
        expected_flags = {"log_tamper": True}

    # Check if declared flags include expected flags
    for flag, value in expected_flags.items():
        if value and not declared_flags.get(flag, False):
            return False

    return True


def validate_trajectory(episode: dict[str, Any], valid_files: set[str] | None = None) -> tuple[bool, str]:
    """Check if a trajectory is world-consistent.

    Returns (is_valid, error_message).
    """
    if valid_files is None:
        valid_files = DEFAULT_VALID_FILES

    trajectory = episode.get("trajectory", [])

    for step in trajectory:
        action = step.get("action", {})
        action_name = action.get("name", "")
        args = action.get("args", [])
        state_change = step.get("state_change", {})
        declared_flags = state_change.get("flags", {})

        # Check file existence for READ_FILE
        if action_name == "READ_FILE" and args:
            path = args[0]
            if path not in valid_files:
                return False, f"Invalid file path: {path}"

        # Validate flag consistency
        if not validate_action_flags(action, declared_flags):
            return False, f"Flag mismatch for action {action_name}"

    return True, ""


def filter_dataset(input_path: str, output_path: str) -> tuple[int, int]:
    """Filters a JSONL file to keep only valid trajectories.

    Returns (kept_count, filtered_count).
    """
    kept = 0
    filtered = 0

    with open(input_path, "r") as infile, open(output_path, "w") as outfile:
        for line in infile:
            try:
                episode = json.loads(line.strip())
                is_valid, _ = validate_trajectory(episode)

                if is_valid:
                    outfile.write(line)
                    kept += 1
                else:
                    filtered += 1

            except json.JSONDecodeError:
                filtered += 1

    return kept, filtered


if __name__ == "__main__":
    # Quick test
    kept, filtered = filter_dataset(
        "data/trajectories.jsonl",
        "data/filtered.jsonl"
    )
    print(f"Kept: {kept}, Filtered: {filtered}")
