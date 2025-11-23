"""Training script for GWM-Lite model."""

import os
from typing import Any

import torch
from torch.utils.data import Dataset, DataLoader
from transformers import GPT2Config, GPT2LMHeadModel, AutoTokenizer, get_linear_schedule_with_warmup

from model.config import MODEL_CONFIG, TRAINING_CONFIG, DEFAULT_TRAIN_PATH, DEFAULT_VAL_PATH, DEFAULT_OUTPUT_DIR


class TextFileDataset(Dataset):
    """PyTorch Dataset for text corpus with chunked sequences."""

    def __init__(self, path: str, tokenizer, block_size: int = 512):
        """Load and tokenize text file into fixed-size chunks."""
        self.examples = []

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

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, torch.Tensor]:
        x = self.examples[idx]
        return x, x  # input_ids and labels are the same for LM training


def train(
    train_path: str = DEFAULT_TRAIN_PATH,
    val_path: str = DEFAULT_VAL_PATH,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Train the GWM-Lite model on trajectory corpus.

    Returns training statistics.
    """
    # Merge configs
    train_config = {**TRAINING_CONFIG, **(config or {})}

    # Setup output directory
    os.makedirs(output_dir, exist_ok=True)

    # Load tokenizer
    print("Loading GPT-2 tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained("gpt2")
    tokenizer.pad_token = tokenizer.eos_token

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
    )

    # Initialize model
    print("Initializing model...")
    model_config = GPT2Config(**MODEL_CONFIG)
    model = GPT2LMHeadModel(model_config)

    # Count parameters
    num_params = sum(p.numel() for p in model.parameters())
    print(f"Model has {num_params:,} parameters ({num_params / 1e6:.1f}M)")

    # Setup device
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using device: {device}")
    model.to(device)

    # Setup optimizer and scheduler
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=train_config["learning_rate"],
    )

    total_steps = len(train_loader) * train_config["epochs"]
    scheduler = get_linear_schedule_with_warmup(
        optimizer,
        num_warmup_steps=train_config["warmup_steps"],
        num_training_steps=total_steps,
    )

    # Training loop
    print(f"\nStarting training for {train_config['epochs']} epochs...")
    model.train()

    training_stats = {
        "train_losses": [],
        "val_losses": [],
        "epochs_completed": 0,
    }

    initial_loss = None

    for epoch in range(train_config["epochs"]):
        total_loss = 0.0
        num_batches = 0

        for batch_idx, (input_ids, labels) in enumerate(train_loader):
            input_ids = input_ids.to(device)
            labels = labels.to(device)

            # Forward pass
            outputs = model(input_ids=input_ids, labels=labels)
            loss = outputs.loss

            # Record initial loss
            if initial_loss is None:
                initial_loss = loss.item()

            # Backward pass
            optimizer.zero_grad()
            loss.backward()

            # Gradient clipping
            torch.nn.utils.clip_grad_norm_(
                model.parameters(),
                train_config["gradient_clip"],
            )

            optimizer.step()
            scheduler.step()

            total_loss += loss.item()
            num_batches += 1

            # Progress update
            if (batch_idx + 1) % 50 == 0:
                avg = total_loss / num_batches
                print(f"  Epoch {epoch + 1}, Batch {batch_idx + 1}/{len(train_loader)}, Loss: {avg:.4f}")

        # Epoch statistics
        avg_train_loss = total_loss / max(1, num_batches)
        training_stats["train_losses"].append(avg_train_loss)

        # Validation loss - set model to inference mode
        model.training = False
        val_loss = 0.0
        val_batches = 0

        with torch.no_grad():
            for input_ids, labels in val_loader:
                input_ids = input_ids.to(device)
                labels = labels.to(device)
                outputs = model(input_ids=input_ids, labels=labels)
                val_loss += outputs.loss.item()
                val_batches += 1

        avg_val_loss = val_loss / max(1, val_batches)
        training_stats["val_losses"].append(avg_val_loss)

        # Back to training mode
        model.train()
        training_stats["epochs_completed"] = epoch + 1

        print(f"Epoch {epoch + 1}/{train_config['epochs']} | "
              f"Train Loss: {avg_train_loss:.4f} | Val Loss: {avg_val_loss:.4f}")

    # Save model and tokenizer
    print(f"\nSaving model to {output_dir}...")
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)

    # Calculate improvement
    final_loss = training_stats["train_losses"][-1]
    loss_reduction = ((initial_loss - final_loss) / initial_loss) * 100 if initial_loss else 0

    training_stats["initial_loss"] = initial_loss
    training_stats["final_train_loss"] = final_loss
    training_stats["loss_reduction_pct"] = loss_reduction
    training_stats["model_path"] = output_dir
    training_stats["num_parameters"] = num_params

    print(f"\nTraining complete!")
    print(f"  Initial loss: {initial_loss:.4f}")
    print(f"  Final loss: {final_loss:.4f}")
    print(f"  Reduction: {loss_reduction:.1f}%")

    return training_stats


def load_model(model_path: str) -> tuple[GPT2LMHeadModel, AutoTokenizer]:
    """Loads a trained model and tokenizer.

    Returns (model, tokenizer) tuple with model in inference mode on appropriate device.
    """
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = GPT2LMHeadModel.from_pretrained(model_path)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    model.training = False  # Set to inference mode

    return model, tokenizer


def generate(
    model: GPT2LMHeadModel,
    tokenizer: AutoTokenizer,
    prompt: str,
    max_new_tokens: int = 128,
    temperature: float = 0.8,
    top_p: float = 0.9,
) -> str:
    """Generates text continuation from prompt."""
    device = next(model.parameters()).device

    input_ids = tokenizer.encode(prompt, return_tensors="pt").to(device)

    with torch.no_grad():
        output_ids = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_p=top_p,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
        )

    return tokenizer.decode(output_ids[0], skip_special_tokens=True)


if __name__ == "__main__":
    # Run training
    stats = train()
    print(f"\nTraining stats: {stats}")
