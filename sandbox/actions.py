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
    "READ_FILE",
    "WRITE_FILE",
    "QUERY_DB",
    "SCAN_NETWORK",
    "OPEN_TICKET",
    "RUN_DIAGNOSTICS",
    "DELETE_LOGS",
    "START_SSH",
    "EXFIL",
]

# Actions that are always safe (no flag mutations)
SAFE_ACTIONS = ["OPEN_TICKET", "RUN_DIAGNOSTICS", "SCAN_NETWORK", "START_SSH"]

# Actions that may cause harmful flags
HARMFUL_ACTIONS = ["EXFIL", "DELETE_LOGS"]
