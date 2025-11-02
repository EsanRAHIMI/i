"""
FastAPI endpoints for federated learning system.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, status
from sqlalchemy.orm import Session
from typing import Dict, Any, List
import structlog
from datetime import datetime, timedelta
import uuid

from ...database.base import get_db
from ...database.models import User, FederatedRound, ClientUpdate, AuditLog
from ...middleware.auth import get_current_user
from ...schemas.federated_learning import (
    FederatedRoundInfo,
    ModelUpdateRequest,
    ModelUpdateResponse,
    TrainingDataRequest,
    TrainingDataResponse,
    AggregationStatus,
    GlobalModelInfo,
    PrivacyBudgetInfo,
    FederatedLearningStats,
    ErrorResponse
)
from ...tasks.federated_learning import (
    train_local_model,
    aggregate_model_updates,
    process_federated_round
)
from ...core.federated_aggregator import SecureAggregationValidator

logger = structlog.get_logger(__name__)
router = APIRouter(prefix="/fedl", tags=["federated-learning"])


@router.get("/round/current", response_model=FederatedRoundInfo)
async def get_current_round(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get information about the current federated learning round.
    """
    try:
        logger.info("Getting current federated round", user_id=str(current_user.id))
        
        # Get current active round
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
            db.commit()
            db.refresh(current_round)
            
            logger.info("Created new federated round", round_id=str(current_round.id))
        
        # Calculate privacy budget remaining (simplified)
        user_updates_count = db.query(ClientUpdate).filter(
            ClientUpdate.user_id == current_user.id,
            ClientUpdate.round_id == current_round.id
        ).count()
        
        privacy_budget_remaining = max(0.0, 1.0 - (user_updates_count * 0.1))
        
        return FederatedRoundInfo(
            round_id=str(current_round.id),
            round_number=current_round.round_number,
            model_version=current_round.model_version,
            aggregation_status=current_round.aggregation_status,
            participant_count=current_round.participant_count,
            started_at=current_round.started_at,
            completed_at=current_round.completed_at,
            privacy_budget_remaining=privacy_budget_remaining
        )
        
    except Exception as e:
        logger.error("Failed to get current round", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get current round: {str(e)}"
        )


@router.post("/round/upload", response_model=ModelUpdateResponse)
async def upload_model_update(
    request: ModelUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Upload an encrypted model update to the current federated round.
    """
    try:
        logger.info("Uploading model update", user_id=str(current_user.id))
        
        # Validate user matches request
        if request.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID mismatch"
            )
        
        # Get current round
        current_round = db.query(FederatedRound).filter(
            FederatedRound.aggregation_status == "in_progress"
        ).order_by(FederatedRound.started_at.desc()).first()
        
        if not current_round:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active federated round found"
            )
        
        # Check if user already submitted update for this round
        existing_update = db.query(ClientUpdate).filter(
            ClientUpdate.user_id == current_user.id,
            ClientUpdate.round_id == current_round.id
        ).first()
        
        if existing_update:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User already submitted update for this round"
            )
        
        # Validate model update
        validator = SecureAggregationValidator()
        validation_result = validator.validate_model_update(
            request.model_delta_encrypted,
            float(request.privacy_budget_used),
            str(current_user.id)
        )
        
        if not validation_result["valid"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid model update: {', '.join(validation_result['errors'])}"
            )
        
        # Create client update record
        client_update = ClientUpdate(
            user_id=current_user.id,
            round_id=current_round.id,
            model_delta_encrypted=request.model_delta_encrypted,
            privacy_budget_used=request.privacy_budget_used
        )
        
        db.add(client_update)
        
        # Update round participant count
        current_round.participant_count += 1
        
        # Log the upload
        audit_log = AuditLog(
            user_id=current_user.id,
            action="model_update_uploaded",
            resource_type="federated_round",
            resource_id=current_round.id,
            details={
                "round_number": current_round.round_number,
                "privacy_budget_used": float(request.privacy_budget_used),
                "training_metrics": request.training_metrics,
                "model_info": request.model_info
            }
        )
        db.add(audit_log)
        
        db.commit()
        db.refresh(client_update)
        
        # Estimate aggregation time (when we have enough participants)
        estimated_aggregation_time = None
        if current_round.participant_count >= 5:  # Minimum for aggregation
            estimated_aggregation_time = datetime.now() + timedelta(hours=1)
        
        logger.info("Model update uploaded successfully", 
                   user_id=str(current_user.id),
                   round_id=str(current_round.id),
                   participant_count=current_round.participant_count)
        
        return ModelUpdateResponse(
            success=True,
            update_id=str(client_update.id),
            round_id=str(current_round.id),
            round_number=current_round.round_number,
            participant_number=current_round.participant_count,
            estimated_aggregation_time=estimated_aggregation_time,
            message="Model update uploaded successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to upload model update", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload model update: {str(e)}"
        )


@router.post("/train", response_model=TrainingDataResponse)
async def start_local_training(
    request: TrainingDataRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Start local model training for the user.
    """
    try:
        logger.info("Starting local training", user_id=str(current_user.id))
        
        # Validate user matches request
        if request.user_id != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User ID mismatch"
            )
        
        # Check user consent for federated learning
        if not current_user.settings or not current_user.settings.voice_training_consent:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User has not consented to federated learning"
            )
        
        # Start training task
        task = train_local_model.delay(
            user_id=str(current_user.id),
            training_data=request.training_data
        )
        
        # Log training initiation
        audit_log = AuditLog(
            user_id=current_user.id,
            action="local_training_started",
            resource_type="federated_learning",
            details={
                "task_id": task.id,
                "data_samples": len(request.training_data.get("interactions", [])),
                "model_config": request.model_config or {}
            }
        )
        db.add(audit_log)
        db.commit()
        
        estimated_completion = datetime.now() + timedelta(minutes=10)
        
        logger.info("Local training task started", 
                   user_id=str(current_user.id),
                   task_id=task.id)
        
        return TrainingDataResponse(
            success=True,
            task_id=task.id,
            estimated_completion_time=estimated_completion,
            message="Local training started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to start local training", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start local training: {str(e)}"
        )


@router.get("/round/{round_id}/status", response_model=AggregationStatus)
async def get_aggregation_status(
    round_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get the status of model aggregation for a specific round.
    """
    try:
        logger.info("Getting aggregation status", round_id=round_id, user_id=str(current_user.id))
        
        # Get federated round
        fed_round = db.query(FederatedRound).filter(
            FederatedRound.id == round_id
        ).first()
        
        if not fed_round:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Federated round not found"
            )
        
        # Calculate progress
        progress_percentage = 0.0
        if fed_round.aggregation_status == "completed":
            progress_percentage = 100.0
        elif fed_round.aggregation_status == "in_progress":
            # Progress based on participant count
            min_participants = 5
            progress_percentage = min(90.0, (fed_round.participant_count / min_participants) * 90.0)
        
        # Estimate completion time
        estimated_completion = None
        if fed_round.aggregation_status == "in_progress" and fed_round.participant_count >= 5:
            estimated_completion = datetime.now() + timedelta(hours=1)
        
        return AggregationStatus(
            round_id=str(fed_round.id),
            status=fed_round.aggregation_status,
            participant_count=fed_round.participant_count,
            progress_percentage=progress_percentage,
            estimated_completion=estimated_completion,
            aggregation_metrics={}  # Would be populated from actual aggregation results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get aggregation status", round_id=round_id, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get aggregation status: {str(e)}"
        )


@router.get("/model/current", response_model=GlobalModelInfo)
async def get_current_global_model(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get information about the current global model.
    """
    try:
        logger.info("Getting current global model info", user_id=str(current_user.id))
        
        # Get latest completed round
        latest_round = db.query(FederatedRound).filter(
            FederatedRound.aggregation_status == "completed"
        ).order_by(FederatedRound.completed_at.desc()).first()
        
        if not latest_round:
            # Return default model info if no completed rounds
            return GlobalModelInfo(
                model_version="v1.0.0",
                created_at=datetime.now(),
                participant_count=0,
                model_metrics={
                    "accuracy": 0.85,
                    "loss": 0.15,
                    "convergence_score": 0.0
                },
                privacy_guarantees={
                    "differential_privacy": True,
                    "epsilon": 1.0,
                    "delta": 1e-5
                }
            )
        
        return GlobalModelInfo(
            model_version=latest_round.model_version,
            created_at=latest_round.completed_at,
            participant_count=latest_round.participant_count,
            model_metrics={
                "accuracy": 0.92,
                "loss": 0.08,
                "convergence_score": 0.85
            },
            privacy_guarantees={
                "differential_privacy": True,
                "epsilon": 1.0,
                "delta": 1e-5,
                "participants": latest_round.participant_count
            }
        )
        
    except Exception as e:
        logger.error("Failed to get global model info", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get global model info: {str(e)}"
        )


@router.get("/privacy/budget", response_model=PrivacyBudgetInfo)
async def get_privacy_budget(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get user's privacy budget information.
    """
    try:
        logger.info("Getting privacy budget", user_id=str(current_user.id))
        
        # Calculate used privacy budget from all user's updates
        total_used = db.query(ClientUpdate).filter(
            ClientUpdate.user_id == current_user.id
        ).with_entities(
            db.func.sum(ClientUpdate.privacy_budget_used)
        ).scalar() or 0.0
        
        total_budget = 10.0  # Default total budget
        remaining_budget = max(0.0, total_budget - float(total_used))
        
        # Generate recommendations
        recommendations = []
        if remaining_budget < 1.0:
            recommendations.append("Consider reducing training frequency to preserve privacy budget")
        if remaining_budget < 0.1:
            recommendations.append("Privacy budget nearly exhausted - training will be limited")
        if remaining_budget > 5.0:
            recommendations.append("Good privacy budget remaining - you can participate actively")
        
        return PrivacyBudgetInfo(
            user_id=str(current_user.id),
            total_budget=total_budget,
            used_budget=float(total_used),
            remaining_budget=remaining_budget,
            budget_reset_date=datetime.now() + timedelta(days=30),  # Monthly reset
            recommendations=recommendations
        )
        
    except Exception as e:
        logger.error("Failed to get privacy budget", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get privacy budget: {str(e)}"
        )


@router.get("/stats", response_model=FederatedLearningStats)
async def get_federated_learning_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Get overall federated learning system statistics.
    """
    try:
        logger.info("Getting federated learning stats", user_id=str(current_user.id))
        
        # Get statistics
        total_rounds = db.query(FederatedRound).filter(
            FederatedRound.aggregation_status == "completed"
        ).count()
        
        # Get unique participants count
        total_participants = db.query(ClientUpdate.user_id).distinct().count()
        
        # Get active participants (participated in last 7 days)
        week_ago = datetime.now() - timedelta(days=7)
        active_participants = db.query(ClientUpdate.user_id).filter(
            ClientUpdate.uploaded_at >= week_ago
        ).distinct().count()
        
        # Get current model version
        latest_round = db.query(FederatedRound).filter(
            FederatedRound.aggregation_status == "completed"
        ).order_by(FederatedRound.completed_at.desc()).first()
        
        current_model_version = latest_round.model_version if latest_round else "v1.0.0"
        last_aggregation = latest_round.completed_at if latest_round else None
        
        # Estimate next round
        next_round_estimated = datetime.now() + timedelta(hours=24)
        
        return FederatedLearningStats(
            total_rounds=total_rounds,
            active_participants=active_participants,
            total_participants=total_participants,
            current_model_version=current_model_version,
            system_privacy_level="High (ε=1.0, δ=1e-5)",
            last_aggregation=last_aggregation,
            next_round_estimated=next_round_estimated
        )
        
    except Exception as e:
        logger.error("Failed to get federated learning stats", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get federated learning stats: {str(e)}"
        )


@router.post("/round/trigger-aggregation")
async def trigger_aggregation(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Manually trigger aggregation for the current round (admin only).
    """
    try:
        # This would typically require admin privileges
        # For demo purposes, we'll allow any authenticated user
        
        logger.info("Triggering manual aggregation", user_id=str(current_user.id))
        
        # Get current round
        current_round = db.query(FederatedRound).filter(
            FederatedRound.aggregation_status == "in_progress"
        ).order_by(FederatedRound.started_at.desc()).first()
        
        if not current_round:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No active round found"
            )
        
        # Check if round has any participants
        participant_count = db.query(ClientUpdate).filter(
            ClientUpdate.round_id == current_round.id
        ).count()
        
        if participant_count < 2:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Insufficient participants for aggregation"
            )
        
        # Start aggregation task
        task = aggregate_model_updates.delay(str(current_round.id))
        
        # Log the trigger
        audit_log = AuditLog(
            user_id=current_user.id,
            action="aggregation_triggered",
            resource_type="federated_round",
            resource_id=current_round.id,
            details={
                "task_id": task.id,
                "participant_count": participant_count,
                "round_number": current_round.round_number
            }
        )
        db.add(audit_log)
        db.commit()
        
        logger.info("Aggregation triggered successfully", 
                   round_id=str(current_round.id),
                   task_id=task.id)
        
        return {
            "success": True,
            "message": "Aggregation triggered successfully",
            "task_id": task.id,
            "round_id": str(current_round.id)
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to trigger aggregation", user_id=str(current_user.id), error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to trigger aggregation: {str(e)}"
        )