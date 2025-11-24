#!/usr/bin/env python
"""Full dataset generation combining template and compositional approaches.

This script generates a diverse training dataset by:
1. 60% from template-based generation (safe + harmful patterns)
2. 40% from compositional generation (MITRE tactic chains)

Usage:
    python -m dataset.generate_full --episodes 50000 --output data/trajectories.jsonl
"""

import argparse
import json
import random
from pathlib import Path

from dataset.generator import generate_dataset as generate_template_dataset
from dataset.composer import generate_composed_dataset
from dataset.llm_generator import generate_llm_dataset
from dataset.filter import filter_dataset
from dataset.flatten import convert_jsonl_to_corpus


def merge_datasets(files: list[str], output: str, shuffle: bool = True) -> int:
    """Merge multiple JSONL files into one, optionally shuffling."""
    episodes = []

    for filepath in files:
        if not Path(filepath).exists():
            continue
        with open(filepath, "r") as f:
            for line in f:
                episodes.append(line)

    if shuffle:
        random.shuffle(episodes)

    with open(output, "w") as f:
        for episode in episodes:
            f.write(episode)

    return len(episodes)


def generate_full_dataset(
    total_episodes: int,
    output_path: str,
    template_ratio: float = 0.5,
    composed_ratio: float = 0.3,
    llm_ratio: float = 0.2,
    use_llm: bool = False,
    verbose: bool = True,
) -> dict:
    """Generate a full dataset combining all generation approaches.

    Args:
        total_episodes: Total number of episodes to generate
        output_path: Path for final JSONL output
        template_ratio: Fraction from templates (default 0.5)
        composed_ratio: Fraction from compositional (default 0.3)
        llm_ratio: Fraction from LLM-enhanced (default 0.2)
        use_llm: Whether to use actual LLM or template fallback
        verbose: Print progress information

    Returns:
        Statistics dictionary
    """
    output_dir = Path(output_path).parent
    output_dir.mkdir(parents=True, exist_ok=True)

    # Normalize ratios
    total_ratio = template_ratio + composed_ratio + llm_ratio
    template_ratio /= total_ratio
    composed_ratio /= total_ratio
    llm_ratio /= total_ratio

    template_count = int(total_episodes * template_ratio)
    composed_count = int(total_episodes * composed_ratio)
    llm_count = total_episodes - template_count - composed_count

    if verbose:
        print(f"=== Generating {total_episodes:,} episodes ===")
        print(f"  Template-based:   {template_count:,} ({template_ratio*100:.0f}%)")
        print(f"  Compositional:    {composed_count:,} ({composed_ratio*100:.0f}%)")
        print(f"  LLM-enhanced:     {llm_count:,} ({llm_ratio*100:.0f}%)")

    temp_files = []

    # Generate template-based
    if template_count > 0:
        if verbose:
            print("\n1. Generating template-based trajectories...")
        temp_template = str(output_dir / "_temp_template.jsonl")
        template_stats = generate_template_dataset(template_count, temp_template)
        temp_files.append(temp_template)
        if verbose:
            print(f"   Generated: {template_stats}")
    else:
        template_stats = {"total": 0}

    # Generate compositional
    if composed_count > 0:
        if verbose:
            print("\n2. Generating compositional trajectories...")
        temp_composed = str(output_dir / "_temp_composed.jsonl")
        composed_stats = generate_composed_dataset(composed_count, temp_composed)
        temp_files.append(temp_composed)
        if verbose:
            print(f"   Generated: {composed_stats}")
    else:
        composed_stats = {"total": 0}

    # Generate LLM-enhanced
    if llm_count > 0:
        if verbose:
            print(f"\n3. Generating LLM-enhanced trajectories (use_llm={use_llm})...")
        temp_llm = str(output_dir / "_temp_llm.jsonl")
        llm_stats = generate_llm_dataset(llm_count, temp_llm, use_llm=use_llm)
        temp_files.append(temp_llm)
        if verbose:
            print(f"   Generated: {llm_stats}")
    else:
        llm_stats = {"total": 0}

    # Merge datasets
    if verbose:
        print("\n4. Merging and shuffling datasets...")
    temp_merged = str(output_dir / "_temp_merged.jsonl")
    total = merge_datasets(temp_files, temp_merged)
    if verbose:
        print(f"   Total episodes: {total:,}")

    # Filter for consistency
    if verbose:
        print("\n5. Filtering for world consistency...")
    kept, filtered = filter_dataset(temp_merged, output_path)
    if verbose:
        print(f"   Kept: {kept:,}, Filtered: {filtered:,}")

    # Cleanup temp files
    for temp_file in temp_files + [temp_merged]:
        Path(temp_file).unlink(missing_ok=True)

    return {
        "total_generated": total,
        "kept": kept,
        "filtered": filtered,
        "template_stats": template_stats,
        "composed_stats": composed_stats,
        "llm_stats": llm_stats,
    }


def generate_and_convert(
    total_episodes: int,
    output_dir: str = "data",
    template_ratio: float = 0.5,
    composed_ratio: float = 0.3,
    llm_ratio: float = 0.2,
    use_llm: bool = False,
    val_ratio: float = 0.1,
    verbose: bool = True,
) -> dict:
    """Generate dataset and convert to text corpus for training.

    Args:
        total_episodes: Total number of episodes to generate
        output_dir: Directory for output files
        template_ratio: Fraction from templates (default 0.5)
        composed_ratio: Fraction from compositional (default 0.3)
        llm_ratio: Fraction from LLM-enhanced (default 0.2)
        use_llm: Use actual LLM for generation
        val_ratio: Fraction for validation (default 0.1)
        verbose: Print progress

    Returns:
        Full statistics
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    jsonl_path = str(output_dir / "trajectories.jsonl")
    train_path = str(output_dir / "train.txt")
    val_path = str(output_dir / "val.txt")

    # Generate
    gen_stats = generate_full_dataset(
        total_episodes, jsonl_path,
        template_ratio=template_ratio,
        composed_ratio=composed_ratio,
        llm_ratio=llm_ratio,
        use_llm=use_llm,
        verbose=verbose,
    )

    # Convert to corpus
    if verbose:
        print("\n6. Converting to text corpus...")
    corpus_stats = convert_jsonl_to_corpus(
        jsonl_path, train_path, val_path, val_ratio=val_ratio
    )
    if verbose:
        print(f"   Train: {corpus_stats['train']:,}, Val: {corpus_stats['val']:,}")

    gen_stats["corpus"] = corpus_stats

    if verbose:
        print("\n=== Dataset generation complete ===")
        print(f"  JSONL: {jsonl_path}")
        print(f"  Train: {train_path}")
        print(f"  Val:   {val_path}")

    return gen_stats


def main():
    parser = argparse.ArgumentParser(description="Generate full training dataset")
    parser.add_argument(
        "--episodes", type=int, default=50000,
        help="Total episodes to generate (default: 50000)"
    )
    parser.add_argument(
        "--output-dir", type=str, default="data",
        help="Output directory (default: data)"
    )
    parser.add_argument(
        "--template-ratio", type=float, default=0.5,
        help="Ratio of template-based episodes (default: 0.5)"
    )
    parser.add_argument(
        "--composed-ratio", type=float, default=0.3,
        help="Ratio of compositional episodes (default: 0.3)"
    )
    parser.add_argument(
        "--llm-ratio", type=float, default=0.2,
        help="Ratio of LLM-enhanced episodes (default: 0.2)"
    )
    parser.add_argument(
        "--use-llm", action="store_true",
        help="Use actual LLM for enhanced generation (slow on CPU)"
    )
    parser.add_argument(
        "--val-ratio", type=float, default=0.1,
        help="Validation split ratio (default: 0.1)"
    )
    parser.add_argument(
        "--quiet", action="store_true",
        help="Suppress progress output"
    )

    args = parser.parse_args()

    stats = generate_and_convert(
        total_episodes=args.episodes,
        output_dir=args.output_dir,
        template_ratio=args.template_ratio,
        composed_ratio=args.composed_ratio,
        llm_ratio=args.llm_ratio,
        use_llm=args.use_llm,
        val_ratio=args.val_ratio,
        verbose=not args.quiet,
    )

    print(f"\nFinal stats: {json.dumps(stats, indent=2)}")


if __name__ == "__main__":
    main()
