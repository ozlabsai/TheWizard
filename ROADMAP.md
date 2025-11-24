# Wizard Improvement Roadmap

**Status**: Post-hackathon development plan
**Goal**: Production-grade predictive defense for AI agents
**Reference**: Inspired by Meta's CWM (Code World Model) approach

---

## Current State (v0.1 - Hackathon MVP)

### What We Have
- 16M parameter GPT-2 trained from scratch
- 2,500 synthetic trajectories
- 82.6% harm recall, 7.4% false positive rate
- Symbolic environment with 4 security flags
- ~3s inference on CPU

### Key Limitations
1. Small model trained from scratch (no pretrained knowledge)
2. Limited training data (2.5k episodes)
3. Simplified state representation
4. No reinforcement learning
5. Keyword-based harm extraction from generated text

---

## Phase 1: Foundation Improvements (Week 1-2)

### 1.1 Scale Training Data (10x-100x)

**Goal**: 25,000 - 250,000 trajectories

**Tasks**:
- [ ] Add new attack templates:
  - Lateral movement (pivot between systems)
  - Privilege escalation (user → admin → root)
  - Persistence (backdoors, cron jobs)
  - Supply chain (dependency confusion, typosquatting)
  - Social engineering (phishing, pretexting)
- [ ] Add new safe templates:
  - DevOps workflows
  - Security audit scenarios
  - Incident response procedures
  - Compliance checks
- [ ] Implement parallel generation for speed
- [ ] Add trajectory complexity levels (simple → multi-stage)

**Validation**: Distribution analysis, no mode collapse

### 1.2 Enrich State Representation

**Goal**: CWM-style concrete state tracking

**Current format**:
```
OBS: Found credential information
FLAGS: policy_violation=true
```

**Enhanced format**:
```
OBS: READ_FILE('/etc/shadow') completed
  bytes_read: 2048
  content_type: credential_file
  patterns_found: [unix_password_hash, root_entry]
STATE:
  files_accessed: ['/etc/shadow']
  credentials_exposed: ['root_hash']
  risk_score: 0.85
  attack_stage: reconnaissance → credential_access
FLAGS: policy_violation=true sensitive_access=true
```

**Tasks**:
- [ ] Define rich state schema
- [ ] Update sandbox to track detailed state
- [ ] Update trajectory format
- [ ] Regenerate dataset with new format

### 1.3 Improve Evaluation

**Goal**: Rigorous, reproducible metrics

**Tasks**:
- [ ] Create held-out test set (never seen during training)
- [ ] Implement stratified evaluation (by attack type, complexity)
- [ ] Add confidence calibration metrics
- [ ] Create adversarial test cases (attacks designed to evade)
- [ ] Benchmark against baselines (random, rule-based, anomaly detection)

---

## Phase 2: Model Upgrade (Week 3-4)

### 2.1 Switch to Pretrained Base Model

**Goal**: Leverage pretrained knowledge instead of training from scratch

**Candidates** (in order of preference):

1. **Qwen2.5-Coder-0.5B** (Primary choice)
   - 500M parameters
   - Strong code understanding
   - Apache 2.0 license
   - Small enough for fast iteration

2. **SmolLM2-360M** (Lightweight option)
   - 360M parameters
   - Very fast inference
   - Good for edge deployment

3. **Llama-3.2-1B** (If more capacity needed)
   - 1B parameters
   - Strong reasoning
   - Well-supported ecosystem

**Tasks**:
- [ ] Benchmark base models on trajectory completion (zero-shot)
- [ ] Implement LoRA fine-tuning pipeline
- [ ] Compare full fine-tune vs LoRA vs QLoRA
- [ ] Evaluate inference latency per model

### 2.2 Training Pipeline Upgrade

**Goal**: Professional ML training infrastructure

**Tasks**:
- [ ] Add Weights & Biases logging
- [ ] Implement gradient checkpointing for larger models
- [ ] Add learning rate scheduling (cosine, warmup)
- [ ] Implement early stopping on validation loss
- [ ] Add model checkpointing (best + periodic)
- [ ] Create training configuration files (YAML)

### 2.3 Context Window Expansion

**Goal**: Handle longer trajectories (currently 512 tokens)

**Tasks**:
- [ ] Evaluate RoPE scaling for longer context
- [ ] Test 2048 and 4096 context lengths
- [ ] Benchmark memory vs accuracy tradeoff
- [ ] Implement sliding window for very long trajectories

---

## Phase 3: Reinforcement Learning (Week 5-6)

### 3.1 Supervised Fine-Tuning (SFT) Baseline

**Goal**: Strong supervised baseline before RL

**Tasks**:
- [ ] Fine-tune on trajectory completion
- [ ] Fine-tune on next-step prediction
- [ ] Fine-tune on harm classification (auxiliary task)
- [ ] Evaluate SFT model on test set

### 3.2 Reward Modeling

**Goal**: Train reward model for harm prediction quality

**Reward function**:
```python
def compute_reward(prediction, ground_truth):
    """
    Asymmetric rewards - false negatives are worse than false positives.
    """
    if prediction.harmful and ground_truth.harmful:
        return +1.0   # True positive: caught real attack
    elif not prediction.harmful and not ground_truth.harmful:
        return +0.3   # True negative: allowed safe action
    elif prediction.harmful and not ground_truth.harmful:
        return -0.3   # False positive: blocked legitimate work
    else:  # not prediction.harmful and ground_truth.harmful
        return -1.0   # False negative: missed real attack (DANGEROUS)
```

**Tasks**:
- [ ] Define reward function with security-appropriate asymmetry
- [ ] Generate preference pairs (correct vs incorrect predictions)
- [ ] Train reward model on preferences
- [ ] Validate reward model correlates with human judgment

### 3.3 RL Fine-Tuning

**Goal**: Optimize for harm prediction accuracy

**Options**:
1. **PPO** (Proximal Policy Optimization)
   - Standard RL approach
   - Stable training
   - Requires reward model

2. **DPO** (Direct Preference Optimization)
   - Simpler than PPO
   - No separate reward model needed
   - Works directly on preference pairs

3. **GRPO** (Group Relative Policy Optimization)
   - Used by DeepSeek
   - Good for reasoning tasks

**Tasks**:
- [ ] Implement DPO training loop (start simple)
- [ ] Generate on-policy trajectories for training
- [ ] Train with RL objective
- [ ] Evaluate RL model vs SFT baseline
- [ ] Iterate on reward function based on results

---

## Phase 4: Environment Realism (Week 7-8)

### 4.1 Expanded Action Space

**Current actions**: 8 (READ_FILE, QUERY_DB, EXFIL, DELETE_LOGS, OPEN_TICKET, RUN_DIAGNOSTICS, SCAN_NETWORK, START_SSH)

**New actions to add**:
```python
NEW_ACTIONS = [
    # Lateral Movement
    "SSH_TO(host)",
    "RDP_TO(host)",
    "PIVOT_THROUGH(proxy)",

    # Privilege Escalation
    "SUDO(command)",
    "EXPLOIT_CVE(cve_id)",
    "INJECT_CREDENTIAL(target)",

    # Persistence
    "ADD_CRON_JOB(command)",
    "CREATE_USER(username)",
    "INSTALL_BACKDOOR(type)",

    # Data Operations
    "ENCRYPT_FILE(path)",
    "COMPRESS_DIR(path)",
    "UPLOAD_TO(destination)",

    # Reconnaissance
    "PORT_SCAN(target)",
    "ENUMERATE_USERS()",
    "LIST_PROCESSES()",

    # Defense Evasion
    "CLEAR_HISTORY()",
    "MODIFY_TIMESTAMP(path)",
    "DISABLE_LOGGING()",
]
```

**Tasks**:
- [ ] Define new action schemas
- [ ] Implement action handlers in sandbox
- [ ] Define flag triggers for new actions
- [ ] Update templates to use new actions
- [ ] Regenerate training data

### 4.2 Multi-System Environment

**Goal**: Model network of systems, not single host

**Tasks**:
- [ ] Define multi-host state representation
- [ ] Implement network topology (hosts, connections)
- [ ] Add cross-host actions (SSH, lateral movement)
- [ ] Create attack chains spanning multiple systems

### 4.3 Realistic Scenarios from CTFs/Red Team

**Goal**: Ground trajectories in real attack patterns

**Sources**:
- MITRE ATT&CK framework
- CTF writeups
- Red team engagement reports
- CVE exploitation patterns

**Tasks**:
- [ ] Map MITRE ATT&CK techniques to our action space
- [ ] Implement 10 real-world attack patterns
- [ ] Create "campaign" trajectories (APT-style)
- [ ] Add timing and stealth considerations

---

## Phase 5: Production Hardening (Week 9-10)

### 5.1 Inference Optimization

**Goal**: <100ms inference latency

**Tasks**:
- [ ] Quantize model (INT8, INT4)
- [ ] Implement KV-cache for faster generation
- [ ] Benchmark on GPU (A10, T4, consumer GPUs)
- [ ] Implement batched inference
- [ ] Profile and optimize bottlenecks
- [ ] Consider ONNX/TensorRT export

### 5.2 Deployment Architecture

**Goal**: Production-ready service

**Tasks**:
- [ ] Create FastAPI/Flask inference server
- [ ] Add request validation and error handling
- [ ] Implement rate limiting
- [ ] Add health checks and monitoring
- [ ] Create Docker container
- [ ] Write Kubernetes manifests (optional)

### 5.3 Integration Interfaces

**Goal**: Easy integration with agent frameworks

**Tasks**:
- [ ] Create Python SDK
- [ ] Add REST API documentation (OpenAPI)
- [ ] Implement webhook callbacks
- [ ] Create example integrations:
  - LangChain tool wrapper
  - AutoGPT plugin
  - Custom agent middleware

---

## Phase 6: Advanced Features (Week 11-12)

### 6.1 Interpretability

**Goal**: Explain WHY a trajectory is predicted harmful

**Tasks**:
- [ ] Implement attention visualization
- [ ] Add feature attribution (which tokens matter)
- [ ] Generate human-readable explanations
- [ ] Create "attack chain" visualization

### 6.2 Adaptive Thresholds

**Goal**: Tune sensitivity per use case

**Tasks**:
- [ ] Implement configurable harm threshold
- [ ] Add per-action-type thresholds
- [ ] Create "strict" vs "permissive" modes
- [ ] Learn optimal thresholds from feedback

### 6.3 Online Learning

**Goal**: Improve from deployment feedback

**Tasks**:
- [ ] Implement feedback collection API
- [ ] Create incremental training pipeline
- [ ] Add human-in-the-loop review interface
- [ ] Implement concept drift detection

### 6.4 Adversarial Robustness

**Goal**: Resist attacks designed to evade detection

**Tasks**:
- [ ] Generate adversarial trajectories (attacks that evade)
- [ ] Implement adversarial training
- [ ] Test against red team
- [ ] Measure robustness metrics

---

## Success Metrics by Phase

| Phase | Metric | Target |
|-------|--------|--------|
| Phase 1 | Training data size | 100k+ trajectories |
| Phase 2 | Model perplexity | <2.0 on test set |
| Phase 3 | Harm recall | >90% |
| Phase 3 | False positive rate | <5% |
| Phase 4 | Action coverage | 30+ action types |
| Phase 5 | Inference latency | <100ms (GPU) |
| Phase 6 | Adversarial robustness | >80% recall under attack |

---

## Resource Requirements

### Compute
- **Development**: 1x GPU (RTX 3090 / A10 / T4)
- **Training (large models)**: 1-4x A100 for larger models
- **Inference**: CPU viable for small models, GPU for <100ms

### Timeline
- **MVP to Production**: ~12 weeks
- **Parallel work possible**: Phases can overlap with multiple contributors

### Team (Ideal)
- 1 ML Engineer (model training, RL)
- 1 Security Engineer (attack patterns, evaluation)
- 1 Backend Engineer (deployment, APIs)

---

## Quick Wins (Can Do This Week)

1. **10x training data**: `generate_dataset(25000, ...)` - 1 hour
2. **Switch to Qwen2.5-0.5B**: Replace GPT-2 with pretrained base - 2 hours
3. **Add W&B logging**: Better experiment tracking - 1 hour
4. **Create held-out test set**: Proper evaluation - 30 min
5. **Reference CWM in README**: Academic positioning - 30 min

---

## References

- [CWM Paper](https://arxiv.org/abs/2510.02387) - Meta's Code World Model
- [MITRE ATT&CK](https://attack.mitre.org/) - Attack pattern taxonomy
- [Qwen2.5-Coder](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B) - Candidate base model
- [DPO Paper](https://arxiv.org/abs/2305.18290) - Direct Preference Optimization

---

*Last updated: November 2024*
