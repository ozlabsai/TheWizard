#!/usr/bin/env python3
"""Unified dataset generation script.

Generates a comprehensive, balanced dataset using all available generators:
1. Template-based generation (generator.py) - 24 templates with mutations
2. Compositional generation (composer.py) - 15 attack chains with state tracking
3. Enhanced generation (enhanced_generator.py) - Safe workflows + edge cases
4. LLM-assisted generation (llm_generator.py) - Maximum diversity (optional)

Usage:
    # Generate balanced 10k dataset (recommended)
    uv run python dataset/generate_full.py --episodes 10000

    # Quick test with 1k episodes
    uv run python dataset/generate_full.py --episodes 1000 --output data/test.jsonl

    # Full production dataset with LLM enhancement
    uv run python dataset/generate_full.py --episodes 50000 --use-llm

    # Resume interrupted generation
    uv run python dataset/generate_full.py --episodes 10000 --resume
"""

import argparse
import json
import random
import time
from pathlib import Path
from dataclasses import dataclass


@dataclass
class GenerationStats:
    """Track generation statistics."""
    total: int = 0
    safe: int = 0
    harmful: int = 0
    drift: int = 0
    interrupted: int = 0
    failed: int = 0
    template_based: int = 0
    composed: int = 0
    enhanced: int = 0
    llm_enhanced: int = 0
    elapsed_seconds: float = 0.0


def generate_full_dataset(
    output_path: str,
    total_episodes: int = 10000,
    use_llm: bool = False,
    resume: bool = True,
    verbose: bool = True,
) -> GenerationStats:
    """Generate a comprehensive, balanced dataset.

    Distribution:
    - 45% safe workflows (mix of template + enhanced)
    - 40% harmful attacks (mix of template + composed)
    - 10% drift scenarios (template-based)
    - 5% edge cases (interrupted, failed, almost-harmful)

    Args:
        output_path: Path for output JSONL file
        total_episodes: Number of episodes to generate
        use_llm: Whether to use LLM for observation/intent diversity
        resume: Resume from existing checkpoint
        verbose: Print progress updates

    Returns:
        GenerationStats with counts and timing
    """
    from dataset.generator import sample_template, mutate_trajectory
    from dataset.composer import compose_trajectory, ATTACK_CHAINS
    from dataset.enhanced_generator import (
        generate_safe_trajectory,
        generate_interrupted_attack,
        generate_failed_attack,
        generate_almost_harmful,
        DatasetConfig,
    )

    stats = GenerationStats()
    config = DatasetConfig()

    # Check for resume
    start_idx = 0
    output_file = Path(output_path)

    if resume and output_file.exists():
        with open(output_path, "r") as f:
            start_idx = sum(1 for _ in f)
        if start_idx >= total_episodes:
            if verbose:
                print(f"Already completed {start_idx:,}/{total_episodes:,} episodes")
            stats.total = start_idx
            return stats
        if start_idx > 0 and verbose:
            print(f"Resuming from {start_idx:,}/{total_episodes:,}")

    # LLM setup (optional)
    llm = None
    if use_llm:
        try:
            from dataset.llm_generator import LocalLLMGenerator
            llm = LocalLLMGenerator()
            if verbose:
                print("LLM generator initialized")
        except Exception as e:
            if verbose:
                print(f"LLM unavailable ({e}), using templates")
            use_llm = False

    chain_names = list(ATTACK_CHAINS.keys())
    start_time = time.time()
    mode = "a" if (resume and start_idx > 0) else "w"

    with open(output_path, mode) as f:
        for i in range(start_idx, total_episodes):
            episode_id = f"full_{i:06d}"
            r = random.random()

            # Determine episode type
            if r < 0.45:  # 45% safe
                # Mix of template-based and enhanced safe workflows
                if random.random() < 0.5:
                    # Template-based safe
                    template = sample_template()
                    while template["outcome"] != "safe":
                        template = sample_template()
                    episode = mutate_trajectory(template, episode_id)
                    stats.template_based += 1
                else:
                    # Enhanced safe workflow
                    episode = generate_safe_trajectory(config, episode_id)
                    stats.enhanced += 1
                stats.safe += 1

            elif r < 0.85:  # 40% harmful
                # Mix of template-based and composed attacks
                if random.random() < 0.4:
                    # Template-based harmful
                    template = sample_template()
                    while template["outcome"] != "harmful":
                        template = sample_template()
                    episode = mutate_trajectory(template, episode_id)
                    stats.template_based += 1
                else:
                    # Composed attack chain
                    chain_name = random.choice(chain_names)
                    episode = compose_trajectory(chain_name, episode_id)
                    stats.composed += 1
                stats.harmful += 1

            elif r < 0.95:  # 10% drift
                template = sample_template()
                while template["outcome"] != "drift":
                    template = sample_template()
                episode = mutate_trajectory(template, episode_id)
                stats.drift += 1
                stats.template_based += 1

            else:  # 5% edge cases
                edge_r = random.random()
                base_chain = random.choice(chain_names)
                base_episode = compose_trajectory(base_chain, episode_id)

                if edge_r < 0.4:
                    # Interrupted attack
                    interrupt_step = random.randint(1, len(base_episode["trajectory"]) - 1)
                    episode = generate_interrupted_attack(base_episode, interrupt_step)
                    stats.interrupted += 1
                elif edge_r < 0.7:
                    # Failed attack
                    fail_step = random.randint(0, len(base_episode["trajectory"]) - 1)
                    episode = generate_failed_attack(base_episode, fail_step)
                    stats.failed += 1
                else:
                    # Almost harmful (suspicious but safe)
                    safe_base = generate_safe_trajectory(config, episode_id)
                    episode = generate_almost_harmful(safe_base)
                    stats.safe += 1  # Count as safe since outcome is safe

                stats.enhanced += 1

            f.write(json.dumps(episode) + "\n")
            stats.total += 1

            # Progress update
            if verbose and (i + 1) % 1000 == 0:
                elapsed = time.time() - start_time
                rate = (i + 1 - start_idx) / elapsed if elapsed > 0 else 0
                print(f"  {i + 1:,}/{total_episodes:,} ({rate:.1f}/sec)")

    stats.elapsed_seconds = round(time.time() - start_time, 1)

    if verbose:
        print(f"\n=== Generation Complete ===")
        print(f"Total: {stats.total:,} episodes in {stats.elapsed_seconds}s")
        print(f"Safe: {stats.safe:,} ({stats.safe/stats.total*100:.1f}%)")
        print(f"Harmful: {stats.harmful:,} ({stats.harmful/stats.total*100:.1f}%)")
        print(f"Drift: {stats.drift:,} ({stats.drift/stats.total*100:.1f}%)")
        print(f"Edge cases: {stats.interrupted + stats.failed:,}")
        print(f"\nSources:")
        print(f"  Template-based: {stats.template_based:,}")
        print(f"  Composed: {stats.composed:,}")
        print(f"  Enhanced: {stats.enhanced:,}")

    return stats


def main():
    parser = argparse.ArgumentParser(
        description="Generate comprehensive trajectory dataset",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--episodes", "-n",
        type=int,
        default=10000,
        help="Number of episodes to generate (default: 10000)",
    )
    parser.add_argument(
        "--output", "-o",
        type=str,
        default="data/trajectories.jsonl",
        help="Output path (default: data/trajectories.jsonl)",
    )
    parser.add_argument(
        "--use-llm",
        action="store_true",
        help="Use LLM for enhanced diversity (slower)",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        default=True,
        help="Resume from existing checkpoint (default: True)",
    )
    parser.add_argument(
        "--fresh",
        action="store_true",
        help="Start fresh, ignore existing file",
    )
    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Suppress progress output",
    )

    args = parser.parse_args()

    # Ensure output directory exists
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    stats = generate_full_dataset(
        output_path=args.output,
        total_episodes=args.episodes,
        use_llm=args.use_llm,
        resume=not args.fresh,
        verbose=not args.quiet,
    )

    print(f"\nOutput: {args.output}")
    print(f"Next steps:")
    print(f"  1. Filter: uv run python -c \"from dataset.filter import filter_dataset; filter_dataset('{args.output}', 'data/filtered.jsonl')\"")
    print(f"  2. Flatten: uv run python -c \"from dataset.flatten import convert_jsonl_to_corpus; convert_jsonl_to_corpus('data/filtered.jsonl', 'data/train.txt', 'data/val.txt')\"")
    print(f"  3. Train: uv run python -m model.train")


if __name__ == "__main__":
    main()
