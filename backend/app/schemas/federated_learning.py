"""
Pydantic schemas for federated learning API endpoints.
"""
from pydantic import BaseModel, Field, validator, ConfigDict
from typing import Optional, Dict, Any, List
from datetime import datetime
from decimal import Decimal


class FederatedRoundInfo(BaseModel):
    """Information about current federated learning round."""
    
    model_config = ConfigDict(protected_namespaces=())
    
    round_id: str = Field(..., description="Unique round identifier")
    round_number: int = Field(..., description="Sequential round number")
    model_version: str = Field(..., description="Current model version")
    aggregation_status: str = Field(..., description="Round status: in_progress, completed, failed")
    participant_count: int = Field(..., description="Number of participants in this round")
    started_at: datetime = Field(..., description="Round start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Round completion timestamp")
    min_participants: int = Field(5, description="Minimum participants required for aggregation")
    privacy_budget_remaining: float = Field(1.0, description="Remaining privacy budget for round")


class ModelUpdateRequest(BaseModel):
    """Request to upload a model update."""
    
    model_config = ConfigDict(protected_namespaces=())
    
    user_id: str = Field(..., description="User identifier")
    model_delta_encrypted: str = Field(..., description="Encrypted model parameter updates")
    privacy_budget_used: Decimal = Field(..., description="Privacy budget consumed for this update")
    training_metrics: Dict[str, Any] = Field(default_factory=dict, description="Local training metrics")
    model_info: Dict[str, Any] = Field(default_factory=dict, description="Model architecture information")
    
    @validator('privacy_budget_used')
    def validate_privacy_budget(cls, v):
        if v <= 0:
            raise ValueError('Privacy budget must be positive')
        if v > 10.0:
            raise ValueError('Privacy budget too high (max 10.0)')
        return v
    
    @validator('model_delta_encrypted')
    def validate_encrypted_data(cls, v):
        if not v or len(v) < 10:
            raise ValueError('Invalid encrypted model data')
        return v


class ModelUpdateResponse(BaseModel):
    """Response after uploading a model update."""
    
    success: bool = Field(..., description="Whether upload was successful")
    update_id: str = Field(..., description="Unique identifier for this update")
    round_id: str = Field(..., description="Round this update belongs to")
    round_number: int = Field(..., description="Round number")
    participant_number: int = Field(..., description="Participant number in this round")
    estimated_aggregation_time: Optional[datetime] = Field(None, description="Estimated aggregation completion time")
    message: str = Field("", description="Status message")


class TrainingDataRequest(BaseModel):
    """Request to start local model training."""
    
    model_config = ConfigDict(protected_namespaces=())
    
    user_id: str = Field(..., description="User identifier")
    training_data: Dict[str, Any] = Field(..., description="Local training data (anonymized)")
    model_configuration: Optional[Dict[str, Any]] = Field(None, description="Model configuration overrides")
    privacy_preferences: Optional[Dict[str, Any]] = Field(None, description="Privacy preferences")


class TrainingDataResponse(BaseModel):
    """Response after initiating local training."""
    
    success: bool = Field(..., description="Whether training was initiated successfully")
    task_id: str = Field(..., description="Celery task ID for tracking")
    estimated_completion_time: Optional[datetime] = Field(None, description="Estimated training completion")
    message: str = Field("", description="Status message")


class AggregationStatus(BaseModel):
    """Status of model aggregation."""
    
    round_id: str = Field(..., description="Round identifier")
    status: str = Field(..., description="Aggregation status")
    participant_count: int = Field(..., description="Number of participants")
    progress_percentage: float = Field(..., description="Aggregation progress (0-100)")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    aggregation_metrics: Dict[str, Any] = Field(default_factory=dict, description="Aggregation metrics")


class GlobalModelInfo(BaseModel):
    """Information about the global model."""
    
    model_config = ConfigDict(protected_namespaces=())
    
    model_version: str = Field(..., description="Current global model version")
    created_at: datetime = Field(..., description="Model creation timestamp")
    participant_count: int = Field(..., description="Number of participants in training")
    model_metrics: Dict[str, Any] = Field(default_factory=dict, description="Global model performance metrics")
    privacy_guarantees: Dict[str, Any] = Field(default_factory=dict, description="Privacy guarantees provided")
    download_url: Optional[str] = Field(None, description="URL to download model (if authorized)")


class PrivacyBudgetInfo(BaseModel):
    """Information about user's privacy budget."""
    
    user_id: str = Field(..., description="User identifier")
    total_budget: float = Field(10.0, description="Total privacy budget allocated")
    used_budget: float = Field(..., description="Privacy budget already consumed")
    remaining_budget: float = Field(..., description="Remaining privacy budget")
    budget_reset_date: Optional[datetime] = Field(None, description="When budget resets")
    recommendations: List[str] = Field(default_factory=list, description="Privacy budget recommendations")


class FederatedLearningStats(BaseModel):
    """Overall federated learning system statistics."""
    
    model_config = ConfigDict(protected_namespaces=())
    
    total_rounds: int = Field(..., description="Total number of completed rounds")
    active_participants: int = Field(..., description="Currently active participants")
    total_participants: int = Field(..., description="Total participants ever")
    current_model_version: str = Field(..., description="Current global model version")
    system_privacy_level: str = Field(..., description="Overall system privacy level")
    last_aggregation: Optional[datetime] = Field(None, description="Last successful aggregation")
    next_round_estimated: Optional[datetime] = Field(None, description="Estimated next round start")


class ErrorResponse(BaseModel):
    """Error response for federated learning endpoints."""
    
    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code for programmatic handling")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")
    suggestions: List[str] = Field(default_factory=list, description="Suggestions to resolve the error")