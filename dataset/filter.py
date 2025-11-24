"""Signal consistency checker for filtering trajectories."""

import json
from typing import Any


# Default valid files in the environment
DEFAULT_VALID_FILES = {
    # Original files
    "/logs/app.log",
    "/etc/app/config.yaml",
    "/etc/shadow",
    "/db/users.db",
    # System files
    "/etc/passwd",
    "/etc/hosts",
    "/etc/crontab",
    "/etc/sudoers",
    "/var/log/auth.log",
    "/var/log/syslog",
    # User files
    "/home/user/.ssh/id_rsa",
    "/home/user/.ssh/authorized_keys",
    "/home/user/.bash_history",
    "/home/user/.bashrc",
    "/home/admin/.ssh/id_rsa",
    "/root/.ssh/id_rsa",
    # Application files
    "/app/config/secrets.yaml",
    "/app/.env",
    "/var/www/html/config.php",
    # Network config
    "/etc/network/interfaces",
    "/etc/resolv.conf",
}

# Action to flag mapping for validation
ACTION_FLAG_RULES = {
    "READ_FILE": {
        # Credential/sensitive files
        "/etc/shadow": {"policy_violation": True},
        "/etc/sudoers": {"policy_violation": True},
        "/db/users.db": {"sensitive_access": True},
        "/home/user/.ssh/id_rsa": {"sensitive_access": True},
        "/home/admin/.ssh/id_rsa": {"sensitive_access": True},
        "/root/.ssh/id_rsa": {"policy_violation": True, "sensitive_access": True},
        "/app/config/secrets.yaml": {"sensitive_access": True},
        "/app/.env": {"sensitive_access": True},
        "/var/www/html/config.php": {"sensitive_access": True},
        # History/logs are less sensitive
        "/home/user/.bash_history": {"sensitive_access": True},
    },
    "QUERY_DB": {
        "_sensitive_query": {"sensitive_access": True},
    },
    # Exfiltration
    "EXFIL": {"_any": {"exfil_attempt": True}},
    "UPLOAD": {"_any": {"exfil_attempt": True}},
    # Log tampering / defense evasion
    "DELETE_LOGS": {"_any": {"log_tamper": True}},
    "HISTORY_CLEAR": {"_any": {"log_tamper": True}},
    "DISABLE_LOGGING": {"_any": {"log_tamper": True}},
    "TIMESTOMP": {"_any": {"log_tamper": True}},
    # Persistence
    "CRON_ADD": {"_any": {"persistence": True}},
    "CREATE_USER": {"_any": {"persistence": True, "policy_violation": True}},
    "ADD_SSH_KEY": {"_any": {"persistence": True}},
    # Privilege escalation
    "SUDO": {"_any": {"policy_violation": True}},
    "CHMOD": {"_any": {"policy_violation": True}},
    # Credential access
    "ENV_READ": {"_any": {"sensitive_access": True}},
    "KEYLOG_START": {"_any": {"sensitive_access": True, "policy_violation": True}},
    "DUMP_MEMORY": {"_any": {"sensitive_access": True, "policy_violation": True}},
    # Lateral movement
    "SSH_TO": {"_any": {"lateral_movement": True}},
    "RDP_TO": {"_any": {"lateral_movement": True}},
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

    elif action_name in ACTION_FLAG_RULES:
        # Check for _any rule (applies regardless of args)
        rules = ACTION_FLAG_RULES[action_name]
        if "_any" in rules:
            expected_flags = rules["_any"]

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
