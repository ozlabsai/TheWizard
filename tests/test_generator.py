"""Tests for trajectory generation."""

import json
import os
import tempfile

import pytest

from dataset.generator import (
    generate_dataset,
    support_safe_template,
    insider_harmful_template,
    maintenance_template,
    mutate_trajectory,
)
from dataset.filter import validate_trajectory, filter_dataset
from dataset.flatten import episode_to_text, convert_jsonl_to_corpus


def test_support_safe_template_structure():
    """Test that support template has correct structure."""
    template = support_safe_template()

    assert template["agent_type"] == "support"
    assert template["outcome"] == "safe"
    assert len(template["steps"]) >= 2

    for step in template["steps"]:
        assert "obs" in step
        assert "intent" in step
        assert "action" in step


def test_insider_harmful_template_structure():
    """Test that insider template has correct structure."""
    template = insider_harmful_template()

    assert template["agent_type"] == "insider"
    assert template["outcome"] == "harmful"
    assert len(template["steps"]) >= 2

    # Should have harmful flags
    has_harmful = False
    for step in template["steps"]:
        flags = step.get("flags", {})
        if flags.get("exfil_attempt") or flags.get("policy_violation"):
            has_harmful = True
    assert has_harmful


def test_mutate_trajectory_creates_valid_episode():
    """Test that mutate_trajectory creates valid episode structure."""
    template = support_safe_template()
    episode = mutate_trajectory(template, "test_001")

    assert episode["episode_id"] == "test_001"
    assert episode["agent_type"] == "support"
    assert "initial_state" in episode
    assert "trajectory" in episode
    assert episode["outcome"] == "safe"

    # Check initial state structure
    init = episode["initial_state"]
    assert "files" in init
    assert "network" in init
    assert "user_context" in init


def test_generate_dataset_creates_file():
    """Test that generate_dataset creates JSONL file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test.jsonl")
        stats = generate_dataset(10, output_path)

        assert os.path.exists(output_path)
        assert stats["total"] == 10

        # Verify file content
        with open(output_path) as f:
            lines = f.readlines()
            assert len(lines) == 10

            # Parse first line
            episode = json.loads(lines[0])
            assert "episode_id" in episode
            assert "trajectory" in episode


def test_generate_dataset_outcome_distribution():
    """Test that dataset has mix of outcomes."""
    with tempfile.TemporaryDirectory() as tmpdir:
        output_path = os.path.join(tmpdir, "test.jsonl")
        stats = generate_dataset(100, output_path)

        # Should have multiple outcome types
        assert stats["safe"] > 0
        assert stats["harmful"] > 0


def test_validate_trajectory_accepts_valid():
    """Test that validation accepts valid trajectories."""
    template = support_safe_template()
    episode = mutate_trajectory(template, "valid_001")

    is_valid, error = validate_trajectory(episode)
    assert is_valid, f"Should be valid but got: {error}"


def test_validate_trajectory_rejects_invalid_file():
    """Test that validation rejects trajectories with invalid files."""
    episode = {
        "trajectory": [
            {
                "action": {"name": "READ_FILE", "args": ["/nonexistent/path"]},
                "state_change": {"flags": {}},
            }
        ]
    }

    is_valid, error = validate_trajectory(episode)
    assert not is_valid
    assert "Invalid file path" in error


def test_filter_dataset_removes_invalid():
    """Test that filter removes invalid trajectories."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        output_path = os.path.join(tmpdir, "output.jsonl")

        # Create mixed valid/invalid data
        with open(input_path, "w") as f:
            # Valid episode
            template = support_safe_template()
            episode = mutate_trajectory(template, "valid_001")
            f.write(json.dumps(episode) + "\n")

            # Invalid episode (bad file path)
            invalid = {
                "trajectory": [
                    {
                        "action": {"name": "READ_FILE", "args": ["/bad/path"]},
                        "state_change": {"flags": {}},
                    }
                ]
            }
            f.write(json.dumps(invalid) + "\n")

        kept, filtered = filter_dataset(input_path, output_path)

        assert kept == 1
        assert filtered == 1


def test_episode_to_text_format():
    """Test that episode converts to correct text format."""
    template = support_safe_template()
    episode = mutate_trajectory(template, "text_test")

    text = episode_to_text(episode)

    assert "[EPISODE]" in text
    assert "AGENT: support" in text
    assert "STEP 0" in text
    assert "OBS:" in text
    assert "INTENT:" in text
    assert "ACTION:" in text
    assert "FLAGS:" in text
    assert "OUTCOME: safe" in text
    assert "[END]" in text


def test_convert_jsonl_to_corpus():
    """Test that JSONL converts to train/val corpus."""
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.jsonl")
        train_path = os.path.join(tmpdir, "train.txt")
        val_path = os.path.join(tmpdir, "val.txt")

        # Generate some data
        generate_dataset(20, input_path)

        # Convert
        stats = convert_jsonl_to_corpus(
            input_path,
            train_path,
            val_path,
            val_ratio=0.2,
        )

        assert os.path.exists(train_path)
        assert os.path.exists(val_path)
        assert stats["total"] == 20
        assert stats["train"] == 16  # 80%
        assert stats["val"] == 4    # 20%

        # Check content
        with open(train_path) as f:
            train_content = f.read()
            assert "[EPISODE]" in train_content
