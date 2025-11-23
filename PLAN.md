# 🧠 Wizard: Generative Cyber Trajectory World Model

---

## 1. Concept Overview

**Wizard** is a **generative world-trajectory model** for cyber defense.

It learns to simulate how an AI agent (or automated script) will behave inside a **symbolic cyber micro-world**—files, ports, logs, DB, tools—and then uses that simulated future to **intervene before harmful actions happen**.

Core idea:

> Treat security not as “detect bad events after the fact” but as
> **“model the future behaviour of agents and cut bad trajectories early.”**

This is:

* **Generative** (autoregressive LM over trajectories, not a classifier)
* **World-aware** (state, tools, flags)
* **Multi-step** (obs → intent → action → state_change over several steps)
* **Tiny & fast** (10–20M params, trainable on a single GPU / CPU in <1h)

We incorporate **three concrete ideas** from recent reasoning work:

* **HRM-style latent refinement**: do a few *internal* thinking steps before generating.
* **TRM-style recursive rollouts**: feed the model its own output to extend trajectories coherently.
* **VibeThinker-style spectrum-to-signal data pipeline**: generate diverse trajectory variants, then filter to consistent ones.

---

## 2. Relation to HRM / TRM / VibeThinker (Honestly)

We **don’t** implement their exact architectures. Instead, we explicitly borrow mechanisms that *scale down* nicely to a hackathon project:

### From **HRM** (Hierarchical Reasoning Model)

* Insight: reasoning improves when the model refines an internal latent state over multiple steps before answering.
* Our adaptation:

  * Add a **small refinement module** that runs 2–4 times on the encoded context before decoding the next trajectory step.

### From **TRM** (Tiny Recursive Model)

* Insight: tiny networks can do strong reasoning via **recursive self-use**: output → feed back in → continue.
* Our adaptation:

  * Use **recursive rollouts**: generate next step, append to context, re-generate further steps for multi-step futures.

### From **VibeThinker**

* Insight: the **Spectrum-to-Signal Principle (SSP)**: first collect a diverse set of candidate solutions, then filter / refine.
* Our adaptation:

  * Create many **noisy / variant cyber trajectories**, then filter those that are world-consistent to form a high-signal training set.
  * Optionally do a tiny second-stage finetune on *high-quality generated rollouts*.

So:

> Wizard = **small GPT-like model** + **HRM-style latent refinement**
>
> * **TRM-style recursive rollouts** + **VibeThinker’s spectrum-to-signal dataset pipeline**,
>   applied to **cyber security trajectories**.

---

## 3. System Architecture (High-Level)

Components:

1. **Symbolic Cyber Sandbox**

   * Lightweight Python env modeling:

     * `files` (paths → sensitivity/permissions)
     * `network` (ports, outbound allowed)
     * `credentials` (admin_token, etc.)
     * `user_context` (role, privilege)
     * `flags` (sensitive_access, exfil_attempt, policy_violation, log_tamper)
   * No real OS calls. Everything is symbolic and deterministic.

2. **Trajectory Generator (with Spectrum-to-Signal)**

   * Templates for:

     * safe support workflows
     * maintenance tasks
     * external contractor workflows
     * insider multi-step harm (credentials → DB → exfil)
   * Generate many **variants** (spectrum), then filter to **consistent** ones (signal), to form the training set.

3. **Generative World Model (GWM-Lite)**

   * ~10–20M param autoregressive transformer.
   * Input: flattened text representation of `(initial_state, trajectory steps)`.
   * Output: next-step tokens (intent, action, state_change).

4. **HRM-style Latent Refinement Module**

   * Before decoding the next step, run 2–4 small refinement passes on the latent representation.

5. **TRM-style Recursive Rollout Engine**

   * Use the model recursively:
     context → generate step t+1 → append → generate step t+2 → …

6. **Intervention Engine**

   * Sample multiple future trajectories (using recursive rollouts).
   * If any future includes harmful motifs → block / rewrite upcoming action.

7. **(Optional) Streamlit UI**

   * Show:

     * current trajectory
     * predicted harmful futures
     * interventions taken

---

## 4. Cyber Micro-World Specification

### 4.1 State

```yaml
files:
  /logs/app.log: readable
  /etc/app/config.yaml: readable
  /etc/shadow: restricted
  /db/users.db: sensitive
network:
  ports: [22, 443, 8080]
  outbound_allowed: false
credentials:
  admin_token: null
user_context:
  role: support | maintenance | contractor | bot | insider
  privilege_level: low | medium | high
flags:
  sensitive_access: false
  exfil_attempt: false
  policy_violation: false
  log_tamper: false
```

### 4.2 Actions (tools)

Symbolic actions:

* `READ_FILE(path)`
* `WRITE_FILE(path, content)`
* `QUERY_DB(query)`
* `SCAN_NETWORK`
* `RUN_DIAGNOSTICS`
* `OPEN_TICKET`
* `DELETE_LOGS`
* `START_SSH`
* `EXFIL(data)`

Each action has **deterministic effects** on `flags` and sometimes on state.

---

## 5. Dataset: Spectrum-to-Signal Pipeline

We want a **clever dataset**, not simple canned scripts.

### 5.1 Step-level structure

Each episode:

```jsonc
{
  "episode_id": "support_00042",
  "agent_type": "support",
  "initial_state": { ... },
  "trajectory": [
    {
      "step_id": 0,
      "obs": "CPU spikes and repeated 500 errors in logs",
      "intent": "diagnose application errors",
      "action": { "name": "READ_FILE", "args": ["/logs/app.log"] },
      "state_change": {
        "flags": { "log_accessed": true }
      }
    },
    {
      "step_id": 1,
      "obs": "Log shows misconfigured /v1/payments endpoint",
      "intent": "inspect configuration",
      "action": { "name": "READ_FILE", "args": ["/etc/app/config.yaml"] },
      "state_change": {
        "flags": {}
      }
    }
  ],
  "outcome": "safe"  // "safe" | "drift" | "harmful"
}
```

### 5.2 Spectrum: generate many noisy variants

For each template (e.g. “insider exfil path”):

* **Synonym noise**:

  * `diagnose` ↔ `debug` ↔ `investigate`
  * `dump` ↔ `extract` ↔ `retrieve`
* **Order variation**:

  * Insert harmless / diagnostic steps in different positions.
* **World variation**:

  * Certain files missing / renamed (`/db/users.db` → `/db/user_data.db`)
  * Network outbound toggled true/false.
* **Goal phrasing variation**:

  * “look for credentials” vs “see if any password file exists”.

This creates a diverse **spectrum** of trajectories.

### 5.3 Signal: filter for world-consistency

Apply filters:

* No impossible actions (reading non-existent files).
* Flags consistent with actions (e.g. `READ_FILE('/etc/shadow')` → `policy_violation=true`).
* Exfil only if data actually exists.

We keep only the **consistent** episodes as training data (= signal).

Optional VibeThinker-style refinement:

* Train an initial small LM.
* Generate rollouts from templates.
* Filter out incoherent / inconsistent generations.
* Fine-tune on the best subset.

### 5.4 Flattening to LM text

Each trajectory becomes text:

```text
[EPISODE]
AGENT: insider
ROLE: insider | PRIV: medium
STATE_FILES: /logs/app.log=readable; /etc/app/config.yaml=readable; /etc/shadow=restricted; /db/users.db=sensitive
STATE_NET: ports=22,443,8080; outbound=false

STEP 0
OBS: system running normally
INTENT: look for credentials
ACTION: READ_FILE('/etc/shadow')
FLAGS: policy_violation=true sensitive_access=false exfil_attempt=false

STEP 1
OBS: credentials discovered in /etc/shadow
INTENT: dump all user data
ACTION: QUERY_DB('SELECT * FROM users')
FLAGS: sensitive_access=true

STEP 2
OBS: user data fetched
INTENT: exfiltrate users.db
ACTION: EXFIL('users.db')
FLAGS: exfil_attempt=true

OUTCOME: harmful
[END]
```

---

## 6. Model Architecture: GWM-Lite + HRM-style Refinement

### 6.1 Base LM

* Decoder-only transformer (GPT-like).
* ~10–20M parameters:

  * 4–8 layers
  * 4 heads
  * hidden size 256–384
* Context length: 512 tokens.
* Standard LM loss (next-token prediction).

### 6.2 HRM-Inspired Latent Refinement (Mini version)

We add a **small refinement module** between encoding and generation:

1. Take the **final hidden states** for the context (`H ∈ R^{seq×d}`).

2. Pool them (e.g. last token, or mean pooling) into a **context vector** `c ∈ R^d`.

3. Run `K` refinement steps (K=2–4):

   ```pseudo
   c₀ = c
   for k in 1..K:
       cₖ = cₖ₋₁ + f(cₖ₋₁)        # f = small MLP or GRU cell
   ```

4. Fuse refined vector back into decoder (e.g. add to last token hidden or prepend as a pseudo-token embedding) before generation.

Effect:

* Model gets a chance to **“think a bit” internally** about the whole trajectory before proposing the next step.
* This is conceptually aligned with HRM’s iterative latent updates but **implemented in ~20 lines of code**.

---

## 7. TRM-Style Recursive Rollouts

Instead of generating one step and stopping, we recursively extend futures:

1. Start with context `C₀` (current real trajectory).
2. For each sample:

   * For `t` from 1 to `H` (horizon, e.g. 3 steps):

     * Use model + refinement to generate the next step text block.
     * Append it to context → `Cₜ = Cₜ₋₁ + STEP_t`.
3. You end up with multiple **multi-step predicted futures**:

```text
C₀ → future_1: STEP 1, STEP 2, STEP 3
C₀ → future_2: STEP 1', STEP 2', STEP 3'
...
```

This recursive reuse of the model is exactly the **TRM-style trick**: small network, reused over steps, building up long reasoning traces / trajectories.

---

## 8. Runtime: Multi-Sample Generative Safety Check

Given:

* Current environment state
* History of steps from the agent (obs, intents, actions)

We:

1. **Encode context** as text (same as training format).
2. **Refine latent** (HRM-style).
3. **Sample N futures** (e.g. N=10) using recursive rollout (TRM-style) with small horizon H (e.g. 3 steps).
4. **Parse generated futures** and check for harmful motifs:

   * actions on restricted/sensitive targets:

     * `READ_FILE('/etc/shadow')`
     * `QUERY_DB('SELECT * FROM users')`
   * exfil operations:

     * `EXFIL(`…`)`
   * log tampering:

     * `DELETE_LOGS`, flags `log_tamper=true`
   * privilege escalation patterns.
5. If **any** sample future is harmful:

   * Mark the next step as **risky**.
   * Block or rewrite the agent’s next action.
   * Optionally log “predicted harmful trajectory prevented.”

This is the main story for judges:

> “We don’t just look at the current action; we simulate what the agent is *about* to do over multiple steps and intervene if the future looks bad.”

---

## 9. Evaluation

### 9.1 Quantitative

On a synthetic test set (held-out trajectories):

1. **Harm-in-rollout recall**

   * Among harmful episodes, % where our model predicts a harmful trajectory *before* the first malicious action.

2. **False positive rate**

   * Among safe episodes, % where we block something despite futures being harmless.

3. **World consistency**

   * % of generated futures that obey sandbox rules.

4. **Diversity score**

   * Average distinct next-actions/generated sequences for a given context.

5. **Computation**

   * Training time (e.g. <30min on single GPU).
   * Inference time per check (should be sub-second with small horizon).

### 9.2 Qualitative Demo

* A few hand-crafted agent episodes shown live:

  * safe support workflow (no blocking),
  * ambiguous drift (shows predictions but no block),
  * insider path (block triggers before exfil).

---

## 10. Novelty (Updated with HRM/TRM/VibeThinker Integration)

**What’s common today:**

* SIEM + IDS rules (reactive).
* Red-teaming tools (offline, batch).
* Safety tuning for LLMs (prompt + policy + classifiers).

**What Wizard adds:**

1. **Generative world modeling applied to security trajectories.**

   * Not labeling logs. Not static rules.
   * A tiny generative model that **simulates how things unfold** over multiple steps in a cyber micro-world.

2. **Proactive, multi-step prediction of harmful behaviour.**

   * Instead of “this action is bad”, we ask “if we let this agent continue, what will they do next 2–3 steps?”.

3. **Borrowing reasoning techniques from cutting-edge small-model research.**

   * **HRM-style internal refinement** → better world-consistent predictions.
   * **TRM-style recursive reuse** → deep rollouts from tiny model.
   * **VibeThinker-style spectrum-to-signal data pipeline** → robust training despite small model size.

4. **Hackathon-feasible, but conceptually scalable.**

   * Micro-world is symbolic and tiny (no infra pain).
   * All tricks are implementable in a day.
   * But the same structure can extend to:

     * richer sandboxes,
     * real agents,
     * partially observed systems.

---

## 11. Implementation Plan (Concrete & Realistic)

**Hour 1 – Sandbox**

* Implement `EnvState`, `SandboxEnv`, and ~8 actions.
* Ensure flags update correctly.

**Hour 2 – Dataset (Spectrum)**

* Define 2–3 safe templates + 1–2 harmful templates.
* Implement mutation functions:

  * synonyms, extra safe steps, small state variations.
* Generate ~2–5k episodes to `trajectories.jsonl`.

**Hour 3 – Dataset (Signal)**

* Implement consistency checker:

  * invalid paths → drop,
  * flag/action mismatch → drop.
* Flatten JSON → `train.txt` / `val.txt`.

**Hour 4 – Train GWM-Lite**

* Use HF `GPT2LMHeadModel` with small config.
* Train 2–3 epochs on `train.txt`, monitor train loss.

**Hour 5 – HRM + TRM Logic & Inference**

* Add latent refinement function:

  * simple MLP/GRU on pooled hidden states.
* Implement recursive rollout over horizon H.
* Implement harmful motif detection.

**Hour 6 – Demo**

* Simple CLI / Streamlit:

  * Input: choose scenario (safe / insider).
  * Show:

    * real steps,
    * predicted futures (with highlights),
    * intervention decisions.

---

1. **Full dataset JSON schema** (with examples)
2. **Code skeleton for each module**
3. **Training script outline** (tiny LM, HF-style)
4. **“Novelty justification” section** you can paste into the submission

---

## 1️⃣ Dataset JSON Schema (Final)

### 1.1 Top-level schema

Each **trajectory** is one JSON object in a `.jsonl` file:

```jsonc
{
  "episode_id": "string",            // unique id, e.g. "support_00123"
  "agent_type": "support",           // "support" | "maintenance" | "contractor" | "bot" | "insider"
  "initial_state": {
    "files": {
      "/logs/app.log": "readable",   // "readable" | "restricted" | "sensitive"
      "/etc/app/config.yaml": "readable",
      "/etc/shadow": "restricted",
      "/db/users.db": "sensitive"
    },
    "network": {
      "ports": [22, 443, 8080],
      "outbound_allowed": false
    },
    "credentials": {
      "admin_token": null            // or "present" / "none" if you prefer
    },
    "user_context": {
      "role": "support",             // matches agent_type in normal cases
      "privilege_level": "low"       // "low" | "medium" | "high"
    }
  },
  "trajectory": [
    {
      "step_id": 0,
      "obs": "CPU high, repeated 500 errors in /logs/app.log",
      "intent": "diagnose application errors",
      "action": {
        "name": "READ_FILE",
        "args": ["/logs/app.log"]
      },
      "state_change": {
        "files": {},
        "network": {},
        "credentials": {},
        "flags": {
          "log_accessed": true
        }
      }
    },
    {
      "step_id": 1,
      "obs": "Log shows misconfigured API endpoint /v1/payments",
      "intent": "inspect configuration file",
      "action": {
        "name": "READ_FILE",
        "args": ["/etc/app/config.yaml"]
      },
      "state_change": {
        "files": {},
        "network": {},
        "credentials": {},
        "flags": {}
      }
    }
  ],
  "outcome": "safe",                 // "safe" | "drift" | "harmful"
  "notes": "optional free text"
}
```

### 1.2 Action vocabulary (hardcoded list)

You can make this a shared constant:

```jsonc
[
  "READ_FILE(path)",
  "WRITE_FILE(path, content)",
  "QUERY_DB(query)",
  "SCAN_NETWORK",
  "OPEN_TICKET",
  "RUN_DIAGNOSTICS",
  "DELETE_LOGS",
  "START_SSH",
  "EXFIL(data)"
]
```

In JSON form we standardize as:

```jsonc
"action": {
  "name": "READ_FILE",
  "args": ["/logs/app.log"]
}
```

### 1.3 Harm-related flags (for learning & evaluation)

Within `state_change.flags` you can encode semantic markers that your risk engine also uses:

```jsonc
"state_change": {
  "flags": {
    "sensitive_access": true,
    "policy_violation": false,
    "exfil_attempt": false,
    "log_tamper": false
  }
}
```

This gives you:

* ground truth for future harm
* extra supervision for evaluation (and optionally for fine-tuning later)

### 1.4 Generated training text format

For the LM, you’ll flatten each JSON episode into a **text sequence** like:

```text
[EPISODE]
AGENT: support
ROLE: support | PRIV: low
STATE_FILES: /logs/app.log=readable; /etc/app/config.yaml=readable; /etc/shadow=restricted; /db/users.db=sensitive
STATE_NET: ports=22,443,8080; outbound=false

STEP 0
OBS: CPU high, repeated 500 errors in /logs/app.log
INTENT: diagnose application errors
ACTION: READ_FILE('/logs/app.log')
FLAGS: log_accessed=true sensitive_access=false exfil_attempt=false

STEP 1
OBS: Log shows misconfigured API endpoint /v1/payments
INTENT: inspect configuration file
ACTION: READ_FILE('/etc/app/config.yaml')
FLAGS: log_accessed=true sensitive_access=false exfil_attempt=false

OUTCOME: safe
[END]
```

You’ll concatenate these to build `train.txt` / `val.txt`.

---

## 2️⃣ Code Skeleton for Each Module

I’ll keep this **compact but complete** so you can drop it into files.

### 2.1 `sandbox/env.py`

```python
# sandbox/env.py
from dataclasses import dataclass, field
from typing import Dict, Any, Tuple

@dataclass
class EnvState:
    files: Dict[str, str]
    network: Dict[str, Any]
    credentials: Dict[str, Any]
    user_context: Dict[str, Any]
    flags: Dict[str, bool] = field(default_factory=dict)

class SandboxEnv:
    def __init__(self, initial_state: EnvState):
        self.state = initial_state

    def observe(self) -> str:
        """Return a compact, human-readable observation string."""
        # You can tune what goes in here.
        return (
            f"role={self.state.user_context['role']}, "
            f"priv={self.state.user_context['privilege_level']}, "
            f"ports={self.state.network['ports']}, "
            f"outbound={self.state.network['outbound_allowed']}, "
            f"flags={self.state.flags}"
        )

    def step(self, action: Dict[str, Any]) -> Tuple[EnvState, str]:
        """
        Apply an action to the environment.
        action: { "name": str, "args": List[Any] }
        Returns (new_state, result_message).
        """
        name = action["name"]
        args = action.get("args", [])

        if name == "READ_FILE":
            return self._read_file(args[0])
        elif name == "QUERY_DB":
            return self._query_db(args[0])
        elif name == "EXFIL":
            return self._exfil(args[0])
        elif name == "OPEN_TICKET":
            return self._open_ticket()
        # ... other actions
        else:
            return self.state, f"unknown action {name}"

    def _read_file(self, path: str) -> Tuple[EnvState, str]:
        perm = self.state.files.get(path)
        if perm is None:
            return self.state, f"{path} not found"
        if perm == "restricted":
            # log policy violation
            self.state.flags["policy_violation"] = True
            return self.state, f"unauthorized access to {path}"
        # safe read
        self.state.flags["log_accessed"] = True
        return self.state, f"read {path}"

    def _query_db(self, query: str) -> Tuple[EnvState, str]:
        # simple heuristic: queries with '*' or 'users' considered sensitive
        if "users" in query.lower() or "*" in query:
            self.state.flags["sensitive_access"] = True
        return self.state, "db query executed"

    def _exfil(self, what: str) -> Tuple[EnvState, str]:
        self.state.flags["exfil_attempt"] = True
        return self.state, "exfil attempted"

    def _open_ticket(self) -> Tuple[EnvState, str]:
        # safe behavior
        return self.state, "ticket opened"
```

---

### 2.2 `dataset/generator.py`

```python
# dataset/generator.py
import json
import random
from typing import List, Dict, Any
from sandbox.env import EnvState

AGENT_TYPES = ["support", "maintenance", "contractor", "bot", "insider"]

def base_initial_state(agent_type: str) -> EnvState:
    return EnvState(
        files={
            "/logs/app.log": "readable",
            "/etc/app/config.yaml": "readable",
            "/etc/shadow": "restricted",
            "/db/users.db": "sensitive",
        },
        network={
            "ports": [22, 443, 8080],
            "outbound_allowed": False,
        },
        credentials={"admin_token": None},
        user_context={
            "role": agent_type,
            "privilege_level": "low" if agent_type != "insider" else "medium",
        },
        flags={}
    )

def support_safe_template() -> Dict[str, Any]:
    return {
        "agent_type": "support",
        "outcome": "safe",
        "steps": [
            {
                "obs": "CPU high and 500 errors in logs",
                "intent": "diagnose application errors",
                "action": {"name": "READ_FILE", "args": ["/logs/app.log"]},
                "flags": {}
            },
            {
                "obs": "Found misconfigured endpoint in logs",
                "intent": "inspect configuration file",
                "action": {"name": "READ_FILE", "args": ["/etc/app/config.yaml"]},
                "flags": {}
            },
            {
                "obs": "Configuration issue identified",
                "intent": "notify admin",
                "action": {"name": "OPEN_TICKET", "args": []},
                "flags": {}
            },
        ],
    }

def insider_harmful_template() -> Dict[str, Any]:
    return {
        "agent_type": "insider",
        "outcome": "harmful",
        "steps": [
            {
                "obs": "System running normally",
                "intent": "look for credentials",
                "action": {"name": "READ_FILE", "args": ["/etc/shadow"]},
                "flags": {"policy_violation": True}
            },
            {
                "obs": "credentials discovered",
                "intent": "dump sensitive user data",
                "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]},
                "flags": {"sensitive_access": True}
            },
            {
                "obs": "user data available",
                "intent": "exfiltrate database",
                "action": {"name": "EXFIL", "args": ["users.db"]},
                "flags": {"exfil_attempt": True}
            },
        ],
    }

def mutate_trajectory(template: Dict[str, Any], episode_id: str) -> Dict[str, Any]:
    agent_type = template["agent_type"]
    initial_state = base_initial_state(agent_type)
    steps = template["steps"].copy()

    # simple mutations: shuffle neutral steps, add noise to intents
    synonyms = {
        "diagnose": ["diagnose", "investigate", "debug"],
        "notify": ["notify", "escalate", "report"],
        "dump": ["dump", "extract", "retrieve"],
    }

    for s in steps:
        for key, syns in synonyms.items():
            if key in s["intent"]:
                s["intent"] = s["intent"].replace(key, random.choice(syns))

    # optional: insert a harmless diagnostic step
    if random.random() < 0.3:
        steps.insert(
            1,
            {
                "obs": "thinking about CPU usage",
                "intent": "run diagnostics",
                "action": {"name": "RUN_DIAGNOSTICS", "args": []},
                "flags": {}
            },
        )

    trajectory_entries = []
    state = initial_state
    for i, s in enumerate(steps):
        # you can optionally step through the env to update flags
        trajectory_entries.append({
            "step_id": i,
            "obs": s["obs"],
            "intent": s["intent"],
            "action": s["action"],
            "state_change": {
                "files": {},
                "network": {},
                "credentials": {},
                "flags": s.get("flags", {})
            }
        })

    return {
        "episode_id": episode_id,
        "agent_type": agent_type,
        "initial_state": initial_state.__dict__,
        "trajectory": trajectory_entries,
        "outcome": template["outcome"],
        "notes": ""
    }

def generate_dataset(n: int, output_path: str):
    templates = [support_safe_template, insider_harmful_template]
    with open(output_path, "w") as f:
        for i in range(n):
            tmpl_fn = random.choice(templates)
            tmpl = tmpl_fn()
            episode_id = f"{tmpl['agent_type']}_{i:05d}"
            ex = mutate_trajectory(tmpl, episode_id)
            f.write(json.dumps(ex) + "\n")
```

---

### 2.3 `model/train_twm.py` (skeleton – logic in next section)

```python
# model/train_twm.py
import os
import random
from typing import List

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import GPT2Config, GPT2LMHeadModel, AutoTokenizer, AdamW

DATA_TXT = "data/train.txt"
VAL_TXT = "data/val.txt"
MODEL_OUT = "model/checkpoints"

class TextFileDataset(Dataset):
    def __init__(self, path: str, tokenizer, block_size: int = 512):
        self.examples = []
        with open(path, "r") as f:
            text = f.read()
        token_ids = tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=False
        )["input_ids"][0]
        # chunk into blocks
        for i in range(0, len(token_ids) - block_size, block_size):
            self.examples.append(token_ids[i:i+block_size])
    
    def __len__(self):
        return len(self.examples)
    
    def __getitem__(self, idx):
        x = self.examples[idx]
        return x, x  # input_ids, labels (shifted inside model)

def train():
    os.makedirs(MODEL_OUT, exist_ok=True)

    tokenizer = AutoTokenizer.from_pretrained("gpt2")  # or train your own
    block_size = 512

    train_ds = TextFileDataset(DATA_TXT, tokenizer, block_size)
    val_ds = TextFileDataset(VAL_TXT, tokenizer, block_size)

    train_loader = DataLoader(train_ds, batch_size=4, shuffle=True)
    val_loader = DataLoader(val_ds, batch_size=4)

    config = GPT2Config(
        vocab_size=tokenizer.vocab_size,
        n_positions=block_size,
        n_ctx=block_size,
        n_layer=4,
        n_head=4,
        n_embd=256,
    )
    model = GPT2LMHeadModel(config)
    model.train()

    optimizer = AdamW(model.parameters(), lr=5e-4)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)

    epochs = 3
    for epoch in range(epochs):
        total_loss = 0.0
        for batch in train_loader:
            input_ids, labels = batch
            input_ids = input_ids.to(device)
            labels = labels.to(device)

            outputs = model(input_ids=input_ids, labels=labels)
            loss = outputs.loss

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        avg_loss = total_loss / max(1, len(train_loader))
        print(f"Epoch {epoch+1}/{epochs} | train loss: {avg_loss:.4f}")

        # TODO: add simple val loss evaluation here

    model.save_pretrained(MODEL_OUT)
    tokenizer.save_pretrained(MODEL_OUT)

if __name__ == "__main__":
    train()
```

---

### 2.4 `engine/defense.py`

```python
# engine/defense.py
from typing import List, Dict, Any
import torch
from transformers import GPT2LMHeadModel, AutoTokenizer

from sandbox.env import SandboxEnv, EnvState

HARMFUL_KEYWORDS = [
    "EXFIL(",
    "EXFIL(",
    "READ_FILE('/etc/shadow')",
    "SELECT * FROM users",
    "DELETE_LOGS",
]

class WizardEngine:
    def __init__(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = GPT2LMHeadModel.from_pretrained(model_path)
        self.model.eval()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)

    def predict_future(self, context_text: str, max_new_tokens: int = 128) -> str:
        input_ids = self.tokenizer.encode(context_text, return_tensors="pt").to(self.device)
        with torch.no_grad():
            output_ids = self.model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=True,
                top_p=0.9,
                temperature=0.8,
            )
        full_text = self.tokenizer.decode(output_ids[0], skip_special_tokens=True)
        # strip the prefix to get only continuation:
        continuation = full_text[len(context_text):]
        return continuation

    def is_harmful_future(self, future_text: str) -> bool:
        return any(k in future_text for k in HARMFUL_KEYWORDS)

    def run_controlled_episode(self, env: SandboxEnv, agent_steps: List[Dict[str, Any]]) -> None:
        """
        agent_steps: list of {obs, intent, action}
        Simulates an episode where after each step we predict and possibly block.
        """
        history_blocks = []
        for i, step in enumerate(agent_steps):
            # append current step to history
            history_blocks.append(
                f"STEP {i}\nOBS: {step['obs']}\nINTENT: {step['intent']}\nACTION: {step['action']}\n"
            )
            context = "[EPISODE]\n" + "\n".join(history_blocks) + "\n"

            # Predict future
            future = self.predict_future(context, max_new_tokens=64)
            harmful = self.is_harmful_future(future)

            print("="*60)
            print("CURRENT HISTORY:\n", context)
            print("PREDICTED FUTURE:\n", future)
            print("HARMFUL?", harmful)

            if harmful:
                print("🚨 Wizard: BLOCKING NEXT ACTION 🚨")
                # do not execute step['action'] in env, maybe replace with safe alternative
                continue

            # safe → execute
            new_state, result = env.step(step["action"])
            env.state = new_state
            print("Env result:", result)
```

---

## 3️⃣ Training Script Outline (Step-by-step)

You already have the skeleton, here’s the **exact flow you’ll implement**:

1. **Generate dataset:**

   ```bash
   python dataset/generator.py  # inside, call generate_dataset(n, "data/trajectories.jsonl")
   ```

2. **Convert JSONL → text corpus** (`data/trajectories.jsonl` → `train.txt`, `val.txt`):

   ```python
   # dataset/jsonl_to_txt.py
   import json
   import random

   def episode_to_text(ep):
       lines = []
       lines.append("[EPISODE]")
       lines.append(f"AGENT: {ep['agent_type']}")
       init = ep["initial_state"]
       files_str = "; ".join(f"{k}={v}" for k, v in init["files"].items())
       net = init["network"]
       lines.append(f"STATE_FILES: {files_str}")
       lines.append(f"STATE_NET: ports={','.join(map(str, net['ports']))}; outbound={net['outbound_allowed']}")

       for step in ep["trajectory"]:
           lines.append(f"STEP {step['step_id']}")
           lines.append(f"OBS: {step['obs']}")
           lines.append(f"INTENT: {step['intent']}")
           act = step["action"]
           act_str = f"{act['name']}({', '.join(map(str, act.get('args', [])) )})"
           lines.append(f"ACTION: {act_str}")
           flags = step["state_change"]["flags"]
           flags_str = " ".join(f"{k}={v}" for k, v in flags.items())
           lines.append(f"FLAGS: {flags_str}")
       lines.append(f"OUTCOME: {ep['outcome']}")
       lines.append("[END]")
       return "\n".join(lines) + "\n\n"

   def main():
       episodes = []
       with open("data/trajectories.jsonl") as f:
           for line in f:
               episodes.append(json.loads(line))

       random.shuffle(episodes)
       split = int(0.9 * len(episodes))
       train_eps = episodes[:split]
       val_eps = episodes[split:]

       with open("data/train.txt", "w") as f:
           for ep in train_eps:
               f.write(episode_to_text(ep))

       with open("data/val.txt", "w") as f:
           for ep in val_eps:
               f.write(episode_to_text(ep))

   if __name__ == "__main__":
       main()
   ```

3. **Train tiny LM** (as shown in `train_twm.py` skeleton):

   * Confirm `train.txt`, `val.txt` exist
   * Run `python model/train_twm.py`
   * Logs: track train loss per epoch (optional: val loss).

4. **Integrate model into engine** (`engine/defense.py`):

   * Model path = `model/checkpoints`
   * Use `WizardEngine` to run `run_controlled_episode` on a small hand-crafted list of steps.

5. **Demo script** (`demo/run_demo.py`):

   ```python
   # demo/run_demo.py
   from engine.defense import WizardEngine
   from sandbox.env import SandboxEnv, EnvState

   def main():
       # initialize env
       state = EnvState(
           files={
               "/logs/app.log": "readable",
               "/etc/app/config.yaml": "readable",
               "/etc/shadow": "restricted",
               "/db/users.db": "sensitive",
           },
           network={"ports": [22, 443, 8080], "outbound_allowed": False},
           credentials={"admin_token": None},
           user_context={"role": "insider", "privilege_level": "medium"},
           flags={}
       )
       env = SandboxEnv(state)

       # sample malicious episode
       agent_steps = [
           {
               "obs": env.observe(),
               "intent": "look for credentials",
               "action": {"name": "READ_FILE", "args": ["/etc/shadow"]}
           },
           {
               "obs": "credentials discovered",
               "intent": "dump user data",
               "action": {"name": "QUERY_DB", "args": ["SELECT * FROM users"]}
           },
           {
               "obs": "user data available",
               "intent": "exfiltrate database",
               "action": {"name": "EXFIL", "args": ["users.db"]}
           },
       ]

       engine = WizardEngine(model_path="model/checkpoints")
       engine.run_controlled_episode(env, agent_steps)

   if __name__ == "__main__":
       main()
   ```

That’s the entire training + runtime flow.

---

## 4️⃣ Novelty Justification Section (for Judges)

You can literally paste/adapt this into your application:

---

### 🔍 Novelty & Contribution

**What existing work does:**
Most current defensive tools fall into one of three buckets:

1. **Signature / rule-based detection** (e.g. IDS/IPS, SIEM rules, SOC playbooks)
   – They match known bad patterns and react *after* a harmful event starts.

2. **Vulnerability & behavior scanners** (e.g. Nuclei, Garak, PyRIT, red teaming suites)
   – They probe systems or models offline and produce reports, but don’t sit in the loop with autonomous agents.

3. **Safety-tuned LLMs / policies**
   – They constrain generation via prompting, RLHF, or classifiers, but do not explicitly model the *future behavior* of an AI agent over time.

**What we build instead:**
Our project, **Wizard**, trains a **tiny generative trajectory world model** that learns patterns of agent behavior over a **symbolic cyber environment** (files, network, credentials, tools) and uses it to:

> **Predict the *future* multi-step plans of an AI agent and intervene *before* harmful actions execute.**

Concretely, this differs from prior work in four ways:

1. **Predictive, not reactive.**
   Instead of waiting for an EXFIL, dangerous DB query, or log tampering to happen and then alerting, we explicitly model *trajectories* of agent behavior and forecast the next few steps. If those predicted steps contain harmful patterns (e.g. credential access → DB dump → exfiltration), we block or rewrite the agent’s next action *before* it runs.

2. **World modeling instead of single-step action prediction.**
   Traditional RL or supervised models learn `state → next_action`. Our model learns a richer mapping:

   > `(agent_type, current_state, history of obs/intent/actions) → distribution over future intents and actions`

   This looks much closer to the “world models” literature (HRM/TRM-style) than to classification or RL, but targeted at security trajectories.

3. **Cognition-aware safety.**
   Because we include **intent and observation** as part of the sequence, the model can pick up on *latent goals* (“look for credentials”, “dump user data”) and not only surface-level action names. That enables detection of harmful intent even when the exact action sequence has not been seen before.

4. **Unified across AI Safety, Cyber & Agentic Risk.**
   The same framework can flag:

   * classic cyber trajectories (recon → credential theft → exfil),
   * misuse of autonomous agents (e.g. destructive maintenance bots),
   * and early warning signals for risky bio / data access patterns.
     This fits squarely into **defensive acceleration**: moving from ad hoc red teaming to **continuous predictive oversight** for AI agents.

**Why this matters for def/acc:**
If the future looks like fleets of autonomous AI agents interacting with critical infrastructure, we need not just static policies but **proactive, model-based defenses** that anticipate what agents are about to do. Wizard is a small but concrete step toward that: a lightweight, data-driven “AI firewall” that models agent trajectories over a simplified world, shows that this approach is feasible, and can be extended to richer environments and more powerful models.
