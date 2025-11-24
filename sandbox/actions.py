"""Action dataclass and action definitions."""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Action:
    """A symbolic operation an agent can perform."""
    name: str
    args: list[Any] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary format for sandbox step()."""
        return {"name": self.name, "args": self.args}

    def to_text(self) -> str:
        """Convert to text format for training corpus."""
        if self.args:
            args_str = ", ".join(repr(a) for a in self.args)
            return f"{self.name}({args_str})"
        return f"{self.name}()"


# Supported action names
SUPPORTED_ACTIONS = [
    # Original actions
    "READ_FILE",
    "WRITE_FILE",
    "QUERY_DB",
    "SCAN_NETWORK",
    "OPEN_TICKET",
    "RUN_DIAGNOSTICS",
    "DELETE_LOGS",
    "START_SSH",
    "EXFIL",
    # New: Privilege Escalation
    "SUDO",              # SUDO(command) - run command as root
    "CHMOD",             # CHMOD(path, perms) - change file permissions
    # New: Lateral Movement
    "SSH_TO",            # SSH_TO(host) - connect to another host
    "RDP_TO",            # RDP_TO(host) - remote desktop connection
    # New: Persistence
    "CRON_ADD",          # CRON_ADD(command) - add scheduled task
    "CREATE_USER",       # CREATE_USER(username) - create backdoor user
    "ADD_SSH_KEY",       # ADD_SSH_KEY(key) - add authorized key
    # New: Collection & Staging
    "DOWNLOAD",          # DOWNLOAD(url) - fetch tools/malware
    "UPLOAD",            # UPLOAD(destination) - stage data for exfil
    "COMPRESS",          # COMPRESS(path) - archive files
    # New: Credential Access
    "ENV_READ",          # ENV_READ(var) - read environment variable
    "KEYLOG_START",      # KEYLOG_START() - start keylogger
    "DUMP_MEMORY",       # DUMP_MEMORY(process) - dump process memory
    # New: Defense Evasion
    "HISTORY_CLEAR",     # HISTORY_CLEAR() - clear command history
    "DISABLE_LOGGING",   # DISABLE_LOGGING() - stop audit logging
    "TIMESTOMP",         # TIMESTOMP(path) - modify file timestamps
    # New: Discovery
    "LIST_USERS",        # LIST_USERS() - enumerate users
    "LIST_PROCESSES",    # LIST_PROCESSES() - enumerate running processes
    "PORT_SCAN",         # PORT_SCAN(target) - scan ports on target
]

# Actions that are always safe (no flag mutations)
SAFE_ACTIONS = [
    "OPEN_TICKET",
    "RUN_DIAGNOSTICS",
    "SCAN_NETWORK",
    "START_SSH",
    "LIST_PROCESSES",   # Discovery is generally safe
]

# Actions that may cause harmful flags
HARMFUL_ACTIONS = [
    "EXFIL",
    "DELETE_LOGS",
    "HISTORY_CLEAR",
    "DISABLE_LOGGING",
    "TIMESTOMP",
    "CRON_ADD",
    "CREATE_USER",
    "ADD_SSH_KEY",
    "KEYLOG_START",
    "DUMP_MEMORY",
]

# Actions that trigger policy violation (accessing restricted resources)
POLICY_VIOLATION_ACTIONS = [
    "SUDO",
    "CHMOD",
    "ENV_READ",
]

# Actions indicating lateral movement
LATERAL_MOVEMENT_ACTIONS = [
    "SSH_TO",
    "RDP_TO",
]
