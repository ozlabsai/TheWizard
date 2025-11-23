"""Model hyperparameters and training configuration."""

# Model architecture configuration (~15M parameters)
MODEL_CONFIG = {
    "vocab_size": 50257,  # GPT-2 tokenizer vocabulary
    "n_positions": 512,   # Maximum sequence length
    "n_ctx": 512,         # Context window size
    "n_layer": 4,         # Number of transformer layers
    "n_head": 4,          # Number of attention heads
    "n_embd": 256,        # Embedding dimension
}

# Training configuration
TRAINING_CONFIG = {
    "batch_size": 4,
    "learning_rate": 5e-4,
    "epochs": 3,
    "block_size": 512,
    "optimizer": "AdamW",
    "warmup_steps": 100,
    "gradient_clip": 1.0,
}

# Generation configuration for inference
GENERATION_CONFIG = {
    "max_new_tokens": 128,
    "temperature": 0.8,
    "top_p": 0.9,
    "do_sample": True,
}

# File paths
DEFAULT_TRAIN_PATH = "data/train.txt"
DEFAULT_VAL_PATH = "data/val.txt"
DEFAULT_OUTPUT_DIR = "model/checkpoints"
