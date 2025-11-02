"""
Core federated learning infrastructure for local model training and aggregation.
"""
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import os
import structlog
from datetime import datetime, timedelta
import pickle

logger = structlog.get_logger(__name__)


class UserBehaviorModel(nn.Module):
    """
    Neural network model for learning user behavior patterns.
    Designed to be lightweight for federated learning.
    """
    
    def __init__(self, input_dim: int = 50, hidden_dim: int = 128, output_dim: int = 10):
        super(UserBehaviorModel, self).__init__()
        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.output_dim = output_dim
        
        # Simple feedforward network
        self.layers = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim // 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim // 2, output_dim),
            nn.Softmax(dim=1)
        )
    
    def forward(self, x):
        return self.layers(x)


class DifferentialPrivacyManager:
    """
    Manages differential privacy for federated learning.
    """
    
    def __init__(self, epsilon: float = 1.0, delta: float = 1e-5, sensitivity: float = 1.0):
        self.epsilon = epsilon
        self.delta = delta
        self.sensitivity = sensitivity
        self.privacy_budget_used = 0.0
    
    def add_noise_to_gradients(self, gradients: Dict[str, torch.Tensor]) -> Dict[str, torch.Tensor]:
        """
        Add Gaussian noise to gradients for differential privacy.
        
        Args:
            gradients: Model gradients
            
        Returns:
            Noisy gradients
        """
        # Calculate noise scale based on privacy parameters
        noise_scale = (2 * self.sensitivity * np.log(1.25 / self.delta)) / self.epsilon
        
        noisy_gradients = {}
        for name, grad in gradients.items():
            if grad is not None:
                noise = torch.normal(0, noise_scale, size=grad.shape)
                noisy_gradients[name] = grad + noise
            else:
                noisy_gradients[name] = grad
        
        # Update privacy budget
        self.privacy_budget_used += self.epsilon
        
        return noisy_gradients
    
    def clip_gradients(self, gradients: Dict[str, torch.Tensor], max_norm: float = 1.0) -> Dict[str, torch.Tensor]:
        """
        Clip gradients to bound sensitivity.
        
        Args:
            gradients: Model gradients
            max_norm: Maximum gradient norm
            
        Returns:
            Clipped gradients
        """
        clipped_gradients = {}
        
        # Calculate total norm
        total_norm = 0.0
        for grad in gradients.values():
            if grad is not None:
                total_norm += grad.norm().item() ** 2
        total_norm = total_norm ** 0.5
        
        # Clip if necessary
        clip_coef = max_norm / (total_norm + 1e-6)
        if clip_coef < 1:
            for name, grad in gradients.items():
                if grad is not None:
                    clipped_gradients[name] = grad * clip_coef
                else:
                    clipped_gradients[name] = grad
        else:
            clipped_gradients = gradients
        
        return clipped_gradients


class LocalModelTrainer:
    """
    Handles local model training for federated learning.
    """
    
    def __init__(self, model_config: Dict[str, Any] = None):
        self.model_config = model_config or {
            "input_dim": 50,
            "hidden_dim": 128,
            "output_dim": 10,
            "learning_rate": 0.001,
            "batch_size": 32,
            "epochs": 5
        }
        
        self.model = UserBehaviorModel(
            input_dim=self.model_config["input_dim"],
            hidden_dim=self.model_config["hidden_dim"],
            output_dim=self.model_config["output_dim"]
        )
        
        self.optimizer = optim.Adam(
            self.model.parameters(), 
            lr=self.model_config["learning_rate"]
        )
        self.criterion = nn.CrossEntropyLoss()
        self.privacy_manager = DifferentialPrivacyManager()
        
    def preprocess_user_data(self, raw_data: Dict[str, Any]) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Preprocess user behavioral data for training.
        
        Args:
            raw_data: Raw user interaction data
            
        Returns:
            Tuple of (features, labels)
        """
        try:
            # Extract features from user interactions
            features = []
            labels = []
            
            # Example feature extraction from user data
            interactions = raw_data.get("interactions", [])
            
            for interaction in interactions:
                # Time-based features
                hour_of_day = interaction.get("hour", 0) / 24.0
                day_of_week = interaction.get("day_of_week", 0) / 7.0
                
                # Activity features
                activity_type = interaction.get("activity_type", 0)  # encoded
                duration = min(interaction.get("duration", 0) / 3600.0, 1.0)  # normalized hours
                
                # Context features
                location_type = interaction.get("location_type", 0)  # encoded
                device_type = interaction.get("device_type", 0)  # encoded
                
                # Create feature vector (pad to input_dim)
                feature_vector = [
                    hour_of_day, day_of_week, activity_type / 10.0, duration,
                    location_type / 5.0, device_type / 3.0
                ]
                
                # Pad with zeros to reach input_dim
                while len(feature_vector) < self.model_config["input_dim"]:
                    feature_vector.append(0.0)
                
                features.append(feature_vector[:self.model_config["input_dim"]])
                
                # Label is the predicted next action or preference
                label = interaction.get("next_action", 0) % self.model_config["output_dim"]
                labels.append(label)
            
            if not features:
                # Generate dummy data if no interactions
                features = [[0.0] * self.model_config["input_dim"]]
                labels = [0]
            
            return torch.tensor(features, dtype=torch.float32), torch.tensor(labels, dtype=torch.long)
            
        except Exception as e:
            logger.error("Data preprocessing failed", error=str(e))
            # Return dummy data on error
            dummy_features = torch.zeros(1, self.model_config["input_dim"])
            dummy_labels = torch.zeros(1, dtype=torch.long)
            return dummy_features, dummy_labels
    
    def train_local_model(self, user_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Train the local model on user data.
        
        Args:
            user_data: User behavioral data
            
        Returns:
            Training results and model update
        """
        try:
            logger.info("Starting local model training")
            
            # Preprocess data
            features, labels = self.preprocess_user_data(user_data)
            
            # Create data loader
            dataset = TensorDataset(features, labels)
            dataloader = DataLoader(
                dataset, 
                batch_size=self.model_config["batch_size"], 
                shuffle=True
            )
            
            # Store initial model state
            initial_state = {name: param.clone() for name, param in self.model.named_parameters()}
            
            # Training loop
            self.model.train()
            total_loss = 0.0
            num_batches = 0
            
            for epoch in range(self.model_config["epochs"]):
                epoch_loss = 0.0
                
                for batch_features, batch_labels in dataloader:
                    self.optimizer.zero_grad()
                    
                    # Forward pass
                    outputs = self.model(batch_features)
                    loss = self.criterion(outputs, batch_labels)
                    
                    # Backward pass
                    loss.backward()
                    
                    # Clip gradients for privacy
                    gradients = {name: param.grad for name, param in self.model.named_parameters()}
                    clipped_gradients = self.privacy_manager.clip_gradients(gradients)
                    
                    # Apply clipped gradients
                    for name, param in self.model.named_parameters():
                        if param.grad is not None:
                            param.grad = clipped_gradients[name]
                    
                    self.optimizer.step()
                    
                    epoch_loss += loss.item()
                    num_batches += 1
                
                total_loss += epoch_loss
                logger.debug("Epoch completed", epoch=epoch, loss=epoch_loss)
            
            # Calculate model update (difference from initial state)
            model_update = {}
            for name, param in self.model.named_parameters():
                model_update[name] = param.data - initial_state[name]
            
            # Add differential privacy noise to model update
            noisy_update = self.privacy_manager.add_noise_to_gradients(model_update)
            
            # Calculate training metrics
            avg_loss = total_loss / max(num_batches, 1)
            
            training_result = {
                "status": "success",
                "model_update": noisy_update,
                "training_metrics": {
                    "average_loss": avg_loss,
                    "epochs": self.model_config["epochs"],
                    "samples_processed": len(features),
                    "privacy_budget_used": self.privacy_manager.privacy_budget_used
                },
                "model_info": {
                    "input_dim": self.model_config["input_dim"],
                    "hidden_dim": self.model_config["hidden_dim"],
                    "output_dim": self.model_config["output_dim"],
                    "parameter_count": sum(p.numel() for p in self.model.parameters())
                }
            }
            
            logger.info("Local model training completed", metrics=training_result["training_metrics"])
            
            return training_result
            
        except Exception as e:
            logger.error("Local model training failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "model_update": {},
                "training_metrics": {}
            }


class ModelUpdateEncryption:
    """
    Handles encryption and decryption of model updates for secure transmission.
    """
    
    def __init__(self, password: str = None):
        self.password = password or os.getenv("FEDERATED_ENCRYPTION_KEY", "default_key_change_in_production")
        self.key = self._derive_key(self.password)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, password: str) -> bytes:
        """Derive encryption key from password."""
        password_bytes = password.encode()
        salt = b'federated_learning_salt'  # In production, use random salt per user
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password_bytes))
        return key
    
    def encrypt_model_update(self, model_update: Dict[str, torch.Tensor]) -> str:
        """
        Encrypt model update for secure transmission.
        
        Args:
            model_update: Model parameter updates
            
        Returns:
            Encrypted model update as base64 string
        """
        try:
            # Convert tensors to serializable format
            serializable_update = {}
            for name, tensor in model_update.items():
                if tensor is not None:
                    serializable_update[name] = tensor.detach().cpu().numpy().tolist()
                else:
                    serializable_update[name] = None
            
            # Serialize to JSON
            json_data = json.dumps(serializable_update)
            
            # Encrypt
            encrypted_data = self.cipher.encrypt(json_data.encode())
            
            # Encode to base64 for storage
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error("Model update encryption failed", error=str(e))
            raise
    
    def decrypt_model_update(self, encrypted_update: str) -> Dict[str, torch.Tensor]:
        """
        Decrypt model update.
        
        Args:
            encrypted_update: Encrypted model update as base64 string
            
        Returns:
            Decrypted model parameter updates
        """
        try:
            # Decode from base64
            encrypted_data = base64.b64decode(encrypted_update.encode())
            
            # Decrypt
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # Deserialize from JSON
            serializable_update = json.loads(decrypted_data.decode())
            
            # Convert back to tensors
            model_update = {}
            for name, data in serializable_update.items():
                if data is not None:
                    model_update[name] = torch.tensor(data, dtype=torch.float32)
                else:
                    model_update[name] = None
            
            return model_update
            
        except Exception as e:
            logger.error("Model update decryption failed", error=str(e))
            raise


class FeatureExtractor:
    """
    Extracts features from user behavioral data for model training.
    """
    
    def __init__(self):
        self.feature_config = {
            "temporal_features": ["hour_of_day", "day_of_week", "month", "is_weekend"],
            "activity_features": ["activity_type", "duration", "frequency"],
            "context_features": ["location_type", "device_type", "app_usage"],
            "interaction_features": ["voice_commands", "calendar_events", "messages"]
        }
    
    def extract_features_from_interactions(self, interactions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Extract features from user interaction history.
        
        Args:
            interactions: List of user interactions
            
        Returns:
            Extracted features for training
        """
        try:
            features = {
                "temporal_patterns": self._extract_temporal_patterns(interactions),
                "activity_patterns": self._extract_activity_patterns(interactions),
                "context_patterns": self._extract_context_patterns(interactions),
                "interaction_patterns": self._extract_interaction_patterns(interactions)
            }
            
            return features
            
        except Exception as e:
            logger.error("Feature extraction failed", error=str(e))
            return {"temporal_patterns": {}, "activity_patterns": {}, "context_patterns": {}, "interaction_patterns": {}}
    
    def _extract_temporal_patterns(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract temporal usage patterns."""
        if not interactions:
            return {"avg_hour": 12.0, "weekend_ratio": 0.5, "daily_frequency": 1.0}
        
        hours = [int(interaction.get("timestamp", "12:00:00").split(":")[0]) for interaction in interactions]
        weekend_count = sum(1 for interaction in interactions if interaction.get("is_weekend", False))
        
        return {
            "avg_hour": sum(hours) / len(hours) if hours else 12.0,
            "weekend_ratio": weekend_count / len(interactions) if interactions else 0.5,
            "daily_frequency": len(interactions) / max(1, len(set(interaction.get("date", "2024-01-01") for interaction in interactions)))
        }
    
    def _extract_activity_patterns(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract activity usage patterns."""
        if not interactions:
            return {"avg_duration": 300.0, "most_common_activity": 0.0, "activity_diversity": 1.0}
        
        durations = [interaction.get("duration", 300) for interaction in interactions]
        activities = [interaction.get("activity_type", 0) for interaction in interactions]
        
        return {
            "avg_duration": sum(durations) / len(durations) if durations else 300.0,
            "most_common_activity": max(set(activities), key=activities.count) if activities else 0.0,
            "activity_diversity": len(set(activities)) / len(activities) if activities else 1.0
        }
    
    def _extract_context_patterns(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract contextual usage patterns."""
        if not interactions:
            return {"primary_location": 0.0, "device_consistency": 1.0, "context_switches": 0.0}
        
        locations = [interaction.get("location_type", 0) for interaction in interactions]
        devices = [interaction.get("device_type", 0) for interaction in interactions]
        
        return {
            "primary_location": max(set(locations), key=locations.count) if locations else 0.0,
            "device_consistency": locations.count(max(set(devices), key=devices.count)) / len(devices) if devices else 1.0,
            "context_switches": len(set(zip(locations, devices))) / len(interactions) if interactions else 0.0
        }
    
    def _extract_interaction_patterns(self, interactions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Extract interaction-specific patterns."""
        if not interactions:
            return {"voice_usage_ratio": 0.3, "calendar_integration": 0.5, "message_frequency": 1.0}
        
        voice_interactions = sum(1 for interaction in interactions if interaction.get("type") == "voice")
        calendar_interactions = sum(1 for interaction in interactions if interaction.get("involves_calendar", False))
        message_interactions = sum(1 for interaction in interactions if interaction.get("type") == "message")
        
        return {
            "voice_usage_ratio": voice_interactions / len(interactions) if interactions else 0.3,
            "calendar_integration": calendar_interactions / len(interactions) if interactions else 0.5,
            "message_frequency": message_interactions / len(interactions) if interactions else 0.3
        }