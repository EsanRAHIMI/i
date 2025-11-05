"""
Tasks API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, and_
from typing import List, Optional
from datetime import datetime, date
import structlog

from ...database.base import get_db
from ...database.models import Task, User
from ...middleware.auth import get_current_user
from ...schemas.tasks import TaskResponse, TaskCreate, TaskUpdate

logger = structlog.get_logger(__name__)
router = APIRouter()


@router.get("/today", response_model=List[TaskResponse])
async def get_today_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get today's tasks for the current user."""
    try:
        user_id = current_user.id
        
        today = date.today()
        
        # Get tasks for today
        tasks = db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                func.date(Task.due_date) == today
            )
        ).order_by(Task.priority.asc(), Task.created_at.asc()).all()
        
        # Also get tasks without due_date that are pending
        pending_tasks = db.query(Task).filter(
            and_(
                Task.user_id == user_id,
                Task.due_date.is_(None),
                Task.status == "pending"
            )
        ).order_by(Task.created_at.asc()).all()
        
        # Combine and return
        all_tasks = list(tasks) + list(pending_tasks)
        
        return [
            TaskResponse(
                id=str(task.id),
                user_id=str(task.user_id),
                title=task.title,
                description=task.description,
                priority=task.priority,
                status=task.status,
                due_date=task.due_date.isoformat() if task.due_date else None,
                context_data=task.context_data or {},
                created_by_ai=task.created_by_ai,
                created_at=task.created_at.isoformat() if task.created_at else None
            )
            for task in all_tasks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get today's tasks", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get today's tasks"
        )


@router.get("", response_model=List[TaskResponse])
async def get_tasks(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status_filter: Optional[str] = None,
    limit: int = 100
):
    """Get all tasks for the current user."""
    try:
        user_id = current_user.id
        
        query = db.query(Task).filter(Task.user_id == user_id)
        
        if status_filter:
            query = query.filter(Task.status == status_filter)
        
        tasks = query.order_by(Task.due_date.asc(), Task.priority.asc()).limit(limit).all()
        
        return [
            TaskResponse(
                id=str(task.id),
                user_id=str(task.user_id),
                title=task.title,
                description=task.description,
                priority=task.priority,
                status=task.status,
                due_date=task.due_date.isoformat() if task.due_date else None,
                context_data=task.context_data or {},
                created_by_ai=task.created_by_ai,
                created_at=task.created_at.isoformat() if task.created_at else None
            )
            for task in tasks
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get tasks", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get tasks"
        )


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new task."""
    try:
        user_id = current_user.id
        
        task = Task(
            user_id=user_id,
            title=task_data.title,
            description=task_data.description,
            priority=task_data.priority or 3,
            status=task_data.status or "pending",
            due_date=datetime.fromisoformat(task_data.due_date) if task_data.due_date else None,
            context_data=task_data.context_data or {},
            created_by_ai=task_data.created_by_ai or False
        )
        
        db.add(task)
        db.commit()
        db.refresh(task)
        
        return TaskResponse(
            id=str(task.id),
            user_id=str(task.user_id),
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date.isoformat() if task.due_date else None,
            context_data=task.context_data or {},
            created_by_ai=task.created_by_ai,
            created_at=task.created_at.isoformat() if task.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to create task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create task"
        )


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: str,
    task_update: TaskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Update a task."""
    try:
        user_id = current_user.id
        
        task = db.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        update_data = task_update.model_dump(exclude_unset=True)
        
        if 'due_date' in update_data and update_data['due_date']:
            update_data['due_date'] = datetime.fromisoformat(update_data['due_date'])
        
        for key, value in update_data.items():
            setattr(task, key, value)
        
        db.commit()
        db.refresh(task)
        
        return TaskResponse(
            id=str(task.id),
            user_id=str(task.user_id),
            title=task.title,
            description=task.description,
            priority=task.priority,
            status=task.status,
            due_date=task.due_date.isoformat() if task.due_date else None,
            context_data=task.context_data or {},
            created_by_ai=task.created_by_ai,
            created_at=task.created_at.isoformat() if task.created_at else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update task"
        )


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete a task."""
    try:
        user_id = current_user.id
        
        task = db.query(Task).filter(
            and_(Task.id == task_id, Task.user_id == user_id)
        ).first()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        db.delete(task)
        db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to delete task", error=str(e), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete task"
        )

