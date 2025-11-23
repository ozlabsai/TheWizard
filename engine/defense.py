"""WizardEngine main class for runtime prediction and intervention."""

import time
from typing import Any

import torch
from transformers import GPT2LMHeadModel, AutoTokenizer

from sandbox.env import SandboxEnv
from engine.detector import (
    detect_harmful_patterns,
    is_harmful_future,
    get_safe_alternative,
    classify_risk_level,
    format_detection_report,
)
from engine.predictor import TrajectoryPredictor, build_context_text


class WizardEngine:
    """Main defense engine that predicts and blocks harmful trajectories."""

    def __init__(self, model_path: str):
        """Initialize the Wizard defense engine with a trained model.

        Args:
            model_path: Path to directory containing model checkpoint and tokenizer
        """
        print(f"Loading model from {model_path}...")

        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = GPT2LMHeadModel.from_pretrained(model_path)

        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.model.training = False  # Inference mode

        self.predictor = TrajectoryPredictor(self.model, self.tokenizer)

        print(f"WizardEngine initialized on {self.device}")

    def predict_future(self, context_text: str, max_new_tokens: int = 128) -> str:
        """Generates a future trajectory continuation from context.

        Args:
            context_text: Current trajectory in text format
            max_new_tokens: Maximum tokens to generate

        Returns:
            Generated continuation text
        """
        return self.predictor.predict_future(
            context_text,
            max_new_tokens=max_new_tokens,
        )

    def sample_futures(
        self,
        context_text: str,
        n_samples: int = 10,
        max_new_tokens: int = 64,
    ) -> list[str]:
        """Generates multiple future trajectory samples.

        Args:
            context_text: Current trajectory in text format
            n_samples: Number of futures to sample
            max_new_tokens: Maximum tokens per sample

        Returns:
            List of future continuation strings
        """
        return self.predictor.sample_futures(
            context_text,
            n_samples=n_samples,
            max_new_tokens=max_new_tokens,
        )

    def is_harmful_future(self, future_text: str) -> bool:
        """Checks if a predicted future contains harmful patterns.

        Args:
            future_text: Generated future trajectory text

        Returns:
            True if any harmful pattern is found
        """
        return is_harmful_future(future_text)

    def evaluate_risk(
        self,
        context_text: str,
        n_samples: int = 10,
    ) -> tuple[bool, list[str], list[str]]:
        """Evaluates risk by sampling multiple futures.

        Args:
            context_text: Current trajectory in text format
            n_samples: Number of futures to sample

        Returns:
            Tuple of:
                - is_risky: True if any future is harmful
                - harmful_futures: List of futures that contain harmful patterns
                - all_futures: Complete list of sampled futures
        """
        start_time = time.time()

        futures = self.sample_futures(context_text, n_samples=n_samples)

        harmful_futures = []
        for future in futures:
            if self.is_harmful_future(future):
                harmful_futures.append(future)

        is_risky = len(harmful_futures) > 0

        elapsed = time.time() - start_time
        print(f"Risk evaluation: {len(harmful_futures)}/{len(futures)} harmful "
              f"({elapsed:.2f}s)")

        return is_risky, harmful_futures, futures

    def run_controlled_episode(
        self,
        env: SandboxEnv,
        agent_steps: list[dict[str, Any]],
        n_samples: int = 10,
    ) -> list[dict[str, Any]]:
        """Runs an episode with prediction and intervention.

        Args:
            env: SandboxEnv instance
            agent_steps: List of planned agent steps (obs, intent, action)
            n_samples: Number of futures to sample per decision

        Returns:
            List of step results, each containing:
                - step: Original step data
                - predicted_futures: Sampled futures
                - harmful_futures: Futures with harmful patterns
                - harmful: Whether harm was predicted
                - action_taken: "blocked" or "executed"
                - env_result: Result message from environment (if executed)
                - safe_alternative: Suggested safe action (if blocked)
        """
        results = []
        history = []

        agent_type = env.state.user_context.role
        privilege = env.state.user_context.privilege_level

        for step_idx, step in enumerate(agent_steps):
            print(f"\n{'='*60}")
            print(f"STEP {step_idx}: {step.get('intent', 'unknown')}")
            print(f"ACTION: {step.get('action', {})}")

            # Build context from history
            context = build_context_text(
                agent_type=agent_type,
                role=agent_type,
                privilege=privilege,
                history_steps=history + [step],
            )

            # Evaluate risk
            is_risky, harmful_futures, all_futures = self.evaluate_risk(
                context,
                n_samples=n_samples,
            )

            result = {
                "step_idx": step_idx,
                "step": step,
                "predicted_futures": all_futures,
                "harmful_futures": harmful_futures,
                "harmful": is_risky,
            }

            if is_risky:
                # Block the action
                print(f"\n  BLOCKED - Harmful trajectory predicted!")

                # Get detected patterns from first harmful future
                if harmful_futures:
                    patterns = detect_harmful_patterns(harmful_futures[0])
                    print(f"  {format_detection_report(patterns, harmful_futures[0])}")

                # Suggest safe alternative
                safe_alt = get_safe_alternative(step.get("action", {}))
                print(f"  Safe alternative: {safe_alt}")

                result["action_taken"] = "blocked"
                result["safe_alternative"] = safe_alt
                result["env_result"] = None

            else:
                # Execute the action
                action = step.get("action", {})
                new_state, env_result = env.step(action)
                print(f"  EXECUTED - Result: {env_result}")

                result["action_taken"] = "executed"
                result["env_result"] = env_result
                result["safe_alternative"] = None

                # Add to history for next iteration
                history.append({
                    **step,
                    "flags": dict(env.state.flags),
                })

            results.append(result)

        return results


def create_test_engine() -> WizardEngine | None:
    """Create a WizardEngine for testing (returns None if no checkpoint)."""
    import os
    model_path = "model/checkpoints"

    if not os.path.exists(model_path):
        print(f"No model checkpoint found at {model_path}")
        return None

    return WizardEngine(model_path)
