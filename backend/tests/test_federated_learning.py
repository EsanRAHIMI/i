"""
Unit tests for federated learning system.
"""
import pytest
import torch
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import json
import base64

from app.core.federated_learning import (
    UserBehaviorModel,
    DifferentialPrivacyManager,
    LocalModelTrainer,
    ModelUpdateEncryption,
    FeatureExtractor
)
from app.core.federated_aggregator import (
    FedAvgAggregator,
    SecureAggregationValidator,
    ModelVersionManager
)
from app.tasks.federated_learning import (
    train_local_model,
    aggregate_model_updates
)
from app.database.models import User, FederatedRound, ClientUpdate


class TestUserBehaviorModel:
    """Test the neural network model for user behavior."""
    
    def test_model_initialization(self):
        """Test model initialization with default parameters."""
        model = UserBehaviorModel()
        
        assert model.input_dim == 50
        assert model.hidden_dim == 128
        assert model.output_dim == 10
        assert len(list(model.parameters())) > 0
    
    def test_model_forward_pass(self):
        """Test model forward pass with sample input."""
        model = UserBehaviorModel(input_dim=10, output_dim=5)
        
        # Create sample input
        batch_size = 4
        input_tensor = torch.randn(batch_size, 10)
        
        # Forward pass
        output = model(input_tensor)
        
        assert output.shape == (batch_size, 5)
        assert torch.allclose(output.sum(dim=1), torch.ones(batch_size), atol=1e-6)  # Softmax check
    
    def test_model_custom_dimensions(self):
        """Test model with custom dimensions."""
        model = UserBehaviorModel(input_dim=20, hidden_dim=64, output_dim=3)
        
        input_tensor = torch.randn(2, 20)
        output = model(input_tensor)
        
        assert output.shape == (2, 3)


class TestDifferentialPrivacyManager:
    """Test differential privacy mechanisms."""
    
    def test_privacy_manager_initialization(self):
        """Test privacy manager initialization."""
        privacy_manager = DifferentialPrivacyManager(epsilon=2.0, delta=1e-6)
        
        assert privacy_manager.epsilon == 2.0
        assert privacy_manager.delta == 1e-6
        assert privacy_manager.privacy_budget_used == 0.0
    
    def test_gradient_clipping(self):
        """Test gradient clipping functionality."""
        privacy_manager = DifferentialPrivacyManager()
        
        # Create test gradients
        gradients = {
            "layer1.weight": torch.tensor([[10.0, -5.0], [3.0, 8.0]]),
            "layer1.bias": torch.tensor([2.0, -1.0]),
            "layer2.weight": None  # Test None gradient
        }
        
        clipped_gradients = privacy_manager.clip_gradients(gradients, max_norm=1.0)
        
        # Check that gradients are clipped
        total_norm = 0.0
        for name, grad in clipped_gradients.items():
            if grad is not None:
                total_norm += grad.norm().item() ** 2
        total_norm = total_norm ** 0.5
        
        assert total_norm <= 1.0 + 1e-6  # Allow small numerical error
        assert clipped_gradients["layer2.weight"] is None
    
    def test_noise_addition(self):
        """Test differential privacy noise addition."""
        privacy_manager = DifferentialPrivacyManager(epsilon=1.0)
        
        gradients = {
            "weight": torch.zeros(2, 2),
            "bias": torch.zeros(2)
        }
        
        noisy_gradients = privacy_manager.add_noise_to_gradients(gradients)
        
        # Check that noise was added (gradients should no longer be zero)
        assert not torch.allclose(noisy_gradients["weight"], gradients["weight"])
        assert not torch.allclose(noisy_gradients["bias"], gradients["bias"])
        assert privacy_manager.privacy_budget_used == 1.0


class TestLocalModelTrainer:
    """Test local model training functionality."""
    
    def test_trainer_initialization(self):
        """Test trainer initialization."""
        trainer = LocalModelTrainer()
        
        assert trainer.model is not None
        assert trainer.optimizer is not None
        assert trainer.criterion is not None
        assert trainer.privacy_manager is not None
    
    def test_data_preprocessing(self):
        """Test user data preprocessing."""
        trainer = LocalModelTrainer()
        
        # Sample user data
        raw_data = {
            "interactions": [
                {
                    "hour": 14,
                    "day_of_week": 1,
                    "activity_type": 2,
                    "duration": 1800,
                    "location_type": 1,
                    "device_type": 0,
                    "next_action": 3
                },
                {
                    "hour": 9,
                    "day_of_week": 5,
                    "activity_type": 1,
                    "duration": 600,
                    "location_type": 0,
                    "device_type": 1,
                    "next_action": 1
                }
            ]
        }
        
        features, labels = trainer.preprocess_user_data(raw_data)
        
        assert features.shape[0] == 2  # Two interactions
        assert features.shape[1] == trainer.model_config["input_dim"]
        assert labels.shape[0] == 2
        assert torch.all(labels >= 0)
        assert torch.all(labels < trainer.model_config["output_dim"])
    
    def test_local_training(self):
        """Test local model training process."""
        trainer = LocalModelTrainer({
            "input_dim": 10,
            "hidden_dim": 32,
            "output_dim": 5,
            "learning_rate": 0.01,
            "batch_size": 2,
            "epochs": 2
        })
        
        # Sample training data
        training_data = {
            "interactions": [
                {
                    "hour": 14, "day_of_week": 1, "activity_type": 2,
                    "duration": 1800, "location_type": 1, "device_type": 0,
                    "next_action": 3
                }
            ]
        }
        
        result = trainer.train_local_model(training_data)
        
        assert result["status"] == "success"
        assert "model_update" in result
        assert "training_metrics" in result
        assert result["training_metrics"]["epochs"] == 2
        assert result["training_metrics"]["privacy_budget_used"] > 0
    
    def test_empty_data_handling(self):
        """Test handling of empty training data."""
        trainer = LocalModelTrainer()
        
        empty_data = {"interactions": []}
        result = trainer.train_local_model(empty_data)
        
        assert result["status"] == "success"  # Should handle gracefully
        assert "model_update" in result


class TestModelUpdateEncryption:
    """Test model update encryption and decryption."""
    
    def test_encryption_decryption(self):
        """Test encryption and decryption of model updates."""
        encryptor = ModelUpdateEncryption("test_password")
        
        # Sample model update
        model_update = {
            "layer1.weight": torch.randn(3, 2),
            "layer1.bias": torch.randn(3),
            "layer2.weight": None
        }
        
        # Encrypt
        encrypted_data = encryptor.encrypt_model_update(model_update)
        assert isinstance(encrypted_data, str)
        assert len(encrypted_data) > 0
        
        # Decrypt
        decrypted_update = encryptor.decrypt_model_update(encrypted_data)
        
        # Verify decryption
        assert set(decrypted_update.keys()) == set(model_update.keys())
        assert torch.allclose(decrypted_update["layer1.weight"], model_update["layer1.weight"])
        assert torch.allclose(decrypted_update["layer1.bias"], model_update["layer1.bias"])
        assert decrypted_update["layer2.weight"] is None
    
    def test_encryption_with_different_passwords(self):
        """Test that different passwords produce different encrypted data."""
        model_update = {"weight": torch.randn(2, 2)}
        
        encryptor1 = ModelUpdateEncryption("password1")
        encryptor2 = ModelUpdateEncryption("password2")
        
        encrypted1 = encryptor1.encrypt_model_update(model_update)
        encrypted2 = encryptor2.encrypt_model_update(model_update)
        
        assert encrypted1 != encrypted2


class TestFeatureExtractor:
    """Test feature extraction from user data."""
    
    def test_feature_extraction(self):
        """Test feature extraction from interactions."""
        extractor = FeatureExtractor()
        
        interactions = [
            {
                "timestamp": "14:30:00",
                "date": "2024-01-01",
                "activity_type": 1,
                "duration": 300,
                "location_type": 1,
                "device_type": 0,
                "type": "voice",
                "involves_calendar": True,
                "is_weekend": False
            },
            {
                "timestamp": "09:15:00",
                "date": "2024-01-02",
                "activity_type": 2,
                "duration": 600,
                "location_type": 0,
                "device_type": 1,
                "type": "message",
                "involves_calendar": False,
                "is_weekend": True
            }
        ]
        
        features = extractor.extract_features_from_interactions(interactions)
        
        assert "temporal_patterns" in features
        assert "activity_patterns" in features
        assert "context_patterns" in features
        assert "interaction_patterns" in features
        
        # Check temporal patterns
        temporal = features["temporal_patterns"]
        assert "avg_hour" in temporal
        assert "weekend_ratio" in temporal
        assert temporal["weekend_ratio"] == 0.5  # 1 out of 2 interactions
    
    def test_empty_interactions(self):
        """Test feature extraction with empty interactions."""
        extractor = FeatureExtractor()
        
        features = extractor.extract_features_from_interactions([])
        
        # Should return default values
        assert features["temporal_patterns"]["avg_hour"] == 12.0
        assert features["activity_patterns"]["avg_duration"] == 300.0


class TestFedAvgAggregator:
    """Test federated averaging aggregation."""
    
    def test_aggregator_initialization(self):
        """Test aggregator initialization."""
        aggregator = FedAvgAggregator(differential_privacy=True)
        
        assert aggregator.differential_privacy is True
        assert aggregator.privacy_manager is not None
        assert aggregator.encryptor is not None
    
    def test_federated_averaging(self):
        """Test federated averaging algorithm."""
        aggregator = FedAvgAggregator(differential_privacy=False)  # Disable DP for testing
        
        # Create sample model updates
        update1 = {
            "weight": torch.tensor([[1.0, 2.0], [3.0, 4.0]]),
            "bias": torch.tensor([0.5, 1.0])
        }
        update2 = {
            "weight": torch.tensor([[2.0, 1.0], [4.0, 3.0]]),
            "bias": torch.tensor([1.0, 0.5])
        }
        
        # Encrypt updates
        encrypted_updates = [
            aggregator.encryptor.encrypt_model_update(update1),
            aggregator.encryptor.encrypt_model_update(update2)
        ]
        
        # Aggregate
        result = aggregator.aggregate_model_updates(encrypted_updates)
        
        assert result["status"] == "success"
        assert result["participant_count"] == 2
        assert result["aggregation_method"] == "FedAvg"
        
        # Decrypt and verify averaging
        aggregated_encrypted = result["aggregated_model_encrypted"]
        aggregated_model = aggregator.encryptor.decrypt_model_update(aggregated_encrypted)
        
        expected_weight = (update1["weight"] + update2["weight"]) / 2
        expected_bias = (update1["bias"] + update2["bias"]) / 2
        
        assert torch.allclose(aggregated_model["weight"], expected_weight, atol=1e-4)
        assert torch.allclose(aggregated_model["bias"], expected_bias, atol=1e-4)
    
    def test_weighted_averaging(self):
        """Test weighted federated averaging."""
        aggregator = FedAvgAggregator(differential_privacy=False)
        
        update1 = {"weight": torch.tensor([1.0, 2.0])}
        update2 = {"weight": torch.tensor([3.0, 4.0])}
        
        encrypted_updates = [
            aggregator.encryptor.encrypt_model_update(update1),
            aggregator.encryptor.encrypt_model_update(update2)
        ]
        
        # Use weights [0.3, 0.7]
        weights = [0.3, 0.7]
        result = aggregator.aggregate_model_updates(encrypted_updates, weights)
        
        assert result["status"] == "success"
        
        aggregated_model = aggregator.encryptor.decrypt_model_update(
            result["aggregated_model_encrypted"]
        )
        
        expected = 0.3 * update1["weight"] + 0.7 * update2["weight"]
        assert torch.allclose(aggregated_model["weight"], expected, atol=1e-4)
    
    def test_insufficient_updates(self):
        """Test handling of insufficient updates."""
        aggregator = FedAvgAggregator()
        
        # Only one update
        update = {"weight": torch.tensor([1.0, 2.0])}
        encrypted_updates = [aggregator.encryptor.encrypt_model_update(update)]
        
        result = aggregator.aggregate_model_updates(encrypted_updates)
        
        assert result["status"] == "error"
        assert "at least 2" in result["error"].lower()


class TestSecureAggregationValidator:
    """Test security validation for model updates."""
    
    def test_validator_initialization(self):
        """Test validator initialization."""
        validator = SecureAggregationValidator()
        
        assert validator.max_update_size_mb == 50
        assert validator.min_privacy_budget == 0.0001
        assert validator.max_privacy_budget == 10.0
    
    def test_valid_model_update(self):
        """Test validation of a valid model update."""
        validator = SecureAggregationValidator()
        encryptor = ModelUpdateEncryption()
        
        # Create valid model update
        model_update = {"weight": torch.randn(10, 10)}
        encrypted_update = encryptor.encrypt_model_update(model_update)
        
        result = validator.validate_model_update(
            encrypted_update, 
            privacy_budget_used=0.5,
            user_id="test_user"
        )
        
        assert result["valid"] is True
        assert len(result["errors"]) == 0
        assert result["metadata"]["privacy_budget_used"] == 0.5
    
    def test_oversized_update(self):
        """Test validation of oversized model update."""
        validator = SecureAggregationValidator()
        
        # Create oversized update (simulate with long string)
        oversized_update = "x" * (60 * 1024 * 1024)  # 60MB string
        
        result = validator.validate_model_update(
            oversized_update,
            privacy_budget_used=0.5,
            user_id="test_user"
        )
        
        assert result["valid"] is False
        assert any("too large" in error.lower() for error in result["errors"])
    
    def test_excessive_privacy_budget(self):
        """Test validation with excessive privacy budget."""
        validator = SecureAggregationValidator()
        encryptor = ModelUpdateEncryption()
        
        model_update = {"weight": torch.randn(5, 5)}
        encrypted_update = encryptor.encrypt_model_update(model_update)
        
        result = validator.validate_model_update(
            encrypted_update,
            privacy_budget_used=15.0,  # Exceeds max of 10.0
            user_id="test_user"
        )
        
        assert result["valid"] is False
        assert any("budget exceeded" in error.lower() for error in result["errors"])
    
    def test_aggregation_readiness(self):
        """Test aggregation readiness validation."""
        validator = SecureAggregationValidator()
        
        # Test sufficient participants
        result = validator.validate_aggregation_readiness(
            round_id="test_round",
            participant_count=10,
            min_participants=5
        )
        
        assert result["ready"] is True
        assert len(result["reasons"]) == 0
        
        # Test insufficient participants
        result = validator.validate_aggregation_readiness(
            round_id="test_round",
            participant_count=3,
            min_participants=5
        )
        
        assert result["ready"] is False
        assert any("insufficient" in reason.lower() for reason in result["reasons"])


class TestModelVersionManager:
    """Test model version management."""
    
    def test_version_manager_initialization(self):
        """Test version manager initialization."""
        manager = ModelVersionManager()
        
        assert manager.current_version == "1.0.0"
        assert len(manager.version_history) == 0
    
    def test_version_creation(self):
        """Test new version creation."""
        manager = ModelVersionManager()
        
        aggregated_model = {"weight": torch.randn(5, 5)}
        metrics = {
            "convergence_score": 0.85,
            "participant_count": 10
        }
        
        new_version = manager.create_new_version(aggregated_model, metrics)
        
        assert new_version != "1.0.0"  # Should be incremented
        assert manager.current_version == new_version
        assert len(manager.version_history) == 1
        
        version_info = manager.version_history[0]
        assert version_info["version"] == new_version
        assert version_info["previous_version"] == "1.0.0"
        assert version_info["aggregation_metrics"] == metrics
    
    def test_version_increment_logic(self):
        """Test version increment based on convergence score."""
        manager = ModelVersionManager()
        
        # High convergence should increment major version
        high_convergence_metrics = {"convergence_score": 0.95}
        version1 = manager.create_new_version({}, high_convergence_metrics)
        assert version1.startswith("2.0.0")
        
        # Medium convergence should increment minor version
        medium_convergence_metrics = {"convergence_score": 0.75}
        version2 = manager.create_new_version({}, medium_convergence_metrics)
        assert version2.startswith("2.1.0")
        
        # Low convergence should increment patch version
        low_convergence_metrics = {"convergence_score": 0.5}
        version3 = manager.create_new_version({}, low_convergence_metrics)
        assert version3.startswith("2.1.1")


class TestFederatedLearningTasks:
    """Test Celery tasks for federated learning."""
    
    @pytest.fixture
    def mock_db_session(self):
        """Mock database session."""
        session = Mock()
        session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        session.query.return_value.filter.return_value.all.return_value = []
        session.query.return_value.filter.return_value.count.return_value = 0
        return session
    
    @patch('app.tasks.federated_learning.SessionLocal')
    def test_train_local_model_task(self, mock_session_local, mock_db_session):
        """Test local model training task."""
        mock_session_local.return_value.__enter__.return_value = mock_db_session
        
        # Mock federated round
        mock_round = Mock()
        mock_round.id = "test_round_id"
        mock_round.round_number = 1
        mock_round.participant_count = 0
        mock_db_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = mock_round
        
        training_data = {
            "interactions": [
                {
                    "timestamp": "14:30:00",
                    "activity_type": 1,
                    "duration": 300,
                    "next_action": 2
                }
            ]
        }
        
        # Mock the task to avoid Celery dependency
        with patch('app.tasks.federated_learning.current_task') as mock_task:
            mock_task.request.id = "test_task_id"
            
            result = train_local_model.run("test_user_id", training_data)
            
            assert "user_id" in result
            assert "model_delta_encrypted" in result
            assert "training_metrics" in result
            assert result["user_id"] == "test_user_id"
    
    @patch('app.tasks.federated_learning.SessionLocal')
    def test_aggregate_model_updates_task(self, mock_session_local, mock_db_session):
        """Test model aggregation task."""
        mock_session_local.return_value.__enter__.return_value = mock_db_session
        
        # Mock federated round
        mock_round = Mock()
        mock_round.id = "test_round_id"
        mock_round.round_number = 1
        mock_round.aggregation_status = "in_progress"
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_round
        
        # Mock client updates
        mock_update1 = Mock()
        mock_update1.user_id = "user1"
        mock_update1.privacy_budget_used = Decimal("0.5")
        
        # Create valid encrypted update
        encryptor = ModelUpdateEncryption()
        model_update = {"weight": torch.randn(3, 3)}
        mock_update1.model_delta_encrypted = encryptor.encrypt_model_update(model_update)
        
        mock_update2 = Mock()
        mock_update2.user_id = "user2"
        mock_update2.privacy_budget_used = Decimal("0.3")
        mock_update2.model_delta_encrypted = encryptor.encrypt_model_update(model_update)
        
        mock_db_session.query.return_value.filter.return_value.all.return_value = [
            mock_update1, mock_update2
        ]
        
        with patch('app.tasks.federated_learning.current_task') as mock_task:
            mock_task.request.id = "test_task_id"
            
            result = aggregate_model_updates.run("test_round_id")
            
            assert "round_id" in result
            assert "participant_count" in result
            assert "aggregation_method" in result
            assert result["aggregation_method"] == "FedAvg"


@pytest.mark.integration
class TestFederatedLearningIntegration:
    """Integration tests for federated learning system."""
    
    def test_end_to_end_federated_learning(self):
        """Test complete federated learning workflow."""
        # This would be a comprehensive integration test
        # that tests the entire workflow from local training
        # to aggregation and model distribution
        
        # 1. Create multiple local trainers
        trainers = [LocalModelTrainer() for _ in range(3)]
        
        # 2. Train local models
        training_data = {
            "interactions": [
                {
                    "hour": 14, "day_of_week": 1, "activity_type": 1,
                    "duration": 300, "location_type": 0, "device_type": 0,
                    "next_action": 2
                }
            ]
        }
        
        model_updates = []
        for trainer in trainers:
            result = trainer.train_local_model(training_data)
            assert result["status"] == "success"
            model_updates.append(result["model_update"])
        
        # 3. Encrypt model updates
        encryptor = ModelUpdateEncryption()
        encrypted_updates = [
            encryptor.encrypt_model_update(update) 
            for update in model_updates
        ]
        
        # 4. Aggregate using FedAvg
        aggregator = FedAvgAggregator(differential_privacy=True)
        aggregation_result = aggregator.aggregate_model_updates(encrypted_updates)
        
        assert aggregation_result["status"] == "success"
        assert aggregation_result["participant_count"] == 3
        assert aggregation_result["differential_privacy_applied"] is True
        
        # 5. Verify aggregated model can be decrypted
        aggregated_encrypted = aggregation_result["aggregated_model_encrypted"]
        aggregated_model = encryptor.decrypt_model_update(aggregated_encrypted)
        
        assert len(aggregated_model) > 0
        
        # 6. Validate aggregation metrics
        metrics = aggregation_result["aggregation_metrics"]
        assert "participant_count" in metrics
        assert "convergence_score" in metrics
        assert "model_size_mb" in metrics
        
        print("End-to-end federated learning test completed successfully")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])