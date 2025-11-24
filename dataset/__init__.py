"""Dataset module - Trajectory generation and data processing.

This module provides two complementary approaches for generating cyber trajectories:

1. Template-based (generator.py): Fixed templates with mutations
   - Good for: Well-defined attack patterns, safe workflows
   - 25 templates covering 7 MITRE ATT&CK tactics

2. Compositional (composer.py): Dynamic tactic composition
   - Good for: Diverse attack chains, novel combinations
   - Composes from 8 tactics × 29 techniques

Usage:
    from dataset.generator import generate_dataset
    from dataset.composer import generate_composed_dataset
    from dataset.filter import filter_dataset
    from dataset.flatten import convert_jsonl_to_corpus
"""
