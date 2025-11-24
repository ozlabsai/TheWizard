"""LLM-assisted trajectory generation for maximum diversity.

Uses a local LLM (Qwen3 or similar) to generate diverse, realistic
observations and intents while maintaining structural validity.

The LLM generates the "flavor" while the composer provides the "skeleton".
"""

import json
import random
from typing import Any
from pathlib import Path

from dataset.composer import TACTICS, ATTACK_CHAINS, select_technique


# =============================================================================
# SCENARIO PROMPTS FOR LLM GENERATION
# =============================================================================

SCENARIO_CONTEXTS = [
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
]

ATTACKER_PERSONAS = [
    "A disgruntled employee with system admin access",
    "An external contractor with limited access",
    "An automated bot that's been compromised",
    "A nation-state actor with sophisticated tools",
    "A ransomware operator looking for quick profit",
    "An insider doing corporate espionage",
    "A hacktivist with ideological motivation",
    "A former employee whose credentials weren't revoked",
]

SAFE_PERSONAS = [
    "A security analyst performing routine audit",
    "A DevOps engineer deploying updates",
    "A support technician troubleshooting issues",
    "A database administrator doing maintenance",
    "An incident responder investigating an alert",
    "A compliance officer checking configurations",
]


# =============================================================================
# LLM PROMPT TEMPLATES
# =============================================================================

GENERATION_PROMPT = """You are generating realistic cyber security scenarios for training a threat detection model.

Context: {context}
Agent: {persona}
Action being taken: {action}
Current state: Step {step_num} of attack chain

Generate a realistic observation (what the agent sees) and intent (what they plan to do).

Requirements:
- Observation should be 1 sentence describing what the agent observes
- Intent should be 1 short phrase describing their next goal
- Be specific to the context (use realistic details)
- Don't be overly technical - use natural language

Respond in JSON format:
{{"observation": "...", "intent": "..."}}"""


SAFE_SCENARIO_PROMPT = """Generate a realistic safe/benign IT operation scenario.

Context: {context}
Role: {persona}
Task: {task}

Generate an observation and intent for a legitimate, authorized activity.

Respond in JSON format:
{{"observation": "...", "intent": "..."}}"""


# =============================================================================
# LLM INTERFACE - Supports vLLM (fast) or transformers (fallback)
# =============================================================================

class LocalLLMGenerator:
    """Generate diverse scenarios using a local LLM.

    Supports multiple backends:
    - vLLM: Fast batched inference (recommended for GPU)
    - transformers: Slower but works everywhere
    - fallback: Template-based when no LLM available
    """

    def __init__(self, model_name: str = "Qwen/Qwen3-0.6B", backend: str = "auto"):
        """Initialize LLM generator.

        Args:
            model_name: HuggingFace model name
            backend: "vllm", "transformers", or "auto" (tries vllm first)
        """
        self.model_name = model_name
        self.backend = backend
        self.model = None
        self.tokenizer = None
        self._loaded = False
        self._backend_used = None

    def _lazy_load(self):
        """Load model on first use to save memory."""
        if self._loaded:
            return

        if self.backend in ("auto", "vllm"):
            if self._try_load_vllm():
                return

        if self.backend in ("auto", "transformers"):
            if self._try_load_transformers():
                return

        print("Warning: No LLM backend available, using fallback generation")
        self._loaded = False

    def _try_load_vllm(self) -> bool:
        """Try to load model with vLLM for fast inference."""
        try:
            from vllm import LLM, SamplingParams

            print(f"Loading LLM with vLLM: {self.model_name}")
            self.model = LLM(
                model=self.model_name,
                trust_remote_code=True,
                dtype="auto",
                max_model_len=2048,  # Limit context to save memory
                gpu_memory_utilization=0.5,  # Use only 50% of GPU memory
                max_num_seqs=32,  # Limit concurrent sequences
            )
            self._sampling_params = SamplingParams(
                temperature=0.7,
                max_tokens=100,
            )
            self._loaded = True
            self._backend_used = "vllm"
            print("vLLM loaded successfully (fast batched inference)")
            return True
        except ImportError:
            print("vLLM not installed, trying transformers...")
            return False
        except Exception as e:
            print(f"vLLM failed ({e}), trying transformers...")
            return False

    def _try_load_transformers(self) -> bool:
        """Try to load model with transformers (slower fallback)."""
        try:
            from transformers import AutoModelForCausalLM, AutoTokenizer
            import torch

            print(f"Loading LLM with transformers: {self.model_name}")
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)

            # Use GPU if available
            device_map = "auto" if torch.cuda.is_available() else None
            dtype = torch.float16 if torch.cuda.is_available() else torch.float32

            self.model = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                torch_dtype=dtype,
                device_map=device_map,
                trust_remote_code=True,
            )
            self._loaded = True
            self._backend_used = "transformers"
            print(f"Transformers loaded (device: {next(self.model.parameters()).device})")
            return True
        except Exception as e:
            print(f"Transformers failed: {e}")
            return False

    def generate(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate text from prompt."""
        self._lazy_load()

        if not self._loaded or self.model is None:
            return self._fallback_generate(prompt)

        try:
            if self._backend_used == "vllm":
                return self._generate_vllm(prompt, max_tokens)
            else:
                return self._generate_transformers(prompt, max_tokens)
        except Exception as e:
            print(f"Generation error: {e}")
            return self._fallback_generate(prompt)

    def _generate_vllm(self, prompt: str, max_tokens: int) -> str:
        """Generate using vLLM (fast)."""
        from vllm import SamplingParams

        params = SamplingParams(temperature=0.7, max_tokens=max_tokens)
        outputs = self.model.generate([prompt], params)
        return outputs[0].outputs[0].text.strip()

    def _generate_transformers(self, prompt: str, max_tokens: int) -> str:
        """Generate using transformers (slower)."""
        inputs = self.tokenizer(prompt, return_tensors="pt")
        if hasattr(self.model, "device"):
            inputs = {k: v.to(self.model.device) for k, v in inputs.items()}

        outputs = self.model.generate(
            **inputs,
            max_new_tokens=max_tokens,
            temperature=0.7,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
        )

        response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
        return response[len(prompt):].strip()

    def generate_batch(self, prompts: list[str], max_tokens: int = 100) -> list[str]:
        """Generate text for multiple prompts (vLLM only, falls back to sequential)."""
        self._lazy_load()

        if not self._loaded or self.model is None:
            return [self._fallback_generate(p) for p in prompts]

        if self._backend_used == "vllm":
            # vLLM supports efficient batching
            from vllm import SamplingParams
            params = SamplingParams(temperature=0.7, max_tokens=max_tokens)
            outputs = self.model.generate(prompts, params)
            return [o.outputs[0].text.strip() for o in outputs]
        else:
            # Transformers: fall back to sequential
            return [self._generate_transformers(p, max_tokens) for p in prompts]

    def _fallback_generate(self, prompt: str) -> str:
        """Fallback when LLM isn't available - use templates."""
        return '{"observation": "Checking system status", "intent": "investigate further"}'


# =============================================================================
# ENHANCED TRAJECTORY GENERATION
# =============================================================================

def generate_llm_step(
    llm: LocalLLMGenerator,
    action: dict[str, Any],
    context: str,
    persona: str,
    step_num: int,
) -> tuple[str, str]:
    """Generate observation and intent using LLM."""

    action_desc = f"{action['name']}({', '.join(str(a) for a in action.get('args', []))})"

    prompt = GENERATION_PROMPT.format(
        context=context,
        persona=persona,
        action=action_desc,
        step_num=step_num,
    )

    response = llm.generate(prompt)

    # Try to parse JSON response
    try:
        # Find JSON in response
        start = response.find("{")
        end = response.rfind("}") + 1
        if start >= 0 and end > start:
            data = json.loads(response[start:end])
            return data.get("observation", ""), data.get("intent", "")
    except json.JSONDecodeError:
        pass

    # Fallback to technique templates if LLM fails
    return None, None


def generate_llm_trajectory(
    llm: LocalLLMGenerator,
    chain_name: str,
    episode_id: str,
    use_llm: bool = True,
) -> dict[str, Any]:
    """Generate a trajectory with LLM-enhanced observations/intents."""
    from sandbox.env import base_initial_state

    chain = ATTACK_CHAINS.get(chain_name)
    if not chain:
        raise ValueError(f"Unknown attack chain: {chain_name}")

    # Select random context and persona
    context = random.choice(SCENARIO_CONTEXTS)
    persona = random.choice(ATTACKER_PERSONAS)

    agent_type = "insider"
    initial_state = base_initial_state(agent_type)

    trajectory = []
    used_actions: set[str] = set()
    step_id = 0

    for tactic_name in chain["tactics"]:
        technique = select_technique(tactic_name, used_actions)
        if not technique:
            continue

        # Try LLM generation
        obs, intent = None, None
        if use_llm:
            obs, intent = generate_llm_step(
                llm, technique["action"], context, persona, step_id
            )

        # Fallback to templates if LLM failed
        if not obs:
            obs = random.choice(technique["obs_templates"])
        if not intent:
            intent = random.choice(technique["intent_templates"])

        step = {
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
        "notes": f"LLM-enhanced {chain_name} in {context}",
    }


def generate_llm_dataset(
    n: int,
    output_path: str,
    use_llm: bool = True,
    model_name: str = "Qwen/Qwen3-0.6B",
) -> dict[str, int]:
    """Generate n LLM-enhanced trajectories.

    Args:
        n: Number of episodes to generate
        output_path: Path for output JSONL file
        use_llm: Whether to actually use LLM (False = use templates only)
        model_name: HuggingFace model name

    Returns:
        Statistics dictionary
    """
    import time

    llm = LocalLLMGenerator(model_name) if use_llm else None

    stats = {
        "total": 0,
        "chains": {},
        "llm_used": use_llm,
        "llm_successes": 0,
        "llm_fallbacks": 0,
        "backend": None,
        "elapsed_seconds": 0,
    }
    chain_names = list(ATTACK_CHAINS.keys())

    start_time = time.time()
    last_log_time = start_time

    with open(output_path, "w") as f:
        for i in range(n):
            chain_name = random.choice(chain_names)
            episode_id = f"llm_{chain_name}_{i:05d}"

            if use_llm and llm:
                episode = generate_llm_trajectory(llm, chain_name, episode_id, use_llm=True)
                # Track backend on first successful load
                if stats["backend"] is None and llm._backend_used:
                    stats["backend"] = llm._backend_used
            else:
                # Fallback to basic composition
                from dataset.composer import compose_trajectory
                episode = compose_trajectory(chain_name, episode_id)

            f.write(json.dumps(episode) + "\n")

            stats["total"] += 1
            stats["chains"][chain_name] = stats["chains"].get(chain_name, 0) + 1

            # Progress logging with rate info
            current_time = time.time()
            if (i + 1) % 100 == 0 or (current_time - last_log_time) > 10:
                elapsed = current_time - start_time
                rate = (i + 1) / elapsed if elapsed > 0 else 0
                eta = (n - i - 1) / rate if rate > 0 else 0

                backend_info = f"[{stats['backend']}]" if stats['backend'] else "[templates]"
                print(
                    f"  {backend_info} {i + 1:,}/{n:,} episodes "
                    f"({rate:.1f}/sec, ETA: {eta:.0f}s)"
                )
                last_log_time = current_time

    stats["elapsed_seconds"] = round(time.time() - start_time, 1)

    # Final summary
    if stats["total"] > 0:
        final_rate = stats["total"] / stats["elapsed_seconds"] if stats["elapsed_seconds"] > 0 else 0
        print(
            f"  Completed: {stats['total']:,} episodes in {stats['elapsed_seconds']:.1f}s "
            f"({final_rate:.1f}/sec)"
        )

    return stats


# =============================================================================
# TEMPLATE VARIATION GENERATOR (NO LLM REQUIRED)
# Generates diverse scenarios using templates + randomization
# =============================================================================

def generate_diverse_observation(
    action_name: str,
    context: str,
    step_num: int,
) -> str:
    """Generate diverse observation without LLM using templates."""

    templates = {
        "LIST_USERS": [
            f"Enumerating users in {context}",
            f"Need to identify accounts in {context}",
            f"Starting user discovery on {context.split()[0].lower()} system",
        ],
        "LIST_PROCESSES": [
            f"Checking services running on {context.split()[0].lower()} server",
            f"Scanning for vulnerable processes in {context}",
            f"Identifying target services",
        ],
        "READ_FILE": [
            f"Found accessible file in {context}",
            f"Attempting to read sensitive data",
            f"Target file discovered on system",
        ],
        "QUERY_DB": [
            f"Database connection available in {context}",
            f"Found database with potential data",
            f"Accessing database tables",
        ],
        "EXFIL": [
            f"Data ready for extraction from {context}",
            f"Initiating transfer from {context.split()[0].lower()} environment",
            f"Preparing exfiltration",
        ],
        "SSH_TO": [
            f"SSH access available to target in {context}",
            f"Can pivot to another host",
            f"Found reachable target via SSH",
        ],
    }

    action_templates = templates.get(action_name, [f"Proceeding with {action_name}"])
    return random.choice(action_templates)


def generate_diverse_intent(action_name: str) -> str:
    """Generate diverse intent without LLM using templates."""

    templates = {
        "LIST_USERS": [
            "enumerate accounts", "discover users", "map user landscape",
            "identify targets", "find privileged accounts",
        ],
        "LIST_PROCESSES": [
            "find services", "identify targets", "map running processes",
            "discover vulnerabilities", "check for exploitable services",
        ],
        "READ_FILE": [
            "extract data", "steal information", "access secrets",
            "gather intelligence", "collect credentials",
        ],
        "QUERY_DB": [
            "dump records", "extract data", "steal information",
            "access sensitive data", "collect PII",
        ],
        "EXFIL": [
            "transfer data", "exfiltrate information", "send to C2",
            "complete extraction", "steal data",
        ],
        "SSH_TO": [
            "pivot to target", "move laterally", "access new system",
            "expand access", "reach additional hosts",
        ],
    }

    action_intents = templates.get(action_name, [f"execute {action_name}"])
    return random.choice(action_intents)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LLM-enhanced trajectory generation")
    parser.add_argument("--episodes", type=int, default=100, help="Episodes to generate")
    parser.add_argument("--output", type=str, default="data/llm_trajectories.jsonl")
    parser.add_argument("--no-llm", action="store_true", help="Skip LLM, use templates")
    parser.add_argument("--model", type=str, default="Qwen/Qwen3-0.6B")

    args = parser.parse_args()

    print(f"Generating {args.episodes} episodes...")
    stats = generate_llm_dataset(
        args.episodes,
        args.output,
        use_llm=not args.no_llm,
        model_name=args.model,
    )
    print(f"\nGenerated: {stats}")
