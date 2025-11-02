"""
Task Planning and Execution Engine for the Agentic Core.

This module implements multi-step task decomposition with dependency management,
action execution for calendar, messaging, email, and reminder operations,
and error recovery with user confirmation workflows.
"""

import uuid
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import asyncio
import logging

logger = logging.getLogger(__name__)


class ActionType(str, Enum):
    """Types of actions that can be executed."""
    
    # Calendar actions
    CALENDAR_CREATE_EVENT = "calendar_create_event"
    CALENDAR_UPDATE_EVENT = "calendar_update_event"
    CALENDAR_DELETE_EVENT = "calendar_delete_event"
    CALENDAR_QUERY_EVENTS = "calendar_query_events"
    
    # Task actions
    TASK_CREATE = "task_create"
    TASK_UPDATE = "task_update"
    TASK_DELETE = "task_delete"
    TASK_COMPLETE = "task_complete"
    TASK_QUERY = "task_query"
    
    # Messaging actions
    MESSAGE_SEND_WHATSAPP = "message_send_whatsapp"
    MESSAGE_SEND_EMAIL = "message_send_email"
    MESSAGE_SCHEDULE_REMINDER = "message_schedule_reminder"
    
    # System actions
    SYSTEM_WAIT = "system_wait"
    SYSTEM_CONFIRM = "system_confirm"
    SYSTEM_NOTIFY = "system_notify"


class TaskStatus(str, Enum):
    """Status of task execution."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    WAITING_CONFIRMATION = "waiting_confirmation"


class Priority(int, Enum):
    """Task priority levels."""
    
    LOW = 1
    MEDIUM = 3
    HIGH = 5
    URGENT = 7
    CRITICAL = 9


@dataclass
class Action:
    """Individual action within a task plan."""
    
    id: str
    action_type: ActionType
    parameters: Dict[str, Any]
    dependencies: List[str] = field(default_factory=list)
    requires_confirmation: bool = False
    retry_count: int = 0
    max_retries: int = 3
    timeout_seconds: int = 30
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


@dataclass
class TaskPlan:
    """Complete task plan with multiple actions."""
    
    id: str
    title: str
    description: str
    user_id: str
    actions: List[Action]
    priority: Priority = Priority.MEDIUM
    status: TaskStatus = TaskStatus.PENDING
    progress: float = 0.0
    estimated_duration_minutes: int = 5
    context: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    def get_next_actions(self) -> List[Action]:
        """Get actions that are ready to execute."""
        ready_actions = []
        
        for action in self.actions:
            if action.status != TaskStatus.PENDING:
                continue
            
            # Check if all dependencies are completed
            dependencies_met = True
            for dep_id in action.dependencies:
                dep_action = next((a for a in self.actions if a.id == dep_id), None)
                if not dep_action or dep_action.status != TaskStatus.COMPLETED:
                    dependencies_met = False
                    break
            
            if dependencies_met:
                ready_actions.append(action)
        
        return ready_actions
    
    def update_progress(self) -> None:
        """Update overall progress based on completed actions."""
        if not self.actions:
            self.progress = 0.0
            return
        
        completed_count = sum(1 for action in self.actions if action.status == TaskStatus.COMPLETED)
        self.progress = (completed_count / len(self.actions)) * 100.0
        
        # Update overall status
        if self.progress == 100.0:
            self.status = TaskStatus.COMPLETED
            self.completed_at = datetime.now()
        elif self.progress > 0:
            self.status = TaskStatus.IN_PROGRESS
            if not self.started_at:
                self.started_at = datetime.now()


class TaskPlanner:
    """
    Task planning and execution engine.
    
    Implements multi-step task decomposition with dependency management
    and provides action execution capabilities across multiple services.
    """
    
    def __init__(self):
        self.active_plans: Dict[str, TaskPlan] = {}
        self.action_executors: Dict[ActionType, Callable] = {}
        self.confirmation_callbacks: Dict[str, Callable] = {}
        
        # Register default action executors
        self._register_default_executors()
    
    def _register_default_executors(self) -> None:
        """Register default action executors."""
        
        # Calendar executors
        self.action_executors[ActionType.CALENDAR_CREATE_EVENT] = self._execute_calendar_create
        self.action_executors[ActionType.CALENDAR_UPDATE_EVENT] = self._execute_calendar_update
        self.action_executors[ActionType.CALENDAR_DELETE_EVENT] = self._execute_calendar_delete
        self.action_executors[ActionType.CALENDAR_QUERY_EVENTS] = self._execute_calendar_query
        
        # Task executors
        self.action_executors[ActionType.TASK_CREATE] = self._execute_task_create
        self.action_executors[ActionType.TASK_UPDATE] = self._execute_task_update
        self.action_executors[ActionType.TASK_DELETE] = self._execute_task_delete
        self.action_executors[ActionType.TASK_COMPLETE] = self._execute_task_complete
        self.action_executors[ActionType.TASK_QUERY] = self._execute_task_query
        
        # Messaging executors
        self.action_executors[ActionType.MESSAGE_SEND_WHATSAPP] = self._execute_whatsapp_send
        self.action_executors[ActionType.MESSAGE_SEND_EMAIL] = self._execute_email_send
        self.action_executors[ActionType.MESSAGE_SCHEDULE_REMINDER] = self._execute_schedule_reminder
        
        # System executors
        self.action_executors[ActionType.SYSTEM_WAIT] = self._execute_system_wait
        self.action_executors[ActionType.SYSTEM_CONFIRM] = self._execute_system_confirm
        self.action_executors[ActionType.SYSTEM_NOTIFY] = self._execute_system_notify
    
    async def create_task_plan(
        self,
        title: str,
        description: str,
        user_id: str,
        intent_type: str,
        entities: Dict[str, Any],
        context: Dict[str, Any]
    ) -> TaskPlan:
        """
        Create a task plan based on intent and entities.
        
        Args:
            title: Task plan title
            description: Task plan description
            user_id: User identifier
            intent_type: Recognized intent type
            entities: Extracted entities
            context: Additional context information
            
        Returns:
            TaskPlan object with decomposed actions
        """
        
        plan_id = str(uuid.uuid4())
        actions = await self._decompose_intent_to_actions(
            intent_type, entities, context, user_id
        )
        
        # Estimate duration based on actions
        estimated_duration = sum(self._estimate_action_duration(action) for action in actions)
        
        task_plan = TaskPlan(
            id=plan_id,
            title=title,
            description=description,
            user_id=user_id,
            actions=actions,
            estimated_duration_minutes=estimated_duration,
            context=context
        )
        
        self.active_plans[plan_id] = task_plan
        
        logger.info(f"Created task plan {plan_id} with {len(actions)} actions")
        return task_plan
    
    async def execute_task_plan(self, plan_id: str) -> TaskPlan:
        """
        Execute a task plan with dependency management and error recovery.
        
        Args:
            plan_id: Task plan identifier
            
        Returns:
            Updated TaskPlan object
        """
        
        if plan_id not in self.active_plans:
            raise ValueError(f"Task plan {plan_id} not found")
        
        plan = self.active_plans[plan_id]
        plan.status = TaskStatus.IN_PROGRESS
        plan.started_at = datetime.now()
        
        logger.info(f"Starting execution of task plan {plan_id}")
        
        try:
            while plan.status == TaskStatus.IN_PROGRESS:
                # Get actions ready for execution
                ready_actions = plan.get_next_actions()
                
                if not ready_actions:
                    # Check if we're waiting for confirmations
                    waiting_actions = [a for a in plan.actions if a.status == TaskStatus.WAITING_CONFIRMATION]
                    if waiting_actions:
                        logger.info(f"Task plan {plan_id} waiting for confirmations")
                        break
                    
                    # Check if all actions are completed
                    pending_actions = [a for a in plan.actions if a.status == TaskStatus.PENDING]
                    if not pending_actions:
                        plan.status = TaskStatus.COMPLETED
                        plan.completed_at = datetime.now()
                        break
                    
                    # If we have pending actions but none are ready, there might be a dependency issue
                    logger.warning(f"Task plan {plan_id} has pending actions but none are ready")
                    break
                
                # Execute ready actions concurrently (up to a limit)
                max_concurrent = 3
                action_batches = [ready_actions[i:i+max_concurrent] 
                                for i in range(0, len(ready_actions), max_concurrent)]
                
                for batch in action_batches:
                    await asyncio.gather(*[
                        self._execute_action(action, plan) for action in batch
                    ], return_exceptions=True)
                
                # Update progress
                plan.update_progress()
                
                # Small delay to prevent tight loops
                await asyncio.sleep(0.1)
            
            logger.info(f"Task plan {plan_id} execution completed with status: {plan.status}")
            return plan
            
        except Exception as e:
            logger.error(f"Error executing task plan {plan_id}: {str(e)}")
            plan.status = TaskStatus.FAILED
            raise
    
    async def _execute_action(self, action: Action, plan: TaskPlan) -> None:
        """Execute a single action with error handling and retries."""
        
        action.status = TaskStatus.IN_PROGRESS
        action.started_at = datetime.now()
        
        logger.info(f"Executing action {action.id}: {action.action_type}")
        
        try:
            # Check if action requires confirmation
            if action.requires_confirmation and action.retry_count == 0:
                await self._request_confirmation(action, plan)
                return
            
            # Get executor for this action type
            executor = self.action_executors.get(action.action_type)
            if not executor:
                raise ValueError(f"No executor found for action type: {action.action_type}")
            
            # Execute with timeout
            result = await asyncio.wait_for(
                executor(action, plan),
                timeout=action.timeout_seconds
            )
            
            # Mark as completed
            action.status = TaskStatus.COMPLETED
            action.completed_at = datetime.now()
            action.result = result
            
            logger.info(f"Action {action.id} completed successfully")
            
        except asyncio.TimeoutError:
            logger.error(f"Action {action.id} timed out")
            await self._handle_action_failure(action, "Action timed out")
            
        except Exception as e:
            logger.error(f"Action {action.id} failed: {str(e)}")
            await self._handle_action_failure(action, str(e))
    
    async def _handle_action_failure(self, action: Action, error_message: str) -> None:
        """Handle action failure with retry logic."""
        
        action.error = error_message
        action.retry_count += 1
        
        if action.retry_count <= action.max_retries:
            # Reset status for retry
            action.status = TaskStatus.PENDING
            logger.info(f"Retrying action {action.id} (attempt {action.retry_count})")
        else:
            # Mark as failed after max retries
            action.status = TaskStatus.FAILED
            logger.error(f"Action {action.id} failed after {action.max_retries} retries")
    
    async def _request_confirmation(self, action: Action, plan: TaskPlan) -> None:
        """Request user confirmation for high-impact actions."""
        
        action.status = TaskStatus.WAITING_CONFIRMATION
        
        # Store confirmation callback
        confirmation_id = f"{plan.id}:{action.id}"
        self.confirmation_callbacks[confirmation_id] = lambda confirmed: self._handle_confirmation(
            action, plan, confirmed
        )
        
        # Send confirmation request (this would integrate with WhatsApp service)
        confirmation_message = self._generate_confirmation_message(action, plan)
        
        # For now, we'll simulate immediate confirmation for non-critical actions
        # In production, this would send a WhatsApp message and wait for response
        if not self._is_high_impact_action(action):
            await self._handle_confirmation(action, plan, True)
        
        logger.info(f"Confirmation requested for action {action.id}")
    
    async def _handle_confirmation(self, action: Action, plan: TaskPlan, confirmed: bool) -> None:
        """Handle confirmation response."""
        
        if confirmed:
            action.status = TaskStatus.PENDING  # Ready for execution
            logger.info(f"Action {action.id} confirmed by user")
        else:
            action.status = TaskStatus.CANCELLED
            logger.info(f"Action {action.id} cancelled by user")
    
    def _generate_confirmation_message(self, action: Action, plan: TaskPlan) -> str:
        """Generate confirmation message for user."""
        
        action_descriptions = {
            ActionType.CALENDAR_CREATE_EVENT: "create a calendar event",
            ActionType.CALENDAR_DELETE_EVENT: "delete a calendar event",
            ActionType.MESSAGE_SEND_WHATSAPP: "send a WhatsApp message",
            ActionType.MESSAGE_SEND_EMAIL: "send an email",
        }
        
        action_desc = action_descriptions.get(action.action_type, "perform an action")
        
        return f"I'm about to {action_desc}. Should I proceed? (Y/N)"
    
    def _is_high_impact_action(self, action: Action) -> bool:
        """Determine if an action is high-impact and requires confirmation."""
        
        high_impact_actions = {
            ActionType.CALENDAR_DELETE_EVENT,
            ActionType.MESSAGE_SEND_EMAIL,
            ActionType.TASK_DELETE
        }
        
        return action.action_type in high_impact_actions
    
    async def _decompose_intent_to_actions(
        self,
        intent_type: str,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Decompose intent into executable actions."""
        
        actions = []
        
        if intent_type == "calendar_create":
            actions.extend(await self._create_calendar_actions(entities, context, user_id))
        elif intent_type == "calendar_query":
            actions.extend(await self._create_calendar_query_actions(entities, context, user_id))
        elif intent_type == "calendar_delete":
            actions.extend(await self._create_calendar_delete_actions(entities, context, user_id))
        elif intent_type == "task_create":
            actions.extend(await self._create_task_actions(entities, context, user_id))
        elif intent_type == "message_send":
            actions.extend(await self._create_message_actions(entities, context, user_id))
        else:
            # Default action for unknown intents
            actions.append(Action(
                id=str(uuid.uuid4()),
                action_type=ActionType.SYSTEM_NOTIFY,
                parameters={"message": "I'm not sure how to help with that. Could you be more specific?"}
            ))
        
        return actions
    
    async def _create_calendar_actions(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Create actions for calendar event creation."""
        
        actions = []
        
        # Extract event details from entities
        title = entities.get("title", "New Event")
        time_info = entities.get("time", [])
        date_info = entities.get("date", [])
        people = entities.get("people", [])
        location = entities.get("location", [])
        
        # Create calendar event action
        create_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.CALENDAR_CREATE_EVENT,
            parameters={
                "title": title,
                "time": time_info,
                "date": date_info,
                "attendees": people,
                "location": location[0] if location else None,
                "user_id": user_id
            },
            requires_confirmation=True
        )
        actions.append(create_action)
        
        # Add confirmation notification
        notify_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.SYSTEM_NOTIFY,
            parameters={
                "message": f"Calendar event '{title}' has been created successfully."
            },
            dependencies=[create_action.id]
        )
        actions.append(notify_action)
        
        return actions
    
    async def _create_calendar_query_actions(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Create actions for calendar queries."""
        
        actions = []
        
        # Query calendar events
        query_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.CALENDAR_QUERY_EVENTS,
            parameters={
                "user_id": user_id,
                "date_range": entities.get("date", ["today"]),
                "filters": entities
            }
        )
        actions.append(query_action)
        
        return actions
    
    async def _create_calendar_delete_actions(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Create actions for calendar event deletion."""
        
        actions = []
        
        # First query to find the event to delete
        query_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.CALENDAR_QUERY_EVENTS,
            parameters={
                "user_id": user_id,
                "filters": entities
            }
        )
        actions.append(query_action)
        
        # Delete the found event
        delete_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.CALENDAR_DELETE_EVENT,
            parameters={
                "user_id": user_id,
                "event_criteria": entities
            },
            dependencies=[query_action.id],
            requires_confirmation=True
        )
        actions.append(delete_action)
        
        return actions
    
    async def _create_task_actions(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Create actions for task management."""
        
        actions = []
        
        # Create task action
        create_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.TASK_CREATE,
            parameters={
                "title": entities.get("title", "New Task"),
                "description": entities.get("description", ""),
                "due_date": entities.get("date"),
                "priority": Priority.MEDIUM.value,
                "user_id": user_id
            }
        )
        actions.append(create_action)
        
        return actions
    
    async def _create_message_actions(
        self,
        entities: Dict[str, Any],
        context: Dict[str, Any],
        user_id: str
    ) -> List[Action]:
        """Create actions for messaging."""
        
        actions = []
        
        # Send WhatsApp message action
        message_action = Action(
            id=str(uuid.uuid4()),
            action_type=ActionType.MESSAGE_SEND_WHATSAPP,
            parameters={
                "recipient": entities.get("people", [""])[0] if entities.get("people") else "",
                "message": entities.get("message", ""),
                "user_id": user_id
            },
            requires_confirmation=True
        )
        actions.append(message_action)
        
        return actions
    
    def _estimate_action_duration(self, action: Action) -> int:
        """Estimate action duration in minutes."""
        
        duration_map = {
            ActionType.CALENDAR_CREATE_EVENT: 2,
            ActionType.CALENDAR_UPDATE_EVENT: 2,
            ActionType.CALENDAR_DELETE_EVENT: 1,
            ActionType.CALENDAR_QUERY_EVENTS: 1,
            ActionType.TASK_CREATE: 1,
            ActionType.TASK_UPDATE: 1,
            ActionType.TASK_DELETE: 1,
            ActionType.MESSAGE_SEND_WHATSAPP: 1,
            ActionType.MESSAGE_SEND_EMAIL: 2,
            ActionType.SYSTEM_WAIT: 0,
            ActionType.SYSTEM_CONFIRM: 0,
            ActionType.SYSTEM_NOTIFY: 0
        }
        
        return duration_map.get(action.action_type, 1)
    
    # Action executor implementations (placeholders for now)
    async def _execute_calendar_create(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute calendar event creation."""
        # This would integrate with the actual calendar service
        logger.info(f"Creating calendar event: {action.parameters}")
        return {"event_id": str(uuid.uuid4()), "status": "created"}
    
    async def _execute_calendar_update(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute calendar event update."""
        logger.info(f"Updating calendar event: {action.parameters}")
        return {"status": "updated"}
    
    async def _execute_calendar_delete(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute calendar event deletion."""
        logger.info(f"Deleting calendar event: {action.parameters}")
        return {"status": "deleted"}
    
    async def _execute_calendar_query(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute calendar query."""
        logger.info(f"Querying calendar events: {action.parameters}")
        return {"events": [], "count": 0}
    
    async def _execute_task_create(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute task creation."""
        logger.info(f"Creating task: {action.parameters}")
        return {"task_id": str(uuid.uuid4()), "status": "created"}
    
    async def _execute_task_update(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute task update."""
        logger.info(f"Updating task: {action.parameters}")
        return {"status": "updated"}
    
    async def _execute_task_delete(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute task deletion."""
        logger.info(f"Deleting task: {action.parameters}")
        return {"status": "deleted"}
    
    async def _execute_task_complete(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute task completion."""
        logger.info(f"Completing task: {action.parameters}")
        return {"status": "completed"}
    
    async def _execute_task_query(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute task query."""
        logger.info(f"Querying tasks: {action.parameters}")
        return {"tasks": [], "count": 0}
    
    async def _execute_whatsapp_send(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute WhatsApp message sending."""
        logger.info(f"Sending WhatsApp message: {action.parameters}")
        return {"message_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _execute_email_send(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute email sending."""
        logger.info(f"Sending email: {action.parameters}")
        return {"message_id": str(uuid.uuid4()), "status": "sent"}
    
    async def _execute_schedule_reminder(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute reminder scheduling."""
        logger.info(f"Scheduling reminder: {action.parameters}")
        return {"reminder_id": str(uuid.uuid4()), "status": "scheduled"}
    
    async def _execute_system_wait(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute system wait."""
        wait_seconds = action.parameters.get("seconds", 1)
        await asyncio.sleep(wait_seconds)
        return {"waited_seconds": wait_seconds}
    
    async def _execute_system_confirm(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute system confirmation."""
        # This would integrate with the confirmation system
        return {"confirmation_requested": True}
    
    async def _execute_system_notify(self, action: Action, plan: TaskPlan) -> Dict[str, Any]:
        """Execute system notification."""
        message = action.parameters.get("message", "Notification")
        logger.info(f"System notification: {message}")
        return {"message": message, "status": "notified"}
    
    def get_task_plan(self, plan_id: str) -> Optional[TaskPlan]:
        """Get a task plan by ID."""
        return self.active_plans.get(plan_id)
    
    def get_user_task_plans(self, user_id: str) -> List[TaskPlan]:
        """Get all task plans for a user."""
        return [plan for plan in self.active_plans.values() if plan.user_id == user_id]
    
    async def cancel_task_plan(self, plan_id: str) -> bool:
        """Cancel a task plan."""
        if plan_id not in self.active_plans:
            return False
        
        plan = self.active_plans[plan_id]
        plan.status = TaskStatus.CANCELLED
        
        # Cancel all pending actions
        for action in plan.actions:
            if action.status in [TaskStatus.PENDING, TaskStatus.IN_PROGRESS]:
                action.status = TaskStatus.CANCELLED
        
        logger.info(f"Task plan {plan_id} cancelled")
        return True