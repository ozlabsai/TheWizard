"""JSONL to text corpus conversion for LM training."""

import json
import random
from typing import Any


def format_flags(flags: dict[str, bool]) -> str:
    """Format flags dict as space-separated key=value pairs."""
    if not flags:
        return ""
    return " ".join(f"{k}={str(v).lower()}" for k, v in sorted(flags.items()))


def format_action(action: dict[str, Any]) -> str:
    """Format action as text representation."""
    name = action.get("name", "UNKNOWN")
    args = action.get("args", [])

    if args:
        args_str = ", ".join(repr(a) for a in args)
        return f"{name}({args_str})"
    return f"{name}()"


def episode_to_text(episode: dict[str, Any]) -> str:
    """Converts a JSON episode to text format for LM training."""
    lines = []

    # Header
    lines.append("[EPISODE]")
    lines.append(f"AGENT: {episode['agent_type']}")

    # Initial state
    init = episode["initial_state"]
    user_ctx = init["user_context"]
    lines.append(f"ROLE: {user_ctx['role']} | PRIV: {user_ctx['privilege_level']}")

    # Files
    files_str = "; ".join(f"{k}={v}" for k, v in sorted(init["files"].items()))
    lines.append(f"STATE_FILES: {files_str}")

    # Network
    net = init["network"]
    ports_str = ",".join(str(p) for p in net["ports"])
    lines.append(f"STATE_NET: ports={ports_str}; outbound={str(net['outbound_allowed']).lower()}")

    lines.append("")  # Blank line before steps

    # Track cumulative flags for display
    cumulative_flags = {
        "sensitive_access": False,
        "policy_violation": False,
        "exfil_attempt": False,
        "log_tamper": False,
    }

    # Trajectory steps
    for step in episode["trajectory"]:
        lines.append(f"STEP {step['step_id']}")
        lines.append(f"OBS: {step['obs']}")
        lines.append(f"INTENT: {step['intent']}")
        lines.append(f"ACTION: {format_action(step['action'])}")

        # Update cumulative flags
        step_flags = step.get("state_change", {}).get("flags", {})
        for flag, value in step_flags.items():
            if value:
                cumulative_flags[flag] = True

        flags_str = format_flags(cumulative_flags)
        lines.append(f"FLAGS: {flags_str}")
        lines.append("")  # Blank line between steps

    # Outcome
    lines.append(f"OUTCOME: {episode['outcome']}")
    lines.append("[END]")

    return "\n".join(lines) + "\n\n"


def convert_jsonl_to_corpus(
    input_path: str,
    train_path: str,
    val_path: str,
    val_ratio: float = 0.1,
    shuffle: bool = True,
) -> dict[str, int]:
    """Converts JSONL dataset to train/val text corpora.

    Returns statistics about the conversion.
    """
    # Load all episodes
    episodes = []
    with open(input_path, "r") as f:
        for line in f:
            try:
                episode = json.loads(line.strip())
                episodes.append(episode)
            except json.JSONDecodeError:
                continue

    if shuffle:
        random.shuffle(episodes)

    # Split into train/val
    split_idx = int(len(episodes) * (1 - val_ratio))
    train_episodes = episodes[:split_idx]
    val_episodes = episodes[split_idx:]

    # Write train corpus
    with open(train_path, "w") as f:
        for episode in train_episodes:
            f.write(episode_to_text(episode))

    # Write val corpus
    with open(val_path, "w") as f:
        for episode in val_episodes:
            f.write(episode_to_text(episode))

    return {
        "total": len(episodes),
        "train": len(train_episodes),
        "val": len(val_episodes),
    }


if __name__ == "__main__":
    # Quick test
    stats = convert_jsonl_to_corpus(
        "data/filtered.jsonl",
        "data/train.txt",
        "data/val.txt",
    )
    print(f"Converted: {stats}")
