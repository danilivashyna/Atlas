# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (c) 2025 Danil Ivashyna

"""
Tests for knowledge distillation (Teacher→Student).

Validates distillation loss functions, checkpoint loading,
and curriculum learning functionality.
"""

import pytest
import torch
import tempfile
import os
from pathlib import Path

from atlas.training import (
    distill_loss,
    kl_distill_loss,
    combined_distill_loss,
    load_teacher_checkpoint,
    create_curriculum_schedule,
    curriculum_distill_step,
    DistillationConfig,
    DEFAULT_OPENAI_CONFIG,
    CURRICULUM_CONFIG,
)


class TestDistillLoss:
    """Test basic distillation loss functions."""
    
    def test_distill_loss_basic(self):
        """Test basic distillation loss computation."""
        student = torch.randn(32, 5)
        teacher = torch.randn(32, 1536)
        
        loss = distill_loss(student, teacher)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.ndim == 0  # Scalar
        assert loss.item() >= 0  # Loss should be non-negative
        assert not torch.isnan(loss)
        assert not torch.isinf(loss)
    
    def test_distill_loss_perfect_alignment(self):
        """Test loss is zero when perfectly aligned."""
        # Create normalized vectors pointing in same direction
        vec = torch.randn(32, 100)
        vec_norm = torch.nn.functional.normalize(vec, dim=-1)
        
        loss = distill_loss(vec_norm, vec_norm)
        
        # Loss should be very close to 0 for identical normalized vectors
        assert loss.item() < 1e-6
    
    def test_distill_loss_opposite_alignment(self):
        """Test loss is high when vectors are opposite."""
        vec = torch.randn(32, 100)
        vec_norm = torch.nn.functional.normalize(vec, dim=-1)
        opposite = -vec_norm
        
        loss = distill_loss(vec_norm, opposite)
        
        # Loss should be close to 2 for opposite vectors
        assert loss.item() > 1.9
    
    def test_distill_loss_different_dims(self):
        """Test distillation works with different dimensions."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        
        loss = distill_loss(student, teacher)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
    
    def test_distill_loss_reduction_mean(self):
        """Test mean reduction."""
        student = torch.randn(32, 5)
        teacher = torch.randn(32, 1536)
        
        loss = distill_loss(student, teacher, reduction="mean")
        
        assert loss.ndim == 0
        assert loss.item() >= 0
    
    def test_distill_loss_reduction_sum(self):
        """Test sum reduction."""
        student = torch.randn(32, 5)
        teacher = torch.randn(32, 1536)
        
        loss_sum = distill_loss(student, teacher, reduction="sum")
        loss_mean = distill_loss(student, teacher, reduction="mean")
        
        # Sum should be approximately batch_size * mean
        assert loss_sum.item() > loss_mean.item()
        assert abs(loss_sum.item() - 32 * loss_mean.item()) < 1e-4
    
    def test_distill_loss_invalid_reduction(self):
        """Test invalid reduction raises error."""
        student = torch.randn(32, 5)
        teacher = torch.randn(32, 1536)
        
        with pytest.raises(ValueError, match="reduction must be"):
            distill_loss(student, teacher, reduction="invalid")
    
    def test_distill_loss_cpu(self):
        """Test distillation loss works on CPU."""
        student = torch.randn(8, 5, device="cpu")
        teacher = torch.randn(8, 1536, device="cpu")
        
        loss = distill_loss(student, teacher)
        
        assert loss.device.type == "cpu"
        assert loss.item() >= 0


class TestKLDistillLoss:
    """Test KL-divergence based distillation loss."""
    
    def test_kl_loss_basic(self):
        """Test basic KL loss computation."""
        student_logits = torch.randn(32, 4)
        teacher_logits = torch.randn(32, 4)
        
        loss = kl_distill_loss(student_logits, teacher_logits)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.ndim == 0
        assert loss.item() >= 0
    
    def test_kl_loss_identical_logits(self):
        """Test KL loss is zero for identical logits."""
        logits = torch.randn(32, 4)
        
        loss = kl_distill_loss(logits, logits)
        
        # KL divergence should be ~0 for identical distributions
        assert loss.item() < 1e-6
    
    def test_kl_loss_with_temperature(self):
        """Test temperature affects KL loss."""
        student_logits = torch.randn(32, 4)
        teacher_logits = torch.randn(32, 4)
        
        loss_low_tau = kl_distill_loss(student_logits, teacher_logits, tau=0.5)
        loss_high_tau = kl_distill_loss(student_logits, teacher_logits, tau=2.0)
        
        # Both should be valid losses
        assert loss_low_tau.item() >= 0
        assert loss_high_tau.item() >= 0


class TestCombinedLoss:
    """Test combined distillation + reconstruction loss."""
    
    def test_combined_loss_basic(self):
        """Test basic combined loss."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        recon_loss = torch.tensor(0.5)
        
        loss = combined_distill_loss(student, teacher, recon_loss, alpha=0.7)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
    
    def test_combined_loss_alpha_zero(self):
        """Test alpha=0 returns only reconstruction loss."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        recon_loss = torch.tensor(0.5)
        
        loss = combined_distill_loss(student, teacher, recon_loss, alpha=0.0)
        
        # Should be equal to reconstruction loss
        assert abs(loss.item() - 0.5) < 1e-6
    
    def test_combined_loss_alpha_one(self):
        """Test alpha=1 returns only distillation loss."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        recon_loss = torch.tensor(0.5)
        
        loss_combined = combined_distill_loss(student, teacher, recon_loss, alpha=1.0)
        loss_distill = distill_loss(student, teacher)
        
        # Should be equal to distillation loss
        assert abs(loss_combined.item() - loss_distill.item()) < 1e-6
    
    def test_combined_loss_no_reconstruction(self):
        """Test combined loss without reconstruction loss."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        
        loss = combined_distill_loss(student, teacher, reconstruction_loss=None, alpha=0.5)
        
        # Should equal distillation loss when no reconstruction
        loss_distill = distill_loss(student, teacher)
        assert abs(loss.item() - loss_distill.item()) < 1e-6
    
    def test_combined_loss_invalid_alpha(self):
        """Test invalid alpha raises error."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        
        with pytest.raises(ValueError, match="alpha must be in"):
            combined_distill_loss(student, teacher, alpha=1.5)
        
        with pytest.raises(ValueError, match="alpha must be in"):
            combined_distill_loss(student, teacher, alpha=-0.1)


class TestCheckpointLoading:
    """Test teacher checkpoint loading."""
    
    def test_load_checkpoint_cpu(self):
        """Test loading checkpoint on CPU."""
        # Create temporary checkpoint
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            checkpoint_path = tmp.name
            checkpoint = {
                "model_state": {"weight": torch.randn(100, 50)},
                "embeddings": torch.randn(10, 1536),
                "metadata": {"version": "1.0"},
            }
            torch.save(checkpoint, checkpoint_path)
        
        try:
            loaded = load_teacher_checkpoint(checkpoint_path, device="cpu")
            
            assert "model_state" in loaded
            assert "embeddings" in loaded
            assert "metadata" in loaded
            assert loaded["embeddings"].shape == (10, 1536)
        finally:
            os.unlink(checkpoint_path)
    
    def test_load_checkpoint_not_found(self):
        """Test loading non-existent checkpoint raises error."""
        with pytest.raises(FileNotFoundError, match="Checkpoint not found"):
            load_teacher_checkpoint("nonexistent_checkpoint.pt")
    
    def test_load_checkpoint_corrupted(self):
        """Test loading corrupted checkpoint raises error."""
        # Create corrupted file
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            checkpoint_path = tmp.name
            tmp.write(b"not a valid pytorch checkpoint")
        
        try:
            with pytest.raises(RuntimeError, match="Failed to load checkpoint"):
                load_teacher_checkpoint(checkpoint_path)
        finally:
            os.unlink(checkpoint_path)


class TestCurriculumSchedule:
    """Test curriculum learning schedule."""
    
    def test_linear_schedule(self):
        """Test linear temperature schedule."""
        schedule = create_curriculum_schedule(4.0, 0.5, num_stages=5, schedule_type="linear")
        
        # Check start and end
        assert abs(schedule(0) - 4.0) < 1e-6
        assert abs(schedule(4) - 0.5) < 1e-6
        
        # Check monotonically decreasing
        for i in range(4):
            assert schedule(i) > schedule(i + 1)
    
    def test_exponential_schedule(self):
        """Test exponential temperature schedule."""
        schedule = create_curriculum_schedule(4.0, 0.5, num_stages=5, schedule_type="exponential")
        
        # Check start and end
        assert abs(schedule(0) - 4.0) < 1e-6
        assert abs(schedule(4) - 0.5) < 1e-6
        
        # Check monotonically decreasing
        for i in range(4):
            assert schedule(i) > schedule(i + 1)
    
    def test_cosine_schedule(self):
        """Test cosine temperature schedule."""
        schedule = create_curriculum_schedule(4.0, 0.5, num_stages=5, schedule_type="cosine")
        
        # Check start and end
        assert abs(schedule(0) - 4.0) < 1e-6
        assert abs(schedule(4) - 0.5) < 1e-6
        
        # Check monotonically decreasing
        for i in range(4):
            assert schedule(i) > schedule(i + 1)
    
    def test_schedule_invalid_params(self):
        """Test invalid schedule parameters."""
        # start_tau <= end_tau
        with pytest.raises(ValueError, match="start_tau"):
            create_curriculum_schedule(0.5, 4.0, num_stages=5)
        
        # num_stages < 1
        with pytest.raises(ValueError, match="num_stages"):
            create_curriculum_schedule(4.0, 0.5, num_stages=0)
        
        # Invalid schedule type
        with pytest.raises(ValueError, match="schedule_type"):
            create_curriculum_schedule(4.0, 0.5, num_stages=5, schedule_type="invalid")
    
    def test_schedule_single_stage(self):
        """Test schedule with single stage."""
        schedule = create_curriculum_schedule(4.0, 0.5, num_stages=1)
        
        # With single stage, should return start_tau
        assert abs(schedule(0) - 4.0) < 1e-6


class TestCurriculumDistillStep:
    """Test curriculum distillation step."""
    
    def test_curriculum_step_basic(self):
        """Test basic curriculum step."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        schedule = create_curriculum_schedule(3.0, 0.5, num_stages=5)
        
        loss, tau = curriculum_distill_step(student, teacher, stage=2, tau_schedule=schedule)
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
        assert isinstance(tau, float)
        assert 0.5 <= tau <= 3.0
    
    def test_curriculum_step_with_reconstruction(self):
        """Test curriculum step with reconstruction loss."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        recon_loss = torch.tensor(0.3)
        schedule = create_curriculum_schedule(3.0, 0.5, num_stages=5)
        
        loss, tau = curriculum_distill_step(
            student, teacher, stage=2, tau_schedule=schedule, 
            alpha=0.7, reconstruction_loss=recon_loss
        )
        
        assert isinstance(loss, torch.Tensor)
        assert loss.item() >= 0
    
    def test_curriculum_step_tau_progression(self):
        """Test temperature decreases across stages."""
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        schedule = create_curriculum_schedule(3.0, 0.5, num_stages=5)
        
        taus = []
        for stage in range(5):
            _, tau = curriculum_distill_step(student, teacher, stage, schedule)
            taus.append(tau)
        
        # Check monotonically decreasing
        for i in range(4):
            assert taus[i] > taus[i + 1]


class TestDistillationConfig:
    """Test distillation configuration dataclass."""
    
    def test_config_creation(self):
        """Test basic config creation."""
        config = DistillationConfig(
            teacher_dim=1536,
            student_dim=5,
            tau=1.0,
            alpha=0.5,
        )
        
        assert config.teacher_dim == 1536
        assert config.student_dim == 5
        assert config.tau == 1.0
        assert config.alpha == 0.5
    
    def test_config_validation_alpha(self):
        """Test alpha validation."""
        # Invalid alpha > 1
        with pytest.raises(ValueError, match="alpha must be in"):
            DistillationConfig(alpha=1.5)
        
        # Invalid alpha < 0
        with pytest.raises(ValueError, match="alpha must be in"):
            DistillationConfig(alpha=-0.1)
    
    def test_config_validation_tau(self):
        """Test tau validation."""
        with pytest.raises(ValueError, match="tau must be positive"):
            DistillationConfig(tau=0)
        
        with pytest.raises(ValueError, match="tau must be positive"):
            DistillationConfig(tau=-1.0)
    
    def test_config_validation_loss_type(self):
        """Test loss_type validation."""
        with pytest.raises(ValueError, match="loss_type must be"):
            DistillationConfig(loss_type="invalid")
    
    def test_config_validation_device(self):
        """Test device validation."""
        with pytest.raises(ValueError, match="device must be"):
            DistillationConfig(device="gpu")
    
    def test_config_curriculum_validation(self):
        """Test curriculum validation."""
        # Invalid curriculum_stages
        with pytest.raises(ValueError, match="curriculum_stages"):
            DistillationConfig(curriculum=True, curriculum_stages=0)
        
        # Invalid tau schedule (start <= end)
        with pytest.raises(ValueError, match="curriculum_tau_schedule"):
            DistillationConfig(
                curriculum=True,
                curriculum_tau_schedule=(0.5, 3.0)
            )
    
    def test_config_get_tau_for_stage(self):
        """Test get_tau_for_stage method."""
        config = DistillationConfig(
            curriculum=True,
            curriculum_stages=5,
            curriculum_tau_schedule=(4.0, 0.5),
        )
        
        tau0 = config.get_tau_for_stage(0)
        tau4 = config.get_tau_for_stage(4)
        
        assert abs(tau0 - 4.0) < 1e-6
        assert abs(tau4 - 0.5) < 1e-6
    
    def test_config_get_tau_no_curriculum(self):
        """Test get_tau_for_stage without curriculum."""
        config = DistillationConfig(curriculum=False, tau=1.5)
        
        # Should always return config.tau
        assert config.get_tau_for_stage(0) == 1.5
        assert config.get_tau_for_stage(10) == 1.5
    
    def test_config_to_dict(self):
        """Test config to dictionary conversion."""
        config = DistillationConfig(tau=2.0, alpha=0.7)
        config_dict = config.to_dict()
        
        assert isinstance(config_dict, dict)
        assert config_dict["tau"] == 2.0
        assert config_dict["alpha"] == 0.7
    
    def test_config_from_dict(self):
        """Test config from dictionary creation."""
        config_dict = {
            "tau": 2.0,
            "alpha": 0.7,
            "teacher_dim": 1536,
            "student_dim": 5,
        }
        config = DistillationConfig.from_dict(config_dict)
        
        assert config.tau == 2.0
        assert config.alpha == 0.7
    
    def test_default_configs(self):
        """Test default configuration presets."""
        # Test DEFAULT_OPENAI_CONFIG
        assert DEFAULT_OPENAI_CONFIG.teacher_dim == 1536
        assert DEFAULT_OPENAI_CONFIG.student_dim == 5
        
        # Test CURRICULUM_CONFIG
        assert CURRICULUM_CONFIG.curriculum is True
        assert CURRICULUM_CONFIG.curriculum_stages > 1


class TestIntegration:
    """Integration tests combining multiple components."""
    
    def test_full_distillation_pipeline_cpu(self):
        """Test complete distillation pipeline on CPU."""
        # Create fake teacher checkpoint
        with tempfile.NamedTemporaryFile(suffix=".pt", delete=False) as tmp:
            checkpoint_path = tmp.name
            checkpoint = {
                "embeddings": torch.randn(100, 1536),
                "metadata": {"model": "teacher"},
            }
            torch.save(checkpoint, checkpoint_path)
        
        try:
            # Load checkpoint
            loaded = load_teacher_checkpoint(checkpoint_path, device="cpu")
            teacher_embeddings = loaded["embeddings"]
            
            # Create student embeddings
            student_embeddings = torch.randn(100, 5)
            
            # Compute loss
            loss = distill_loss(student_embeddings, teacher_embeddings)
            
            assert loss.item() >= 0
            assert teacher_embeddings.device.type == "cpu"
        finally:
            os.unlink(checkpoint_path)
    
    def test_curriculum_learning_full_cycle(self):
        """Test full curriculum learning cycle."""
        config = CURRICULUM_CONFIG
        schedule = create_curriculum_schedule(
            config.curriculum_tau_schedule[0],
            config.curriculum_tau_schedule[1],
            config.curriculum_stages,
        )
        
        student = torch.randn(16, 5)
        teacher = torch.randn(16, 1536)
        
        losses = []
        taus = []
        
        for stage in range(config.curriculum_stages):
            loss, tau = curriculum_distill_step(
                student, teacher, stage, schedule, alpha=config.alpha
            )
            losses.append(loss.item())
            taus.append(tau)
        
        # Verify tau decreases
        for i in range(len(taus) - 1):
            assert taus[i] > taus[i + 1]
        
        # All losses should be valid
        for loss in losses:
            assert loss >= 0
            assert not torch.isnan(torch.tensor(loss))
