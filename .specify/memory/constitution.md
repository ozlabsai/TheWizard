<!--
================================================================================
SYNC IMPACT REPORT
================================================================================
Version change: 1.0.0 → 1.1.0 (Model flexibility update)
Modified principles: None renamed
Added sections: None
Removed sections: None
Modified sections:
  - Hackathon Constraints: Updated model size to reflect LoRA fine-tuning approach
    (was: 10-20M parameters, now: flexible with LoRA adapters)
Templates requiring updates:
  - .specify/templates/plan-template.md: ✅ No updates needed (Constitution Check section compatible)
  - .specify/templates/spec-template.md: ✅ No updates needed (requirements format compatible)
  - .specify/templates/tasks-template.md: ✅ No updates needed (phase structure compatible)
  - .specify/templates/checklist-template.md: ✅ No updates needed
  - .specify/templates/agent-file-template.md: ✅ No updates needed
Follow-up TODOs: None
================================================================================
-->

# Wizard Constitution

## Core Principles

### I. Working Code First

All features MUST be demonstrable within the hackathon timeframe. Every implementation decision prioritizes:

- Functional prototypes over comprehensive documentation
- Hardcoded values over configurable abstractions (until proven needed)
- Single-file implementations before modular refactoring
- Console output before UI polish

**Rationale**: Wizard is a hackathon project. Judges evaluate working demos, not elegant architecture. Ship something that runs.

### II. Symbolic Simplicity

The cyber micro-world MUST remain symbolic and deterministic:

- No real OS calls, network requests, or file system access in the sandbox
- State changes MUST be predictable and traceable
- New actions MUST define explicit flag mutations upfront
- Environment state MUST serialize to human-readable text for LM training

**Rationale**: Complexity in the sandbox undermines the core research goal. The model learns patterns, not real system behavior.

### III. YAGNI (You Ain't Gonna Need It)

Code MUST solve only the current, concrete requirement:

- No generic abstractions until 3+ concrete use cases exist
- No feature flags, configuration systems, or plugin architectures
- No backward compatibility layers—change code directly
- No "future-proofing" comments or TODO placeholders for hypothetical needs

**Rationale**: Premature abstraction is the root of hackathon failure. Three similar lines beat one clever abstraction.

### IV. ML Pipeline Clarity

The trajectory-to-model pipeline MUST be traceable:

- Raw trajectories → JSONL with documented schema
- JSONL → text corpus via explicit flattening rules
- Text corpus → model training with logged hyperparameters
- Model outputs → parsed predictions with clear format expectations

**Rationale**: When the model misbehaves, debugging requires knowing exactly what went in and what should come out.

### V. UV as Package Manager

All Python dependencies MUST be managed via UV:

- Use `uv pip install` for package installation
- Use `uv run` for script execution
- Maintain `pyproject.toml` as the single source of dependencies
- No manual pip or conda commands

**Rationale**: Consistent tooling eliminates "works on my machine" issues during hackathon crunch time.

## Development Workflow

### Iteration Cycle

1. **Define** the next demonstrable feature (what will judges see?)
2. **Implement** the minimal working version
3. **Validate** with a manual test (run it, see output)
4. **Commit** with a clear message describing what now works
5. **Repeat** until demo-ready

### Code Organization

- `sandbox/` — Symbolic environment and action definitions
- `dataset/` — Trajectory generation and data processing
- `model/` — Training scripts and checkpoints
- `engine/` — Runtime prediction and intervention logic
- `demo/` — Demo scripts and UI (if applicable)

## Hackathon Constraints

These constraints reflect the hackathon context and MUST be respected:

| Constraint | Limit | Enforcement |
|------------|-------|-------------|
| Model approach | LoRA fine-tuning of pretrained models OR scratch GPT-2 | Config in model/config.py (BASE_MODEL) |
| Training time | <1 hour on single GPU/CPU | Monitor and abort if exceeded |
| Inference latency | Sub-second per prediction (GPU), ~3s acceptable (CPU) | Profile before demo |
| Dataset size | 2-5k episodes | Generator output cap |

**Note**: The project supports both approaches: (1) LoRA fine-tuning of larger pretrained models (e.g., Qwen3-0.6B) for better reasoning, or (2) training a small GPT-2 from scratch (~16M params) for minimal dependencies. Select via `BASE_MODEL` in config.

## Governance

### Amendment Process

1. Propose change with rationale in PR description
2. Update constitution version according to semantic versioning:
   - **MAJOR**: Principle removal or fundamental redefinition
   - **MINOR**: New principle or significant guidance expansion
   - **PATCH**: Clarifications, wording improvements
3. Update `LAST_AMENDED_DATE` to change date

### Compliance

- All PRs MUST not violate YAGNI (Principle III)
- Sandbox changes MUST maintain symbolic simplicity (Principle II)
- Pipeline changes MUST preserve traceability (Principle IV)
- Complexity MUST be justified if it exceeds hackathon constraints

**Version**: 1.1.0 | **Ratified**: 2025-11-23 | **Last Amended**: 2025-11-30
