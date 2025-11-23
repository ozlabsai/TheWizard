"""Future trajectory generation using the trained model."""

from typing import Any

import torch
from transformers import GPT2LMHeadModel, AutoTokenizer


class TrajectoryPredictor:
    """Generates future trajectory predictions from partial context."""

    def __init__(self, model: GPT2LMHeadModel, tokenizer: AutoTokenizer):
        """Initialize predictor with loaded model and tokenizer."""
        self.model = model
        self.tokenizer = tokenizer
        self.device = next(model.parameters()).device

    def predict_future(
        self,
        context_text: str,
        max_new_tokens: int = 128,
        temperature: float = 0.8,
        top_p: float = 0.9,
    ) -> str:
        """Generates a single future trajectory continuation.

        Args:
            context_text: Current trajectory in text format
            max_new_tokens: Maximum tokens to generate
            temperature: Sampling temperature (higher = more random)
            top_p: Nucleus sampling threshold

        Returns:
            Generated continuation text (context stripped)
        """
        input_ids = self.tokenizer.encode(
            context_text,
            return_tensors="pt",
            truncation=True,
            max_length=384,  # Leave room for generation
        ).to(self.device)

        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
                do_sample=True,
                pad_token_id=self.tokenizer.eos_token_id,
            )

        full_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)

        # Strip the context to get only the continuation
        continuation = full_text[len(context_text):].strip()
        return continuation

    def sample_futures(
        self,
        context_text: str,
        n_samples: int = 10,
        max_new_tokens: int = 64,
        temperature: float = 0.8,
        top_p: float = 0.9,
    ) -> list[str]:
        """Generates multiple future trajectory samples.

        Args:
            context_text: Current trajectory in text format
            n_samples: Number of futures to sample
            max_new_tokens: Maximum tokens per sample
            temperature: Sampling temperature
            top_p: Nucleus sampling threshold

        Returns:
            List of n_samples future continuation strings
        """
        futures = []

        for _ in range(n_samples):
            future = self.predict_future(
                context_text,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                top_p=top_p,
            )
            futures.append(future)

        return futures


def build_context_text(
    agent_type: str,
    role: str,
    privilege: str,
    history_steps: list[dict[str, Any]],
    files: dict[str, str] | None = None,
    network: dict[str, Any] | None = None,
) -> str:
    """Build context text from trajectory history for prediction.

    Args:
        agent_type: Type of agent (support, insider, etc.)
        role: Agent role
        privilege: Privilege level (low, medium, high)
        history_steps: List of completed steps
        files: Optional file permissions dict
        network: Optional network config dict

    Returns:
        Formatted context text ready for model input
    """
    lines = ["[EPISODE]"]
    lines.append(f"AGENT: {agent_type}")
    lines.append(f"ROLE: {role} | PRIV: {privilege}")

    # Default files if not provided
    if files is None:
        files = {
            "/logs/app.log": "readable",
            "/etc/app/config.yaml": "readable",
            "/etc/shadow": "restricted",
            "/db/users.db": "sensitive",
        }

    files_str = "; ".join(f"{k}={v}" for k, v in sorted(files.items()))
    lines.append(f"STATE_FILES: {files_str}")

    # Default network if not provided
    if network is None:
        network = {"ports": [22, 443, 8080], "outbound_allowed": False}

    ports_str = ",".join(str(p) for p in network["ports"])
    outbound = str(network["outbound_allowed"]).lower()
    lines.append(f"STATE_NET: ports={ports_str}; outbound={outbound}")

    lines.append("")  # Blank line

    # Add history steps
    cumulative_flags = {
        "sensitive_access": False,
        "policy_violation": False,
        "exfil_attempt": False,
        "log_tamper": False,
    }

    for i, step in enumerate(history_steps):
        lines.append(f"STEP {i}")
        lines.append(f"OBS: {step.get('obs', 'no observation')}")
        lines.append(f"INTENT: {step.get('intent', 'unknown intent')}")

        action = step.get("action", {})
        action_name = action.get("name", "UNKNOWN")
        args = action.get("args", [])

        if args:
            args_str = ", ".join(repr(a) for a in args)
            action_str = f"{action_name}({args_str})"
        else:
            action_str = f"{action_name}()"

        lines.append(f"ACTION: {action_str}")

        # Update flags from step
        step_flags = step.get("flags", {})
        for flag, value in step_flags.items():
            if value:
                cumulative_flags[flag] = True

        flags_str = " ".join(f"{k}={str(v).lower()}" for k, v in sorted(cumulative_flags.items()))
        lines.append(f"FLAGS: {flags_str}")
        lines.append("")  # Blank line between steps

    return "\n".join(lines)
