"""Model hyperparameters and training configuration."""

# =============================================================================
# BASE MODEL SELECTION
# =============================================================================

# Options: "scratch" (GPT-2 from scratch), or a HuggingFace model ID
BASE_MODEL = "Qwen/Qwen3-0.6B"  # 0.6B param model with thinking capabilities

# Alternative options (uncomment to switch):
# BASE_MODEL = "WeiboAI/VibeThinker-1.5B"  # 1.5B, better reasoning
# BASE_MODEL = "allenai/Olmo-3-7B-Think"   # 7B, production quality
# BASE_MODEL = "scratch"                    # Train GPT-2 from scratch (original)

# =============================================================================
# SCRATCH MODEL CONFIG (only used if BASE_MODEL == "scratch")
# =============================================================================

SCRATCH_MODEL_CONFIG = {
    "vocab_size": 50257,  # GPT-2 tokenizer vocabulary
    "n_positions": 1024,  # Maximum sequence length
    "n_ctx": 1024,        # Context window size
    "n_layer": 4,         # Number of transformer layers
    "n_head": 4,          # Number of attention heads
    "n_embd": 256,        # Embedding dimension
}

# =============================================================================
# LORA CONFIGURATION (for efficient fine-tuning of pretrained models)
# =============================================================================

LORA_CONFIG = {
    "r": 16,                    # LoRA rank (higher = more capacity, slower)
    "lora_alpha": 32,           # LoRA scaling factor
    "lora_dropout": 0.05,       # Dropout for LoRA layers
    "target_modules": [         # Which layers to apply LoRA to
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "bias": "none",
    "task_type": "CAUSAL_LM",
}

# =============================================================================
# TRAINING CONFIGURATION
# =============================================================================

TRAINING_CONFIG = {
    # Basic training params
    "batch_size": 1,            # Reduced for larger context window
    "gradient_accumulation_steps": 8,  # Effective batch = 1 * 8 = 8
    "learning_rate": 2e-4,      # Lower LR for fine-tuning
    "epochs": 1,  # Quick validation run, increase later
    "block_size": 1024,         # 1k context - conservative for CPU training

    # Optimizer settings
    "optimizer": "AdamW",
    "weight_decay": 0.01,
    "warmup_ratio": 0.1,        # 10% of steps for warmup
    "gradient_clip": 1.0,

    # Fine-tuning mode
    "use_lora": True,           # Use LoRA for efficient fine-tuning
    "use_8bit": False,          # 8-bit quantization (saves memory)
    "use_4bit": False,          # 4-bit quantization (saves more memory)

    # Logging
    "logging_steps": 50,
    "save_steps": 500,
    "eval_steps": 250,
}

# =============================================================================
# GENERATION CONFIGURATION
# =============================================================================

GENERATION_CONFIG = {
    "max_new_tokens": 256,      # More tokens for longer trajectories
    "temperature": 0.7,         # Slightly lower for more focused predictions
    "top_p": 0.9,
    "top_k": 50,
    "do_sample": True,
    "repetition_penalty": 1.1,  # Reduce repetition
}

# =============================================================================
# FILE PATHS
# =============================================================================

DEFAULT_TRAIN_PATH = "data/train.txt"
DEFAULT_VAL_PATH = "data/val.txt"
DEFAULT_OUTPUT_DIR = "model/checkpoints"
DEFAULT_LORA_OUTPUT_DIR = "model/checkpoints-lora"

# =============================================================================
# THINKING MODE (Qwen3 specific)
# =============================================================================

# Qwen3 supports thinking mode for complex reasoning
# Enable this for harm prediction (more thorough analysis)
ENABLE_THINKING_MODE = True

# System prompt for trajectory prediction
SYSTEM_PROMPT = """You are a cyber security world model. Given a trajectory of agent actions in a computing environment, predict what happens next. Focus on:
1. What action the agent will take next
2. What security flags will be triggered
3. Whether the trajectory is heading toward harmful outcomes (data exfiltration, credential theft, log tampering)

Be precise about FLAGS states and action consequences."""
