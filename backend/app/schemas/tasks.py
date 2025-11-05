"""
Task Pydantic schemas.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator


class TaskResponse(BaseModel):
    """Schema for task response data."""
    id: str
    user_id: str
    title: str
    description: Optional[str] = None
    priority: int = Field(ge=1, le=5, default=3)
    status: str = Field(default="pending")
    due_date: Optional[str] = None
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_by_ai: bool = False
    created_at: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    """Schema for creating a task."""
    title: str = Field(min_length=1, max_length=500)
    description: Optional[str] = None
    priority: int = Field(ge=1, le=5, default=3)
    status: str = Field(default="pending")
    due_date: Optional[str] = None
    context_data: Dict[str, Any] = Field(default_factory=dict)
    created_by_ai: bool = False
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v


class TaskUpdate(BaseModel):
    """Schema for updating a task."""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1, le=5)
    status: Optional[str] = None
    due_date: Optional[str] = None
    context_data: Optional[Dict[str, Any]] = None
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, v):
        if v is not None:
            valid_statuses = ["pending", "in_progress", "completed", "cancelled"]
            if v not in valid_statuses:
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

