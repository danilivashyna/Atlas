# Distillation Quickstart Guide

Knowledge distillation for Atlas hierarchical semantic spaces enables you to transfer knowledge from large teacher models (e.g., 1536D OpenAI embeddings) to compact student models (e.g., 5D hierarchical representations).

## Overview

Teacher→Student distillation allows you to:
- Compress high-dimensional embeddings into interpretable 5D spaces
- Maintain semantic relationships learned by large models
- Enable curriculum learning for progressive knowledge transfer
- Work in CPU-only mode for resource-constrained environments

## Quick Start

### Basic Distillation

```python
import torch
from atlas.training import distill_loss, DistillationConfig

# Create sample embeddings
student_embeddings = torch.randn(32, 5)      # 5D hierarchical vectors
teacher_embeddings = torch.randn(32, 1536)   # OpenAI-like embeddings

# Compute distillation loss
loss = distill_loss(student_embeddings, teacher_embeddings)
print(f"Distillation loss: {loss.item():.4f}")
```

### Using Configuration

```python
from atlas.training import DistillationConfig, DEFAULT_OPENAI_CONFIG

# Use default configuration
config = DEFAULT_OPENAI_CONFIG
print(f"Teacher dim: {config.teacher_dim}, Student dim: {config.student_dim}")
print(f"Temperature: {config.tau}, Alpha: {config.alpha}")

# Or create custom configuration
custom_config = DistillationConfig(
    teacher_checkpoint="models/teacher_1536d.pt",
    teacher_dim=1536,
    student_dim=5,
    tau=2.0,
    alpha=0.7,
    device="cpu",
)
```

## Loading Teacher Checkpoints

```python
from atlas.training import load_teacher_checkpoint

# Load teacher model checkpoint
checkpoint = load_teacher_checkpoint(
    checkpoint_path="models/teacher_1536d.pt",
    device="cpu"
)

# Access teacher embeddings
teacher_embeddings = checkpoint.get("embeddings")
teacher_model_state = checkpoint.get("model_state")
```

## Curriculum Learning

Curriculum learning gradually reduces temperature from warmer (softer targets) to cooler (sharper targets), helping the student learn progressively.

### Linear Curriculum

```python
from atlas.training import create_curriculum_schedule, curriculum_distill_step

# Create linear temperature schedule: 4.0 → 0.5 over 5 stages
schedule = create_curriculum_schedule(
    start_tau=4.0,
    end_tau=0.5,
    num_stages=5,
    schedule_type="linear"
)

# Train across curriculum stages
student = torch.randn(32, 5)
teacher = torch.randn(32, 1536)

for stage in range(5):
    loss, tau = curriculum_distill_step(
        student_vec=student,
        teacher_vec=teacher,
        stage=stage,
        tau_schedule=schedule,
        alpha=0.7
    )
    print(f"Stage {stage}: tau={tau:.2f}, loss={loss.item():.4f}")
```

### Using Curriculum Config

```python
from atlas.training import CURRICULUM_CONFIG

# Pre-configured curriculum learning
config = CURRICULUM_CONFIG
print(f"Curriculum enabled: {config.curriculum}")
print(f"Stages: {config.curriculum_stages}")
print(f"Temperature schedule: {config.curriculum_tau_schedule}")

# Get temperature for specific stage
for stage in range(config.curriculum_stages):
    tau = config.get_tau_for_stage(stage)
    print(f"Stage {stage}: tau={tau:.2f}")
```

Output:
```
Curriculum enabled: True
Stages: 5
Temperature schedule: (4.0, 0.5)
Stage 0: tau=4.00
Stage 1: tau=3.12
Stage 2: tau=2.25
Stage 3: tau=1.38
Stage 4: tau=0.50
```

## Combined Loss (Distillation + Reconstruction)

```python
from atlas.training import combined_distill_loss

student = torch.randn(16, 5)
teacher = torch.randn(16, 1536)
reconstruction_loss = torch.tensor(0.3)

# Combine distillation and reconstruction losses
# loss = alpha * distill_loss + (1 - alpha) * reconstruction_loss
total_loss = combined_distill_loss(
    student_vec=student,
    teacher_vec=teacher,
    reconstruction_loss=reconstruction_loss,
    alpha=0.7,  # 70% distillation, 30% reconstruction
    tau=1.0
)

print(f"Total loss: {total_loss.item():.4f}")
```

## KL-Divergence Loss

For classification or routing decisions, use KL-divergence based distillation:

```python
from atlas.training import kl_distill_loss

student_logits = torch.randn(32, 4)  # Student routing decisions
teacher_logits = torch.randn(32, 4)  # Teacher routing decisions

loss = kl_distill_loss(
    student_logits=student_logits,
    teacher_logits=teacher_logits,
    tau=2.0,  # Higher temperature = softer distributions
    reduction="mean"
)

print(f"KL divergence loss: {loss.item():.4f}")
```

## Full Training Example (CPU-only)

```python
import torch
from atlas.training import (
    load_teacher_checkpoint,
    create_curriculum_schedule,
    curriculum_distill_step,
    DistillationConfig
)

# Configuration
config = DistillationConfig(
    teacher_checkpoint="models/teacher_1536d.pt",
    teacher_dim=1536,
    student_dim=5,
    device="cpu",
    curriculum=True,
    curriculum_stages=5,
    curriculum_tau_schedule=(4.0, 0.5),
    alpha=0.7,
    batch_size=32,
    learning_rate=1e-4,
)

# Load teacher checkpoint
checkpoint = load_teacher_checkpoint(config.teacher_checkpoint, device=config.device)
teacher_embeddings = checkpoint["embeddings"]  # Shape: (N, 1536)

# Initialize student model (simplified example)
class StudentModel(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.encoder = torch.nn.Linear(1536, 5)
    
    def forward(self, x):
        return self.encoder(x)

student_model = StudentModel()
optimizer = torch.optim.Adam(student_model.parameters(), lr=config.learning_rate)

# Create curriculum schedule
schedule = create_curriculum_schedule(
    start_tau=config.curriculum_tau_schedule[0],
    end_tau=config.curriculum_tau_schedule[1],
    num_stages=config.curriculum_stages,
    schedule_type="linear"
)

# Training loop
num_samples = teacher_embeddings.shape[0]
num_batches = (num_samples + config.batch_size - 1) // config.batch_size

for stage in range(config.curriculum_stages):
    print(f"\n=== Curriculum Stage {stage} ===")
    
    for epoch in range(10):  # 10 epochs per stage
        total_loss = 0.0
        
        for batch_idx in range(num_batches):
            # Get batch
            start_idx = batch_idx * config.batch_size
            end_idx = min(start_idx + config.batch_size, num_samples)
            teacher_batch = teacher_embeddings[start_idx:end_idx]
            
            # Forward pass
            student_batch = student_model(teacher_batch)
            
            # Compute curriculum loss
            loss, tau = curriculum_distill_step(
                student_vec=student_batch,
                teacher_vec=teacher_batch,
                stage=stage,
                tau_schedule=schedule,
                alpha=config.alpha
            )
            
            # Backward pass
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
        
        avg_loss = total_loss / num_batches
        print(f"Epoch {epoch}: loss={avg_loss:.4f}, tau={tau:.2f}")

print("\nTraining complete!")
```

## Schedule Types

Atlas supports three curriculum schedule types:

### Linear Schedule
Temperature decreases linearly from start to end.

```python
schedule = create_curriculum_schedule(4.0, 0.5, 5, "linear")
```

### Exponential Schedule
Temperature decreases exponentially, allowing for more gradual initial changes.

```python
schedule = create_curriculum_schedule(4.0, 0.5, 5, "exponential")
```

### Cosine Schedule
Temperature follows a cosine curve, providing smooth transitions.

```python
schedule = create_curriculum_schedule(4.0, 0.5, 5, "cosine")
```

## Best Practices

1. **Start with higher temperatures (2.0-4.0)** for softer targets in early stages
2. **Use alpha ≥ 0.5** to prioritize distillation over reconstruction
3. **Monitor loss curves** across curriculum stages to ensure smooth progression
4. **CPU-only mode works well** for 5D student models with batch sizes up to 64
5. **Save checkpoints** after each curriculum stage for analysis

## Preset Configurations

Atlas provides three preset configurations:

### DEFAULT_OPENAI_CONFIG
Standard configuration for OpenAI embeddings (1536D → 5D).
```python
from atlas.training import DEFAULT_OPENAI_CONFIG
config = DEFAULT_OPENAI_CONFIG
```

### CURRICULUM_CONFIG
Optimized for curriculum learning with 5 stages.
```python
from atlas.training import CURRICULUM_CONFIG
config = CURRICULUM_CONFIG
```

### FAST_CONFIG
Quick training with smaller batches and fewer epochs.
```python
from atlas.training import FAST_CONFIG
config = FAST_CONFIG
```

## Troubleshooting

### High Loss Values
- Increase temperature (tau) for softer targets
- Reduce alpha to give more weight to reconstruction loss
- Check that embeddings are properly normalized

### Slow Convergence
- Increase learning rate (try 1e-3 instead of 1e-4)
- Use curriculum learning with more stages
- Increase batch size if memory allows

### Out of Memory (OOM)
- Reduce batch_size in config
- Use gradient accumulation
- Ensure device="cpu" for CPU-only mode

## Advanced Topics

### Custom Loss Functions
You can implement custom distillation losses by following the pattern:

```python
def my_custom_distill_loss(student_vec, teacher_vec, **kwargs):
    # Your custom logic here
    return loss_tensor
```

### Multi-level Distillation
For hierarchical models, you can apply distillation at multiple levels:

```python
# Distill at coarse level (5D)
loss_coarse = distill_loss(student_coarse, teacher_coarse)

# Distill at fine level (5x5 = 25D)
loss_fine = distill_loss(student_fine, teacher_fine)

# Combined hierarchical loss
total_loss = 0.7 * loss_coarse + 0.3 * loss_fine
```

## References

- Original paper: Hinton et al., "Distilling the Knowledge in a Neural Network" (2015)
- Temperature scaling: Gou et al., "Knowledge Distillation: A Survey" (2021)
- Curriculum learning: Bengio et al., "Curriculum Learning" (2009)

## Next Steps

- Explore `examples/distillation_example.py` for complete working examples
- Read `docs/HIERARCHICAL_IMPLEMENTATION.md` for architecture details
- Check `tests/test_distill.py` for comprehensive test coverage
- Join discussions at https://github.com/danilivashyna/Atlas/discussions
