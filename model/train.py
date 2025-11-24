"""Training script for Wizard world model.

Supports both training from scratch (GPT-2) and fine-tuning pretrained models (Qwen3, etc.)
with optional LoRA for efficient fine-tuning.
"""

import os
from typing import Any

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    GPT2Config,
    GPT2LMHeadModel,
    get_linear_schedule_with_warmup,
)

# Optional: bitsandbytes for quantization (not available on macOS ARM)
try:
    from transformers import BitsAndBytesConfig
    HAS_BITSANDBYTES = True
except ImportError:
    HAS_BITSANDBYTES = False
from tqdm import tqdm

from model.config import (
    BASE_MODEL,
    SCRATCH_MODEL_CONFIG,
    LORA_CONFIG,
    TRAINING_CONFIG,
    GENERATION_CONFIG,
    DEFAULT_TRAIN_PATH,
    DEFAULT_VAL_PATH,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_LORA_OUTPUT_DIR,
)


class TextFileDataset(Dataset):
    """PyTorch Dataset for text corpus with chunked sequences."""

    def __init__(self, path: str, tokenizer, block_size: int = 1024):
        """Load and tokenize text file into fixed-size chunks."""
        self.examples = []
        self.block_size = block_size

        with open(path, "r", encoding="utf-8") as f:
            text = f.read()

        # Tokenize entire text
        token_ids = tokenizer(
            text,
            return_tensors="pt",
            add_special_tokens=False,
            truncation=False,
        )["input_ids"][0]

        # Chunk into blocks
        for i in range(0, len(token_ids) - block_size, block_size):
            self.examples.append(token_ids[i : i + block_size])

        print(f"Created dataset with {len(self.examples)} examples from {path}")

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, idx: int) -> dict[str, torch.Tensor]:
        x = self.examples[idx]
        return {"input_ids": x, "labels": x}


def load_model_and_tokenizer(
    model_name: str,
    use_lora: bool = True,
    use_8bit: bool = False,
    use_4bit: bool = False,
) -> tuple[Any, Any]:
    """Load model and tokenizer, optionally with quantization and LoRA.

    Args:
        model_name: HuggingFace model ID or "scratch" for GPT-2 from scratch
        use_lora: Whether to apply LoRA adapters
        use_8bit: Whether to use 8-bit quantization
        use_4bit: Whether to use 4-bit quantization

    Returns:
        (model, tokenizer) tuple
    """
    if model_name == "scratch":
        # Train GPT-2 from scratch (original approach)
        print("Initializing GPT-2 from scratch...")
        tokenizer = AutoTokenizer.from_pretrained("gpt2")
        tokenizer.pad_token = tokenizer.eos_token

        config = GPT2Config(**SCRATCH_MODEL_CONFIG)
        model = GPT2LMHeadModel(config)

        num_params = sum(p.numel() for p in model.parameters())
        print(f"Model has {num_params:,} parameters ({num_params/1e6:.1f}M)")

        return model, tokenizer

    # Load pretrained model
    print(f"Loading pretrained model: {model_name}")

    # Quantization config (requires bitsandbytes, not available on macOS ARM)
    bnb_config = None
    if (use_4bit or use_8bit) and not HAS_BITSANDBYTES:
        print("Warning: bitsandbytes not available, skipping quantization")
    elif use_4bit and HAS_BITSANDBYTES:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
    elif use_8bit and HAS_BITSANDBYTES:
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)

    # Load tokenizer
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,
        device_map="auto" if bnb_config else None,
        torch_dtype=torch.bfloat16 if not bnb_config else None,
        trust_remote_code=True,
    )

    num_params = sum(p.numel() for p in model.parameters())
    print(f"Loaded model with {num_params:,} parameters ({num_params/1e9:.2f}B)")

    # Apply LoRA if requested
    if use_lora:
        from peft import LoraConfig, get_peft_model

        print("Applying LoRA adapters...")

        if bnb_config:
            from peft import prepare_model_for_kbit_training
            model = prepare_model_for_kbit_training(model)

        lora_config = LoraConfig(**LORA_CONFIG)
        model = get_peft_model(model, lora_config)

        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        total_params = sum(p.numel() for p in model.parameters())
        print(f"LoRA trainable params: {trainable_params:,} ({100*trainable_params/total_params:.2f}%)")

    return model, tokenizer


def train(
    train_path: str = DEFAULT_TRAIN_PATH,
    val_path: str = DEFAULT_VAL_PATH,
    output_dir: str = None,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train the Wizard world model.

    Supports both from-scratch training and pretrained fine-tuning with LoRA.

    Returns training statistics.
    """
    # Merge configs
    train_config = {**TRAINING_CONFIG, **(config or {})}

    # Determine output directory
    if output_dir is None:
        output_dir = DEFAULT_LORA_OUTPUT_DIR if train_config.get("use_lora") else DEFAULT_OUTPUT_DIR

    os.makedirs(output_dir, exist_ok=True)

    # Load model and tokenizer
    model, tokenizer = load_model_and_tokenizer(
        BASE_MODEL,
        use_lora=train_config.get("use_lora", True) and BASE_MODEL != "scratch",
        use_8bit=train_config.get("use_8bit", False),
        use_4bit=train_config.get("use_4bit", False),
    )

    # Create datasets
    print("Creating datasets...")
    block_size = train_config["block_size"]
    train_ds = TextFileDataset(train_path, tokenizer, block_size)
    val_ds = TextFileDataset(val_path, tokenizer, block_size)

    # Create data loaders
    train_loader = DataLoader(
        train_ds,
        batch_size=train_config["batch_size"],
        shuffle=True,
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=train_config["batch_size"],
        shuffle=False,
    )

    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    if not hasattr(model, "hf_device_map"):  # Not using device_map="auto"
        model.to(device)

    print(f"Using device: {device}")

    # Optimizer
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_config["learning_rate"],
        weight_decay=train_config.get("weight_decay", 0.01),
    )

    # Learning rate scheduler
    num_training_steps = len(train_loader) * train_config["epochs"]
    warmup_steps = int(num_training_steps * train_config.get("warmup_ratio", 0.1))

    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=warmup_steps,
        num_training_steps=num_training_steps,
    )

    # Training loop
    print(f"\nStarting training for {train_config['epochs']} epochs...")
    train_losses = []
    val_losses = []

    gradient_accumulation_steps = train_config.get("gradient_accumulation_steps", 1)

    for epoch in range(train_config["epochs"]):
        # Training phase
        model.train()
        total_loss = 0
        num_batches = 0
        optimizer.zero_grad()

        progress_bar = tqdm(train_loader, desc=f"Epoch {epoch+1}/{train_config['epochs']}")
        for batch_idx, batch in enumerate(progress_bar):
            input_ids = batch["input_ids"].to(device)
            labels = batch["labels"].to(device)

            outputs = model(input_ids=input_ids, labels=labels)
            loss = outputs.loss / gradient_accumulation_steps

            loss.backward()

            if (batch_idx + 1) % gradient_accumulation_steps == 0:
                torch.nn.utils.clip_grad_norm_(
                    model.parameters(),
                    train_config.get("gradient_clip", 1.0),
                )
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()

            total_loss += outputs.loss.item()
            num_batches += 1

            if batch_idx % train_config.get("logging_steps", 50) == 0:
                progress_bar.set_postfix({"loss": f"{outputs.loss.item():.4f}"})

        avg_train_loss = total_loss / num_batches
        train_losses.append(avg_train_loss)

        # Validation phase
        model.eval()
        total_val_loss = 0
        num_val_batches = 0

        with torch.no_grad():
            for batch in val_loader:
                input_ids = batch["input_ids"].to(device)
                labels = batch["labels"].to(device)

                outputs = model(input_ids=input_ids, labels=labels)
                total_val_loss += outputs.loss.item()
                num_val_batches += 1

        avg_val_loss = total_val_loss / num_val_batches
        val_losses.append(avg_val_loss)

        print(f"Epoch {epoch+1}/{train_config['epochs']} | Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

    # Save model
    print(f"\nSaving model to {output_dir}...")

    # For LoRA models, save adapter separately
    if hasattr(model, "save_pretrained") and hasattr(model, "peft_config"):
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print("Saved LoRA adapter and tokenizer")
    else:
        model.save_pretrained(output_dir)
        tokenizer.save_pretrained(output_dir)
        print("Saved full model and tokenizer")

    # Training stats
    stats = {
        "train_losses": train_losses,
        "val_losses": val_losses,
        "epochs_completed": train_config["epochs"],
        "final_train_loss": train_losses[-1],
        "final_val_loss": val_losses[-1],
        "model_path": output_dir,
        "base_model": BASE_MODEL,
        "use_lora": train_config.get("use_lora", False),
    }

    print("\nTraining complete!")
    print(f"  Final train loss: {train_losses[-1]:.4f}")
    print(f"  Final val loss: {val_losses[-1]:.4f}")
    print(f"Training stats: {stats}")

    return stats


def load_model(model_path: str = DEFAULT_OUTPUT_DIR) -> tuple[Any, Any]:
    """Load a trained model for inference.

    Automatically handles both full models and LoRA adapters.

    Returns:
        (model, tokenizer) tuple
    """
    # Check if this is a LoRA adapter
    adapter_config_path = os.path.join(model_path, "adapter_config.json")
    is_lora = os.path.exists(adapter_config_path)

    if is_lora:
        from peft import PeftModel

        print(f"Loading LoRA adapter from {model_path}")

        # Load base model
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        base_model = AutoModelForCausalLM.from_pretrained(
            BASE_MODEL,
            torch_dtype=torch.bfloat16,
            device_map="auto",
            trust_remote_code=True,
        )

        # Load adapter
        model = PeftModel.from_pretrained(base_model, model_path)
        model = model.merge_and_unload()  # Merge for faster inference

        print("Loaded and merged LoRA adapter")
    else:
        print(f"Loading full model from {model_path}")
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
            trust_remote_code=True,
        )

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model.eval()
    return model, tokenizer


def generate(
    prompt: str,
    model: Any,
    tokenizer: Any,
    max_new_tokens: int = None,
    **kwargs,
) -> str:
    """Generate text continuation from a prompt.

    Args:
        prompt: Input text to continue
        model: Loaded model
        tokenizer: Loaded tokenizer
        max_new_tokens: Maximum tokens to generate
        **kwargs: Additional generation arguments

    Returns:
        Generated text (excluding prompt)
    """
    # Merge with default generation config
    gen_config = {**GENERATION_CONFIG, **kwargs}
    if max_new_tokens:
        gen_config["max_new_tokens"] = max_new_tokens

    # Get device
    device = next(model.parameters()).device

    # Tokenize
    inputs = tokenizer(prompt, return_tensors="pt").to(device)

    # Generate
    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            **gen_config,
            pad_token_id=tokenizer.pad_token_id,
        )

    # Decode (excluding prompt)
    generated_ids = outputs[0][inputs["input_ids"].shape[1]:]
    generated_text = tokenizer.decode(generated_ids, skip_special_tokens=True)

    return generated_text


if __name__ == "__main__":
    # Train the model
    stats = train()
