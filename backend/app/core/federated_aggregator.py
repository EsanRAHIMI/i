"""
Federated aggregation service implementing FedAvg algorithm with differential privacy.
"""
import torch
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import structlog
from datetime import datetime
import json
import statistics
from collections import defaultdict

from .federated_learning import ModelUpdateEncryption, DifferentialPrivacyManager, UserBehaviorModel

logger = structlog.get_logger(__name__)


class FedAvgAggregator:
    """
    Implements Federated Averaging (FedAvg) algorithm for model aggregation.
    """
    
    def __init__(self, differential_privacy: bool = True):
        self.differential_privacy = differential_privacy
        self.privacy_manager = DifferentialPrivacyManager() if differential_privacy else None
        self.encryptor = ModelUpdateEncryption()
        
    def aggregate_model_updates(self, encrypted_updates: List[str], 
                              client_weights: Optional[List[float]] = None) -> Dict[str, Any]:
        """
        Aggregate encrypted model updates using FedAvg algorithm.
        
        Args:
            encrypted_updates: List of encrypted model updates from clients
            client_weights: Optional weights for each client (based on data size)
            
        Returns:
            Aggregated model and aggregation metadata
        """
        try:
            logger.info("Starting FedAvg aggregation", num_clients=len(encrypted_updates))
            
            if len(encrypted_updates) < 2:
                raise ValueError("Need at least 2 client updates for aggregation")
            
            # Decrypt all model updates
            decrypted_updates = []
            for encrypted_update in encrypted_updates:
                try:
                    decrypted_update = self.encryptor.decrypt_model_update(encrypted_update)
                    decrypted_updates.append(decrypted_update)
                except Exception as e:
                    logger.warning("Failed to decrypt model update", error=str(e))
                    continue
            
            if len(decrypted_updates) < 2:
                raise ValueError("Insufficient valid model updates after decryption")
            
            # Set equal weights if not provided
            if client_weights is None:
                client_weights = [1.0 / len(decrypted_updates)] * len(decrypted_updates)
            else:
                # Normalize weights
                total_weight = sum(client_weights)
                client_weights = [w / total_weight for w in client_weights]
            
            # Perform federated averaging
            aggregated_model = self._federated_average(decrypted_updates, client_weights)
            
            # Apply differential privacy if enabled
            if self.differential_privacy and self.privacy_manager:
                aggregated_model = self.privacy_manager.add_noise_to_gradients(aggregated_model)
            
            # Calculate aggregation metrics
            aggregation_metrics = self._calculate_aggregation_metrics(
                decrypted_updates, aggregated_model, client_weights
            )
            
            # Encrypt aggregated model for storage
            encrypted_aggregated_model = self.encryptor.encrypt_model_update(aggregated_model)
            
            result = {
                "status": "success",
                "aggregated_model_encrypted": encrypted_aggregated_model,
                "aggregation_metrics": aggregation_metrics,
                "participant_count": len(decrypted_updates),
                "differential_privacy_applied": self.differential_privacy,
                "aggregation_method": "FedAvg"
            }
            
            logger.info("FedAvg aggregation completed successfully", 
                       participants=len(decrypted_updates),
                       convergence_score=aggregation_metrics.get("convergence_score", 0))
            
            return result
            
        except Exception as e:
            logger.error("FedAvg aggregation failed", error=str(e))
            return {
                "status": "error",
                "error": str(e),
                "aggregated_model_encrypted": None,
                "aggregation_metrics": {}
            }
    
    def _federated_average(self, model_updates: List[Dict[str, torch.Tensor]], 
                          weights: List[float]) -> Dict[str, torch.Tensor]:
        """
        Perform weighted averaging of model parameters.
        
        Args:
            model_updates: List of model parameter updates
            weights: Weights for each client
            
        Returns:
            Averaged model parameters
        """
        if not model_updates:
            raise ValueError("No model updates provided")
        
        # Initialize aggregated model with zeros
        aggregated_model = {}
        
        # Get parameter names from first model
        param_names = set(model_updates[0].keys())
        
        # Ensure all models have the same parameters
        for update in model_updates[1:]:
            if set(update.keys()) != param_names:
                logger.warning("Model parameter mismatch detected")
                # Use intersection of parameter names
                param_names = param_names.intersection(set(update.keys()))
        
        # Perform weighted averaging for each parameter
        for param_name in param_names:
            # Collect all parameter values
            param_values = []
            valid_weights = []
            
            for i, update in enumerate(model_updates):
                if param_name in update and update[param_name] is not None:
                    param_values.append(update[param_name])
                    valid_weights.append(weights[i])
            
            if param_values:
                # Normalize weights for this parameter
                total_weight = sum(valid_weights)
                if total_weight > 0:
                    normalized_weights = [w / total_weight for w in valid_weights]
                    
                    # Weighted average
                    weighted_sum = torch.zeros_like(param_values[0])
                    for param_value, weight in zip(param_values, normalized_weights):
                        weighted_sum += weight * param_value
                    
                    aggregated_model[param_name] = weighted_sum
                else:
                    # Fallback to simple average
                    aggregated_model[param_name] = torch.mean(torch.stack(param_values), dim=0)
            else:
                logger.warning("No valid values for parameter", param_name=param_name)
                aggregated_model[param_name] = None
        
        return aggregated_model
    
    def _calculate_aggregation_metrics(self, model_updates: List[Dict[str, torch.Tensor]], 
                                     aggregated_model: Dict[str, torch.Tensor],
                                     weights: List[float]) -> Dict[str, Any]:
        """
        Calculate metrics about the aggregation process.
        
        Args:
            model_updates: Original model updates
            aggregated_model: Aggregated model
            weights: Client weights
            
        Returns:
            Aggregation metrics
        """
        try:
            metrics = {
                "participant_count": len(model_updates),
                "parameter_count": 0,
                "convergence_score": 0.0,
                "diversity_score": 0.0,
                "weight_distribution": {
                    "min": min(weights) if weights else 0,
                    "max": max(weights) if weights else 0,
                    "std": statistics.stdev(weights) if len(weights) > 1 else 0
                }
            }
            
            # Calculate parameter statistics
            total_params = 0
            param_variances = []
            convergence_scores = []
            
            for param_name in aggregated_model.keys():
                if aggregated_model[param_name] is not None:
                    param_tensor = aggregated_model[param_name]
                    total_params += param_tensor.numel()
                    
                    # Calculate variance across clients for this parameter
                    param_values = []
                    for update in model_updates:
                        if param_name in update and update[param_name] is not None:
                            param_values.append(update[param_name])
                    
                    if len(param_values) > 1:
                        # Calculate variance
                        param_stack = torch.stack(param_values)
                        param_var = torch.var(param_stack, dim=0).mean().item()
                        param_variances.append(param_var)
                        
                        # Calculate convergence score (inverse of variance)
                        convergence_scores.append(1.0 / (1.0 + param_var))
            
            metrics["parameter_count"] = total_params
            
            if param_variances:
                metrics["diversity_score"] = statistics.mean(param_variances)
            
            if convergence_scores:
                metrics["convergence_score"] = statistics.mean(convergence_scores)
            
            # Calculate model size metrics
            model_size_bytes = 0
            for param_name, param_tensor in aggregated_model.items():
                if param_tensor is not None:
                    model_size_bytes += param_tensor.element_size() * param_tensor.numel()
            
            metrics["model_size_mb"] = model_size_bytes / (1024 * 1024)
            
            return metrics
            
        except Exception as e:
            logger.error("Failed to calculate aggregation metrics", error=str(e))
            return {
                "participant_count": len(model_updates),
                "parameter_count": 0,
                "convergence_score": 0.0,
                "diversity_score": 0.0,
                "model_size_mb": 0.0
            }


class SecureAggregationValidator:
    """
    Validates model updates for security and privacy compliance.
    """
    
    def __init__(self):
        self.max_update_size_mb = 50  # Maximum model update size
        self.min_privacy_budget = 0.0001  # Minimum privacy budget required
        self.max_privacy_budget = 10.0  # Maximum privacy budget allowed
    
    def validate_model_update(self, encrypted_update: str, 
                            privacy_budget_used: float,
                            user_id: str) -> Dict[str, Any]:
        """
        Validate a model update for security and privacy compliance.
        
        Args:
            encrypted_update: Encrypted model update
            privacy_budget_used: Privacy budget consumed
            user_id: User ID for logging
            
        Returns:
            Validation result
        """
        try:
            validation_result = {
                "valid": True,
                "errors": [],
                "warnings": [],
                "metadata": {}
            }
            
            # Check update size
            update_size_mb = len(encrypted_update.encode()) / (1024 * 1024)
            validation_result["metadata"]["size_mb"] = update_size_mb
            
            if update_size_mb > self.max_update_size_mb:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Model update too large: {update_size_mb:.2f}MB > {self.max_update_size_mb}MB")
            
            # Check privacy budget
            validation_result["metadata"]["privacy_budget_used"] = privacy_budget_used
            
            if privacy_budget_used < self.min_privacy_budget:
                validation_result["warnings"].append(f"Very low privacy budget: {privacy_budget_used}")
            
            if privacy_budget_used > self.max_privacy_budget:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Privacy budget exceeded: {privacy_budget_used} > {self.max_privacy_budget}")
            
            # Try to decrypt update to verify format
            try:
                encryptor = ModelUpdateEncryption()
                decrypted_update = encryptor.decrypt_model_update(encrypted_update)
                
                # Check if update contains valid tensor data
                param_count = 0
                for param_name, param_tensor in decrypted_update.items():
                    if param_tensor is not None and hasattr(param_tensor, 'numel'):
                        param_count += param_tensor.numel()
                
                validation_result["metadata"]["parameter_count"] = param_count
                
                if param_count == 0:
                    validation_result["warnings"].append("Model update contains no parameters")
                
            except Exception as e:
                validation_result["valid"] = False
                validation_result["errors"].append(f"Failed to decrypt/validate model update: {str(e)}")
            
            # Log validation result
            if validation_result["valid"]:
                logger.info("Model update validation passed", 
                           user_id=user_id, 
                           size_mb=update_size_mb,
                           privacy_budget=privacy_budget_used)
            else:
                logger.warning("Model update validation failed", 
                              user_id=user_id, 
                              errors=validation_result["errors"])
            
            return validation_result
            
        except Exception as e:
            logger.error("Model update validation error", user_id=user_id, error=str(e))
            return {
                "valid": False,
                "errors": [f"Validation error: {str(e)}"],
                "warnings": [],
                "metadata": {}
            }
    
    def validate_aggregation_readiness(self, round_id: str, 
                                     participant_count: int,
                                     min_participants: int = 5) -> Dict[str, Any]:
        """
        Validate if a federated round is ready for aggregation.
        
        Args:
            round_id: Federated round ID
            participant_count: Number of participants
            min_participants: Minimum participants required
            
        Returns:
            Validation result
        """
        try:
            validation_result = {
                "ready": True,
                "reasons": [],
                "metadata": {
                    "participant_count": participant_count,
                    "min_participants": min_participants
                }
            }
            
            # Check minimum participants for privacy
            if participant_count < min_participants:
                validation_result["ready"] = False
                validation_result["reasons"].append(
                    f"Insufficient participants: {participant_count} < {min_participants}"
                )
            
            # Additional privacy checks could be added here
            # e.g., geographic distribution, temporal distribution, etc.
            
            logger.info("Aggregation readiness check", 
                       round_id=round_id,
                       ready=validation_result["ready"],
                       participants=participant_count)
            
            return validation_result
            
        except Exception as e:
            logger.error("Aggregation readiness validation error", 
                        round_id=round_id, error=str(e))
            return {
                "ready": False,
                "reasons": [f"Validation error: {str(e)}"],
                "metadata": {}
            }


class ModelVersionManager:
    """
    Manages model versions and distribution in federated learning.
    """
    
    def __init__(self):
        self.current_version = "1.0.0"
        self.version_history = []
    
    def create_new_version(self, aggregated_model: Dict[str, torch.Tensor],
                          aggregation_metrics: Dict[str, Any]) -> str:
        """
        Create a new model version after successful aggregation.
        
        Args:
            aggregated_model: Aggregated model parameters
            aggregation_metrics: Metrics from aggregation
            
        Returns:
            New version string
        """
        try:
            # Parse current version
            major, minor, patch = map(int, self.current_version.split('.'))
            
            # Increment version based on convergence
            convergence_score = aggregation_metrics.get("convergence_score", 0.0)
            
            if convergence_score > 0.9:  # Major improvement
                major += 1
                minor = 0
                patch = 0
            elif convergence_score > 0.7:  # Minor improvement
                minor += 1
                patch = 0
            else:  # Patch improvement
                patch += 1
            
            new_version = f"{major}.{minor}.{patch}"
            
            # Store version history
            version_info = {
                "version": new_version,
                "previous_version": self.current_version,
                "created_at": datetime.now().isoformat(),
                "aggregation_metrics": aggregation_metrics,
                "participant_count": aggregation_metrics.get("participant_count", 0)
            }
            
            self.version_history.append(version_info)
            self.current_version = new_version
            
            logger.info("New model version created", 
                       version=new_version,
                       convergence_score=convergence_score)
            
            return new_version
            
        except Exception as e:
            logger.error("Failed to create new model version", error=str(e))
            return self.current_version
    
    def get_version_info(self, version: str = None) -> Dict[str, Any]:
        """
        Get information about a specific model version.
        
        Args:
            version: Version string (current version if None)
            
        Returns:
            Version information
        """
        if version is None:
            version = self.current_version
        
        # Find version in history
        for version_info in self.version_history:
            if version_info["version"] == version:
                return version_info
        
        # Return current version info if not found in history
        return {
            "version": self.current_version,
            "created_at": datetime.now().isoformat(),
            "aggregation_metrics": {},
            "participant_count": 0
        }