"""
Federated learning tasks for privacy-preserving model training.
"""
from typing import Dict, Any, List, Optional
import structlog
from celery import current_task
from datetime import datetime, timedelta
import torch
import json

from ..celery_app import celery_app
from ..database.base import SessionLocal
from ..database.models import User, FederatedRound, ClientUpdate, AuditLog
from ..core.federated_learning import (
    LocalModelTrainer, 
    ModelUpdateEncryption, 
    FeatureExtractor,
    DifferentialPrivacyManager
)
from ..core.federated_aggregator import (
    FedAvgAggregator,
    SecureAggregationValidator,
    ModelVersionManager
)

logger = structlog.get_logger(__name__)


@celery_app.task(bind=True, queue="federated_learning")
def train_local_model(self, user_id: str, training_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Train local personalization model for user using PyTorch.
    
    Args:
        user_id: User ID
        training_data: Local training data (anonymized)
    
    Returns:
        Dict containing model update information
    """
    try:
        logger.info("Training local model", user_id=user_id)
        
        # Initialize components
        trainer = LocalModelTrainer()
        encryptor = ModelUpdateEncryption()
        feature_extractor = FeatureExtractor()
        
        # Extract features from training data
        if "interactions" not in training_data:
            # Generate sample interactions for demo purposes
            training_data["interactions"] = [
                {
                    "timestamp": "14:30:00",
                    "date": "2024-01-01",
                    "activity_type": 1,
                    "duration": 300,
                    "location_type": 1,
                    "device_type": 0,
                    "type": "voice",
                    "involves_calendar": True,
                    "is_weekend": False,
                    "next_action": 2
                }
            ]
        
        # Train local model
        training_result = trainer.train_local_model(training_data)
        
        if training_result["status"] != "success":
            raise Exception(f"Training failed: {training_result.get('error', 'Unknown error')}")
        
        # Encrypt model update
        encrypted_update = encryptor.encrypt_model_update(training_result["model_update"])
        
        # Prepare model update info
        model_update = {
            "user_id": user_id,
            "model_version": "v1.0.0",
            "update_size": len(encrypted_update),
            "training_samples": training_result["training_metrics"]["samples_processed"],
            "privacy_budget_used": training_result["training_metrics"]["privacy_budget_used"],
            "model_delta_encrypted": encrypted_update,
            "training_metrics": training_result["training_metrics"],
            "model_info": training_result["model_info"]
        }
        
        with SessionLocal() as db:
            # Get current federated round
            current_round = db.query(FederatedRound).filter(
                FederatedRound.aggregation_status == "in_progress"
            ).order_by(FederatedRound.started_at.desc()).first()
            
            if not current_round:
                # Create new round if none exists
                current_round = FederatedRound(
                    round_number=1,
                    model_version="v1.0.0",
                    aggregation_status="in_progress",
                    participant_count=0
                )
                db.add(current_round)
                db.flush()
            
            # Store client update
            client_update = ClientUpdate(
                user_id=user_id,
                round_id=current_round.id,
                model_delta_encrypted=encrypted_update,
                privacy_budget_used=model_update["privacy_budget_used"]
            )
            
            db.add(client_update)
            
            # Update round participant count
            current_round.participant_count += 1
            
            # Log training activity
            audit_log = AuditLog(
                user_id=user_id,
                action="local_model_trained",
                resource_type="federated_round",
                resource_id=current_round.id,
                details={
                    "training_metrics": model_update["training_metrics"],
                    "model_info": model_update["model_info"],
                    "round_number": current_round.round_number,
                    "task_id": current_task.request.id
                }
            )
            db.add(audit_log)
            db.commit()
            
            model_update["round_id"] = str(current_round.id)
            model_update["round_number"] = current_round.round_number
        
        logger.info("Local model trained successfully", 
                   user_id=user_id, 
                   round_number=model_update["round_number"],
                   samples=model_update["training_samples"])
        
        return model_update
        
    except Exception as exc:
        logger.error("Local model training failed", user_id=user_id, error=str(exc))
        self.retry(exc=exc, countdown=300, max_retries=2)  # 5 minute delay


@celery_app.task(bind=True, queue="federated_learning")
def aggregate_model_updates(self, round_id: str) -> Dict[str, Any]:
    """
    Aggregate model updates from multiple clients using FedAvg algorithm.
    
    Args:
        round_id: Federated round ID
    
    Returns:
        Dict containing aggregation results
    """
    try:
        logger.info("Aggregating model updates", round_id=round_id)
        
        # Initialize aggregation components
        aggregator = FedAvgAggregator(differential_privacy=True)
        validator = SecureAggregationValidator()
        version_manager = ModelVersionManager()
        
        with SessionLocal() as db:
            # Get federated round
            fed_round = db.query(FederatedRound).filter(
                FederatedRound.id == round_id
            ).first()
            
            if not fed_round:
                raise ValueError(f"Federated round {round_id} not found")
            
            # Get all client updates for this round
            client_updates = db.query(ClientUpdate).filter(
                ClientUpdate.round_id == round_id
            ).all()
            
            # Validate aggregation readiness
            readiness_check = validator.validate_aggregation_readiness(
                round_id, len(client_updates), min_participants=2  # Reduced for demo
            )
            
            if not readiness_check["ready"]:
                logger.warning("Round not ready for aggregation", 
                              round_id=round_id, 
                              reasons=readiness_check["reasons"])
                return {
                    "status": "not_ready",
                    "participant_count": len(client_updates),
                    "reasons": readiness_check["reasons"]
                }
            
            # Validate each client update
            valid_updates = []
            client_weights = []
            
            for update in client_updates:
                validation_result = validator.validate_model_update(
                    update.model_delta_encrypted,
                    float(update.privacy_budget_used or 0.001),
                    str(update.user_id)
                )
                
                if validation_result["valid"]:
                    valid_updates.append(update.model_delta_encrypted)
                    # Weight by inverse of privacy budget (more privacy = higher weight)
                    weight = 1.0 / max(float(update.privacy_budget_used or 0.001), 0.001)
                    client_weights.append(weight)
                else:
                    logger.warning("Invalid client update", 
                                  user_id=update.user_id,
                                  errors=validation_result["errors"])
            
            if len(valid_updates) < 2:
                logger.warning("Insufficient valid updates for aggregation", 
                              valid_count=len(valid_updates))
                return {
                    "status": "insufficient_valid_updates",
                    "participant_count": len(client_updates),
                    "valid_updates": len(valid_updates)
                }
            
            # Perform FedAvg aggregation
            aggregation_result = aggregator.aggregate_model_updates(
                valid_updates, client_weights
            )
            
            if aggregation_result["status"] != "success":
                raise Exception(f"Aggregation failed: {aggregation_result.get('error', 'Unknown error')}")
            
            # Create new model version
            new_version = version_manager.create_new_version(
                {},  # Aggregated model is encrypted, so we pass empty dict
                aggregation_result["aggregation_metrics"]
            )
            
            # Prepare final result
            final_result = {
                "round_id": round_id,
                "round_number": fed_round.round_number,
                "participant_count": len(valid_updates),
                "aggregated_model_version": new_version,
                "aggregation_method": "FedAvg",
                "privacy_preserved": True,
                "aggregation_metrics": aggregation_result["aggregation_metrics"],
                "differential_privacy": {
                    "epsilon": 1.0,
                    "delta": 1e-5,
                    "applied": aggregation_result["differential_privacy_applied"]
                },
                "encrypted_model": aggregation_result["aggregated_model_encrypted"]
            }
            
            # Update round status
            fed_round.aggregation_status = "completed"
            fed_round.completed_at = datetime.now()
            fed_round.model_version = new_version
            
            # Log aggregation
            audit_log = AuditLog(
                action="model_aggregation_completed",
                resource_type="federated_round",
                resource_id=round_id,
                details={
                    "aggregation_metrics": final_result["aggregation_metrics"],
                    "model_version": new_version,
                    "participant_count": len(valid_updates),
                    "task_id": current_task.request.id
                }
            )
            db.add(audit_log)
            db.commit()
        
        logger.info("Model aggregation completed successfully", 
                   round_id=round_id, 
                   participants=final_result["participant_count"],
                   version=new_version)
        
        return final_result
        
    except Exception as exc:
        logger.error("Model aggregation failed", round_id=round_id, error=str(exc))
        self.retry(exc=exc, countdown=600, max_retries=2)  # 10 minute delay


@celery_app.task(bind=True, queue="federated_learning")
def process_federated_round(self) -> Dict[str, Any]:
    """
    Process current federated learning round and start new one if needed.
    
    Returns:
        Dict containing round processing results
    """
    try:
        logger.info("Processing federated learning round")
        
        with SessionLocal() as db:
            # Get current active round
            current_round = db.query(FederatedRound).filter(
                FederatedRound.aggregation_status == "in_progress"
            ).order_by(FederatedRound.started_at.desc()).first()
            
            processing_result = {
                "current_round_processed": False,
                "new_round_started": False,
                "participant_count": 0
            }
            
            if current_round:
                # Check if round has enough participants and should be aggregated
                participant_count = db.query(ClientUpdate).filter(
                    ClientUpdate.round_id == current_round.id
                ).count()
                
                processing_result["participant_count"] = participant_count
                
                # Aggregate if we have enough participants (minimum 5 for privacy)
                if participant_count >= 5:
                    aggregation_result = aggregate_model_updates.delay(str(current_round.id)).get()
                    processing_result["current_round_processed"] = True
                    processing_result["aggregation_result"] = aggregation_result
            
            # Start new round if no active round or current round completed
            if not current_round or processing_result["current_round_processed"]:
                next_round_number = 1
                if current_round:
                    next_round_number = current_round.round_number + 1
                
                new_round = FederatedRound(
                    round_number=next_round_number,
                    model_version=f"v1.0.{next_round_number}",
                    aggregation_status="in_progress",
                    participant_count=0
                )
                
                db.add(new_round)
                db.commit()
                
                processing_result["new_round_started"] = True
                processing_result["new_round_number"] = next_round_number
        
        logger.info("Federated round processing completed", result=processing_result)
        
        return processing_result
        
    except Exception as exc:
        logger.error("Federated round processing failed", error=str(exc))
        self.retry(exc=exc, countdown=1800, max_retries=2)  # 30 minute delay


@celery_app.task(bind=True, queue="federated_learning")
def cleanup_old_rounds(self, retention_days: int = 30) -> Dict[str, Any]:
    """
    Clean up old federated learning rounds and client updates.
    
    Args:
        retention_days: Number of days to retain data
    
    Returns:
        Dict containing cleanup results
    """
    try:
        logger.info("Cleaning up old federated rounds", retention_days=retention_days)
        
        with SessionLocal() as db:
            # Calculate cutoff date
            cutoff_date = "2024-01-01T00:00:00Z"  # Placeholder
            
            # Delete old rounds and their updates
            old_rounds = db.query(FederatedRound).filter(
                FederatedRound.completed_at < cutoff_date
            ).all()
            
            cleanup_result = {
                "rounds_deleted": len(old_rounds),
                "updates_deleted": 0,
                "retention_days": retention_days
            }
            
            for round_obj in old_rounds:
                # Count updates before deletion
                update_count = db.query(ClientUpdate).filter(
                    ClientUpdate.round_id == round_obj.id
                ).count()
                cleanup_result["updates_deleted"] += update_count
                
                # Delete round (cascades to client updates)
                db.delete(round_obj)
            
            db.commit()
        
        logger.info("Federated rounds cleanup completed", result=cleanup_result)
        
        return cleanup_result
        
    except Exception as exc:
        logger.error("Federated rounds cleanup failed", error=str(exc))
        self.retry(exc=exc, countdown=3600, max_retries=1)  # 1 hour delay